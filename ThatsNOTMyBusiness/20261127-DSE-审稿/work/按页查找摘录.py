from pathlib import Path
import re,sys
sys.stdout.reconfigure(encoding='utf-8')
pid=sys.argv[1]
raw=(Path('work')/f'DSEJ-D-26-{pid}.txt').read_text(encoding='utf-8')
parts=re.split(r'\n\n========== PDF_PHYSICAL_PAGE (\d+) \|[^\n]+==========\n\n',raw)
pages={int(parts[i]):re.sub(r'\s+',' ',parts[i+1]).strip() for i in range(1,len(parts),2)}
for query in sys.argv[2:]:
    print('\nQUERY',query)
    for p,t in pages.items():
        for m in list(re.finditer(re.escape(query),t,re.I))[:3]:
            print('P',p,repr(t[max(0,m.start()-80):min(len(t),m.end()+160)]))
