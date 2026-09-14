"""Decorator and automated schema generator for JARVIS tools via Python function introspection."""

import inspect
import re
from functools import wraps
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Type,
    Union,
    get_args,
    get_origin,
)
from jarvis.tools.models import (
    ApprovalMode,
    RiskLevel,
    ToolDefinition,
    ToolExecutionContext,
    ToolPermission,
)


def _python_type_to_json_schema(py_type: Any) -> Dict[str, Any]:
    """Maps Python typing structures to standard JSON Schema types."""
    if py_type in (str, Optional[str]):
        return {"type": "string"}
    if py_type in (int, Optional[int]):
        return {"type": "integer"}
    if py_type in (float, Optional[float]):
        return {"type": "number"}
    if py_type in (bool, Optional[bool]):
        return {"type": "boolean"}
    if py_type in (dict, Dict, Dict[str, Any]):
        return {"type": "object"}

    origin = get_origin(py_type)
    if origin is list or origin is List:
        args = get_args(py_type)
        if args:
            return {"type": "array", "items": _python_type_to_json_schema(args[0])}
        return {"type": "array"}

    if origin is Union:
        args = get_args(py_type)
        # Handle Optional[T] = Union[T, NoneType]
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return _python_type_to_json_schema(non_none[0])
        return {"anyOf": [_python_type_to_json_schema(a) for a in non_none]}

    # Fallback to string or object
    return {"type": "string"}


def _extract_docstring_param_descriptions(docstring: Optional[str]) -> Dict[str, str]:
    """Extracts parameter descriptions from Sphinx or Google style docstrings."""
    descriptions: Dict[str, str] = {}
    if not docstring:
        return descriptions

    # Match Sphinx: :param name: description
    for match in re.finditer(r":param\s+(\w+):\s*(.+)", docstring):
        descriptions[match.group(1)] = match.group(2).strip()

    # Match Google style: name (type): description or name: description
    args_section = re.search(r"Args:\s*\n((?:\s+\w+.*?\n)+)", docstring)
    if args_section:
        for line in args_section.group(1).splitlines():
            line_match = re.match(r"\s+(\w+)(?:\s*\([^)]+\))?:\s*(.+)", line)
            if line_match:
                descriptions[line_match.group(1)] = line_match.group(2).strip()

    return descriptions


def generate_tool_schema(func: Callable[..., Any]) -> Dict[str, Any]:
    """Inspects a Python function signature, type annotations, and docstrings to generate JSON Schema."""
    sig = inspect.signature(func)
    try:
        type_hints = inspect.get_annotations(func, eval_str=True)
    except Exception:
        type_hints = getattr(func, "__annotations__", {})

    docstring = inspect.getdoc(func)
    param_docs = _extract_docstring_param_descriptions(docstring)

    properties: Dict[str, Any] = {}
    required: List[str] = []

    for name, param in sig.parameters.items():
        # Context parameters are injected at runtime, not supplied by AI caller
        if name == "context" or param.annotation is ToolExecutionContext:
            continue

        py_type = type_hints.get(name, param.annotation if param.annotation != inspect.Parameter.empty else str)
        schema_prop = _python_type_to_json_schema(py_type)

        if name in param_docs:
            schema_prop["description"] = param_docs[name]

        if param.default != inspect.Parameter.empty:
            schema_prop["default"] = param.default
        else:
            # Check if type is Optional
            origin = get_origin(py_type)
            if origin is Union and type(None) in get_args(py_type):
                pass  # Optional parameters are not required
            else:
                required.append(name)

        properties[name] = schema_prop

    schema: Dict[str, Any] = {
        "type": "object",
        "properties": properties,
    }
    if required:
        schema["required"] = required

    return schema


def tool(
    name: Optional[str] = None,
    tool_id: Optional[str] = None,
    description: Optional[str] = None,
    category: str = "general",
    version: str = "1.0.0",
    permissions: Optional[Set[ToolPermission]] = None,
    risk_level: RiskLevel = RiskLevel.LOW,
    approval_mode: ApprovalMode = ApprovalMode.AUTO_APPROVE,
    timeout_seconds: float = 30.0,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to transform a Python async function into a registered JARVIS tool with validated schema."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        actual_name = name or func.__name__
        actual_id = tool_id or actual_name
        raw_doc = inspect.getdoc(func)
        actual_description = description or (raw_doc.split("\n\n")[0].strip() if raw_doc else actual_name)

        input_schema = generate_tool_schema(func)

        tool_def = ToolDefinition(
            id=actual_id,
            name=actual_name,
            version=version,
            description=actual_description,
            category=category,
            input_schema=input_schema,
            permissions=permissions or set(),
            risk_level=risk_level,
            approval_mode=approval_mode,
            timeout_seconds=timeout_seconds,
            enabled=True,
        )

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        # Attach metadata to the wrapper
        wrapper.tool_definition = tool_def  # type: ignore[attr-defined]
        wrapper.__tool_func__ = func  # type: ignore[attr-defined]
        return wrapper

    return decorator
