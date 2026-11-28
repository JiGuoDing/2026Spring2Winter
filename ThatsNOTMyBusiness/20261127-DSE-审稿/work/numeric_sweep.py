from pathlib import Path
import csv,json,re,sys,collections
sys.stdout.reconfigure(encoding='utf-8')
w=Path('work')
rows=list(csv.DictReader((w/'主张覆盖索引.tsv').open(encoding='utf-8-sig',newline=''),delimiter='\t'))
data=json.loads((w/'台账数据.json').read_text(encoding='utf-8'))
pids=['00526','00527','00544','00551','00552','00553','00558','00560','00561','00562']
pattern=re.compile(r'(?<!\w)(?:[+\-−≈~])?\d+(?:,\d{3})*(?:\.\d+)?(?:[eE][+\-]?\d+)?')
cache={}
for pid in pids:
 raw=(w/f'DSEJ-D-26-{pid}.txt').read_text(encoding='utf-8')
 v=re.split(r'\n\n========== PDF_PHYSICAL_PAGE (\d+) \|[^\n]+==========\n\n',raw)
 cache[pid]={int(v[i]):re.sub(r'\s+',' ',v[i+1]) for i in range(1,len(v),2)}
out=[]
for pid in pids:
 src=[r for r in rows if r['稿件']==pid and r['含数字或编号']=='True']
 vals=collections.defaultdict(list)
 for r in src:
  text=r['摘录'].replace(f'DSEJ-D-26-{pid}','')
  for m in pattern.finditer(text):
   value=m.group().lstrip('+−-≈~').replace(',','')
   if value not in vals or r['清单编号'] not in vals[value]: vals[value].append(r['清单编号'])
 for number,ids in vals.items():
  hits=[]
  # Ignore thousands separators for retrieval; a hit is only a lead, not a verdict.
  for page,t in cache[pid].items():
   normalized=t.replace(',','')
   if re.search(r'(?<![\d.])'+re.escape(number)+r'(?![\d.])',normalized): hits.append(str(page))
  led=[e['id'] for e in data if e['pid']==pid and re.search(r'(?<![\d.])'+re.escape(number)+r'(?![\d.])',e['claim'].replace(',',''))]
  out.append({'稿件':pid,'数值文本':number,'来源片段':','.join(ids),'抽取文本候选物理页':','.join(hits),'台账提及编号':','.join(led),'状态':'仅定位待人工判断'})
with (w/'数值全面扫查.tsv').open('w',encoding='utf-8-sig',newline='') as f:
 wr=csv.DictWriter(f,fieldnames=list(out[0]),delimiter='\t');wr.writeheader();wr.writerows(out)
print('tokens',len(out),'no_pdf_hit',sum(not x['抽取文本候选物理页'] for x in out),'no_ledger_mention',sum(not x['台账提及编号'] for x in out))
for pid in pids:
 part=[x for x in out if x['稿件']==pid]
 print(pid,len(part),'no_pdf_hit',sum(not x['抽取文本候选物理页'] for x in part),'no_ledger',sum(not x['台账提及编号'] for x in part))
