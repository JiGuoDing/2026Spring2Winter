#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prepare the v2 MD for Feishu markdown import.

Transformations (faithful, no content deletion):
1. Drop the leading H1 line (becomes --title).
2. Convert bare http(s) URLs in prose/table cells to markdown links [url](url).
3. Bold-wrap evidence markers 【实测…】【推导…】【假设…】【待补…】.
Code fences are left untouched.
"""
import re

SRC = "/Users/bytedance/workspace/2026Spring2Winter/MasterGraduationProject/Design/缓存内容深度探索_综合分析_v2.md"
DST = "/Users/bytedance/workspace/2026Spring2Winter/MasterGraduationProject/Design/_feishu_import_v2.md"

with open(SRC, encoding="utf-8") as f:
    text = f.read()

# 1. drop leading H1
lines = text.split("\n")
if lines and lines[0].startswith("# "):
    lines = lines[1:]
while lines and lines[0].strip() == "":
    lines = lines[1:]
text = "\n".join(lines)

# Split out fenced code blocks so we never touch their contents.
parts = re.split(r"(```.*?```)", text, flags=re.DOTALL)

URL_RE = re.compile(r"https?://[^\s\)\]\|，。；）】>]+")
MARKER_RE = re.compile(r"【(实测|推导|假设|待补)[^】]*】")

def transform_prose(s: str) -> str:
    # bare URL -> clickable link (do not double-wrap)
    def link(m):
        url = m.group(0)
        return f"[{url}]({url})"
    s = URL_RE.sub(link, s)
    # bold evidence markers
    s = MARKER_RE.sub(lambda m: f"**{m.group(0)}**", s)
    return s

out = []
for i, part in enumerate(parts):
    if i % 2 == 1:
        out.append(part)  # code fence, verbatim
    else:
        out.append(transform_prose(part))

result = "".join(out)

with open(DST, "w", encoding="utf-8") as f:
    f.write(result)

# stats
n_url = len(URL_RE.findall(text))
n_marker = len(MARKER_RE.findall(text))
print(f"written: {DST}")
print(f"bare urls wrapped: {n_url}")
print(f"markers bolded: {n_marker}")
print(f"total chars: {len(result)}")
