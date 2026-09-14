"""Human-in-the-loop approval manager for high-risk autonomous agent operations."""

import logging
from typing import Dict, List, Optional
from jarvis.agents.models import AgentApprovalRequest

logger = logging.getLogger("jarvis.agents.approval")


class ApprovalManager:
    """Manages pending, approved, and denied human-in-the-loop authorization requests."""

    def __init__(self) -> None:
        self._pending_requests: Dict[str, AgentApprovalRequest] = {}
        self._history: Dict[str, AgentApprovalRequest] = {}

    def create_request(
        self,
        run_id: str,
        task_id: str,
        agent_id: str,
        tool_id: str,
        reason: str,
        risk_level: str,
        arguments: Optional[Dict[str, any]] = None,
    ) -> AgentApprovalRequest:
        """Creates a pending authorization request."""
        req = AgentApprovalRequest(
            run_id=run_id,
            task_id=task_id,
            agent_id=agent_id,
            tool_id=tool_id,
            reason=reason,
            risk_level=risk_level,
            arguments=arguments or {},
        )
        self._pending_requests[req.approval_id] = req
        self._history[req.approval_id] = req
        logger.info(
            "Approval requested [%s]: tool='%s' risk='%s' agent='%s' reason='%s'",
            req.approval_id[:8],
            tool_id,
            risk_level,
            agent_id,
            reason,
        )
        return req

    def resolve_request(
        self,
        approval_id: str,
        approved: bool,
        resolved_by: str = "user",
    ) -> AgentApprovalRequest:
        """Explicitly resolves a pending authorization request. Never accepts self-approval."""
        if approval_id not in self._pending_requests:
            raise KeyError(f"Approval request '{approval_id}' is not pending.")

        req = self._pending_requests.pop(approval_id)
        req.approved = approved
        req.resolved_by = resolved_by
        self._history[approval_id] = req

        logger.info(
            "Approval [%s] resolved: approved=%s by='%s'",
            approval_id[:8],
            approved,
            resolved_by,
        )
        return req

    def get_request(self, approval_id: str) -> Optional[AgentApprovalRequest]:
        """Retrieves an approval request by ID."""
        return self._history.get(approval_id)

    def list_pending(self, run_id: Optional[str] = None) -> List[AgentApprovalRequest]:
        """Lists pending requests, optionally filtered by run_id."""
        requests = list(self._pending_requests.values())
        if run_id:
            requests = [r for r in requests if r.run_id == run_id]
        return requests
