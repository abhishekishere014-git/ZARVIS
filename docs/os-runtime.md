# Phase 08 — Windows OS Automation Runtime Guide

## 1. Module Layout
The OS automation runtime is housed under `services/python-core/jarvis/os`:
- `models.py`: Pydantic v2 schemas and enums (`ScreenCaptureRequest`, `MouseMoveRequest`, `WindowInfo`, etc.).
- `config.py`: `OSAutomationConfig` dataclass with configurable thresholds, timeouts, and directories.
- `errors.py`: Error taxonomy (`OSAutomationError`, `WindowAmbiguityError`, `CoordinatesOutOfBoundsError`, etc.).
- `security.py`: `OSSecurityManager` coordinate validation, key allowlists, and secret redaction.
- `manager.py`: `OSAutomationManager` orchestrating all subsystems and emitting scrubbed `JarvisEvent`s over `AsyncEventBus`.
- `providers/`:
  - `base.py`: `OSProvider` Protocol contract.
  - `windows.py`: Native `WindowsOSProvider` using ctypes and Pillow.
  - `mock.py`: Virtual `MockOSProvider` for deterministic headless CI execution.
- `screen/`: `ScreenCaptureManager` and `MonitorManager`.
- `input/`: `MouseManager` and `KeyboardManager`.
- `window/`: `WindowManager`.
- `clipboard/`: `ClipboardManager`.
- `system/`: `SystemInfoManager`.
- `verification/`: `OSActionVerifier`.
- `tools/`: 20 typed `@tool` functions and `register_os_tools(registry, os_manager)`.

## 2. Registering OS Tools with Phase 04 ToolRegistry
```python
from jarvis.tools.factory import build_tool_system
from jarvis.os.manager import OSAutomationManager
from jarvis.os.tools.registration import register_os_tools

tool_system = build_tool_system(workspace_dir=workspace_path)
os_manager = OSAutomationManager(workspace_root=workspace_path)
register_os_tools(tool_system.registry, os_manager=os_manager)
```

## 3. Registered Tool Suite (20 Tools)
| Tool ID | Description | Permissions | Risk Level |
|---|---|---|---|
| `os.screen.capture` | Captures visual display pixels | `READ` | `LOW` |
| `os.screen.monitors` | Enumerates active display monitors | `READ` | `LOW` |
| `os.screen.info` | Overall virtual desktop geometry | `READ` | `LOW` |
| `os.mouse.move` | Moves pointer to coordinates | `EXECUTE` | `LOW` |
| `os.mouse.click` | Triggers single/double/right click | `EXECUTE` | `MEDIUM` |
| `os.mouse.double_click` | Triggers double click | `EXECUTE` | `MEDIUM` |
| `os.mouse.right_click` | Triggers right click | `EXECUTE` | `MEDIUM` |
| `os.mouse.scroll` | Scrolls wheel delta | `EXECUTE` | `LOW` |
| `os.keyboard.type` | Types text into foreground window | `EXECUTE` | `MEDIUM` |
| `os.keyboard.press` | Presses single discrete key | `EXECUTE` | `LOW` |
| `os.keyboard.hotkey` | Executes hotkey combination | `EXECUTE` | `MEDIUM` |
| `os.window.list` | Enumerates visible application windows | `READ` | `LOW` |
| `os.window.focus` | Brings target window to foreground | `EXECUTE` | `LOW` |
| `os.window.minimize` | Minimizes target window | `EXECUTE` | `LOW` |
| `os.window.maximize` | Maximizes target window | `EXECUTE` | `LOW` |
| `os.window.restore` | Restores target window | `EXECUTE` | `LOW` |
| `os.clipboard.read` | Reads text from system clipboard | `READ` | `LOW` |
| `os.clipboard.write` | Writes text to system clipboard | `WRITE` | `LOW` |
| `os.clipboard.clear` | Purges system clipboard | `WRITE` | `LOW` |
| `os.system.info` | Host telemetry & active window | `READ` | `LOW` |
