"""Data models and schemas for JARVIS Phase 09 Vision Subsystem."""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field, model_validator

from jarvis.vision.errors import InvalidBoundingBoxError


class ElementType(str, Enum):
    """Types of visual elements detectable on screen."""
    BUTTON = "button"
    INPUT_TEXT = "input_text"
    INPUT_PASSWORD = "input_password"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    LINK = "link"
    ICON = "icon"
    TAB = "tab"
    MENU_ITEM = "menu_item"
    HEADING = "heading"
    TEXT = "text"
    IMAGE = "image"
    WINDOW = "window"
    MODAL = "modal"
    SCROLLBAR = "scrollbar"
    UNKNOWN = "unknown"


class RegionType(str, Enum):
    """Types of semantic screen regions."""
    WINDOW = "window"
    MODAL = "modal"
    TOOLBAR = "toolbar"
    SIDEBAR = "sidebar"
    STATUS_BAR = "status_bar"
    CONTENT_AREA = "content_area"
    FORM = "form"
    SENSITIVE = "sensitive"


class ConfidenceLevel(str, Enum):
    """Categorical confidence rating for grounding matches."""
    HIGH = "high"        # >= 0.85: Safe for autonomous action
    MEDIUM = "medium"    # 0.60 - 0.84: Usable with confirmation/fallback
    LOW = "low"          # < 0.60: Rejected/unreliable


class VisionPoint(BaseModel):
    """2D screen coordinate in virtual desktop pixels."""
    x: int
    y: int

    def to_tuple(self) -> tuple[int, int]:
        return (self.x, self.y)

    def to_dict(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y}


class BoundingBox(BaseModel):
    """Rectangle bounding box on screen."""
    x: int
    y: int
    width: int
    height: int

    @model_validator(mode="after")
    def validate_bounds(self) -> BoundingBox:
        if self.width < 0 or self.height < 0:
            raise InvalidBoundingBoxError(
                f"Bounding box width ({self.width}) and height ({self.height}) must be non-negative"
            )
        return self

    @property
    def left(self) -> int:
        return self.x

    @property
    def top(self) -> int:
        return self.y

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    @property
    def center(self) -> VisionPoint:
        return VisionPoint(
            x=self.x + self.width // 2,
            y=self.y + self.height // 2,
        )

    @property
    def area(self) -> int:
        return self.width * self.height

    def contains(self, point: VisionPoint) -> bool:
        return self.left <= point.x <= self.right and self.top <= point.y <= self.bottom

    def intersects(self, other: BoundingBox) -> bool:
        return not (
            self.right < other.left
            or self.left > other.right
            or self.bottom < other.top
            or self.top > other.bottom
        )

    def intersection(self, other: BoundingBox) -> Optional[BoundingBox]:
        if not self.intersects(other):
            return None
        ix = max(self.left, other.left)
        iy = max(self.top, other.top)
        iw = max(0, min(self.right, other.right) - ix)
        ih = max(0, min(self.bottom, other.bottom) - iy)
        return BoundingBox(x=ix, y=iy, width=iw, height=ih)

    def iou(self, other: BoundingBox) -> float:
        inter = self.intersection(other)
        if not inter:
            return 0.0
        inter_area = inter.area
        union_area = self.area + other.area - inter_area
        return inter_area / union_area if union_area > 0 else 0.0

    def to_dict(self) -> dict[str, int]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "center_x": self.center.x,
            "center_y": self.center.y,
        }


class VisualElement(BaseModel):
    """An individual visual element detected on screen."""
    element_id: str = Field(default_factory=lambda: f"elem_{uuid.uuid4().hex[:8]}")
    element_type: ElementType = ElementType.UNKNOWN
    bounds: BoundingBox
    label: str = ""
    ocr_text: str = ""
    placeholder: Optional[str] = None
    confidence: float = 1.0
    is_clickable: bool = True
    is_focusable: bool = False
    is_sensitive: bool = False
    parent_region_id: Optional[str] = None
    attributes: dict[str, Any] = Field(default_factory=dict)

    @property
    def center(self) -> VisionPoint:
        return self.bounds.center

    @property
    def display_text(self) -> str:
        return self.label or self.ocr_text or self.placeholder or ""

    def to_summary(self) -> dict[str, Any]:
        return {
            "element_id": self.element_id,
            "element_type": self.element_type.value,
            "bounds": self.bounds.to_dict(),
            "center": self.center.to_dict(),
            "label": self.label,
            "ocr_text": self.ocr_text,
            "confidence": self.confidence,
            "is_clickable": self.is_clickable,
            "is_sensitive": self.is_sensitive,
        }


class ScreenRegion(BaseModel):
    """A semantic region grouping multiple elements."""
    region_id: str = Field(default_factory=lambda: f"reg_{uuid.uuid4().hex[:8]}")
    region_type: RegionType = RegionType.WINDOW
    bounds: BoundingBox
    title: str = ""
    is_focused: bool = False
    is_sensitive: bool = False
    element_ids: List[str] = Field(default_factory=list)

    def to_summary(self) -> dict[str, Any]:
        return {
            "region_id": self.region_id,
            "region_type": self.region_type.value,
            "bounds": self.bounds.to_dict(),
            "title": self.title,
            "is_focused": self.is_focused,
            "is_sensitive": self.is_sensitive,
            "element_count": len(self.element_ids),
        }


class ScreenObservation(BaseModel):
    """A point-in-time visual snapshot with detected elements and regions."""
    observation_id: str = Field(default_factory=lambda: f"obs_{uuid.uuid4().hex[:8]}")
    timestamp: float = Field(default_factory=time.time)
    screenshot_path: Optional[str] = None
    image_width: int = 1920
    image_height: int = 1080
    monitor_index: int = 0
    elements: List[VisualElement] = Field(default_factory=list)
    regions: List[ScreenRegion] = Field(default_factory=list)
    active_window_title: Optional[str] = None
    is_stale: bool = False
    raw_text: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    def age(self, current_time: Optional[float] = None) -> float:
        now = current_time if current_time is not None else time.time()
        return max(0.0, now - self.timestamp)

    def check_staleness(self, ttl_sec: float, current_time: Optional[float] = None) -> bool:
        stale = self.age(current_time) > ttl_sec
        self.is_stale = stale
        return stale

    def find_by_id(self, element_id: str) -> Optional[VisualElement]:
        for el in self.elements:
            if el.element_id == element_id:
                return el
        return None

    def find_at_point(self, point: VisionPoint) -> List[VisualElement]:
        return [el for el in self.elements if el.bounds.contains(point)]

    def find_in_region(self, region_id: str) -> List[VisualElement]:
        return [el for el in self.elements if el.parent_region_id == region_id]

    def to_summary(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "timestamp": self.timestamp,
            "age_seconds": round(self.age(), 2),
            "is_stale": self.is_stale,
            "dimensions": {"width": self.image_width, "height": self.image_height},
            "monitor_index": self.monitor_index,
            "element_count": len(self.elements),
            "region_count": len(self.regions),
            "active_window": self.active_window_title,
        }


class GroundingCandidate(BaseModel):
    """A scored candidate matching a semantic query."""
    element: VisualElement
    score: float
    match_reason: str


class GroundingResult(BaseModel):
    """The resolved spatial target for a semantic query."""
    query: str
    element: VisualElement
    target_point: VisionPoint
    confidence: float
    confidence_level: ConfidenceLevel
    observation_id: str
    candidates: List[GroundingCandidate] = Field(default_factory=list)
    is_ambiguous: bool = False
    suggested_action: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "element_id": self.element.element_id,
            "element_type": self.element.element_type.value,
            "target_point": self.target_point.to_dict(),
            "confidence": round(self.confidence, 4),
            "confidence_level": self.confidence_level.value,
            "observation_id": self.observation_id,
            "is_ambiguous": self.is_ambiguous,
            "candidate_count": len(self.candidates),
            "bounds": self.element.bounds.to_dict(),
            "suggested_action": self.suggested_action,
        }
