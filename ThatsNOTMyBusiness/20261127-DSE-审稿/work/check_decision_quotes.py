from pathlib import Path
import re

root=Path.cwd()
review=(root/'复审-决策复核.md').read_text(encoding='utf-8')
review=review.split('## 十篇逐篇复核',1)[1].split('## 横向一致性',1)[0]
blocks=re.split(r'(?m)^### (005\d\d)[^\n]*\n',review)
for i in range(1,len(blocks),2):
    pid,block=blocks[i],blocks[i+1]
    raw=(root/'work'/f'DSEJ-D-26-{pid}.txt').read_text(encoding='utf-8')
    norm=re.sub(r'\s+',' ',raw)
    for quote in re.findall(r'“([^”]+)”',block):
        if not re.search(r'[A-Za-z]',quote): continue
        if len(quote.split())>25: print('OVER_25',pid,len(quote.split()),quote)
        elif quote not in norm: print('NOT_IN_PDF',pid,quote)
