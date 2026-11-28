from pathlib import Path
import csv,json,sys
sys.stdout.reconfigure(encoding='utf-8')
w=Path.cwd()/'work'
pid=sys.argv[1]
with (w/'主张覆盖索引.tsv').open(encoding='utf-8-sig',newline='') as f:
 rows=[r for r in csv.DictReader(f,delimiter='\t') if r['稿件']==pid and r['含数字或编号']=='True']
ledger=json.loads((w/'台账数据.json').read_text(encoding='utf-8'))
print('### SOURCE FRAGMENTS',pid,len(rows))
for r in rows:
 print(r['清单编号'],r['来源'][:8],r['位置'], '['+r['关联台账编号']+']',r['摘录'])
print('\n### LEDGER',pid)
for e in ledger:
 if e['pid']==pid: print(e['id'],e['verdict'],e['claim'],' -> ',e['fix'])
