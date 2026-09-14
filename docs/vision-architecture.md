# Vision, Screen Understanding & Visual Grounding Layer Architecture

## Overview
Phase 09 introduces the **Visual Grounding and Perception Subsystem** to JARVIS. This layer acts as the "eyes" of the assistant, providing semantic understanding of visual displays and spatial mapping from natural language queries to pixel coordinates, without executing physical actions directly.

```
       [Screen Capture / Window / Monitor]
                       │
                       ▼
             [ScreenAnalyzer / OCR]
                       │
                       ▼
          [ScreenObservation Snapshot]
         (Elements, Regions, BoundingBoxes)
                       │
                       ▼
               [ElementMatcher]
    (Semantic similarity, type hints, ranking)
                       │
                       ▼
               [TargetResolver]
  (Staleness check, ambiguity gating, coordinate grounding)
                       │
                       ▼
               [GroundingResult]
          (Screen coordinates & Action hint)
                       │
                       ▼
        [Phase 08 Controlled OS Automation]
     (os.mouse.click, os.keyboard.type, etc.)
```

## Architectural Principles
1. **Perception-Action Separation**: Phase 09 provides vision analysis and spatial grounding only. All physical interactions remain mediated through Phase 08 tools (`os.mouse.click`, `os.keyboard.type`).
2. **Deterministic Virtual Mocking**: `MockVisionProvider` simulates full multi-monitor virtual desktop environments with browser windows, search inputs, buttons, and sensitive forms for headless/CI testing.
3. **Observation Staleness Guard**: Every observation carries a creation timestamp and a TTL (default 15.0s). Attempting to ground against an observation older than TTL raises `StaleObservationError`.
4. **Ambiguity Prevention**: If two candidate elements match a query with close confidence (score delta $\le 0.08$), `TargetAmbiguityError` is raised unless `allow_ambiguous=True`.
5. **Coordinate Space Parity**: Coordinates match Phase 08's `SCREEN` space virtual desktop bounding rect spanning all physical monitors.
