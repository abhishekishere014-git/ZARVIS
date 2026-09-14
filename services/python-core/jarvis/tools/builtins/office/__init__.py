"""Built-in Office Generation Suite tools."""

from jarvis.tools.builtins.office.docx_tool import create_docx
from jarvis.tools.builtins.office.pdf_tool import create_pdf
from jarvis.tools.builtins.office.pptx_tool import create_pptx
from jarvis.tools.builtins.office.xlsx_tool import create_xlsx
from jarvis.tools.registry import ToolRegistry


def register_office_tools(registry: ToolRegistry) -> None:
    """Registers all 4 native office document generators with the ToolRegistry."""
    registry.register_tool(create_docx)
    registry.register_tool(create_xlsx)
    registry.register_tool(create_pptx)
    registry.register_tool(create_pdf)


__all__ = [
    "create_docx",
    "create_xlsx",
    "create_pptx",
    "create_pdf",
    "register_office_tools",
]
