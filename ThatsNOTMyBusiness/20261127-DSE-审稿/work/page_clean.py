from pathlib import Path
import re, sys
sys.stdout.reconfigure(encoding='utf-8')
pid=sys.argv[1]
selected={int(x) for x in sys.argv[2:]}
s=(Path('work')/f'DSEJ-D-26-{pid}.txt').read_text(encoding='utf-8')
v=re.split(r'\n\n========== PDF_PHYSICAL_PAGE (\d+) \|[^\n]+==========\n\n',s)
for i in range(1,len(v),2):
 p=int(v[i])
 if p not in selected: continue
 lines=[line for line in v[i+1].splitlines() if not re.fullmatch(r'\s*\d{1,2}\s*',line)]
 print(f'\n===== PDF physical p{p} =====')
 print('\n'.join(lines))
