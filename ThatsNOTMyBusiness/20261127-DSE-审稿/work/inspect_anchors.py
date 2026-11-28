from pathlib import Path
import re, json, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
w=Path('work')
data=json.loads((w/'台账数据.json').read_text(encoding='utf-8'))
for pid in sorted({e['pid'] for e in data}):
    raw=(w/f'DSEJ-D-26-{pid}.txt').read_text(encoding='utf-8')
    xs=re.split(r'\n\n========== PDF_PHYSICAL_PAGE (\d+) \|[^\n]+==========\n\n',raw)
    pages={int(xs[i]):xs[i+1] for i in range(1,len(xs),2)}
    print('\n###',pid)
    for n in sorted({a[0] for e in data if e['pid']==pid for a in e['anchors']}):
        lines=[re.sub(r'\s+',' ',x).strip() for x in pages[n].splitlines() if x.strip()]
        key=[]
        for line in lines:
            if re.match(r'^(?:\d(?:\.\d+){1,3}\.?\s+\D|(?:Table|Fig(?:ure)?\.|Appendix)\s*[\dA-Z])',line,re.I): key.append(line[:110])
        print(n,' / '.join(key[:5]),' ; opening=', ' '.join(lines[:2])[:110])
