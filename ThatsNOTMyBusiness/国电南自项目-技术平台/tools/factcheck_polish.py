# -*- coding: utf-8 -*-
"""逐条比对：润色前后数字/编号/标记是否一致。"""
import re, json, os

BASE = r"Q:/workspace/2026Spring2Winter/ThatsNOTMyBusiness/国电南自项目-技术平台/交付物"
meta = json.load(open(os.path.join(BASE, "润色", "in", "meta.json"), encoding="utf8"))
lines = open(os.path.join(BASE, "多租户平台架构设计方案-v0.1.md"), encoding="utf8").read().split("\n")

pol = {}
for i in range(1, 7):
    txt = open(os.path.join(BASE, "润色", "out", "batch-%d.md" % i), encoding="utf8").read()
    b = re.split(r"^@@(P\d{3})@@\s*$", txt, flags=re.M)
    for j in range(1, len(b), 2):
        pol[b[j]] = "\n".join(l.strip() for l in b[j + 1].strip().split("\n") if l.strip())

num = lambda s: re.findall(r"\d+(?:\.\d+)?", s)
tags = lambda s: re.findall(r"【[^】]*】", s)
xref = lambda s: re.findall(r"§\d+(?:\.\d+)?|表\s*\d+-\d+|图\s*\d+-\d+|[A-F]-\d+|Q-\d+|M-\d|NFR-\d+|V-\d+|H-\d+|R-\d+|T\d\d|I\d\d|P\d", s)
cjk = lambda s: len(re.findall(r"[\u4e00-\u9fa5]", s))

from collections import Counter
bad = []
for m in meta:
    pid, ln = m["id"], m["line"]
    o = lines[ln].strip()
    n = pol.get(pid, "")
    if not n:
        bad.append((pid, "缺失", "", ""))
        continue
    if Counter(num(o)) != Counter(num(n)):
        miss = Counter(num(o)) - Counter(num(n))
        add = Counter(num(n)) - Counter(num(o))
        bad.append((pid, "数字差异", dict(miss), dict(add)))
    if Counter(tags(o)) != Counter(tags(n)):
        bad.append((pid, "占位符差异", Counter(tags(o)) - Counter(tags(n)), Counter(tags(n)) - Counter(tags(o))))
    if Counter(xref(o)) != Counter(xref(n)):
        bad.append((pid, "交叉引用差异", dict(Counter(xref(o)) - Counter(xref(n))), dict(Counter(xref(n)) - Counter(xref(o)))))
    if o.count("**") != n.count("**"):
        bad.append((pid, "加粗标记数 %d->%d" % (o.count("**"), n.count("**")), "", ""))
    if cjk(o) and abs(cjk(n) - cjk(o)) / cjk(o) > 0.15:
        bad.append((pid, "长度 %d->%d (%+.0f%%)" % (cjk(o), cjk(n), (cjk(n) - cjk(o)) / cjk(o) * 100), "", ""))
    if n.startswith("- ") != o.startswith("- ") or re.match(r"^\d+\.", n) != re.match(r"^\d+\.", o):
        bad.append((pid, "列表格式变化", "", ""))

if bad:
    for b in bad:
        print(" | ".join(str(x) for x in b))
    print("共", len(bad), "条需人工看")
else:
    print("全部一致：数字、占位符、交叉引用、加粗标记、列表格式、长度")
