"""Window enumeration, discovery, targeting, and state management."""

import logging
import re
from typing import List, Optional
from jarvis.os.errors import WindowAmbiguityError, WindowNotFoundError
from jarvis.os.models import WindowAction, WindowInfo, WindowQuery
from jarvis.os.providers.base import OSProvider

logger = logging.getLogger("jarvis.os.window.manager")


class WindowManager:
    """Controls desktop window enumeration, deterministic targeting, and state changes."""

    def __init__(self, provider: OSProvider) -> None:
        self.provider = provider

    def list_windows(self) -> List[WindowInfo]:
        """Lists all currently visible desktop application windows."""
        return self.provider.list_windows()

    def get_foreground_window(self) -> Optional[WindowInfo]:
        """Returns the currently active foreground window."""
        return self.provider.get_foreground_window()

    def find_window(self, query: WindowQuery) -> WindowInfo:
        """Finds a window matching query criteria, ensuring unambiguous resolution."""
        windows = self.list_windows()
        matches: List[WindowInfo] = []

        for win in windows:
            title_match = True
            proc_match = True

            if query.title_pattern:
                if query.exact_match:
                    title_match = win.title.lower() == query.title_pattern.lower()
                else:
                    title_match = query.title_pattern.lower() in win.title.lower()

            if query.process_name:
                proc_match = query.process_name.lower() in win.process_name.lower()

            if title_match and proc_match:
                matches.append(win)

        if not matches:
            raise WindowNotFoundError(
                f"No window matched query: title_pattern='{query.title_pattern}', process_name='{query.process_name}'"
            )

        if len(matches) > 1:
            candidate_details = [
                {"handle_id": w.handle_id, "title": w.title, "process_id": w.process_id}
                for w in matches
            ]
            raise WindowAmbiguityError(
                f"Multiple windows ({len(matches)}) matched query: '{query.title_pattern}'. Ambiguous resolution prohibited.",
                details={"matches": candidate_details, "query": query.model_dump()},
            )

        return matches[0]

    def set_foreground(self, handle_id: int) -> bool:
        """Brings the window to the foreground."""
        return self.provider.set_foreground_window(handle_id)

    focus_window = set_foreground

    def set_state(self, handle_id: int, action: WindowAction) -> bool:
        """Applies a state modification (FOCUS, MINIMIZE, MAXIMIZE, RESTORE)."""
        return self.provider.set_window_state(handle_id, action)

    def minimize_window(self, handle_id: int) -> bool:
        return self.set_state(handle_id, WindowAction.MINIMIZE)

    def maximize_window(self, handle_id: int) -> bool:
        return self.set_state(handle_id, WindowAction.MAXIMIZE)

    def restore_window(self, handle_id: int) -> bool:
        return self.set_state(handle_id, WindowAction.RESTORE)
