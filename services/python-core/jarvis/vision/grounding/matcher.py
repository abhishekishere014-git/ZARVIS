"""Semantic element matching engine for Phase 09 Visual Grounding."""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from jarvis.vision.grounding.confidence import calculate_text_similarity
from jarvis.vision.models import (
    ElementType,
    GroundingCandidate,
    VisualElement,
)

TYPE_HINTS = {
    ElementType.BUTTON: ["button", "btn", "press", "click"],
    ElementType.INPUT_TEXT: ["input", "text box", "textbox", "field", "type", "search bar", "url bar", "address bar"],
    ElementType.INPUT_PASSWORD: ["password", "pin", "passcode"],
    ElementType.CHECKBOX: ["checkbox", "check box", "tick"],
    ElementType.RADIO: ["radio", "radio button", "option"],
    ElementType.LINK: ["link", "hyperlink", "anchor"],
    ElementType.ICON: ["icon", "symbol", "glyph", "close", "settings", "gear"],
    ElementType.TAB: ["tab", "page tab"],
    ElementType.MENU_ITEM: ["menu", "item", "option", "dropdown"],
}

_STRIP_WORDS = ["click", "press", "tap", "type", "enter", "select", "the", "a", "an"]
for keywords in TYPE_HINTS.values():
    _STRIP_WORDS.extend(keywords)
_STRIP_PATTERN = re.compile(r"\b(" + "|".join(re.escape(w) for w in _STRIP_WORDS) + r")\b", re.IGNORECASE)


class ElementMatcher:
    """Matches free-form user/agent queries to visual elements."""

    def __init__(self):
        pass

    def extract_type_hints(self, query: str) -> List[ElementType]:
        """Detect element type hints mentioned in the query."""
        q = query.lower()
        matched_types = []
        for el_type, keywords in TYPE_HINTS.items():
            for kw in keywords:
                if re.search(r"\b" + re.escape(kw) + r"\b", q):
                    matched_types.append(el_type)
                    break
        return matched_types

    def clean_query_text(self, query: str) -> str:
        """Strip action words and element type descriptors from query."""
        cleaned = _STRIP_PATTERN.sub("", query)
        return " ".join(cleaned.split())

    def score_element(
        self,
        query: str,
        element: VisualElement,
        clean_text_query: Optional[str] = None,
        type_hints: Optional[List[ElementType]] = None,
    ) -> Tuple[float, str]:
        """Calculate match score [0.0..1.0] and match reason for an element."""
        cleaned_query = query.strip()
        reasons = []

        # 1. Direct ID match
        if cleaned_query.lower() == element.element_id.lower():
            return 1.0, "Exact element_id match"

        # 2. Text similarity across label, ocr_text, placeholder
        sim_label = calculate_text_similarity(cleaned_query, element.label) if element.label else 0.0
        sim_ocr = calculate_text_similarity(cleaned_query, element.ocr_text) if element.ocr_text else 0.0
        sim_placeholder = calculate_text_similarity(cleaned_query, element.placeholder) if element.placeholder else 0.0

        max_text_sim = max(sim_label, sim_ocr, sim_placeholder)

        # Also evaluate similarity with stripped text query if provided
        ctq = clean_text_query if clean_text_query is not None else self.clean_query_text(cleaned_query)
        if ctq and ctq != cleaned_query:
            sim_label_stripped = calculate_text_similarity(ctq, element.label) if element.label else 0.0
            sim_ocr_stripped = calculate_text_similarity(ctq, element.ocr_text) if element.ocr_text else 0.0
            sim_placeholder_stripped = calculate_text_similarity(ctq, element.placeholder) if element.placeholder else 0.0
            max_text_sim = max(max_text_sim, sim_label_stripped, sim_ocr_stripped, sim_placeholder_stripped)

        if max_text_sim >= 0.8:
            reasons.append(f"Strong text match ({max_text_sim:.2f})")
        elif max_text_sim >= 0.4:
            reasons.append(f"Partial text match ({max_text_sim:.2f})")

        # 3. Type hint bonus and mismatch penalty
        hints = type_hints if type_hints is not None else self.extract_type_hints(cleaned_query)
        type_adjustment = 0.0
        if hints:
            if element.element_type in hints:
                type_adjustment = 0.15
                reasons.append(f"Type matches query hint ({element.element_type.value})")
            else:
                # Type penalty when caller explicitly requested another element type
                type_adjustment = -0.20
                reasons.append(f"Type mismatch (requested {hints[0].value}, element is {element.element_type.value})")

        # 4. Attribute / role matching
        attr_bonus = 0.0
        if element.is_clickable and any(w in cleaned_query.lower() for w in ["click", "press", "tap"]):
            attr_bonus += 0.04
            reasons.append("Element is clickable as requested")

        # If query has specific text requirement but text similarity is near zero,
        # don't make unrelated elements match just because of element type
        if ctq and max_text_sim < 0.25:
            return 0.0, "No semantic text correlation"

        # 5. Combine scores
        if max_text_sim >= 0.95:
            total_score = 0.92 + (max_text_sim - 0.95) * 1.0 + type_adjustment + attr_bonus
        elif max_text_sim >= 0.70:
            total_score = 0.75 + (max_text_sim - 0.70) * 0.5 + type_adjustment + attr_bonus
        elif max_text_sim >= 0.35:
            total_score = 0.40 + (max_text_sim - 0.35) * 0.8 + type_adjustment + attr_bonus
        elif hints and element.element_type in hints:
            total_score = 0.45 + type_adjustment + attr_bonus
        else:
            total_score = max_text_sim * 0.4 + type_adjustment

        total_score = min(1.0, max(0.0, total_score * element.confidence))

        reason_str = "; ".join(reasons) if reasons else "Low semantic correlation"
        return total_score, reason_str

    def match(
        self, query: str, elements: List[VisualElement]
    ) -> List[GroundingCandidate]:
        """Score and rank all candidate elements for a given query."""
        clean_text_query = self.clean_query_text(query.strip())
        type_hints = self.extract_type_hints(query.strip())

        candidates: List[GroundingCandidate] = []
        for el in elements:
            score, reason = self.score_element(
                query=query,
                element=el,
                clean_text_query=clean_text_query,
                type_hints=type_hints,
            )
            if score >= 0.30:
                candidates.append(
                    GroundingCandidate(
                        element=el,
                        score=score,
                        match_reason=reason,
                    )
                )

        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates
