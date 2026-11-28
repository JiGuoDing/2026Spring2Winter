from docx import Document
d=Document('Decision letter for DSE-2026-22.docx')
for i,p in enumerate(d.paragraphs):
 print(i, 'runs',len(p.runs),'style',p.style.name,'numpr',bool(p._p.pPr is not None and p._p.pPr.numPr is not None),'texts',[r.text[:55] for r in p.runs])
