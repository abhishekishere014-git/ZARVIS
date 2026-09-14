# Native Office Generation Suite

JARVIS provides local, native generation of professional office documents across four formats without relying on external cloud APIs or closed-source tooling.

---

## 1. Supported Formats & Libraries

| Format | File Extension | Tool ID | Underlying Engine | License | Key Capabilities |
| :--- | :---: | :--- | :--- | :---: | :--- |
| **Word** | `.docx` | `office.create_docx` | `python-docx` | MIT | Headings (H1–H3), formatted paragraphs, italic subtitles, bulleted lists, styled grid tables. |
| **Excel** | `.xlsx` | `office.create_xlsx` | `openpyxl` | MIT | Multi-sheet workbooks, colored header fills, bold fonts, auto-fit column widths, typed data rows. |
| **PowerPoint** | `.pptx` | `office.create_pptx` | `python-pptx` | MIT | Title slides, content slides, structured bullet points, body text formatting. |
| **PDF** | `.pdf` | `office.create_pdf` | `reportlab` | BSD | Document titles, styled subtitles, headings, body text, styled colored tables, page breaks. |

---

## 2. Tool Interfaces & Payloads

### `office.create_docx`
```json
{
  "filename": "quarterly_briefing.docx",
  "title": "Q3 Intelligence Report",
  "subtitle": "System Analysis & Telemetry",
  "sections": [
    {
      "heading": "Summary",
      "level": 1,
      "paragraph": "Autonomous agent runtime performed within normal operational limits."
    },
    {
      "heading": "Deliverables",
      "level": 2,
      "bullets": [
        "Sandboxed tool execution pipeline",
        "Deterministic policy enforcement"
      ]
    },
    {
      "heading": "Metrics",
      "level": 2,
      "table": [
        ["Subsystem", "Latency", "Status"],
        ["AI Router", "0.26ms", "Healthy"],
        ["Tool Engine", "0.38ms", "Healthy"]
      ]
    }
  ]
}
```

### `office.create_xlsx`
```json
{
  "filename": "financial_projection.xlsx",
  "sheets": [
    {
      "name": "Revenue",
      "headers": ["Quarter", "Target ($)", "Actual ($)", "Variance (%)"],
      "rows": [
        ["Q1", 100000, 112000, 12.0],
        ["Q2", 125000, 131000, 4.8]
      ]
    },
    {
      "name": "Headcount",
      "headers": ["Department", "FTEs"],
      "rows": [
        ["Engineering", 12],
        ["Security", 4]
      ]
    }
  ]
}
```

### `office.create_pptx`
```json
{
  "filename": "executive_briefing.pptx",
  "title": "JARVIS Platform Roadmap",
  "subtitle": "Phase 04 Technical Review",
  "slides": [
    {
      "title": "Core Architecture",
      "bullets": [
        "Hybrid Core: Python (Intelligence) + Node (Real-time Gateway)",
        "Zero arbitrary shell execution",
        "Deterministic path sandboxing"
      ]
    }
  ]
}
```

### `office.create_pdf`
```json
{
  "filename": "audit_compliance.pdf",
  "title": "System Compliance Certification",
  "subtitle": "SDLC Verification Report",
  "sections": [
    {
      "heading": "Audit Finding",
      "paragraph": "All 10 mandatory Quality Gates verified with 100% test pass rate."
    },
    {
      "bullets": [
        "Path traversal blocked",
        "Secret leakage scrubbed",
        "Artifact structural verification active"
      ]
    },
    {
      "page_break": true
    },
    {
      "heading": "Detailed Metrics",
      "table": [
        ["Gate", "Requirement", "Status"],
        ["QG-06", "Automated Testing", "Passed (110 tests)"]
      ]
    }
  ]
}
```

---

## 3. Post-Generation Artifact Verification
A tool call is never marked as `ToolExecutionStatus.SUCCESS` simply because the function completed without raising an uncaught exception. Each office generator actively opens and verifies the generated file:
* **DOCX Verification:** Reopens file via `docx.Document(path)` and validates that paragraphs or tables were created.
* **XLSX Verification:** Loads workbook via `openpyxl.load_workbook(path, read_only=True)` and verifies sheet count and sheet names match the request.
* **PPTX Verification:** Loads presentation via `pptx.Presentation(path)` and confirms slide counts match expected layouts.
* **PDF Verification:** Inspects raw file bytes to confirm `%PDF-` header and `%%EOF` trailer markers exist.
