"""Confidence scoring and threshold calibration for Phase 09 Visual Grounding."""

from __future__ import annotations

from jarvis.vision.models import ConfidenceLevel


def calculate_text_similarity(query_text: str, target_text: str) -> float:
    """Calculate normalized similarity ratio between two text strings [0.0..1.0]."""
    if not query_text or not target_text:
        return 0.0

    q = query_text.strip().lower()
    t = target_text.strip().lower()

    if q == t:
        return 1.0

    # Exact substring match bonus
    if q in t:
        return 0.90 + 0.10 * (len(q) / len(t))
    if t in q:
        return 0.85 + 0.10 * (len(t) / len(q))

    # Token overlap (Jaccard similarity on words)
    q_words = set(q.split())
    t_words = set(t.split())
    if q_words and t_words:
        intersection = q_words.intersection(t_words)
        if intersection:
            jaccard = len(intersection) / len(q_words.union(t_words))
            return 0.70 + (jaccard * 0.25)

    # Fast character bigram Dice coefficient for fuzzy matching (O(N) vs O(N*M))
    if len(q) < 2 or len(t) < 2:
        return 0.0

    q_bigrams = {q[i : i + 2] for i in range(len(q) - 1)}
    t_bigrams = {t[i : i + 2] for i in range(len(t) - 1)}
    common = q_bigrams.intersection(t_bigrams)
    if not common:
        return 0.0

    dice = (2.0 * len(common)) / (len(q_bigrams) + len(t_bigrams))
    return dice if dice >= 0.3 else 0.0


def categorize_confidence(
    score: float,
    high_threshold: float = 0.85,
    medium_threshold: float = 0.60,
) -> ConfidenceLevel:
    """Categorize numerical confidence score into ConfidenceLevel enum."""
    if score >= high_threshold:
        return ConfidenceLevel.HIGH
    elif score >= medium_threshold:
        return ConfidenceLevel.MEDIUM
    else:
        return ConfidenceLevel.LOW
