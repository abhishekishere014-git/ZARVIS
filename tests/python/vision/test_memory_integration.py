"""Integration tests between Phase 06 Tri-Tier Memory and Phase 09 Vision Grounding."""

import pytest
from jarvis.memory.working.window import WorkingMemory
from jarvis.vision.manager import VisionManager
from jarvis.vision.providers.mock import MockVisionProvider


@pytest.mark.asyncio
async def test_vision_grounding_stored_in_sliding_window_memory():
    working_memory = WorkingMemory()
    provider = MockVisionProvider()
    vision_mgr = VisionManager(provider=provider)

    # 1. Resolve visual target
    res = await vision_mgr.resolve_target("Google Search", monitor_index=0)

    # 2. Add visual grounding record to working memory
    working_memory.append_message(
        role="assistant",
        content=f"Grounded '{res.query}' to element '{res.element.element_id}' at ({res.target_point.x}, {res.target_point.y})",
        metadata={
            "observation_id": res.observation_id,
            "element_id": res.element.element_id,
            "coordinates": res.target_point.to_dict(),
        },
    )

    # 3. Retrieve context from buffer for next turn
    messages = working_memory.get_recent_messages()
    assert len(messages) == 1
    assert "elem_search_btn" in messages[0].content
    assert messages[0].metadata["coordinates"] == {"x": 560, "y": 338}
