from pathlib import Path
import csv, sys

pid = sys.argv[1]
with (Path('work') / '数值全面扫查.tsv').open(encoding='utf-8-sig', newline='') as f:
    rows = [r for r in csv.DictReader(f, delimiter='\t') if r['稿件'] == pid and not r['台账提及编号']]
for r in rows:
    v = r['数值文本']
    if len(v) < 2 and '.' not in v:
        continue
    print(f"{v:>10} | {r['来源片段']} | PDF候选页:{r['抽取文本候选物理页']}")
