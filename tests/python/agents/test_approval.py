"""Tests for human-in-the-loop ApprovalManager."""

import pytest
from jarvis.agents.approval import ApprovalManager


def test_approval_manager_request_and_resolution() -> None:
    mgr = ApprovalManager()

    req = mgr.create_request(
        run_id="run_100",
        task_id="task_delete",
        agent_id="agent.coding",
        tool_id="system.format_drive",
        reason="Dangerous disk action",
        risk_level="critical",
    )

    assert req.approved is None
    assert len(mgr.list_pending()) == 1
    assert mgr.get_request(req.approval_id) is req

    # Resolve approval
    resolved = mgr.resolve_request(req.approval_id, approved=True, resolved_by="admin_user")
    assert resolved.approved is True
    assert resolved.resolved_by == "admin_user"
    assert len(mgr.list_pending()) == 0


def test_approval_manager_rejects_unknown_id() -> None:
    mgr = ApprovalManager()
    with pytest.raises(KeyError):
        mgr.resolve_request("fake_id", approved=True)
