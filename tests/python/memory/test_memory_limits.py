"""Tests for bounded memory capacity limits and oversized payloads."""

from jarvis.memory.config import WorkingMemoryConfig
from jarvis.memory.working.window import WorkingMemory


def test_working_memory_hard_message_bound() -> None:
    config = WorkingMemoryConfig(max_messages=10)
    wm = WorkingMemory(config)

    for i in range(25):
        wm.append_message(role="user", content=f"message {i}")

    # Must never exceed configured boundary
    assert wm.message_count() <= 10


def test_working_memory_hard_token_bound() -> None:
    # 100 tokens max limit (~400 characters)
    config = WorkingMemoryConfig(max_messages=100, max_estimated_tokens=100)
    wm = WorkingMemory(config)

    for i in range(10):
        # Each message ~100 characters (~25 tokens)
        wm.append_message(role="user", content="x" * 100)

    assert wm.total_tokens() <= 100
