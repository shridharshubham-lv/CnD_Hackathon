from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "e2e-demo-pack"


BRIEF_TITLE = "Northstar RevOps Demo Campaign"

BRIEF_LINES = [
    "Campaign Name: Northstar RevOps Demo Campaign",
    "Business Objective: Convert 35 enterprise trial accounts into booked demos and close 12 new annual contracts before the end of Q3.",
    "Target Audience: VP Revenue Operations, Director of Marketing Operations, and Revenue Systems leaders at B2B SaaS companies with 500 to 3000 employees.",
    "Key Message: Northstar removes manual reporting work so RevOps teams can act on pipeline changes within minutes, not days.",
    "Channels: Email, LinkedIn, Paid Search, Landing Page, Sales Outreach",
    "Budget: 42000 USD total. 12000 LinkedIn, 10000 paid search, 8000 email + sales enablement, 12000 landing page refresh and design.",
    "Timeline: Brief approved June 10. Assets locked June 24. Campaign launches July 1 and runs for 6 weeks.",
    "Success Metrics: 35 booked demos from active trials, 12 net-new annual contracts, landing page conversion rate above 7 percent, LinkedIn CTR above 1.2 percent.",
    "Constraints: Do not say AI-powered without proof. Do not mention competitors. CTA must be Book a demo. Tone should be confident, executive, and specific.",
    "Proof Points: Customers cut weekly reporting time by 6 to 10 hours. One customer reduced board prep time from 2 days to 2 hours.",
]


ASSETS = {
    "02_email_asset_aligned.docx": [
        "Channel: Email",
        "Subject: Your pipeline review should take minutes, not Mondays",
        "Preview text: See how RevOps leaders cut manual reporting work before QBR season.",
        "Hi {{First Name}},",
        "Revenue teams at growing SaaS companies lose hours every week stitching together pipeline reports before decisions can happen.",
        "Northstar gives RevOps leaders a live view of changes across pipeline, forecast, and conversion so they can act quickly and show executives what changed.",
        "Customers report saving 6 to 10 hours each week on manual reporting, and one team cut board prep from 2 days to 2 hours.",
        "Book a demo to see how Northstar can help your team move from spreadsheet cleanup to confident action.",
        "CTA: Book a demo",
    ],
    "03_linkedin_asset_bad_cta.pdf": [
        "Channel: LinkedIn",
        "Manual reporting is still slowing down too many RevOps teams.",
        "Northstar helps revenue leaders spot pipeline shifts in minutes so they can make decisions before the weekly report is finished.",
        "If your team is tired of stitching dashboards together, start a free trial today and see the data for yourself.",
        "CTA: Start your free trial",
        "Issue seeded for demo: CTA conflicts with brief, which requires Book a demo.",
    ],
    "04_paid_search_asset_wrong_audience.docx": [
        "Channel: Paid Search",
        "Headline 1: Reporting Software for Small Teams",
        "Headline 2: Built for Startup Founders",
        "Headline 3: Start Free in Minutes",
        "Description 1: Replace manual spreadsheets and get instant reporting visibility.",
        "Description 2: Perfect for early-stage teams that need a lightweight dashboard.",
        "CTA: Start free",
        "Issue seeded for demo: audience and CTA are misaligned with the enterprise brief.",
    ],
    "05_landing_page_asset_aligned.pdf": [
        "Channel: Landing Page",
        "Headline: RevOps visibility without the reporting backlog",
        "Subheadline: Northstar helps enterprise revenue teams act on pipeline changes in minutes instead of waiting days for manual updates.",
        "Body: Built for RevOps and marketing operations leaders who need a reliable view of what changed, why it changed, and where to focus next.",
        "Proof: Customers save 6 to 10 hours per week on reporting and one customer cut board prep from 2 days to 2 hours.",
        "CTA: Book a demo",
    ],
    "06_sales_outreach_asset_aligned.docx": [
        "Channel: Sales Outreach",
        "Subject: Quick idea for your RevOps reporting workflow",
        "Hi {{First Name}},",
        "I noticed your team is scaling pipeline coverage across multiple segments. That usually means more reporting handoffs and slower executive updates.",
        "Northstar gives RevOps leaders a faster way to see pipeline movement, explain changes, and reduce manual reporting work by 6 to 10 hours each week.",
        "Open to a 20-minute conversation next week?",
        "CTA: Book a demo",
    ],
}


def escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_simple_pdf(lines: list[str]) -> bytes:
    content_lines = ["BT", "/F1 11 Tf", "50 770 Td", "14 TL"]
    for index, line in enumerate(lines):
        escaped = escape_pdf_text(line)
        if index == 0:
            content_lines.append(f"({escaped}) Tj")
        else:
            content_lines.append(f"T* ({escaped}) Tj")
    content_lines.append("ET")
    content_stream = "\n".join(content_lines).encode("latin-1", errors="replace")

    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n",
        b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
        b"5 0 obj\n<< /Length " + str(len(content_stream)).encode("ascii") + b" >>\nstream\n" + content_stream + b"\nendstream\nendobj\n",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)

    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


def xml_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build_simple_docx(lines: list[str]) -> bytes:
    document_body = "".join(
        f"<w:p><w:r><w:t xml:space=\"preserve\">{xml_escape(line)}</w:t></w:r></w:p>"
        for line in lines
    )
    document_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<w:document xmlns:wpc=\"http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas\" "
        "xmlns:mc=\"http://schemas.openxmlformats.org/markup-compatibility/2006\" "
        "xmlns:o=\"urn:schemas-microsoft-com:office:office\" "
        "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" "
        "xmlns:m=\"http://schemas.openxmlformats.org/officeDocument/2006/math\" "
        "xmlns:v=\"urn:schemas-microsoft-com:vml\" "
        "xmlns:wp14=\"http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing\" "
        "xmlns:wp=\"http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing\" "
        "xmlns:w10=\"urn:schemas-microsoft-com:office:word\" "
        "xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\" "
        "xmlns:w14=\"http://schemas.microsoft.com/office/word/2010/wordml\" "
        "xmlns:wpg=\"http://schemas.microsoft.com/office/word/2010/wordprocessingGroup\" "
        "xmlns:wpi=\"http://schemas.microsoft.com/office/word/2010/wordprocessingInk\" "
        "xmlns:wne=\"http://schemas.microsoft.com/office/word/2006/wordml\" "
        "xmlns:wps=\"http://schemas.microsoft.com/office/word/2010/wordprocessingShape\" mc:Ignorable=\"w14 wp14\">"
        f"<w:body>{document_body}<w:sectPr><w:pgSz w:w=\"12240\" w:h=\"15840\"/><w:pgMar w:top=\"1440\" w:right=\"1440\" w:bottom=\"1440\" w:left=\"1440\" w:header=\"708\" w:footer=\"708\" w:gutter=\"0\"/></w:sectPr></w:body></w:document>"
    )

    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
"""

    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"""

    doc_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>
"""

    core = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Campaign Intelligence Demo Asset</dc:title>
  <dc:creator>GitHub Copilot</dc:creator>
  <cp:lastModifiedBy>GitHub Copilot</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">2026-05-03T00:00:00Z</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">2026-05-03T00:00:00Z</dcterms:modified>
</cp:coreProperties>
"""

    app = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Campaign Intelligence Demo Pack</Application>
</Properties>
"""

    from io import BytesIO

    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("docProps/core.xml", core)
        archive.writestr("docProps/app.xml", app)
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/_rels/document.xml.rels", doc_rels)
    return buffer.getvalue()


def write_file(path: Path, lines: list[str]) -> None:
    if path.suffix == ".pdf":
        path.write_bytes(build_simple_pdf(lines))
    elif path.suffix == ".docx":
        path.write_bytes(build_simple_docx(lines))
    else:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_manifest() -> str:
    return """# E2E Demo Pack

This folder contains realistic upload files for a full Campaign Intelligence demo.

Recommended demo path:
1. In Stage 1, upload `01_campaign_brief_enterprise_demo.pdf`.
2. In Stage 2, use Agent 1 suggested answers for high-priority questions when available.
3. In Stage 3, approve the execution plan.
4. In Stage 4, upload at least these assets:
   - `02_email_asset_aligned.docx`
   - `03_linkedin_asset_bad_cta.pdf`
   - `04_paid_search_asset_wrong_audience.docx`
   - `05_landing_page_asset_aligned.pdf`
   - `06_sales_outreach_asset_aligned.docx`
5. Run the consistency check and review the seeded errors in Stage 5.

Expected demo outcome:
- Email, landing page, and sales outreach should read as aligned.
- LinkedIn should trigger a CTA mismatch because it says `Start your free trial` instead of `Book a demo`.
- Paid Search should trigger audience and CTA problems because it targets startup founders and says `Start free`.

If you want to test alternate upload types, a DOCX copy of the brief is included as `01_campaign_brief_enterprise_demo.docx`.
"""


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    write_file(OUTPUT_DIR / "01_campaign_brief_enterprise_demo.pdf", BRIEF_LINES)
    write_file(OUTPUT_DIR / "01_campaign_brief_enterprise_demo.docx", BRIEF_LINES)
    for file_name, lines in ASSETS.items():
        write_file(OUTPUT_DIR / file_name, lines)
    (OUTPUT_DIR / "README.md").write_text(build_manifest(), encoding="utf-8")
    print(f"Created demo pack in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()