from pathlib import Path
import re,sys,json
sys.stdout.reconfigure(encoding='utf-8')
queries=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
for pid,needles in queries.items():
 print('\n###',pid)
 raw=(Path('work')/f'DSEJ-D-26-{pid}.txt').read_text(encoding='utf-8')
 parts=re.split(r'\n\n========== PDF_PHYSICAL_PAGE (\d+) \|[^\n]+==========\n\n',raw)
 pages={int(parts[i]):re.sub(r'\s+',' ',parts[i+1]).strip() for i in range(1,len(parts),2)}
 for needle in needles:
  print('\n--',needle)
  n=0
  for page,t in pages.items():
   for m in re.finditer(re.escape(needle),t,re.I):
    print('p',page,repr(t[max(0,m.start()-80):min(len(t),m.end()+150)]))
    n+=1
    if n>=8: break
   if n>=8: break
  if not n: print('not found')
