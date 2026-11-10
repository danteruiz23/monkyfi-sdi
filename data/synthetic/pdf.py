"""PDF rendering of synthetic documents (D30).

SYNTHETIC — NOT REAL DATA. Every page carries the synthetic mark at the top and
at the bottom. Output is byte-for-byte reproducible (reportlab invariant mode).

A document is a list of blocks (see generate.py). build_pdf returns the number of
pages and the page on which each block was drawn, so golden labels can cite a page.
"""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import BaseDocTemplate, Frame, KeepTogether, PageTemplate, Paragraph, Spacer, Table, TableStyle

MARK = "SYNTHETIC — NOT REAL DATA"

_base = getSampleStyleSheet()
BODY = ParagraphStyle("body", parent=_base["BodyText"], fontName="Helvetica", fontSize=9.5, leading=13)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=9, leading=11.5)
CELL_BOLD = ParagraphStyle("cell_bold", parent=CELL, fontName="Helvetica-Bold")
TITLE = ParagraphStyle("title", parent=BODY, fontName="Helvetica-Bold", fontSize=15, leading=19, spaceAfter=6)
HEADING = ParagraphStyle("heading", parent=BODY, fontName="Helvetica-Bold", fontSize=11, leading=14,
                         spaceBefore=8, spaceAfter=4)
NOTE = ParagraphStyle("note", parent=BODY, fontName="Helvetica-Oblique", fontSize=7.5, leading=9.5)
HIDDEN = ParagraphStyle("hidden", parent=BODY, fontSize=1, leading=1.2, textColor=colors.white)

TABLE_STYLE = TableStyle([
    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
    ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
])


class _Document(BaseDocTemplate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.block_pages: dict[int, int] = {}

    def afterFlowable(self, flowable):
        index = getattr(flowable, "_block_index", None)
        if index is not None:
            self.block_pages.setdefault(index, self.page)


def _mark_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica-Bold", 9)
    canvas.setFillColor(colors.red)
    width, height = A4
    canvas.drawCentredString(width / 2, height - 1.1 * cm, MARK)
    canvas.drawCentredString(width / 2, 0.9 * cm, MARK)
    canvas.restoreState()


def _table(columns: list[str], rows: list[list[str]], widths: list[float]) -> Table:
    data = [[Paragraph(escape(c), CELL_BOLD) for c in columns]]
    data += [[Paragraph(escape(str(cell)), CELL) for cell in row] for row in rows]
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(TABLE_STYLE)
    return table


def _tag(flowable, index: int):
    flowable._block_index = index
    return flowable


def build_pdf(path: Path, title: str, blocks: list[dict]) -> tuple[int, dict[int, int]]:
    """Write one document. Returns (page count, {block index: page})."""
    doc = _Document(str(path), pagesize=A4, invariant=1, title=title, author=MARK, subject=MARK,
                    leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=1.6 * cm)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="body")
    doc.addPageTemplates([PageTemplate(id="page", frames=[frame], onPage=_mark_page)])
    story = []
    for index, block in enumerate(blocks):
        kind = block["t"]
        if kind == "title":
            story.append(_tag(Paragraph(escape(block["text"]), TITLE), index))
        elif kind in ("line", "para"):
            for part in block["text"].split("\n\n"):
                story.append(_tag(Paragraph(escape(part), BODY), index))
                story.append(Spacer(1, 4))
        elif kind == "meta":
            for key, value in block["items"]:
                story.append(_tag(Paragraph(f"<b>{escape(key)}:</b> {escape(value)}", BODY), index))
            story.append(Spacer(1, 6))
        elif kind == "section":
            table = _tag(_table(["Field", "Value"], [list(r) for r in block["rows"]], [5.5 * cm, doc.width - 5.5 * cm]),
                         index)
            story.append(KeepTogether([Paragraph(escape(f"{block['n']}. {block['heading']}"), HEADING), table]))
        elif kind == "table":
            n = len(block["columns"])
            story.append(_tag(_table(block["columns"], block["rows"], [doc.width / n] * n), index))
            story.append(Spacer(1, 6))
        elif kind == "note":
            story.append(_tag(Paragraph(escape(block["text"]), NOTE), index))
        elif kind == "hidden":
            # Text a person does not see but a text extractor does (mandatory case 12).
            story.append(_tag(Paragraph(escape(block["text"]), HIDDEN), index))
        else:
            raise ValueError(f"unknown block type: {kind}")
    doc.build(story)
    missing = [i for i in range(len(blocks)) if i not in doc.block_pages]
    if missing:
        raise ValueError(f"{path.name}: no page recorded for blocks {missing}")
    return doc.page, doc.block_pages
