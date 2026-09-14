"""Unit tests for VoiceSession and VoiceStateMachine."""

import asyncio
import pytest
from jarvis.voice.errors import VoiceStateError
from jarvis.voice.models import (
    Transcript,
    VoiceRequest,
    VoiceResponse,
    VoiceSessionState,
)
from jarvis.voice.session import VoiceSession
from jarvis.voice.state import VoiceStateMachine


def test_state_machine_valid_transitions():
    sm = VoiceStateMachine()
    assert sm.current_state == VoiceSessionState.IDLE

    sm.transition_to(VoiceSessionState.LISTENING)
    assert sm.current_state == VoiceSessionState.LISTENING

    sm.transition_to(VoiceSessionState.PROCESSING)
    assert sm.current_state == VoiceSessionState.PROCESSING

    sm.transition_to(VoiceSessionState.SPEAKING)
    assert sm.current_state == VoiceSessionState.SPEAKING

    sm.transition_to(VoiceSessionState.IDLE)
    assert sm.current_state == VoiceSessionState.IDLE


def test_state_machine_invalid_transition_raises():
    sm = VoiceStateMachine()
    # Direct jump from IDLE to SPEAKING is forbidden
    with pytest.raises(VoiceStateError):
        sm.transition_to(VoiceSessionState.SPEAKING)


def test_state_machine_listeners():
    sm = VoiceStateMachine()
    transitions = []

    def on_change(old_state, new_state):
        transitions.append((old_state, new_state))

    sm.add_listener(on_change)
    sm.transition_to(VoiceSessionState.LISTENING)
    sm.transition_to(VoiceSessionState.IDLE)

    assert len(transitions) == 2
    assert transitions[0] == (VoiceSessionState.IDLE, VoiceSessionState.LISTENING)
    assert transitions[1] == (VoiceSessionState.LISTENING, VoiceSessionState.IDLE)


@pytest.mark.asyncio
async def test_session_barge_in_cancellation():
    session = VoiceSession()
    session.start_listening()
    session.start_processing()

    # Simulate long playback task
    async def dummy_playback():
        await asyncio.sleep(10.0)

    task = asyncio.create_task(dummy_playback())
    session.start_speaking(task)
    assert session.state == VoiceSessionState.SPEAKING

    # Trigger barge-in
    session.interrupt()
    assert session.state == VoiceSessionState.INTERRUPTED
    await asyncio.sleep(0.01)
    assert task.cancelled()


def test_session_complete_turn():
    session = VoiceSession()
    session.start_listening()
    session.start_processing()
    session.start_speaking()

    req = VoiceRequest(transcript=Transcript(text="hi"))
    resp = VoiceResponse(session_id=session.session_id, correlation_id="c1", text="hello")
    session.complete_turn(req, resp)

    assert session.state == VoiceSessionState.IDLE
    assert len(session.history) == 1
