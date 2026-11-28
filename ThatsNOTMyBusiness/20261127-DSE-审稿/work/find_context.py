from pathlib import Path
import re,sys
sys.stdout.reconfigure(encoding='utf-8')
pid=sys.argv[1]; needle=sys.argv[2]
s=(Path('work')/f'DSEJ-D-26-{pid}.txt').read_text(encoding='utf-8')
v=re.split(r'\n\n========== PDF_PHYSICAL_PAGE (\d+) \|[^\n]+==========\n\n',s)
for i in range(1,len(v),2):
 p=int(v[i]); t=re.sub(r'\s+',' ',v[i+1]).strip()
 start=0
 while (idx:=t.lower().find(needle.lower(),start))>=0:
  print('PDFp',p,repr(t[max(0,idx-140):idx+len(needle)+220]))
  start=idx+len(needle)
