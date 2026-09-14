"""Tests for WorkingMemory bounded sliding window and priority eviction."""

from jarvis.memory.config import WorkingMemoryConfig
from jarvis.memory.working.window import WorkingMemory


def test_sliding_window_message_limit_and_overflow_summary() -> None:
    config = WorkingMemoryConfig(max_messages=3, priority_threshold=5)
    wm = WorkingMemory(config)

    wm.append_message(role="user", content="message one", priority=1)
    wm.append_message(role="assistant", content="message two", priority=1)
    wm.append_message(role="user", content="message three", priority=1)

    assert wm.message_count() == 3
    assert wm.summary is None

    # Appending 4th message should evict oldest (message one) and update summary
    wm.append_message(role="assistant", content="message four", priority=1)

    assert wm.message_count() == 3
    recent = wm.get_recent_messages()
    contents = [m.content for m in recent]
    assert "message one" not in contents
    assert "message four" in contents
    assert wm.summary is not None
    assert "message one" in wm.summary


def test_sliding_window_preserves_high_priority() -> None:
    config = WorkingMemoryConfig(max_messages=2, priority_threshold=5)
    wm = WorkingMemory(config)

    # First message has high priority 8
    wm.append_message(role="system", content="vital system instruction", priority=8)
    # Second message has low priority 1
    wm.append_message(role="user", content="casual question", priority=1)

    # Third message arrives with priority 1
    wm.append_message(role="assistant", content="casual answer", priority=1)

    recent = wm.get_recent_messages()
    contents = [m.content for m in recent]
    # High priority message should be preserved, casual question evicted
    assert "vital system instruction" in contents
    assert "casual question" not in contents
    assert "casual answer" in contents


def test_snapshot_and_restore() -> None:
    wm = WorkingMemory()
    wm.set_system_context("Base System Prompt")
    wm.set_task_context("Active Task #42")
    wm.append_message(role="user", content="test message")

    snap = wm.snapshot()
    assert snap.system_context == "Base System Prompt"
    assert snap.active_task_context == "Active Task #42"
    assert len(snap.messages) == 1

    # Clear and restore
    wm.clear()
    assert wm.message_count() == 0

    wm.restore(snap)
    assert wm.system_context == "Base System Prompt"
    assert wm.active_task_context == "Active Task #42"
    assert wm.message_count() == 1
