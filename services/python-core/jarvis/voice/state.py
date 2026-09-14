"""Deterministic state machine governing voice conversation lifecycles."""

import logging
from typing import Callable, Dict, List, Optional, Set
from jarvis.voice.errors import VoiceStateError
from jarvis.voice.models import VoiceSessionState

logger = logging.getLogger("jarvis.voice.state")


class VoiceStateMachine:
    """Enforces valid state transitions and triggers listener callbacks."""

    # Explicit transition graph
    VALID_TRANSITIONS: Dict[VoiceSessionState, Set[VoiceSessionState]] = {
        VoiceSessionState.IDLE: {
            VoiceSessionState.LISTENING,
            VoiceSessionState.PROCESSING,
            VoiceSessionState.ERROR,
        },
        VoiceSessionState.LISTENING: {
            VoiceSessionState.PROCESSING,
            VoiceSessionState.IDLE,
            VoiceSessionState.ERROR,
        },
        VoiceSessionState.PROCESSING: {
            VoiceSessionState.SPEAKING,
            VoiceSessionState.IDLE,
            VoiceSessionState.ERROR,
        },
        VoiceSessionState.SPEAKING: {
            VoiceSessionState.IDLE,
            VoiceSessionState.INTERRUPTED,
            VoiceSessionState.ERROR,
        },
        VoiceSessionState.INTERRUPTED: {
            VoiceSessionState.LISTENING,
            VoiceSessionState.IDLE,
            VoiceSessionState.ERROR,
        },
        VoiceSessionState.ERROR: {VoiceSessionState.IDLE},
    }

    def __init__(self, initial_state: VoiceSessionState = VoiceSessionState.IDLE) -> None:
        self._current_state = initial_state
        self._listeners: List[Callable[[VoiceSessionState, VoiceSessionState], None]] = []

    @property
    def current_state(self) -> VoiceSessionState:
        return self._current_state

    def add_listener(
        self, callback: Callable[[VoiceSessionState, VoiceSessionState], None]
    ) -> None:
        """Registers a callback invoked upon state transition (old_state, new_state)."""
        self._listeners.append(callback)

    def transition_to(self, new_state: VoiceSessionState) -> None:
        """Transitions to new_state if the transition is allowed."""
        if new_state == self._current_state:
            return

        allowed = self.VALID_TRANSITIONS.get(self._current_state, set())
        if new_state not in allowed:
            err_msg = (
                f"Invalid voice state transition: '{self._current_state.value}' -> '{new_state.value}'. "
                f"Allowed target states: {[s.value for s in allowed]}"
            )
            logger.error(err_msg)
            raise VoiceStateError(
                err_msg,
                details={"from_state": self._current_state.value, "to_state": new_state.value},
            )

        old_state = self._current_state
        self._current_state = new_state
        logger.debug("Voice state: %s -> %s", old_state.value, new_state.value)

        for listener in self._listeners:
            try:
                listener(old_state, new_state)
            except Exception as exc:
                logger.warning("Listener callback failed during transition %s->%s: %s", old_state, new_state, exc)

    def reset(self) -> None:
        """Safely resets the state machine back to IDLE."""
        if self._current_state != VoiceSessionState.IDLE:
            self._current_state = VoiceSessionState.IDLE
