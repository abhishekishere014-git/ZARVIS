"""Native Microsoft Excel (.xlsx) generation tool with structural verification."""

from typing import Any, Dict, List, Optional
import openpyxl
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
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
    name="create_xlsx",
    tool_id="office.create_xlsx",
    description="Generate a formatted Microsoft Excel (.xlsx) workbook with multiple sheets, headers, rows, and safe formulas.",
    category="office",
    version="1.0.0",
    permissions={ToolPermission.WRITE},
    risk_level=RiskLevel.LOW,
    timeout_seconds=30.0,
)
async def create_xlsx(
    filename: str,
    sheets: List[Dict[str, Any]],
    context: Optional[ToolExecutionContext] = None,
) -> Dict[str, Any]:
    """Generates an Excel workbook (.xlsx) and verifies its internal structure.

    :param filename: Output filename, e.g. 'financials.xlsx'
    :param sheets: List of sheet dicts (keys: 'name', 'headers', 'rows')
    """
    if not context or not context.sandbox:
        raise ValueError("Tool execution context with sandbox is required.")

    if not sheets:
        raise ValueError("At least one sheet specification is required.")

    # 1. Resolve safe destination inside workspace
    clean_name = context.sandbox.sanitize_filename(filename)
    if not clean_name.lower().endswith(".xlsx"):
        clean_name += ".xlsx"

    safe_path = context.sandbox.resolve_safe_path(clean_name, allowed_extensions={"xlsx"})

    # 2. Build Workbook
    wb = openpyxl.Workbook()
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)

    total_rows = 0
    created_sheet_names = []

    for idx, sheet_spec in enumerate(sheets):
        sheet_name = str(sheet_spec.get("name", f"Sheet{idx + 1}"))[:31]  # Excel 31 char sheet limit
        if idx == 0:
            ws = wb.active
            ws.title = sheet_name
        else:
            ws = wb.create_sheet(title=sheet_name)

        created_sheet_names.append(sheet_name)

        headers = sheet_spec.get("headers", [])
        if headers:
            if len(headers) > DEFAULT_LIMITS.max_table_cols:
                raise ResourceLimitExceededError(
                    f"Column count ({len(headers)}) exceeds limit of {DEFAULT_LIMITS.max_table_cols}"
                )
            ws.append(headers)
            # Format header row
            for col_idx in range(1, len(headers) + 1):
                cell = ws.cell(row=1, column=col_idx)
                cell.fill = header_fill
                cell.font = header_font

        rows = sheet_spec.get("rows", [])
        if rows:
            total_rows += len(rows)
            if total_rows > DEFAULT_LIMITS.max_table_rows:
                raise ResourceLimitExceededError(
                    f"Total rows ({total_rows}) exceeds limit of {DEFAULT_LIMITS.max_table_rows}"
                )
            for row in rows:
                ws.append(row)

        # Auto-adjust column widths
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or "")
                if len(val_str) > max_len:
                    max_len = len(val_str)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 10)

    # 3. Save workbook
    wb.save(str(safe_path))

    # 4. Verify artifact size and structural integrity
    size_bytes = verify_file_size_within_limit(safe_path)
    try:
        reopened = openpyxl.load_workbook(str(safe_path), read_only=True)
        sheet_count = len(reopened.sheetnames)
        if sheet_count != len(created_sheet_names):
            raise ArtifactVerificationError(
                f"Expected {len(created_sheet_names)} sheets, found {sheet_count}"
            )
        reopened.close()
    except Exception as exc:
        raise ArtifactVerificationError(f"XLSX structural verification failed: {exc}") from exc

    return {
        "status": "success",
        "filename": safe_path.name,
        "path": str(safe_path),
        "size_bytes": size_bytes,
        "sheets_count": len(created_sheet_names),
        "sheet_names": created_sheet_names,
        "total_rows": total_rows,
        "artifacts": [str(safe_path)],
    }
