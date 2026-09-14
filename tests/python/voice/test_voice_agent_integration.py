"""Integration tests between Voice Pipeline and Phase 05 Agent Runtime."""

from unittest.mock import AsyncMock, MagicMock
import pytest
from jarvis.agents.models import AgentFinalResponse, AgentState
from jarvis.agents.orchestrator import AgentOrchestrator
from jarvis.voice.audio.capture import AudioCapture
from jarvis.voice.audio.playback import AudioPlayback
from jarvis.voice.audio.virtual import VirtualAudioCapture, VirtualAudioPlayback
from jarvis.voice.config import VoiceConfig
from jarvis.voice.models import AudioFormat
from jarvis.voice.pipeline import VoicePipeline
from jarvis.voice.stt.mock import MockSTTProvider
from jarvis.voice.stt.router import STTRouter
from jarvis.voice.tts.mock import MockTTSProvider
from jarvis.voice.vad.base import VADSegmenter
from jarvis.voice.vad.mock import MockVAD


@pytest.mark.asyncio
async def test_voice_calls_agent_orchestrator():
    fmt = AudioFormat(sample_rate=16000)
    capture = AudioCapture(audio_format=fmt, virtual_backend=VirtualAudioCapture(fmt))
    playback = AudioPlayback(audio_format=fmt, virtual_backend=VirtualAudioPlayback())

    vad = MockVAD()
    segmenter = VADSegmenter(vad_provider=vad, audio_format=fmt)

    stt = MockSTTProvider(default_text="Draft an executive summary")
    router = STTRouter(providers={"mock": stt}, fastpath_provider="mock", accurate_provider="mock")
    tts = MockTTSProvider()

    # Mock AgentOrchestrator
    mock_orchestrator = MagicMock(spec=AgentOrchestrator)
    mock_orchestrator.run = AsyncMock(
        return_value=AgentFinalResponse(
            run_id="run_123",
            goal_id="goal_123",
            status=AgentState.COMPLETED,
            summary="The executive summary has been drafted and verified.",
            task_statistics={"total": 2, "completed": 2},
        )
    )

    config = VoiceConfig()
    pipeline = VoicePipeline(
        config=config,
        capture=capture,
        playback=playback,
        vad_segmenter=segmenter,
        stt_router=router,
        tts_provider=tts,
        orchestrator=mock_orchestrator,
    )

    resp = await pipeline.process_speech(audio_bytes=b"\x00" * 3200)

    # Verify orchestrator was called with user's transcribed goal
    mock_orchestrator.run.assert_awaited_once_with("Draft an executive summary")
    assert resp.text == "The executive summary has been drafted and verified."
    assert resp.agent_status == "completed"
    assert tts.synthesize_count == 1
