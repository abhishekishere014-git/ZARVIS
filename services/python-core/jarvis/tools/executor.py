"""Supervised ToolExecutor managing validation, policy checks, sandboxing, timeouts, and auditing."""

import asyncio
import inspect
import logging
import time
from typing import Any, Dict, List, Optional
from jarvis.core.bus import AsyncEventBus
from jarvis.protocol.models import JarvisEvent
from jarvis.tools.audit import AuditLogger
from jarvis.tools.errors import (
    ArtifactVerificationError,
    ResourceLimitExceededError,
    SandboxViolationError,
    ToolError,
    ToolNotFoundError,
)
from jarvis.tools.models import (
    ToolExecutionContext,
    ToolExecutionStatus,
    ToolRequest,
    ToolResult,
)
from jarvis.tools.permissions import SecurityProfile
from jarvis.tools.policy import ToolPolicyEngine
from jarvis.tools.registry import ToolRegistry
from jarvis.tools.sandbox import FileSystemSandbox

logger = logging.getLogger("jarvis.tools.executor")


class ToolExecutor:
    """Supervised execution pipeline orchestrating policy, isolation, timeouts, and auditing."""

    def __init__(
        self,
        registry: ToolRegistry,
        policy_engine: ToolPolicyEngine,
        sandbox: FileSystemSandbox,
        event_bus: Optional[AsyncEventBus] = None,
        audit_logger: Optional[AuditLogger] = None,
    ) -> None:
        self.registry = registry
        self.policy_engine = policy_engine
        self.sandbox = sandbox
        self.event_bus = event_bus
        self.audit_logger = audit_logger or AuditLogger()

    async def _emit_event(
        self,
        event_type: str,
        execution_id: str,
        tool_id: str,
        correlation_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Publishes lifecycle events to the shared AsyncEventBus if active."""
        if not self.event_bus or not self.event_bus.is_running:
            return

        data = {
            "execution_id": execution_id,
            "tool_id": tool_id,
            **(payload or {}),
        }
        event = JarvisEvent(
            id=f"evt_{execution_id}_{event_type.replace('.', '_')}",
            type=event_type,
            correlation_id=correlation_id,
            payload=data,
        )
        try:
            await self.event_bus.publish(event)
        except Exception as exc:
            logger.warning("Failed to publish event '%s': %s", event_type, exc)

    def _validate_arguments(self, schema: Dict[str, Any], arguments: Dict[str, Any]) -> Optional[str]:
        """Validates that required schema properties are provided in arguments."""
        required_fields = schema.get("required", [])
        missing = [field for field in required_fields if field not in arguments]
        if missing:
            return f"Missing required arguments: {missing}"
        return None

    async def execute(
        self,
        request: ToolRequest,
        caller_profile: Optional[SecurityProfile] = None,
    ) -> ToolResult:
        """Executes a tool request through the supervised sandbox pipeline."""
        start_time = time.perf_counter()
        tool_version = "unknown"

        await self._emit_event(
            event_type="tool.requested",
            execution_id=request.execution_id,
            tool_id=request.tool_id,
            correlation_id=request.correlation_id,
            payload={"caller": request.caller},
        )

        # 1. Resolve tool in registry
        try:
            tool_def = self.registry.get(request.tool_id)
            handler = self.registry.get_handler(request.tool_id)
            tool_version = tool_def.version
        except ToolNotFoundError as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            await self._emit_event(
                event_type="tool.failed",
                execution_id=request.execution_id,
                tool_id=request.tool_id,
                correlation_id=request.correlation_id,
                payload={"error": str(exc)},
            )
            self.audit_logger.record_event(
                execution_id=request.execution_id,
                tool_id=request.tool_id,
                tool_version=tool_version,
                actor=request.caller,
                policy_decision="tool_not_found",
                duration_ms=duration_ms,
                status=ToolExecutionStatus.FAILED,
                correlation_id=request.correlation_id,
                arguments=request.arguments,
                error_code="TOOL_NOT_FOUND",
            )
            return ToolResult(
                execution_id=request.execution_id,
                tool_id=request.tool_id,
                status=ToolExecutionStatus.FAILED,
                error=str(exc),
                duration_ms=duration_ms,
            )

        # 2. Evaluate Policy
        decision = self.policy_engine.evaluate(tool_def, request, caller_profile)
        if not decision.allowed or decision.approval_required:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            reason = decision.reason
            if decision.approval_required:
                reason = f"User approval required for high-risk operation: {reason}"

            await self._emit_event(
                event_type="tool.denied",
                execution_id=request.execution_id,
                tool_id=request.tool_id,
                correlation_id=request.correlation_id,
                payload={"reason": reason, "risk_level": decision.risk_level.value},
            )
            self.audit_logger.record_event(
                execution_id=request.execution_id,
                tool_id=request.tool_id,
                tool_version=tool_version,
                actor=request.caller,
                policy_decision="denied",
                duration_ms=duration_ms,
                status=ToolExecutionStatus.DENIED,
                correlation_id=request.correlation_id,
                arguments=request.arguments,
                error_code="POLICY_DENIED",
            )
            return ToolResult(
                execution_id=request.execution_id,
                tool_id=request.tool_id,
                status=ToolExecutionStatus.DENIED,
                error=reason,
                duration_ms=duration_ms,
            )

        await self._emit_event(
            event_type="tool.authorized",
            execution_id=request.execution_id,
            tool_id=request.tool_id,
            correlation_id=request.correlation_id,
        )

        # 3. Argument Validation
        arg_error = self._validate_arguments(tool_def.input_schema, request.arguments)
        if arg_error:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            await self._emit_event(
                event_type="tool.failed",
                execution_id=request.execution_id,
                tool_id=request.tool_id,
                correlation_id=request.correlation_id,
                payload={"error": arg_error},
            )
            self.audit_logger.record_event(
                execution_id=request.execution_id,
                tool_id=request.tool_id,
                tool_version=tool_version,
                actor=request.caller,
                policy_decision="validation_failed",
                duration_ms=duration_ms,
                status=ToolExecutionStatus.FAILED,
                correlation_id=request.correlation_id,
                arguments=request.arguments,
                error_code="INVALID_ARGUMENTS",
            )
            return ToolResult(
                execution_id=request.execution_id,
                tool_id=request.tool_id,
                status=ToolExecutionStatus.FAILED,
                error=arg_error,
                duration_ms=duration_ms,
            )

        # 4. Build Execution Context
        context = ToolExecutionContext(
            execution_id=request.execution_id,
            tool_id=request.tool_id,
            correlation_id=request.correlation_id,
            caller=request.caller,
            workspace_dir=self.sandbox.workspace_root,
            sandbox=self.sandbox,
            timeout_seconds=tool_def.timeout_seconds,
        )

        # 5. Invoke Handler with Timeout and Sandbox Confinement
        await self._emit_event(
            event_type="tool.started",
            execution_id=request.execution_id,
            tool_id=request.tool_id,
            correlation_id=request.correlation_id,
        )

        # Inspect if handler accepts `context`
        sig = inspect.signature(handler)
        call_kwargs = dict(request.arguments)
        if "context" in sig.parameters:
            call_kwargs["context"] = context

        status = ToolExecutionStatus.SUCCESS
        output_payload: Any = None
        error_msg: Optional[str] = None
        error_code: Optional[str] = None
        artifacts: List[str] = []

        try:
            coro = handler(**call_kwargs)
            if inspect.iscoroutine(coro):
                output_payload = await asyncio.wait_for(coro, timeout=tool_def.timeout_seconds)
            else:
                # Run synchronous handler in default threadpool if needed
                loop = asyncio.get_running_loop()
                output_payload = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: handler(**call_kwargs)),
                    timeout=tool_def.timeout_seconds,
                )

            # Check if output provides artifact paths
            if isinstance(output_payload, dict) and "artifacts" in output_payload:
                artifacts = list(output_payload["artifacts"])
            elif isinstance(output_payload, dict) and "artifact" in output_payload:
                artifacts = [output_payload["artifact"]]

        except asyncio.TimeoutError:
            status = ToolExecutionStatus.TIMEOUT
            error_msg = f"Execution timed out after {tool_def.timeout_seconds}s"
            error_code = "TIMEOUT"
            await self._emit_event(
                event_type="tool.timeout",
                execution_id=request.execution_id,
                tool_id=request.tool_id,
                correlation_id=request.correlation_id,
                payload={"error": error_msg},
            )
        except SandboxViolationError as exc:
            status = ToolExecutionStatus.FAILED
            error_msg = f"Sandbox violation: {exc}"
            error_code = "SANDBOX_VIOLATION"
            await self._emit_event(
                event_type="tool.failed",
                execution_id=request.execution_id,
                tool_id=request.tool_id,
                correlation_id=request.correlation_id,
                payload={"error": error_msg},
            )
        except ResourceLimitExceededError as exc:
            status = ToolExecutionStatus.FAILED
            error_msg = f"Resource limit exceeded: {exc}"
            error_code = "RESOURCE_LIMIT_EXCEEDED"
            await self._emit_event(
                event_type="tool.failed",
                execution_id=request.execution_id,
                tool_id=request.tool_id,
                correlation_id=request.correlation_id,
                payload={"error": error_msg},
            )
        except ArtifactVerificationError as exc:
            status = ToolExecutionStatus.FAILED
            error_msg = f"Artifact structural verification failed: {exc}"
            error_code = "VERIFICATION_FAILED"
            await self._emit_event(
                event_type="tool.failed",
                execution_id=request.execution_id,
                tool_id=request.tool_id,
                correlation_id=request.correlation_id,
                payload={"error": error_msg},
            )
        except Exception as exc:
            status = ToolExecutionStatus.FAILED
            error_msg = f"Execution error: {exc}"
            error_code = "EXECUTION_ERROR"
            await self._emit_event(
                event_type="tool.failed",
                execution_id=request.execution_id,
                tool_id=request.tool_id,
                correlation_id=request.correlation_id,
                payload={"error": error_msg},
            )

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        if status == ToolExecutionStatus.SUCCESS:
            await self._emit_event(
                event_type="tool.completed",
                execution_id=request.execution_id,
                tool_id=request.tool_id,
                correlation_id=request.correlation_id,
                payload={"artifacts": artifacts, "duration_ms": duration_ms},
            )

        # 6. Audit Logging
        self.audit_logger.record_event(
            execution_id=request.execution_id,
            tool_id=request.tool_id,
            tool_version=tool_version,
            actor=request.caller,
            policy_decision="allowed",
            duration_ms=duration_ms,
            status=status,
            correlation_id=request.correlation_id,
            arguments=request.arguments,
            error_code=error_code,
            artifacts=artifacts,
        )

        return ToolResult(
            execution_id=request.execution_id,
            tool_id=request.tool_id,
            status=status,
            output=output_payload,
            error=error_msg,
            duration_ms=duration_ms,
            artifacts=artifacts,
        )
