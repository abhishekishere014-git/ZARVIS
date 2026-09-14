"""Tests for Voice subsystem integration with OS Automation actions."""

import pytest
from jarvis.os.manager import OSAutomationManager
from jarvis.os.models import ScreenCaptureRequest
from jarvis.os.providers.mock import MockOSProvider
from jarvis.voice.models import Transcript, VoiceRequest, VoiceResponse


@pytest.mark.asyncio
async def test_voice_command_triggers_os_capture(tmp_path):
    provider = MockOSProvider()
    os_mgr = OSAutomationManager(provider=provider, workspace_root=tmp_path)

    # Simulating parsed voice command
    voice_req = VoiceRequest(
        transcript=Transcript(text="Jarvis, take a screenshot of my screen", confidence=0.95),
        session_id="voice_session_42",
    )

    # Simulated router maps intent to os.screen.capture
    if "screenshot" in voice_req.transcript.text.lower():
        req = ScreenCaptureRequest(image_format="png")
        cap_res = os_mgr.screen.capture(req)
        response = VoiceResponse(
            text=f"Screenshot captured and saved to {cap_res.image_path}.",
            session_id=voice_req.session_id,
            correlation_id="corr_voice_42",
        )

    assert "Screenshot captured" in response.text
    assert cap_res.width == 1920
    assert cap_res.height == 1080


@pytest.mark.asyncio
async def test_voice_command_triggers_window_focus(tmp_path):
    provider = MockOSProvider()
    os_mgr = OSAutomationManager(provider=provider, workspace_root=tmp_path)

    voice_req = VoiceRequest(
        transcript=Transcript(text="Switch to Calculator", confidence=0.98),
        session_id="voice_session_43",
    )

    if "calculator" in voice_req.transcript.text.lower():
        calc_win = os_mgr.window.find_window(
            type("Query", (), {"title": "Calculator", "title_pattern": "Calculator", "process_name": None, "exact_match": False})()
        )
        focused = os_mgr.window.focus_window(calc_win.handle_id)
        response = VoiceResponse(
            text=f"Focused {calc_win.title}." if focused else "Failed to focus.",
            session_id=voice_req.session_id,
            correlation_id="corr_voice_43",
        )

    assert response.text == "Focused Calculator."
    fg = os_mgr.window.get_foreground_window()
    assert fg is not None
    assert fg.handle_id == 1001
