"""Voice session management, barge-in handling, and turn coordination."""

import asyncio
import logging
import uuid
from typing import List, Optional
from jarvis.voice.errors import VoiceInterruptedError
from jarvis.voice.models import VoiceRequest, VoiceResponse, VoiceSessionState
from jarvis.voice.state import VoiceStateMachine

logger = logging.getLogger("jarvis.voice.session")


class VoiceSession:
    """Manages an active conversational voice interaction."""

    def __init__(self, session_id: Optional[str] = None) -> None:
        self.session_id = session_id or f"vses_{uuid.uuid4().hex[:12]}"
        self.state_machine = VoiceStateMachine()
        self.active_playback_task: Optional[asyncio.Task] = None
        self.history: List[tuple[VoiceRequest, VoiceResponse]] = []
        self._interrupted = False

    @property
    def state(self) -> VoiceSessionState:
        return self.state_machine.current_state

    def start_listening(self) -> None:
        """Transitions into LISTENING state."""
        self._interrupted = False
        self.state_machine.transition_to(VoiceSessionState.LISTENING)

    def start_processing(self) -> None:
        """Transitions into PROCESSING state."""
        self.state_machine.transition_to(VoiceSessionState.PROCESSING)

    def start_speaking(self, playback_task: Optional[asyncio.Task] = None) -> None:
        """Transitions into SPEAKING state and tracks the playback task."""
        self.active_playback_task = playback_task
        self.state_machine.transition_to(VoiceSessionState.SPEAKING)

    def complete_turn(self, request: VoiceRequest, response: VoiceResponse) -> None:
        """Completes the turn and returns to IDLE state."""
        self.history.append((request, response))
        self.active_playback_task = None
        if self.state != VoiceSessionState.IDLE:
            self.state_machine.transition_to(VoiceSessionState.IDLE)

    def interrupt(self) -> None:
        """Executes barge-in interruption: stops playback and transitions to INTERRUPTED."""
        if self.state == VoiceSessionState.SPEAKING:
            logger.info("Barge-in triggered: interrupting active speech playback for session %s", self.session_id)
            self._interrupted = True
            if self.active_playback_task and not self.active_playback_task.done():
                self.active_playback_task.cancel()
            self.active_playback_task = None
            self.state_machine.transition_to(VoiceSessionState.INTERRUPTED)

    def fail(self, reason: str = "") -> None:
        """Transitions into ERROR state on unhandled exception."""
        logger.error("Session %s failed: %s", self.session_id, reason)
        self.state_machine.transition_to(VoiceSessionState.ERROR)

    def reset(self) -> None:
        """Resets the session state back to IDLE."""
        if self.active_playback_task and not self.active_playback_task.done():
            self.active_playback_task.cancel()
        self.active_playback_task = None
        self.state_machine.reset()
        self._interrupted = False
