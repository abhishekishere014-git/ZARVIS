"""Native PDF generation tool with structural verification."""

from typing import Any, Dict, List, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from jarvis.tools.builtins.office.base import (
    DEFAULT_LIMITS,
    verify_file_size_within_limit,
)
from jarvis.tools.decorator import tool
from jarvis.tools.errors import (
    ArtifactVerificationError,
    ResourceLimitExceededError,
)
from jarvis.tools.models import (
    RiskLevel,
    ToolExecutionContext,
    ToolPermission,
)


@tool(
    name="create_pdf",
    tool_id="office.create_pdf",
    description="Generate a formatted PDF document with titles, headings, paragraphs, bullet lists, tables, and page breaks.",
    category="office",
    version="1.0.0",
    permissions={ToolPermission.WRITE},
    risk_level=RiskLevel.LOW,
    timeout_seconds=30.0,
)
async def create_pdf(
    filename: str,
    title: str,
    sections: List[Dict[str, Any]],
    subtitle: Optional[str] = None,
    context: Optional[ToolExecutionContext] = None,
) -> Dict[str, Any]:
    """Generates a PDF document (.pdf) and verifies its internal binary structure.

    :param filename: Output filename, e.g. 'summary.pdf'
    :param title: Main document title
    :param sections: List of section dicts (keys: 'heading', 'paragraph', 'bullets', 'table', 'page_break')
    :param subtitle: Optional document subtitle
    """
    if not context or not context.sandbox:
        raise ValueError("Tool execution context with sandbox is required.")

    # 1. Resolve safe destination inside workspace
    clean_name = context.sandbox.sanitize_filename(filename)
    if not clean_name.lower().endswith(".pdf"):
        clean_name += ".pdf"

    safe_path = context.sandbox.resolve_safe_path(clean_name, allowed_extensions={"pdf"})

    # 2. Build PDF Story
    styles = getSampleStyleSheet()
    story = []

    # Title & Subtitle
    story.append(Paragraph(title, styles["Title"]))
    story.append(Spacer(1, 12))
    if subtitle:
        sub_style = ParagraphStyle("Subtitle", parent=styles["Normal"], textColor=colors.HexColor("#555555"))
        story.append(Paragraph(subtitle, sub_style))
        story.append(Spacer(1, 12))

    total_rows = 0
    for sec in sections:
        if sec.get("page_break", False):
            story.append(PageBreak())
            continue

        heading = sec.get("heading")
        if heading:
            story.append(Paragraph(str(heading), styles["Heading2"]))
            story.append(Spacer(1, 6))

        para = sec.get("paragraph")
        if para:
            story.append(Paragraph(str(para), styles["BodyText"]))
            story.append(Spacer(1, 8))

        bullets = sec.get("bullets")
        if bullets and isinstance(bullets, list):
            for bullet in bullets:
                story.append(Paragraph(f"&bull; {bullet}", styles["BodyText"]))
            story.append(Spacer(1, 8))

        table_data = sec.get("table")
        if table_data and isinstance(table_data, list) and len(table_data) > 0:
            total_rows += len(table_data)
            if total_rows > DEFAULT_LIMITS.max_table_rows:
                raise ResourceLimitExceededError(
                    f"Total table rows ({total_rows}) exceeds limit of {DEFAULT_LIMITS.max_table_rows}"
                )

            table = Table(table_data)
            table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F497D")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F2F2F2")),
                    ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#CCCCCC")),
                ])
            )
            story.append(table)
            story.append(Spacer(1, 12))

    # 3. Compile document
    doc = SimpleDocTemplate(
        str(safe_path),
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54,
    )
    try:
        doc.build(story)
    except Exception as exc:
        raise ArtifactVerificationError(f"PDF compilation failed: {exc}") from exc

    # 4. Verify artifact size and structural integrity
    size_bytes = verify_file_size_within_limit(safe_path)
    try:
        with open(safe_path, "rb") as f:
            header = f.read(5)
            if header != b"%PDF-":
                raise ArtifactVerificationError(f"File '{safe_path.name}' is not a valid PDF (invalid magic header).")
            f.seek(-1024, 2)  # Read last 1024 bytes
            tail = f.read()
            if b"%%EOF" not in tail:
                raise ArtifactVerificationError(f"File '{safe_path.name}' is incomplete (missing %%EOF marker).")
    except Exception as exc:
        raise ArtifactVerificationError(f"PDF structural verification failed: {exc}") from exc

    return {
        "status": "success",
        "filename": safe_path.name,
        "path": str(safe_path),
        "size_bytes": size_bytes,
        "artifacts": [str(safe_path)],
    }
