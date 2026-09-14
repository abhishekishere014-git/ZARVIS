"""Mouse pointer positioning, clicking, and wheel scrolling."""

import logging
from typing import Optional, Tuple
from jarvis.os.errors import MouseActionError, OSPolicyViolationError
from jarvis.os.models import CoordinateSpace, MouseButton, MouseClickRequest, MouseMoveRequest, MouseScrollRequest, WindowInfo
from jarvis.os.providers.base import OSProvider
from jarvis.os.security import OSSecurityManager

logger = logging.getLogger("jarvis.os.input.mouse")


class MouseManager:
    """Manages pointer movements and click actions with coordinate validation."""

    def __init__(
        self,
        provider: OSProvider,
        security_manager: Optional[OSSecurityManager] = None,
        security: Optional[OSSecurityManager] = None,
        require_approval_for_destructive: bool = True,
        **kwargs,
    ) -> None:
        self.provider = provider
        sec = security or security_manager
        if sec is None:
            sec = OSSecurityManager(screens_temp_dir="temp/screens")
        self.security = sec
        self.require_approval_for_destructive = require_approval_for_destructive

    def get_position(self) -> Tuple[int, int]:
        return self.provider.get_cursor_pos()

    def move(
        self,
        request: MouseMoveRequest,
        target_window: Optional[WindowInfo] = None,
    ) -> Tuple[int, int]:
        """Moves cursor to validated coordinates."""
        screen_info = self.provider.get_screen_info()
        target_x, target_y = self.security.validate_coordinates(
            x=request.x,
            y=request.y,
            screen_info=screen_info,
            coordinate_space=request.coordinate_space,
            target_window=target_window,
            target_monitor_id=request.monitor_id,
        )

        self.provider.move_cursor(target_x, target_y)
        return target_x, target_y

    def click(
        self,
        request: MouseClickRequest,
        target_window: Optional[WindowInfo] = None,
        approved: bool = False,
    ) -> Tuple[int, int]:
        """Executes mouse click, enforcing destructive operation policies."""
        if request.is_destructive and self.require_approval_for_destructive and not approved:
            raise OSPolicyViolationError(
                "Destructive mouse click action requires explicit user approval before execution."
            )

        if request.x is not None and request.y is not None:
            screen_info = self.provider.get_screen_info()
            target_x, target_y = self.security.validate_coordinates(
                x=request.x,
                y=request.y,
                screen_info=screen_info,
                coordinate_space=request.coordinate_space,
                target_window=target_window,
            )
            self.provider.move_cursor(target_x, target_y)
        else:
            target_x, target_y = self.provider.get_cursor_pos()

        self.provider.mouse_click(button=request.button, clicks=request.clicks)
        return target_x, target_y

    def scroll(self, request: MouseScrollRequest) -> None:
        """Executes mouse wheel scroll."""
        if request.x is not None and request.y is not None:
            screen_info = self.provider.get_screen_info()
            tx, ty = self.security.validate_coordinates(
                x=request.x,
                y=request.y,
                screen_info=screen_info,
                coordinate_space=CoordinateSpace.SCREEN,
            )
            self.provider.move_cursor(tx, ty)

        self.provider.mouse_scroll(request.clicks)
        return request.clicks
