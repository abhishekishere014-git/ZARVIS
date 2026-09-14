"""Performance and latency benchmark for the JARVIS Tool Subsystem."""

import time
from pathlib import Path
import pytest
from jarvis.tools.decorator import tool
from jarvis.tools.executor import ToolExecutor
from jarvis.tools.models import ToolPermission, ToolRequest
from jarvis.tools.policy import ToolPolicyEngine
from jarvis.tools.registry import ToolRegistry
from jarvis.tools.sandbox import FileSystemSandbox


@pytest.mark.asyncio
async def test_tool_subsystem_dispatch_latency(tmp_path: Path) -> None:
    sandbox = FileSystemSandbox(workspace_root=tmp_path)
    policy_engine = ToolPolicyEngine(sandbox=sandbox)
    registry = ToolRegistry()

    @tool(tool_id="perf.noop", permissions={ToolPermission.READ})
    async def noop_tool(val: int) -> int:
        return val * 2

    registry.register_tool(noop_tool)
    executor = ToolExecutor(registry=registry, policy_engine=policy_engine, sandbox=sandbox)

    # Warmup
    await executor.execute(ToolRequest(tool_id="perf.noop", arguments={"val": 1}))

    # Benchmark 100 iterations
    iterations = 100
    start = time.perf_counter()
    for i in range(iterations):
        res = await executor.execute(ToolRequest(tool_id="perf.noop", arguments={"val": i}))
        assert res.is_success is True
    total_time = time.perf_counter() - start

    avg_latency_ms = (total_time / iterations) * 1000.0
    print(f"\n[PERF] Tool dispatch overhead: {avg_latency_ms:.3f} ms / call across {iterations} iterations")

    # Overhead must be well below 2ms
    assert avg_latency_ms < 2.0, f"Tool dispatch overhead {avg_latency_ms:.3f}ms exceeds 2.0ms threshold"
