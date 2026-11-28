from pathlib import Path
from decimal import Decimal
from itertools import combinations
import csv, re

root = Path.cwd()
text = (root / 'work' / 'DSEJ-D-26-00558.txt').read_text(encoding='utf-8')
pages = re.split(r'\n\n========== PDF_PHYSICAL_PAGE (\d+) \|[^\n]+==========\n\n', text)
p14 = re.sub(r'\s+', ' ', dict(zip(pages[1::2], pages[2::2]))['14'])
models = ['Qwen3-8B', 'Qwen3-235B-A22B', 'Llama 3.1 8B', 'Llama 3.3 70B', 'DeepSeek-Flash', 'GPT-5-mini']
datasets = ['MuSiQue', '2WikiMHQA', 'HotpotQA']
number = r'(\d+\.\d+)%\s+(\d+\.\d+)%\s+\(\+(\d+\.\d+)\)'
results = []
for model in models:
    match = re.search(re.escape(model) + r'\s+' + r'\s+'.join([number]*3), p14)
    if not match:
        raise ValueError(model)
    for i, dataset in enumerate(datasets):
        before, after, reported = map(Decimal, match.groups()[3*i:3*i+3])
        computed = after-before
        assert computed == reported
        results.append({'模型': model, '基准': dataset, '原分数%': str(before), '清洗后%': str(after), '所报增加pp': str(reported), '复算增加pp': str(computed)})
reversals = []
for dataset in datasets:
    group = {x['模型']: x for x in results if x['基准'] == dataset}
    for a, b in combinations(models, 2):
        before = Decimal(group[a]['原分数%'])-Decimal(group[b]['原分数%'])
        after = Decimal(group[a]['清洗后%'])-Decimal(group[b]['清洗后%'])
        if before * after < 0:
            reversals.append((dataset, a, b))
assert len(results)==18 and len(reversals)==3
assert min(Decimal(x['复算增加pp']) for x in results)==Decimal('3.9')
assert max(Decimal(x['复算增加pp']) for x in results)==Decimal('31.1')
out = root/'work'/'00558-Table1逐项复算.tsv'
with out.open('w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=list(results[0]), delimiter='\t')
    writer.writeheader()
    writer.writerows(results)
print('18/18 deltas matched; 3/45 ranking reversals')
for item in reversals:
    print(item)
