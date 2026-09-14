# Vision Runtime & Tool Registry Integration

## Registered Vision Tools
Phase 09 registers three core tools into the Phase 04 `ToolRegistry`:

| Tool Name | Tool ID | Permissions | Risk Level | Description |
|-----------|---------|-------------|------------|-------------|
| `screen_analyze` | `vision.screen.analyze` | `READ` | `LOW` | Analyzes current screen imagery into structured UI elements and regions. |
| `element_find` | `vision.element.find` | `READ` | `LOW` | Searches for visual elements by text label, element type, or region. |
| `target_resolve` | `vision.target.resolve` | `READ` | `LOW` | Grounds semantic description to validated coordinates and suggested action. |

## Usage Workflow

```python
from jarvis.vision.manager import VisionManager
from jarvis.vision.tools.registration import register_vision_tools
from jarvis.tools.registry import ToolRegistry

registry = ToolRegistry()
vision_manager = VisionManager()
register_vision_tools(registry, vision_manager=vision_manager)

# Resolve coordinate for a target
result = await vision_manager.resolve_target("Google Search", monitor_index=0)
target_x = result.target_point.x
target_y = result.target_point.y

# Execute click via Phase 08 OS tool
await mouse_click(x=target_x, y=target_y)
```
