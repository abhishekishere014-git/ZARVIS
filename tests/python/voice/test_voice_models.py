"""Unit tests for Voice & Audio domain models and contracts."""

import pytest
from jarvis.voice.models import (
    AudioChunk,
    AudioEncoding,
    AudioFormat,
    AudioMetadata,
    STTConfidence,
    STTRequest,
    STTResult,
    Transcript,
    TranscriptSegment,
    TTSRequest,
    TTSResult,
    VADResult,
    VoiceRequest,
    VoiceResponse,
    VoiceSessionState,
)


def test_audio_format_calculations():
    fmt = AudioFormat(sample_rate=16000, channels=1, sample_width=2)
    assert fmt.bytes_per_second == 32000
    assert fmt.frame_size == 2

    stereo_fmt = AudioFormat(sample_rate=48000, channels=2, sample_width=2)
    assert stereo_fmt.bytes_per_second == 192000
    assert stereo_fmt.frame_size == 4


def test_transcript_confidence_tiers():
    assert STTConfidence.from_score(0.95) == STTConfidence.HIGH
    assert STTConfidence.from_score(0.80) == STTConfidence.HIGH
    assert STTConfidence.from_score(0.79) == STTConfidence.MEDIUM
    assert STTConfidence.from_score(0.50) == STTConfidence.MEDIUM
    assert STTConfidence.from_score(0.49) == STTConfidence.LOW
    assert STTConfidence.from_score(0.0) == STTConfidence.LOW


def test_transcript_construction_and_methods():
    seg1 = TranscriptSegment(text="hello", start_sec=0.0, end_sec=0.5, confidence=0.9)
    seg2 = TranscriptSegment(text="jarvis", start_sec=0.5, end_sec=1.0, confidence=0.85)

    transcript = Transcript(
        text="hello jarvis",
        segments=[seg1, seg2],
        language="en",
        confidence=0.875,
        is_final=True,
    )
    assert transcript.text == "hello jarvis"
    assert len(transcript.segments) == 2
    assert transcript.confidence_tier == STTConfidence.HIGH
    assert transcript.is_final is True


def test_voice_request_and_response_contracts():
    transcript = Transcript(text="what is the time?", confidence=0.92)
    v_req = VoiceRequest(
        transcript=transcript,
        language="en",
        confidence=0.92,
    )
    assert v_req.text == "what is the time?"
    assert v_req.session_id.startswith("vses_")
    assert v_req.correlation_id.startswith("vcorr_")

    v_resp = VoiceResponse(
        session_id=v_req.session_id,
        correlation_id=v_req.correlation_id,
        text="It is 5:00 PM",
        agent_status="completed",
        duration_sec=1.5,
    )
    assert v_resp.session_id == v_req.session_id
    assert v_resp.text == "It is 5:00 PM"
    assert v_resp.agent_status == "completed"


def test_stt_result_conversion_to_transcript():
    res = STTResult(
        text="open word",
        segments=[TranscriptSegment(text="open word", start_sec=0.0, end_sec=0.8, confidence=0.95)],
        language="en",
        confidence=0.95,
        provider="mock",
    )
    tr = res.to_transcript()
    assert tr.text == "open word"
    assert tr.confidence == 0.95
    assert tr.raw_text == "open word"
