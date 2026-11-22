# -*- coding: utf-8 -*-
"""Extract readable text from generated HTML reports (Answer-me-with-HTML style)."""
import os
import re
import sys
from lxml import html as LH

SRC = [
    r"第一章_问题背景分析_逻辑草稿.html",
    r"第一章_参考文献问题背景写法分析.html",
    r"Design\20261120_流式Agent缓存_场景价值与本质.html",
    r"Design\OnCall_异质缓存与统一管理动机.html",
    r"Design\OnCall_版本化执行图缓存覆盖模型与算法.html",
    r"Design\20261118_第一章研究背景与问题重构.html",
    r"第一章_改后初稿_设计图解.html",
]
ROOT = r"C:\workspace\2026Spring2Winter\MasterGraduationProject"
OUT = os.path.join(ROOT, "tmp", "extracted")
os.makedirs(OUT, exist_ok=True)

BLOCK = {"p", "div", "section", "article", "li", "tr", "h1", "h2", "h3", "h4",
         "h5", "h6", "blockquote", "pre", "table", "ul", "ol", "figcaption",
         "header", "footer", "main", "aside", "dd", "dt", "dl", "br"}


def clean(s):
    s = s.replace("\u200b", "")
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


def walk(node, depth=0, out=None):
    if out is None:
        out = []
    tag = node.tag if isinstance(node.tag, str) else ""
    if tag in ("script", "style", "svg", "noscript", "head"):
        return out
    if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
        lvl = int(tag[1])
        txt = clean(" ".join(node.itertext()))
        if txt:
            out.append("\n" + "#" * lvl + " " + txt + "\n")
        return out
    if tag == "li":
        txt = clean(" ".join(node.itertext()))
        if txt:
            out.append("- " + txt)
        return out
    if tag == "tr":
        cells = []
        for c in node.iter():
            if isinstance(c.tag, str) and c.tag in ("td", "th"):
                t = clean(" ".join(c.itertext()))
                if t:
                    cells.append(t)
        if cells:
            out.append("| " + " | ".join(cells) + " |")
        return out
    if tag == "pre":
        txt = node.text_content()
        if clean(txt):
            out.append("\n```\n" + txt.strip() + "\n```\n")
        return out
    if tag == "br":
        out.append("")
        return out
    # container: recurse
    if node.text and clean(node.text):
        out.append(clean(node.text))
    for child in node:
        walk(child, depth + 1, out)
        if child.tail and clean(child.tail):
            out.append(clean(child.tail))
    if tag in BLOCK:
        out.append("")
    return out


def extract(path):
    with open(path, "rb") as f:
        raw = f.read()
    doc = LH.fromstring(raw)
    for bad in doc.xpath("//script|//style|//svg|//noscript"):
        bad.getparent().remove(bad)
    body = doc.body
    lines = walk(body)
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # dedupe consecutive identical lines (noise from nested containers)
    res = []
    for ln in text.split("\n"):
        if res and ln.strip() and ln.strip() == res[-1].strip():
            continue
        res.append(ln)
    return "\n".join(res).strip()


for rel in SRC:
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        print("MISSING", rel)
        continue
    txt = extract(p)
    name = os.path.splitext(os.path.basename(rel))[0] + ".txt"
    op = os.path.join(OUT, name)
    with open(op, "w", encoding="utf-8") as f:
        f.write(txt)
    print(f"{rel} -> {name}  {len(txt)} chars")
