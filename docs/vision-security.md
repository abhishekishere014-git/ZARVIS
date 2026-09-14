# Vision Subsystem Security & Privacy Specification

## Threat Model & Protective Controls
Visual inspection introduces unique privacy and security risks:
1. **Accidental Exposure of Credentials**: Passwords, API keys, and private tokens visible on screen.
2. **Coordinate Drift / Blind Clicks**: Grounding outdated screenshots or guessing ambiguous elements leading to unintended clicks.
3. **Prompt Injection / Arbitrary Execution**: Malicious strings in query text attempting shell execution or SQL injection.

## Security Architecture

### 1. VisionSecurityManager
`VisionSecurityManager` provides automatic screening and redaction:
- **Sensitive Keyword Detection**: Matches against sensitive patterns (`password`, `api_key`, `token`, `secret`, `cvv`, `ssn`, `private_key`).
- **Element Redaction**:
  - `INPUT_PASSWORD` fields: OCR text replaced with `********`, label replaced with `[PASSWORD FIELD]`.
  - Sensitive labels/placeholders: Replaced with `[REDACTED_LABEL]` or `[REDACTED_PLACEHOLDER]`.
- **Telemetry Scrubbing**: All telemetry events emitted to `AsyncEventBus` (`vision.observation.captured`, `vision.target.grounded`, `vision.target.ambiguous`) are sanitized.

### 2. Coordinate Boundary Validation
- All resolved targets are validated against screen bounding rectangles.
- Negative coordinates or points exceeding monitor boundaries raise `VisionError`.

### 3. Execution Safety Guarantees
- Zero use of `eval()`, `exec()`, `os.system()`, or `shell=True`.
- Visual queries are treated purely as text comparison strings.
