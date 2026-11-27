# -*- coding: utf-8 -*-
import copy
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

SRC = "Q:/workspace/2026Spring2Winter/ThatsNOTMyBusiness/国电南自项目-技术平台/交付物/_raw2.docx"
DST = "Q:/workspace/2026Spring2Winter/ThatsNOTMyBusiness/国电南自项目-技术平台/交付物/集团级多租户技术平台架构设计方案（初版）-v0.1-润色版.docx"

SONG = "宋体"
HEI = "黑体"
YAHEI = "微软雅黑"
LATIN = "Times New Roman"
DARK = RGBColor(0x1F, 0x38, 0x64)
GRAY = RGBColor(0x59, 0x59, 0x59)

doc = Document(SRC)

# ---------- page setup ----------
for s in doc.sections:
    s.page_width = Cm(21.0)
    s.page_height = Cm(29.7)
    s.left_margin = Cm(2.2)
    s.right_margin = Cm(2.2)
    s.top_margin = Cm(2.4)
    s.bottom_margin = Cm(2.2)
    s.header_distance = Cm(1.3)
    s.footer_distance = Cm(1.3)


def set_font(run, ascii_font=LATIN, ea=SONG, size=12, bold=None, color=None, italic=None):
    run.font.name = ascii_font
    run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if italic is not None:
        run.font.italic = italic
    if color is not None:
        run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), ea)
    rfonts.set(qn("w:ascii"), ascii_font)
    rfonts.set(qn("w:hAnsi"), ascii_font)


def style_font(style, ascii_font=LATIN, ea=SONG, size=12, bold=None, color=None):
    style.font.name = ascii_font
    style.font.size = Pt(size)
    if bold is not None:
        style.font.bold = bold
    if color is not None:
        style.font.color.rgb = color
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), ea)
    rfonts.set(qn("w:ascii"), ascii_font)
    rfonts.set(qn("w:hAnsi"), ascii_font)


def para_border_left(p, color="1F3864", size=12):
    pPr = p._p.get_or_add_pPr()
    bdr = OxmlElement("w:pBdr")
    left = OxmlElement("w:left")
    left.set(qn("w:val"), "single")
    left.set(qn("w:sz"), str(size))
    left.set(qn("w:space"), "8")
    left.set(qn("w:color"), color)
    bdr.append(left)
    pPr.append(bdr)


def shade_para(p, fill="F2F2F2"):
    pPr = p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    pPr.append(shd)


# ---------- styles ----------
st = doc.styles
normal = st["Normal"]
style_font(normal, LATIN, SONG, 12)
normal.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
normal.paragraph_format.line_spacing = 1.5
normal.paragraph_format.space_before = Pt(0)
normal.paragraph_format.space_after = Pt(0)
normal.paragraph_format.first_line_indent = Pt(24)

for nm in ("Body Text", "First Paragraph", "Compact", "List Paragraph"):
    try:
        s = st[nm]
        style_font(s, LATIN, SONG, 12)
        s.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        s.paragraph_format.line_spacing = 1.5
        s.paragraph_format.space_before = Pt(0)
        s.paragraph_format.space_after = Pt(6)
        s.paragraph_format.first_line_indent = Pt(24)
    except KeyError:
        pass

h1 = st["Heading 1"]
style_font(h1, YAHEI, YAHEI, 18, True, DARK)
h1.paragraph_format.page_break_before = True
h1.paragraph_format.space_before = Pt(6)
h1.paragraph_format.space_after = Pt(14)
h1.paragraph_format.first_line_indent = Pt(0)
h1.paragraph_format.keep_with_next = True

h2 = st["Heading 2"]
style_font(h2, YAHEI, YAHEI, 14, True, DARK)
h2.paragraph_format.space_before = Pt(14)
h2.paragraph_format.space_after = Pt(6)
h2.paragraph_format.first_line_indent = Pt(0)
h2.paragraph_format.keep_with_next = True

h3 = st["Heading 3"]
style_font(h3, YAHEI, YAHEI, 12, True, RGBColor(0x2E, 0x3B, 0x4E))
h3.paragraph_format.space_before = Pt(10)
h3.paragraph_format.space_after = Pt(4)
h3.paragraph_format.first_line_indent = Pt(0)
h3.paragraph_format.keep_with_next = True

h4 = st["Heading 4"]
style_font(h4, YAHEI, YAHEI, 11.5, True, RGBColor(0x2E, 0x3B, 0x4E))
h4.paragraph_format.space_before = Pt(8)
h4.paragraph_format.space_after = Pt(3)
h4.paragraph_format.first_line_indent = Pt(0)

try:
    tstyle = st["Title"]
    style_font(tstyle, YAHEI, YAHEI, 26, True, DARK)
    tstyle.paragraph_format.first_line_indent = Pt(0)
except KeyError:
    pass

try:
    cap = st["Caption"]
    style_font(cap, HEI, HEI, 9.5, True, RGBColor(0x2E, 0x3B, 0x4E))
    cap.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_before = Pt(8)
    cap.paragraph_format.space_after = Pt(3)
    cap.paragraph_format.first_line_indent = Pt(0)
    cap.paragraph_format.keep_with_next = True
except KeyError:
    pass

# ---------- remap heading levels (chapter = Heading1) ----------
title_par = None
sub_par = None
paras = list(doc.paragraphs)
for p in paras:
    name = p.style.name
    if name == "Heading 1" and title_par is None:
        title_par = p
        p.style = st["Title"]
    elif name == "Heading 2":
        p.style = st["Heading 1"]
    elif name == "Heading 3":
        p.style = st["Heading 2"]
    elif name == "Heading 4":
        p.style = st["Heading 3"]

# subtitle paragraph = first non-empty paragraph after title, before first table
body = doc.element.body
if title_par is not None:
    idx = paras.index(title_par)
    if idx + 1 < len(paras):
        sub_par = paras[idx + 1]
        sub_par.style = st["Normal"]
        for r in sub_par.runs:
            set_font(r, YAHEI, YAHEI, 14, True, GRAY)
        sub_par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sub_par.paragraph_format.first_line_indent = Pt(0)
        sub_par.paragraph_format.space_before = Pt(6)

# ---------- run-level font fix + caption detection ----------
for p in doc.paragraphs:
    nm = p.style.name
    txt = p.text.strip()
    if nm.startswith("Heading") or nm == "Title":
        size = {"Heading 1": 18, "Heading 2": 14, "Heading 3": 12, "Heading 4": 11.5, "Title": 26}.get(nm, 12)
        for r in p.runs:
            set_font(r, YAHEI, YAHEI, size, True, DARK if nm in ("Heading 1", "Heading 2", "Title") else RGBColor(0x2E, 0x3B, 0x4E))
        p.paragraph_format.first_line_indent = Pt(0)
    elif txt.startswith("图 ") and "图示结构说明" in txt:
        head, tail = txt.split("图示结构说明", 1)
        p.text = ""
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.first_line_indent = Pt(0)
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(8)
        r1 = p.add_run(head.strip())
        set_font(r1, HEI, HEI, 9.5, True, RGBColor(0x2E, 0x3B, 0x4E))
        r1.add_break()
        r2 = p.add_run("图示结构说明" + tail)
        set_font(r2, SONG, SONG, 10.5, False, GRAY)
    elif txt.startswith("表 ") or txt.startswith("图 "):
        if len(txt) < 80 and not txt.startswith("表 1-1 能力"):
            p.style = st["Caption"]
            for r in p.runs:
                set_font(r, HEI, HEI, 9.5, True, RGBColor(0x2E, 0x3B, 0x4E))
            p.paragraph_format.first_line_indent = Pt(0)
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif nm == "Block Text":
        for r in p.runs:
            set_font(r, SONG, SONG, 10.5, False, GRAY)
        p.paragraph_format.left_indent = Cm(0.4)
        p.paragraph_format.right_indent = Cm(0.4)
        p.paragraph_format.first_line_indent = Pt(0)
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(10)
        shade_para(p)
        para_border_left(p)

# inline code runs -> monospace
for p in doc.paragraphs:
    for r in p.runs:
        rpr = r._element.rPr
        if rpr is not None and rpr.rFonts is not None and rpr.rFonts.get(qn("w:ascii")) == "Consolas":
            r.font.size = Pt(10.5)
            r.font.name = "Consolas"
            rpr.rFonts.set(qn("w:eastAsia"), SONG)
            break

# ---------- tables ----------
def set_cell_margins(table, top=40, bottom=40, left=80, right=80):
    tblPr = table._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for side, val in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        e = OxmlElement("w:" + side)
        e.set(qn("w:w"), str(val))
        e.set(qn("w:type"), "dxa")
        mar.append(e)
    tblPr.append(mar)


def set_table_borders(table, color="BFBFBF"):
    tblPr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement("w:" + edge)
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), "4")
        e.set(qn("w:space"), "0")
        e.set(qn("w:color"), color)
        borders.append(e)
    tblPr.append(borders)


def shade_cell(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    e = OxmlElement("w:tblHeader")
    e.set(qn("w:val"), "true")
    trPr.append(e)


for ti, t in enumerate(doc.tables):
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = True
    set_table_borders(t)
    set_cell_margins(t)
    hdr = t.rows[0]
    repeat_header(hdr)
    for ri, row in enumerate(t.rows):
        trPr = row._tr.get_or_add_trPr()
        cant = OxmlElement("w:cantSplit")
        trPr.append(cant)
        for cell in row.cells:
            if ri == 0:
                shade_cell(cell, "D9E2F3" if ti > 0 else "D9E2F3")
            for p in cell.paragraphs:
                p.paragraph_format.first_line_indent = Pt(0)
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.15
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                for r in p.runs:
                    set_font(r, LATIN, SONG, 8.5 if len(t.columns) >= 7 else 9, True if ri == 0 else None,
                             RGBColor(0x1F, 0x38, 0x64) if ri == 0 else None)
    # 固定宽度 = 文本栏宽
    tblPr = t._tbl.tblPr
    for old in tblPr.findall(qn("w:tblW")):
        tblPr.remove(old)
    for old in tblPr.findall(qn("w:tblLayout")):
        tblPr.remove(old)
    tblW = OxmlElement("w:tblW")
    tblW.set(qn("w:type"), "dxa")
    tblW.set(qn("w:w"), str(int(16.6 / 2.54 * 1440)))
    tblPr.append(tblW)
    lay = OxmlElement("w:tblLayout")
    lay.set(qn("w:type"), "fixed")
    tblPr.append(lay)

# ---------- cover ----------
def add_par(text="", size=12, bold=False, color=None, ea=SONG, ascii_f=LATIN,
            align=WD_ALIGN_PARAGRAPH.CENTER, before=0, after=0, font_ea=None):
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = 1.3
    if text:
        r = p.add_run(text)
        set_font(r, ascii_f, font_ea or ea, size, bold, color)
    return p


cover = []
cover.append(add_par("", 12, after=0))
cover.append(add_par("国电南京自动化股份有限公司", 12, False, GRAY, YAHEI, before=36, after=4))
cover.append(add_par("技术平台组", 12, False, GRAY, YAHEI, after=80))
cover.append(add_par("集团级多租户技术平台", 30, True, DARK, YAHEI, after=6))
cover.append(add_par("架构设计方案", 30, True, DARK, YAHEI, after=10))
cover.append(add_par("（初版 · v0.1）", 16, False, RGBColor(0x40, 0x40, 0x40), YAHEI, after=18))
cover.append(add_par("—— 面向中国华电集团体系 · 华电睿思数智底座 ——", 13, False, GRAY, YAHEI, after=100))
cover.append(add_par("文档编号：CHD-MTP-ARC-2026-001", 11, False, RGBColor(0x40, 0x40, 0x40), "宋体", before=0, after=6))
cover.append(add_par("版本：v0.1（初版，供 2026-12-03 客户技术交流）", 11, False, RGBColor(0x40, 0x40, 0x40), "宋体", after=6))
cover.append(add_par("编制日期：2026 年 11 月 26 日", 11, False, RGBColor(0x40, 0x40, 0x40), "宋体", after=6))
cover.append(add_par("密级：内部资料，仅限项目相关方传阅", 11, False, RGBColor(0x40, 0x40, 0x40), "宋体", after=0))

# page break paragraph
pb = doc.add_paragraph()
pb.paragraph_format.space_after = Pt(0)
pb.add_run().add_break(WD_BREAK.PAGE)

cover_els = [p._p for p in cover] + [pb._p]
for el in reversed(cover_els):
    body.insert(0, el)

# remove original title/subtitle paragraphs from body (now rendered on cover)
if title_par is not None:
    title_par._p.getparent().remove(title_par._p)
if sub_par is not None:
    sub_par._p.getparent().remove(sub_par._p)

# ---------- TOC before 摘要 ----------
target = None
for p in doc.paragraphs:
    if p.text.strip() == "摘要" and p.style.name == "Heading 1":
        target = p
        break

if target is not None:
    pb2 = target.insert_paragraph_before()
    pb2.paragraph_format.first_line_indent = Pt(0)
    pb2.add_run().add_break(WD_BREAK.PAGE)
    toc_title = target.insert_paragraph_before()
    toc_title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    toc_title.paragraph_format.first_line_indent = Pt(0)
    toc_title.paragraph_format.space_after = Pt(12)
    r = toc_title.add_run("目　录")
    set_font(r, YAHEI, YAHEI, 18, True, DARK)

    tp = target.insert_paragraph_before()
    tp.paragraph_format.first_line_indent = Pt(0)
    run = tp.add_run()
    fldChar = OxmlElement("w:fldChar")
    fldChar.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = 'TOC \\o "1-2" \\h \\z \\u'
    sep = OxmlElement("w:fldChar")
    sep.set(qn("w:fldCharType"), "separate")
    t = OxmlElement("w:t")
    t.text = "（目录将在打开文档后自动生成；若未生成，请右键此处选择“更新域”）"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(fldChar)
    run._r.append(instr)
    run._r.append(sep)
    run._r.append(t)
    run._r.append(end)

# page break after TOC block: insert before target a page-break paragraph
if target is not None:
    brk = target.insert_paragraph_before()
    brk.paragraph_format.first_line_indent = Pt(0)
    brk.add_run().add_break(WD_BREAK.PAGE)


# ---------- TOC styles ----------
from docx.enum.style import WD_STYLE_TYPE
for nm, ind in (("toc 1", 0), ("toc 2", 0.7)):
    try:
        s_ = st[nm]
    except KeyError:
        s_ = st.add_style(nm, WD_STYLE_TYPE.PARAGRAPH)
    style_font(s_, LATIN, SONG, 10.5, nm == "toc 1", RGBColor(0x1F, 0x38, 0x64) if nm == "toc 1" else GRAY)
    s_.paragraph_format.first_line_indent = Pt(0)
    s_.paragraph_format.left_indent = Cm(ind)
    s_.paragraph_format.space_before = Pt(5 if nm == "toc 1" else 0)
    s_.paragraph_format.space_after = Pt(0)
    s_.paragraph_format.line_spacing = Pt(14 if nm == "toc 2" else 17)
    s_.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY

# ---------- 列宽自适应 ----------
TOTAL = 16.6
for t in doc.tables:
    ncol = len(t.columns)
    if ncol < 2:
        continue
    weights = []
    for ci in range(ncol):
        vals = []
        for row in t.rows[:14]:
            try:
                txt = row.cells[ci].text
            except IndexError:
                continue
            vals.append(sum(2 if ord(ch) > 127 else 1 for ch in txt))
        tot_c = sum(min(v, 90) for v in vals) if vals else 8
        weights.append(max(8.0, tot_c ** 0.62))
    tot = sum(weights)
    widths = [max(1.7, TOTAL * w / tot) for w in weights]
    k = TOTAL / sum(widths)
    widths = [w * k for w in widths]
    for ci, w in enumerate(widths):
        t.columns[ci].width = Cm(w)
        for cell in t.columns[ci].cells:
            cell.width = Cm(w)
    t.autofit = False

# ---------- header / footer ----------
def add_field(paragraph, instr, size=9):
    run = paragraph.add_run()
    f1 = OxmlElement("w:fldChar")
    f1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = instr
    f2 = OxmlElement("w:fldChar")
    f2.set(qn("w:fldCharType"), "end")
    run._r.append(f1)
    run._r.append(it)
    run._r.append(f2)
    set_font(run, LATIN, SONG, size, False, GRAY)


sec = doc.sections[0]
sec.different_first_page_header_footer = True

hp = sec.header.paragraphs[0]
hp.text = ""
hp.alignment = WD_ALIGN_PARAGRAPH.LEFT
hp.paragraph_format.first_line_indent = Pt(0)
r1 = hp.add_run("集团级多租户技术平台架构设计方案（初版）　v0.1")
set_font(r1, SONG, SONG, 9, False, GRAY)
hp.add_run("\t\t")
r2 = hp.add_run("内部资料")
set_font(r2, SONG, SONG, 9, False, GRAY)

fp = sec.footer.paragraphs[0]
fp.text = ""
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
fp.paragraph_format.first_line_indent = Pt(0)
r3 = fp.add_run("— ")
set_font(r3, SONG, SONG, 9, False, GRAY)
add_field(fp, " PAGE ")
r4 = fp.add_run(" —")
set_font(r4, SONG, SONG, 9, False, GRAY)

# first page (cover) header/footer blank
sec.first_page_header.paragraphs[0].text = ""
sec.first_page_footer.paragraphs[0].text = ""

# ---------- update fields on open ----------
settings = doc.settings.element
uf = OxmlElement("w:updateFields")
uf.set(qn("w:val"), "true")
settings.append(uf)

doc.save(DST)
print("saved", DST)

# quick verification
d2 = Document(DST)
print("paras", len(d2.paragraphs), "tables", len(d2.tables))
h1c = sum(1 for p in d2.paragraphs if p.style.name == "Heading 1")
h2c = sum(1 for p in d2.paragraphs if p.style.name == "Heading 2")
print("H1", h1c, "H2", h2c)
print("first 8:", [p.text[:30] for p in d2.paragraphs[:8]])
