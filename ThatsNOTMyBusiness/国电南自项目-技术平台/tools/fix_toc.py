# -*- coding: utf-8 -*-
"""第二遍：Word 已生成目录后，统一 toc 1/toc 2 样式（Word 内置样式按 styleId 匹配，python-docx 预建不生效）。"""
import sys
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

PATH = sys.argv[1]
doc = Document(PATH)


def style_font(style, ascii_font, ea, size, bold=None, color=None):
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


n = 0
for s in doc.styles:
    nm = (s.name or "").strip().lower()
    if nm in ("toc 1", "toc 2", "toc 3"):
        lvl = nm[-1]
        style_font(s, "Times New Roman", "宋体", 10.5,
                   bold=(lvl == "1"),
                   color=RGBColor(0x1F, 0x38, 0x64) if lvl == "1" else RGBColor(0x59, 0x59, 0x59))
        pf = s.paragraph_format
        pf.first_line_indent = Pt(0)
        pf.left_indent = Cm(0 if lvl == "1" else 0.75)
        pf.space_before = Pt(6 if lvl == "1" else 0)
        pf.space_after = Pt(0)
        pf.line_spacing = Pt(17 if lvl == "1" else 14)
        pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        n += 1

doc.save(PATH)
print("formatted toc styles:", n)
