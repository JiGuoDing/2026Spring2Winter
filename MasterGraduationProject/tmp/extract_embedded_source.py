# -*- coding: utf-8 -*-
"""Pull the embedded markdown source (textarea#am-source) out of generated HTML reports."""
import os
import re
import html as H
from lxml import html as LH

ROOT = r"C:\workspace\2026Spring2Winter\MasterGraduationProject"
OUT = os.path.join(ROOT, "tmp", "extracted", "sources")
os.makedirs(OUT, exist_ok=True)

FILES = [
    r"第一章_问题背景分析_逻辑草稿.html",
    r"第一章_参考文献问题背景写法分析.html",
    r"Design\20261120_流式Agent缓存_场景价值与本质.html",
    r"Design\OnCall_异质缓存与统一管理动机.html",
    r"Design\OnCall_版本化执行图缓存覆盖模型与算法.html",
    r"Design\20261118_第一章研究背景与问题重构.html",
]

for rel in FILES:
    p = os.path.join(ROOT, rel)
    raw = open(p, "rb").read()
    doc = LH.fromstring(raw)
    ta = doc.xpath("//textarea[@id='am-source']")
    if not ta:
        print(f"[no am-source] {rel}")
        continue
    src = ta[0].text_content()
    name = os.path.splitext(os.path.basename(rel))[0] + ".src.md"
    op = os.path.join(OUT, name)
    with open(op, "w", encoding="utf-8") as f:
        f.write(src)
    print(f"{rel} -> {name}  {len(src)} chars")
