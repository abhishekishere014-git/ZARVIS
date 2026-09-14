"""Heuristic classification and adversarial injection detection for memory persistence."""

import re
from typing import Optional, Tuple
from jarvis.memory.errors import MemoryPoisoningError
from jarvis.memory.models import MemoryScope, MemoryType, TrustLevel

# Conversational non-durable filler phrases
TRIVIAL_PHRASES = {
    "hello", "hi", "hey", "good morning", "good evening", "ok", "okay",
    "thanks", "thank you", "sure", "got it", "yes", "no", "bye", "cool",
    "great", "done", "alright", "fine", "test", "ping"
}

# Adversarial prompt injection signatures
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"(?i)ignore\s+(all\s+)?previous\s+instructions"),
    re.compile(r"(?i)system\s*prompt\s*override"),
    re.compile(r"(?i)you\s+are\s+now\s+(in\s+)?(dan|jailbreak|unrestricted|god)\s+mode"),
    re.compile(r"(?i)disregard\s+(the\s+)?system\s+rules"),
    re.compile(r"(?i)always\s+execute\s+.*whenever\b"),
    re.compile(r"(?i)override\s+(security|sandbox|policy)"),
    re.compile(r"(?i)<\s*system\s*>.*<\s*/\s*system\s*>"),
]


class MemoryClassifier:
    """Evaluates memory-worthiness, classifies memory types, and detects adversarial poisoning."""

    @classmethod
    def is_memory_worthy(cls, content: str) -> bool:
        """Determines if content contains substantive information worth persisting."""
        stripped = content.strip().lower()
        if len(stripped) < 4:
            return False
        if stripped in TRIVIAL_PHRASES:
            return False
        return True

    @classmethod
    def detect_injection(cls, content: str) -> bool:
        """Checks if content attempts prompt injection or policy subversion."""
        for pattern in PROMPT_INJECTION_PATTERNS:
            if pattern.search(content):
                return True
        return False

    @classmethod
    def classify(
        cls,
        content: str,
        source: str = "user",
        explicit_type: Optional[MemoryType] = None,
        explicit_scope: Optional[MemoryScope] = None,
    ) -> Tuple[MemoryType, MemoryScope, TrustLevel, float]:
        """Classifies content into MemoryType, Scope, TrustLevel, and Importance.

        Raises:
            MemoryPoisoningError: If untrusted input attempts to establish permanent system rules.
        """
        is_injection = cls.detect_injection(content)

        # Assign Trust Level
        source_lower = source.lower()
        if is_injection:
            trust_level = TrustLevel.UNTRUSTED
            if source_lower not in ("system", "admin"):
                raise MemoryPoisoningError(
                    f"Adversarial memory injection attempt detected in source '{source}'. Content rejected."
                )
        elif source_lower in ("system", "developer"):
            trust_level = TrustLevel.SYSTEM
        elif source_lower in ("user", "human"):
            trust_level = TrustLevel.USER_VERIFIED
        else:
            trust_level = TrustLevel.MODEL_GENERATED

        # Detect Memory Type if not explicitly provided
        lowered = content.lower()
        if explicit_type:
            mem_type = explicit_type
        elif any(k in lowered for k in ("prefer", "preference", "favorite", "always use", "never use", "my theme", "i like")):
            mem_type = MemoryType.PREFERENCE
        elif any(k in lowered for k in ("project", "architecture", "repository", "codebase", "monorepo")):
            mem_type = MemoryType.PROJECT
        elif any(k in lowered for k in ("task", "todo", "assigned", "action item")):
            mem_type = MemoryType.TASK
        elif any(k in lowered for k in ("summary", "overview", "recap")):
            mem_type = MemoryType.SUMMARY
        else:
            mem_type = MemoryType.FACT

        # Detect Scope if not explicitly provided
        if explicit_scope:
            scope = explicit_scope
        elif mem_type == MemoryType.PREFERENCE:
            scope = MemoryScope.USER
        elif mem_type == MemoryType.PROJECT:
            scope = MemoryScope.PROJECT
        else:
            scope = MemoryScope.CONVERSATION

        # Estimate Base Importance (0.0 to 1.0)
        if mem_type == MemoryType.PREFERENCE:
            importance = 0.85
        elif mem_type == MemoryType.PROJECT:
            importance = 0.80
        elif mem_type == MemoryType.FACT:
            importance = 0.65
        elif mem_type == MemoryType.TASK:
            importance = 0.60
        else:
            importance = 0.50

        return mem_type, scope, trust_level, importance
