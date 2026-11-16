#!/usr/bin/env python3
"""House style for every Word file the agent makes, matching the PDFs.

Navy headings with a thin rule, a letterhead with a rule under it, page numbers,
tables with a navy header row and light banding, and even spacing throughout.
Used by firm.py (agreements, letters, quotes, PR plans, translations) and portal_sheet.py.
"""
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

NAVY = RGBColor(0x1F, 0x38, 0x64)
GREY = RGBColor(0x55, 0x55, 0x55)
DARK = RGBColor(0x22, 0x22, 0x22)
NAVY_HEX, LIGHT_HEX, RULE_HEX = "1F3864", "EEF2F8", "C9D3E3"
FONT = "Calibri"


def _font(style_or_run, size=None, bold=None, color=None, name=FONT):
    f = style_or_run.font
    f.name = name
    rpr = style_or_run.element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.insert(0, fonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fonts.set(qn(attr), name)
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
        fonts.attrib.pop(qn(attr), None)
    if size:
        f.size = Pt(size)
    if bold is not None:
        f.bold = bold
    if color is not None:
        f.color.rgb = color


def border(paragraph, side="bottom", color=NAVY_HEX, size=8, space=1):
    """A rule above or below a paragraph (size in eighths of a point)."""
    ppr = paragraph._p.get_or_add_pPr()
    bdr = ppr.find(qn("w:pBdr"))
    if bdr is None:
        bdr = OxmlElement("w:pBdr")
        ppr.append(bdr)
    el = OxmlElement(f"w:{side}")
    for k, v in (("val", "single"), ("sz", str(size)), ("space", str(space)), ("color", color)):
        el.set(qn(f"w:{k}"), v)
    bdr.append(el)


def setup(d, body_size=10.5, landscape=False):
    """Page, margins and styles for a new docx.Document()."""
    sec = d.sections[0]
    if landscape:
        sec.orientation = WD_ORIENT.LANDSCAPE
        sec.page_width, sec.page_height = Inches(11), Inches(8.5)
    else:
        sec.page_width, sec.page_height = Inches(8.5), Inches(11)
    sec.left_margin = sec.right_margin = Inches(1)
    sec.top_margin, sec.bottom_margin = Inches(0.9), Inches(0.85)
    sec.header_distance, sec.footer_distance = Inches(0.4), Inches(0.4)
    st = d.styles
    normal = st["Normal"]
    _font(normal, body_size, color=DARK)
    pf = normal.paragraph_format
    pf.space_before, pf.space_after, pf.line_spacing = Pt(0), Pt(6), 1.15
    title = st["Title"]
    _font(title, 20, True, NAVY)
    title.paragraph_format.space_before, title.paragraph_format.space_after = Pt(0), Pt(4)
    for name, size, before, after in (("Heading 1", 13, 14, 6), ("Heading 2", 11.5, 10, 4), ("Heading 3", 10.5, 8, 2)):
        h = st[name]
        _font(h, size, True, NAVY)
        h.font.italic = False
        h.paragraph_format.space_before, h.paragraph_format.space_after = Pt(before), Pt(after)
        h.paragraph_format.keep_with_next = True
    for name in ("List Bullet", "List Number"):
        lp = st[name].paragraph_format
        lp.space_after, lp.line_spacing = Pt(3), 1.15
    # Word's default Title style draws a blue underline of its own; drop it so only our rule shows
    ppr = title.element.get_or_add_pPr()
    for b in ppr.findall(qn("w:pBdr")):
        ppr.remove(b)
    return sec


def _field(paragraph, code, size=8, color=GREY):
    """A PAGE / NUMPAGES field; each part in its own run so the number keeps the footer's size."""
    for kind, text in (("begin", None), (None, code), ("separate", None), ("result", "1"), ("end", None)):
        run = paragraph.add_run()
        _font(run, size, color=color)
        if kind == "result":
            el = OxmlElement("w:t")
            el.text = text
        elif kind:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = f" {text} "
        run._r.append(el)


def text_run(paragraph, text, size=None, bold=None, color=None, italic=None):
    r = paragraph.add_run(text)
    _font(r, size, bold, color)
    if italic is not None:
        r.italic = italic
    return r


def letterhead(sec, profile):
    """Logo, firm name and contact line, with a navy rule under them. Plain paper when there are no firm details."""
    import pathlib
    head = sec.header.paragraphs[0]
    head.paragraph_format.space_after = Pt(0)
    has_logo = bool(profile.get("logo") and pathlib.Path(profile["logo"]).exists())
    if has_logo:
        head.add_run().add_picture(profile["logo"], height=Inches(0.55))
        head = sec.header.add_paragraph()
        head.paragraph_format.space_after = Pt(0)
    name = profile.get("business") or profile.get("name", "")
    if not name:
        return
    text_run(head, name, 14, True, NAVY)
    line = "  |  ".join(x for x in (profile.get("address"), profile.get("phone"), profile.get("email"), profile.get("website")) if x)
    last = head
    if line:
        last = sec.header.add_paragraph()
        last.paragraph_format.space_before, last.paragraph_format.space_after = Pt(2), Pt(0)
        text_run(last, line, 8.5, color=GREY)
    border(last, "bottom", NAVY_HEX, 12, 4)


def footer(sec, line=None):
    """Optional small grey line (e.g. the RCIC licence statement) and 'Page X of Y', with a thin rule above."""
    first = sec.footer.paragraphs[0]
    first.alignment = WD_ALIGN_PARAGRAPH.CENTER
    first.paragraph_format.space_after = Pt(0)
    border(first, "top", RULE_HEX, 6, 4)
    pages = first
    if line:
        text_run(first, line, 7.5, color=GREY)
        pages = sec.footer.add_paragraph()
        pages.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pages.paragraph_format.space_before, pages.paragraph_format.space_after = Pt(2), Pt(0)
    text_run(pages, "Page ", 8, color=GREY)
    _field(pages, "PAGE")
    text_run(pages, " of ", 8, color=GREY)
    _field(pages, "NUMPAGES")


def title(d, text, subtitle=None):
    p = d.add_paragraph(style="Title")
    p.add_run(text)
    border(p, "bottom", NAVY_HEX, 12, 6)
    p.paragraph_format.space_after = Pt(10 if not subtitle else 4)
    if subtitle:
        s = d.add_paragraph()
        text_run(s, subtitle, 9.5, color=GREY)
        s.paragraph_format.space_after = Pt(10)
    return p


def heading(d, text, level=1):
    p = d.add_paragraph(style=f"Heading {level}")
    p.add_run(text)
    if level == 1:
        border(p, "bottom", RULE_HEX, 6, 2)
    return p


def _shade(cell, hex_fill):
    tcpr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:color"), "auto")
    sh.set(qn("w:fill"), hex_fill)
    tcpr.append(sh)


def _table_borders(table, color=RULE_HEX):
    tblpr = table._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        b.append(el)
    tblpr.append(b)
    mar = OxmlElement("w:tblCellMar")
    for side, w in (("top", 50), ("bottom", 50), ("left", 100), ("right", 100)):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), str(w))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tblpr.append(mar)


def style_table(table, widths=None, size=9.5, header=True):
    """Navy header row (repeats on each page), light banding, thin blue-grey borders, rows kept whole."""
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    _table_borders(table)
    if widths:  # Word and LibreOffice read the grid, not just the cells
        table.autofit = False
        for col, w in zip(table._tbl.tblGrid.findall(qn("w:gridCol")), widths):
            col.set(qn("w:w"), str(int(w.inches * 1440)))
    for i, row in enumerate(table.rows):
        trpr = row._tr.get_or_add_trPr()
        cant = OxmlElement("w:cantSplit")
        trpr.append(cant)
        if i == 0 and header:
            rep = OxmlElement("w:tblHeader")
            trpr.append(rep)
        for j, cell in enumerate(row.cells):
            if widths:
                cell.width = widths[j]
            if i == 0 and header:
                _shade(cell, NAVY_HEX)
            elif i % 2 == 0:
                _shade(cell, LIGHT_HEX)
            for p in cell.paragraphs:
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.05
                for r in p.runs:
                    _font(r, size, True if (i == 0 and header) else None, RGBColor(0xFF, 0xFF, 0xFF) if (i == 0 and header) else None)


def spacer(d, pts=4):
    p = d.add_paragraph()
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1
    r = p.add_run()
    r.font.size = Pt(pts)
    return p


def no_borders(table):
    tblpr = table._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"), "nil")
        b.append(el)
    tblpr.append(b)
