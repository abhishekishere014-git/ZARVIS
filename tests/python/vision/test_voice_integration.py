"""Integration tests between Phase 07 Voice pipeline and Phase 09 Vision Grounding."""

import pytest
from jarvis.vision.manager import VisionManager
from jarvis.vision.providers.mock import MockVisionProvider
from jarvis.voice.session import VoiceSession, VoiceSessionState


@pytest.mark.asyncio
async def test_voice_command_to_vision_grounding():
    # 1. Simulate voice session with incoming voice command transcript
    session = VoiceSession(session_id="voice_sess_1")
    session.start_listening()
    session.start_processing()

    voice_command_transcript = "click the search button"

    # 2. Vision Manager resolves target for voice command
    provider = MockVisionProvider()
    vision_mgr = VisionManager(provider=provider)

    grounding = await vision_mgr.resolve_target(
        query=voice_command_transcript,
        monitor_index=0,
    )

    assert grounding.element is not None
    assert "Search" in grounding.element.label
    assert grounding.suggested_action == "click"

    # 3. Formulate spoken confirmation feedback
    spoken_feedback = f"Clicking {grounding.element.label} at coordinates {grounding.target_point.x}, {grounding.target_point.y}"
    assert "Clicking Google Search" in spoken_feedback

    session.start_speaking()
    assert session.state == VoiceSessionState.SPEAKING
