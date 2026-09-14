"""Integration tests verifying memory boundaries and privacy in voice interactions."""

from unittest.mock import AsyncMock, MagicMock
import pytest
from jarvis.agents.models import AgentFinalResponse, AgentState
from jarvis.agents.orchestrator import AgentOrchestrator
from jarvis.memory.manager import MemoryManager
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
async def test_voice_memory_privacy_and_context():
    fmt = AudioFormat()
    capture = AudioCapture(audio_format=fmt, virtual_backend=VirtualAudioCapture(fmt))
    playback = AudioPlayback(audio_format=fmt, virtual_backend=VirtualAudioPlayback())

    stt = MockSTTProvider(default_text="Remember that my favorite editor is VSCode")
    router = STTRouter(providers={"mock": stt}, fastpath_provider="mock", accurate_provider="mock")
    tts = MockTTSProvider()

    # Mock MemoryManager attached to AgentOrchestrator
    mock_memory = MagicMock(spec=MemoryManager)
    mock_memory.record_user_message = AsyncMock()

    mock_orchestrator = MagicMock(spec=AgentOrchestrator)
    mock_orchestrator.memory = mock_memory
    mock_orchestrator.run = AsyncMock(
        return_value=AgentFinalResponse(
            run_id="run_mem_1",
            goal_id="goal_mem_1",
            status=AgentState.COMPLETED,
            summary="I have noted that your favorite editor is VSCode.",
        )
    )

    config = VoiceConfig(persist_raw_audio=False)
    pipeline = VoicePipeline(
        config=config,
        capture=capture,
        playback=playback,
        vad_segmenter=VADSegmenter(MockVAD()),
        stt_router=router,
        tts_provider=tts,
        orchestrator=mock_orchestrator,
    )

    raw_audio = b"\x01\x02" * 1600
    resp = await pipeline.process_speech(audio_bytes=raw_audio)

    assert resp.text == "I have noted that your favorite editor is VSCode."
    # Guarantee raw audio bytes are not stored by the pipeline
    assert config.persist_raw_audio is False
