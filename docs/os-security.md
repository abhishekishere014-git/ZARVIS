# Phase 08 — Windows OS Automation Security & Safety Architecture

## 1. Zero Arbitrary Execution Mandate
Phase 08 strictly complies with JARVIS Security Directives:
- **No Arbitrary Shell Execution**: `shell=True`, `eval()`, `exec()`, `os.system()`, and raw command prompts are completely absent and structurally forbidden.
- **Audited Tool Envelopes**: All desktop automation functions are implemented as typed tools registered in Phase 04 `ToolRegistry`, subject to validation by `ToolPolicyEngine`.
- **Typed Parameter Contracts**: All inputs are validated via Pydantic v2 schemas before reaching OS provider drivers.

## 2. Coordinate Validation & Containment
All screen and window coordinates undergo boundary checks in `OSSecurityManager.validate_coordinates`:
- `CoordinateSpace.SCREEN`: Validated against virtual desktop bounding rectangle `[virtual_x, virtual_x + virtual_width) x [virtual_y, virtual_y + virtual_height)`. Out-of-bounds coordinates raise `CoordinatesOutOfBoundsError` / `OSSecurityError`.
- `CoordinateSpace.MONITOR`: Validated against designated monitor physical resolution and transformed to desktop space.
- `CoordinateSpace.WINDOW`: Validated against target window client boundaries `[0, width) x [0, height)` and translated to desktop space.

## 3. Keyboard Input Allowlist & Safeguards
- Single keys and hotkeys are restricted to the `SUPPORTED_KEYS` allowlist. Arbitrary scan codes or injected binary controls are rejected.
- Hotkey sequences are bounded between 2 and 4 keys.
- Text typing length is bounded to `keyboard_max_type_length` (default 500 characters).

## 4. Privacy & Sensitive Data Protection
- **Temporary Screenshot Storage**: All screenshots are written strictly into the sandboxed temporary directory `data/workspace/temp/screens/`. Filenames are sanitized and checked against path traversal (`..`, absolute paths, symlinks).
- **Redaction from Logs and Events**:
  - `OSSecurityManager.scrub_telemetry_payload` omits raw screenshot bytes (`[OMITTED_SCREENSHOT_DATA]`) and clipboard/password text (`[OMITTED_SENSITIVE_TEXT]`).
  - Regex heuristic scanners detect API keys (`sk-...`, `ghp_...`, `Bearer ...`, `password: ...`) and redact them with `[REDACTED_SECRET]`.
  - Clipboard write responses do not echo written contents.

## 5. Human-in-the-Loop Approval Policies
- Destructive mouse clicks (`is_destructive=True`) and sensitive text typing (`is_sensitive=True` or heuristic match) require explicit authorization (`ApprovalMode.USER_APPROVAL`) from the policy engine.
