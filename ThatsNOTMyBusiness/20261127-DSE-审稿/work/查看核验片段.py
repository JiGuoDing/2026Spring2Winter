from pathlib import Path
import csv,sys
sys.stdout.reconfigure(encoding='utf-8')
pid=sys.argv[1]
rows=list(csv.DictReader((Path('work')/'主张覆盖索引.tsv').open(encoding='utf-8-sig',newline=''),delimiter='\t'))
for r in rows:
    if r['稿件']==pid and (r['含数字或编号']=='True' or len(sys.argv)>2):
        print(r['清单编号'],r['位置'], '['+r['关联台账编号']+']',r['摘录'])
