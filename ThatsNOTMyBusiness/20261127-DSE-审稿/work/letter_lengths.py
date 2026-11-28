from pathlib import Path
from docx import Document
import re, statistics, sys
sys.stdout.reconfigure(encoding='utf-8')
for name in ['Decision letter for 0807(1)-2.docx','Decision letter for DSE-2026-22.docx','Decision letter for DSE-2026-22 (复审修订).docx']:
    d=Document(name)
    s='\n'.join(p.text for p in d.paragraphs)
    chunks=re.split(r'Decision for (DSEJ-D-\d{2}-\d+):\s*Desk reject',s,flags=re.I)
    print('\n',name,'desk papers',len(chunks)//2)
    values=[]
    for i in range(1,len(chunks),2):
        content=chunks[i+1]
        words=len(re.findall(r"\b[\w]+(?:[-’'][\w]+)*\b",content))
        sentences=len([x for x in re.split(r'(?<=[.!?])\s+(?=[A-Z])',content.strip()) if x])
        values.append(words)
        print(chunks[i],words,sentences)
    if values: print('word mean',round(statistics.mean(values),1),'median',statistics.median(values),'min',min(values),'max',max(values))
