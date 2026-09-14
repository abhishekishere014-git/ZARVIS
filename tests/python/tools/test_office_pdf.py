"""Tests for native PDF generation and binary structure verification."""

from pathlib import Path
import pytest
from jarvis.tools.builtins.office.pdf_tool import create_pdf
from jarvis.tools.errors import ResourceLimitExceededError
from jarvis.tools.models import ToolExecutionContext
from jarvis.tools.sandbox import FileSystemSandbox


@pytest.mark.asyncio
async def test_create_pdf_full_lifecycle(tmp_path: Path) -> None:
    sandbox = FileSystemSandbox(workspace_root=tmp_path)
    context = ToolExecutionContext(
        execution_id="test_pdf_1",
        tool_id="office.create_pdf",
        workspace_dir=tmp_path,
        sandbox=sandbox,
    )

    sections = [
        {"heading": "Status Report", "paragraph": "System integrity check confirms all components healthy."},
        {"bullets": ["Database online", "Sandbox operational", "Zero security violations"]},
        {
            "table": [
                ["Metric", "Value", "Threshold"],
                ["CPU", "4.2%", "< 80%"],
                ["Memory", "145MB", "< 2GB"],
            ]
        },
        {"page_break": True},
        {"heading": "Next Steps", "paragraph": "Proceed with autonomous agent loop initialization."},
    ]

    result = await create_pdf(
        filename="system_audit.pdf",
        title="JARVIS Health Audit",
        subtitle="Internal Telemetry & Compliance",
        sections=sections,
        context=context,
    )

    assert result["status"] == "success"
    assert result["filename"] == "system_audit.pdf"
    assert result["size_bytes"] > 0

    # Verify physical file existence and PDF magic bytes
    file_path = Path(result["path"])
    assert file_path.exists()

    with open(file_path, "rb") as f:
        header = f.read(5)
        assert header == b"%PDF-"
        f.seek(-1024, 2)
        tail = f.read()
        assert b"%%EOF" in tail


@pytest.mark.asyncio
async def test_create_pdf_enforces_limits(tmp_path: Path) -> None:
    sandbox = FileSystemSandbox(workspace_root=tmp_path)
    context = ToolExecutionContext(
        execution_id="test_pdf_2",
        tool_id="office.create_pdf",
        workspace_dir=tmp_path,
        sandbox=sandbox,
    )

    # Exceed table row limit
    huge_table = [["H1", "H2"]] + [["v1", "v2"] for _ in range(10_005)]
    sections = [{"table": huge_table}]

    with pytest.raises(ResourceLimitExceededError):
        await create_pdf(
            filename="overflow.pdf",
            title="Overflow",
            sections=sections,
            context=context,
        )
