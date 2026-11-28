from pathlib import Path
from docx import Document
from collections import Counter
import importlib.util, json, re
root=Path.cwd(); w=root/'work'
sp=importlib.util.spec_from_file_location("ledger",str(w/'build_ledger.py')); m=importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
(w/'台账数据.json').write_text(json.dumps(m.entries,ensure_ascii=False,indent=2),encoding='utf-8')
print('COUNTS',Counter(e['pid'] for e in m.entries));print('VERDICTS',Counter(e['verdict'] for e in m.entries))
for name in ['Decision letter for DSE-2026-22.docx','Decision letter for 0807(1)-2.docx']:
 d=Document(root/name)
 lines=[]
 for i,p in enumerate(d.paragraphs):
  if p.text.strip(): lines.append(f'P{i:03} [{p.style.name}] {p.text}')
 for i,t in enumerate(d.tables):
  lines.append('TABLE '+str(i))
  for row in t.rows:
   lines.append(' | '.join(c.text.replace('\n',' / ') for c in row.cells))
 out=w/('待审决定信结构.txt' if 'DSE-2026' in name else '先例决定信结构.txt')
 out.write_text('\n'.join(lines),encoding='utf-8')
 print(name,'paras',len(d.paragraphs),'tables',len(d.tables),'sections',len(d.sections),'chars',sum(len(p.text) for p in d.paragraphs))
