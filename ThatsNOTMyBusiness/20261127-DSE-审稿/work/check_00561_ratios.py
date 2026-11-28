from pathlib import Path
import csv
import re

raw = (Path('work') / 'DSEJ-D-26-00561.txt').read_text(encoding='utf-8')
pages = re.split(r'\n\n========== PDF_PHYSICAL_PAGE (\d+) \|[^\n]+==========\n\n', raw)
all_text = '\n'.join(pages[2::2])
text = re.sub(r'\s+', ' ', all_text)
titles = [
    'Table 2. One-step-ahead forecasting results for Simulation 1',
    'Table 3. Two-step-ahead forecasting results for Simulation 1',
    'Table 4. Three-step-ahead forecasting results for Simulation 1',
    'Table 5. One-step-ahead forecasting results for Simulation 2',
    'Table 6. Multi-step-ahead (h = 2, 3) forecasting results for Simulation 2',
    'Table 7. One-step-ahead forecasting results for Simulation 3',
    'Table 8. Multi-step-ahead (h = 2, 3) forecasting results for Simulation 3',
]
models = ['MTF-MSE', 'PatchTST', 'TimesNet', 'DLinear', 'N-BEATS', 'Informer',
          'LightGBM', 'XGBoost', 'ExtraTrees', 'Random Forest', 'GBDT + flattened MTF']
data = {}
for ix, title in enumerate(titles):
    start = text.find(title)
    assert start >= 0, title
    end = text.find(titles[ix + 1], start + len(title)) if ix + 1 < len(titles) else len(text)
    section = text[start:end]
    n = 4 if ix in (4, 6) else 2
    data[ix + 2] = {}
    for model in models:
        pat = re.escape(model) + r'\s+' + r'\s+'.join([r'([0-9]+\.[0-9]{6})'] * n)
        matches = list(re.finditer(pat, section))
        assert matches, (title, model)
        data[ix + 2][model] = tuple(float(x) for x in matches[0].groups())

checks = []
ratio_differences = []
paired_checks = []
detail = []
scalar_detail = []
for table, rows in data.items():
    for k in range(0, len(rows['MTF-MSE']), 2):
        horizon = {2:[1],3:[2],4:[3],5:[1],6:[2,3],7:[1],8:[2,3]}[table][k//2]
        base = rows['MTF-MSE'][k + 1] / rows['MTF-MSE'][k]
        for model in models[1:]:
            v = rows[model]
            delta = abs(v[k + 1] / v[k] - base)
            ratio_differences.append((delta, table, horizon, model))
            detail.append([table,horizon,model,f'{v[k]:.6f}',f'{v[k+1]:.6f}',
                           f'{base:.8f}',f'{v[k+1]/v[k]:.8f}',f'{delta:.8f}'])
        for ref, group, factors in [
            ('LightGBM', ['LightGBM', 'XGBoost', 'ExtraTrees', 'Random Forest'], [1,1.03,1.06,1.09]),
            ('PatchTST', ['PatchTST', 'TimesNet', 'DLinear', 'N-BEATS', 'Informer'], [1,1.04,1.07,1.10,1.16]),
        ]:
            for measure in (k, k + 1):
                values = sorted(rows[m][measure] for m in group)
                expected = sorted(rows[ref][measure] * factor for factor in factors)
                worst = max(abs(a-b) for a,b in zip(values,expected))
                checks.append((worst, table, horizon, ref, measure % 2))
            for model in group:
                factor = min(factors, key=lambda f: abs(rows[model][k] - rows[ref][k] * f))
                residual = abs(rows[model][k+1] - rows[ref][k+1] * factor)
                paired_checks.append((residual, table, horizon, model, factor))
                scalar_detail.append([table,horizon,ref,model,f'{factor:.2f}',
                    f'{rows[ref][k]:.6f}',f'{rows[model][k]:.6f}',
                    f'{abs(rows[model][k]-rows[ref][k]*factor):.8f}',
                    f'{rows[ref][k+1]:.6f}',f'{rows[model][k+1]:.6f}',f'{residual:.8f}'])

assert len(detail)==90
assert len(scalar_detail)==81
assert max(x[0] for x in ratio_differences)<0.0000131
assert max(x[0] for x in checks)<0.000000961
assert max(x[0] for x in paired_checks)<0.000000961
with (Path('work')/'00561-比值逐项复算.tsv').open('w',encoding='utf-8-sig',newline='') as f:
    out=csv.writer(f,delimiter='\t')
    out.writerow(['原文表号','预测步长','对照方法','MAPE','MASE','本文方法的MASE除以MAPE','对照的MASE除以MAPE','两比值绝对差'])
    out.writerows(detail)
with (Path('work')/'00561-倍率逐项复算.tsv').open('w',encoding='utf-8-sig',newline='') as f:
    out=csv.writer(f,delimiter='\t')
    out.writerow(['原文表号','预测步长','参照模型','模型','倍率','参照MAPE','模型MAPE','MAPE绝对残差','参照MASE','模型MASE','MASE绝对残差'])
    out.writerows(scalar_detail)

print('Table/horizon pairs:', sum(len(r['MTF-MSE'])//2 for r in data.values()))
print('Largest absolute MASE/MAPE ratio discrepancies:', sorted(ratio_differences,reverse=True)[:12])
print('Largest scalar-multiplier absolute numeric residuals:', sorted(checks,reverse=True)[:12])
print('Largest paired MAPE/MASE multiplier residuals:', sorted(paired_checks,reverse=True)[:12])
for table, rows in data.items():
    print('Table', table, 'MTF-MSE',rows['MTF-MSE'],'LightGBM',rows['LightGBM'],'PatchTST',rows['PatchTST'])
