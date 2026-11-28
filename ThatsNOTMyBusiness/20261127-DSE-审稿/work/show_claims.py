import csv,sys
sys.stdout.reconfigure(encoding='utf-8')
with open('work/一轮主张清单-待逐条核对.tsv',encoding='utf-8-sig',newline='') as f:
 d=list(csv.DictReader(f,delimiter='\t'))
for pid in sys.argv[1:]:
 print('\n========= '+pid+' ============')
 for r in d:
  if r['稿件']==pid: print(r['清单编号'],r['来源'][:8],r['位置'],r['摘录'])
