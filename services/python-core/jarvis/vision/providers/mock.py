"""Mock Vision Provider for deterministic testing in headless/CI environments."""

from __future__ import annotations

import time
import uuid
from typing import Any, List, Optional

from jarvis.vision.errors import VisionProviderError
from jarvis.vision.models import (
    BoundingBox,
    ElementType,
    RegionType,
    ScreenObservation,
    ScreenRegion,
    VisualElement,
)
from jarvis.vision.providers.base import VisionProvider


class MockVisionProvider:
    """Deterministic, configurable mock vision provider."""

    def __init__(self, simulate_failure: bool = False):
        self.simulate_failure = simulate_failure
        self._custom_elements: List[VisualElement] = []
        self._custom_regions: List[ScreenRegion] = []
        self._custom_active_window: Optional[str] = "Google Chrome - Search"
        self._custom_raw_text: str = ""

    def reset(self) -> None:
        """Reset custom elements and failure flags."""
        self._custom_elements.clear()
        self._custom_regions.clear()
        self.simulate_failure = False
        self._custom_active_window = "Google Chrome - Search"
        self._custom_raw_text = ""

    def add_element(self, element: VisualElement) -> None:
        """Add an element to the mock provider output."""
        self._custom_elements.append(element)

    def add_region(self, region: ScreenRegion) -> None:
        """Add a region to the mock provider output."""
        self._custom_regions.append(region)

    def set_active_window(self, title: str) -> None:
        """Set the active window title."""
        self._custom_active_window = title

    def set_raw_text(self, text: str) -> None:
        """Set raw OCR text."""
        self._custom_raw_text = text

    def _generate_default_desktop(
        self, width: int, height: int, monitor_index: int = 0
    ) -> tuple[List[VisualElement], List[ScreenRegion], str]:
        """Generate a standard realistic virtual desktop environment."""
        x_offset = monitor_index * 1920

        # Region: Browser Window
        browser_region_id = f"reg_browser_{monitor_index}"
        browser_region = ScreenRegion(
            region_id=browser_region_id,
            region_type=RegionType.WINDOW,
            bounds=BoundingBox(x=x_offset + 100, y=50, width=1200, height=800),
            title="Google Chrome - Search",
            is_focused=True,
        )

        # Region: Taskbar
        taskbar_region_id = f"reg_taskbar_{monitor_index}"
        taskbar_region = ScreenRegion(
            region_id=taskbar_region_id,
            region_type=RegionType.TOOLBAR,
            bounds=BoundingBox(x=x_offset, y=height - 40, width=width, height=40),
            title="Windows Taskbar",
            is_focused=False,
        )

        # Region: Login Dialog (for sensitive testing)
        login_region_id = f"reg_login_{monitor_index}"
        login_region = ScreenRegion(
            region_id=login_region_id,
            region_type=RegionType.FORM,
            bounds=BoundingBox(x=x_offset + 400, y=400, width=400, height=300),
            title="Account Login",
            is_sensitive=True,
        )

        elements = [
            # In browser window
            VisualElement(
                element_id="elem_url_bar",
                element_type=ElementType.INPUT_TEXT,
                bounds=BoundingBox(x=x_offset + 200, y=80, width=800, height=32),
                label="Address Bar",
                ocr_text="https://www.google.com",
                placeholder="Search or enter web address",
                confidence=0.98,
                parent_region_id=browser_region_id,
            ),
            VisualElement(
                element_id="elem_search_input",
                element_type=ElementType.INPUT_TEXT,
                bounds=BoundingBox(x=x_offset + 350, y=250, width=500, height=44),
                label="Search Box",
                ocr_text="",
                placeholder="Search Google or type a URL",
                confidence=0.95,
                parent_region_id=browser_region_id,
            ),
            VisualElement(
                element_id="elem_search_btn",
                element_type=ElementType.BUTTON,
                bounds=BoundingBox(x=x_offset + 500, y=320, width=120, height=36),
                label="Google Search",
                ocr_text="Google Search",
                confidence=0.99,
                parent_region_id=browser_region_id,
            ),
            VisualElement(
                element_id="elem_lucky_btn",
                element_type=ElementType.BUTTON,
                bounds=BoundingBox(x=x_offset + 640, y=320, width=140, height=36),
                label="I'm Feeling Lucky",
                ocr_text="I'm Feeling Lucky",
                confidence=0.92,
                parent_region_id=browser_region_id,
            ),
            VisualElement(
                element_id="elem_settings_btn",
                element_type=ElementType.BUTTON,
                bounds=BoundingBox(x=x_offset + 1220, y=60, width=32, height=32),
                label="Settings",
                ocr_text="Settings",
                confidence=0.90,
                parent_region_id=browser_region_id,
            ),
            VisualElement(
                element_id="elem_close_btn",
                element_type=ElementType.BUTTON,
                bounds=BoundingBox(x=x_offset + 1260, y=55, width=35, height=30),
                label="Close window",
                ocr_text="X",
                confidence=0.97,
                parent_region_id=browser_region_id,
            ),
            # In Taskbar
            VisualElement(
                element_id="elem_start_btn",
                element_type=ElementType.BUTTON,
                bounds=BoundingBox(x=x_offset + 5, y=height - 35, width=30, height=30),
                label="Start Menu",
                ocr_text="Start",
                confidence=0.99,
                parent_region_id=taskbar_region_id,
            ),
            VisualElement(
                element_id="elem_clock_txt",
                element_type=ElementType.TEXT,
                bounds=BoundingBox(x=x_offset + width - 90, y=height - 35, width=80, height=30),
                label="System Clock",
                ocr_text="12:00 PM",
                confidence=0.88,
                parent_region_id=taskbar_region_id,
            ),
            # Sensitive form elements
            VisualElement(
                element_id="elem_username_field",
                element_type=ElementType.INPUT_TEXT,
                bounds=BoundingBox(x=x_offset + 420, y=430, width=360, height=34),
                label="Username",
                ocr_text="admin@zarvis.local",
                placeholder="Enter username",
                confidence=0.95,
                parent_region_id=login_region_id,
            ),
            VisualElement(
                element_id="elem_password_field",
                element_type=ElementType.INPUT_PASSWORD,
                bounds=BoundingBox(x=x_offset + 420, y=480, width=360, height=34),
                label="Password",
                ocr_text="s3cr3tP@ss!",
                placeholder="Enter password",
                confidence=0.96,
                is_sensitive=True,
                parent_region_id=login_region_id,
            ),
            VisualElement(
                element_id="elem_login_btn",
                element_type=ElementType.BUTTON,
                bounds=BoundingBox(x=x_offset + 420, y=530, width=120, height=36),
                label="Sign In",
                ocr_text="Sign In",
                confidence=0.94,
                parent_region_id=login_region_id,
            ),
        ]

        regions = [browser_region, taskbar_region, login_region]
        for reg in regions:
            reg.element_ids = [el.element_id for el in elements if el.parent_region_id == reg.region_id]

        return elements, regions, "Google Chrome - Search"

    async def analyze_screen(
        self,
        screenshot_path: str,
        screen_width: int,
        screen_height: int,
        monitor_index: int = 0,
    ) -> ScreenObservation:
        """Extract elements and regions from screen."""
        if self.simulate_failure:
            raise VisionProviderError("Simulated vision provider failure in MockVisionProvider")

        default_elements, default_regions, active_window = self._generate_default_desktop(
            screen_width, screen_height, monitor_index
        )

        elements = list(default_elements) + list(self._custom_elements)
        regions = list(default_regions) + list(self._custom_regions)
        active_win = self._custom_active_window or active_window

        # Aggregate raw OCR text
        raw_texts = [el.ocr_text for el in elements if el.ocr_text]
        raw_text = self._custom_raw_text or "\n".join(raw_texts)

        return ScreenObservation(
            observation_id=f"obs_{uuid.uuid4().hex[:8]}",
            timestamp=time.time(),
            screenshot_path=screenshot_path,
            image_width=screen_width,
            image_height=screen_height,
            monitor_index=monitor_index,
            elements=elements,
            regions=regions,
            active_window_title=active_win,
            is_stale=False,
            raw_text=raw_text,
            metadata={"provider": "mock", "screenshot": screenshot_path},
        )

    async def health_check(self) -> bool:
        """Health check returns True unless simulate_failure is True."""
        return not self.simulate_failure
