# -*- coding: utf-8 -*-
"""重建后五项自检。"""
import os
import re
from docx import Document
from docx.oxml.ns import qn

P = r"Q:\workspace\2026Spring2Winter\ThatsNOTMyBusiness\国电南自项目-技术平台\交付物\集团级多租户技术平台架构设计方案（初版）-v0.1-润色版.docx"
doc = Document(P)
paras = doc.paragraphs
texts = [p.text.strip() for p in paras]

toc = [(p.style.name, p.text.strip()) for p in paras if (p.style.name or "").lower().startswith("toc")]
toc1 = [t for s, t in toc if s.lower() == "toc 1"]
toc2 = [t for s, t in toc if s.lower() == "toc 2"]
print("== 1. 目录 ==")
print("TOC 段落:", len(toc), " toc1:", len(toc1), " toc2:", len(toc2))
for t in toc1:
    print("   ", t)
hit = [t for t in toc1 if t.startswith("附录 F")]
print("附录 F 目录行:", hit, "| 页码非零:", bool(hit and re.search(r"\t\s*[1-9]\d*$", hit[0])))

print("\n== 2. 附录 F 正文 ==")
heads = [t for t in texts if re.match(r"^F\.[1-8]\s", t) and "\t" not in t]
print("F.x 标题数:", len(heads))
for h in heads:
    print("   ", h)
f8 = None
for i, t in enumerate(doc.tables):
    h = [c.text.strip() for c in t.rows[0].cells]
    if h[:2] == ["#", "冲突点"]:
        f8 = (i, h, len(t.rows), len(t.columns))
print("F.8 表:", f8)
print("F.8 第 1 行数据:", [c.text.strip() for c in doc.tables[f8[0]].rows[1].cells] if f8 else None)
print("表格总数:", len(doc.tables))

print("\n== 3. 方括号编号 ==")
alltext = "\n".join(texts)
for t in doc.tables:
    for r in t.rows:
        for c in r.cells:
            alltext += "\n" + c.text
print("N 组编号出现次数:", len(re.findall(r"\[N-\d{2}\]", alltext)), " 种类:", sorted(set(re.findall(r"\[N-\d{2}\]", alltext))))
print("G 组出现次数:", len(re.findall(r"\[G-\d{2}\]", alltext)))
print("方括号编号总种类:", len(set(re.findall(r"\[[A-Z]-\d{1,2}\]", alltext))))
hl = doc.element.body.findall(".//" + qn("w:hyperlink"))
print("w:hyperlink 元素:", len(hl))
bad = ["".join(n.text or "" for n in h.iter(qn("w:t"))) for h in hl
       if re.search(r"\[[A-Z]-\d{1,2}\]", "".join(n.text or "" for n in h.iter(qn("w:t"))))]
print("超链接文字含编号:", bad)
print("锚点全为 _Toc:", all((h.get(qn("w:anchor")) or "").startswith("_Toc") for h in hl))
print("外部链接 rel 数:", len([r for r in doc.part.rels.values() if r.is_external]))
print("自动编号(numPr/numId)段落数:", len(doc.element.body.findall(".//" + qn("w:numPr"))))

print("\n== 4. HNC ==")
hnc = [t for t in texts if t.startswith("关于 HNC")]
print("段:", hnc[0][-60:] if hnc else "缺失")
print("含“既已归档”:", bool(hnc) and "既已归档" in hnc[0], "| 含【待确认-I01】:", bool(hnc) and "【待确认-I01" in hnc[0])
print("全文残留“已确认归档”:", sum(1 for t in texts if "已确认归档" in t))

print("\n== 5. 其他 ==")
print("docx 字节:", os.path.getsize(P))
cnt = {}
for p in paras:
    cnt[p.style.name] = cnt.get(p.style.name, 0) + 1
for k in ("Heading 1", "Heading 2", "Heading 3", "Heading 4"):
    print(k, cnt.get(k, 0))
print("一级项（章节+附录）:", len([t for t in toc1 if re.match(r"^(第 \d+ 章|附录 [A-F])", t)]))
print("摘要标题:", [t for t in texts if t.startswith("四、") and "\t" not in t])
print("收益段:", [t for t in texts if t.startswith("收益也要说清")])
print("四笔账:", [t[:6] for t in texts if re.match(r"^(资源账|人力账|治理账|可复制账)", t)])
blocks = [p for p in paras if p.style.name == "Block Text" and "本章依据" in p.text]
print("本章依据框:", len(blocks), [p.text.count("\n") + 1 for p in blocks])
