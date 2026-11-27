# -*- coding: utf-8 -*-
"""把润色结果回填到原 Markdown，表格/标题/结构零改动。"""
import json, re, sys, os, shutil

BASE = r"Q:/workspace/2026Spring2Winter/ThatsNOTMyBusiness/国电南自项目-技术平台/交付物"
SRC = os.path.join(BASE, "多租户平台架构设计方案-v0.1.md")
DST = os.path.join(BASE, "多租户平台架构设计方案-v0.1-润色版.md")
OUTDIR = os.path.join(BASE, "润色", "out")

meta = json.load(open(os.path.join(BASE, "润色", "in", "meta.json"), encoding="utf8"))
id2line = {m["id"]: m["line"] for m in meta}

new = {}
problems = []
for i in range(1, 7):
    p = os.path.join(OUTDIR, "batch-%d.md" % i)
    if not os.path.exists(p):
        problems.append("缺失批次文件 batch-%d.md" % i)
        continue
    txt = open(p, encoding="utf8").read()
    blocks = re.split(r"^@@(P\d{3})@@\s*$", txt, flags=re.M)
    # blocks: ['', id1, body1, id2, body2, ...]
    for j in range(1, len(blocks), 2):
        pid = blocks[j]
        body = blocks[j + 1]
        body = "\n".join(l.strip() for l in body.strip().split("\n") if l.strip())
        if not body:
            problems.append("%s 内容为空" % pid)
            continue
        if pid in new and new[pid] != body:
            problems.append("%s 重复且内容不同" % pid)
        new[pid] = body

missing = [pid for pid in id2line if pid not in new]
extra = [pid for pid in new if pid not in id2line]
if missing:
    problems.append("未润色条目: " + ",".join(sorted(missing)[:20]) + ("..." if len(missing) > 20 else ""))
if extra:
    problems.append("多余条目: " + ",".join(sorted(extra)[:20]))

lines = open(SRC, encoding="utf8").read().split("\n")
orig_cjk = sum(len(re.findall(r"[\u4e00-\u9fa5]", lines[i])) for i in id2line.values())
new_cjk = 0
changed = 0
for pid, ln in id2line.items():
    if pid not in new:
        continue
    t = new[pid]
    new_cjk += len(re.findall(r"[\u4e00-\u9fa5]", t))
    if t != lines[ln].strip():
        changed += 1
    lines[ln] = t

open(DST, "w", encoding="utf8").write("\n".join(lines))

print("回填条目", changed, "/", len(id2line))
print("原文汉字", orig_cjk, "润色后", new_cjk, "变动 %+.1f%%" % ((new_cjk - orig_cjk) / orig_cjk * 100))
print("输出", DST)
if problems:
    print("\n!! 问题:")
    for p in problems:
        print("  -", p)
else:
    print("无缺漏")
