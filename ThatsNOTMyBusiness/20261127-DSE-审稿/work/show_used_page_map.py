import json,csv,sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
d=json.loads(Path('work/台账数据.json').read_text(encoding='utf-8'))
mp={}
with open('work/页码映射-校核.tsv',encoding='utf-8-sig',newline='') as f:
 for row in csv.DictReader(f,delimiter='\t'):
  mp[(row['稿件'][-5:],int(row['PDF物理页']))]=row['原文实际印刷页码']
for pid in sorted(set(e['pid'] for e in d)):
 pages=sorted(set(a[0] for e in d if e['pid']==pid for a in e['anchors']))
 print(pid,[(p,mp.get((pid,p),'?')) for p in pages])
