from pathlib import Path
import re,sys
sys.stdout.reconfigure(encoding='utf-8')
pid=sys.argv[1]
pages={int(sys.argv[i]) for i in range(2,len(sys.argv))}
s=(Path('work')/f'DSEJ-D-26-{pid}.txt').read_text(encoding='utf-8')
v=re.split(r'\n\n========== PDF_PHYSICAL_PAGE (\d+) \|[^\n]+==========\n\n',s)
for i in range(1,len(v),2):
 n=int(v[i])
 if n in pages: print(f"\n================= PDF physical p{n} =================\n{v[i+1]}")

