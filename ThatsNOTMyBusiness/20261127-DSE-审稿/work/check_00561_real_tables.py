from pathlib import Path
from collections import defaultdict
import csv, math, re, statistics

raw = Path('work/DSEJ-D-26-00561.txt').read_text(encoding='utf-8')
parts = re.split(r'\n\n========== PDF_PHYSICAL_PAGE (\d+) \|[^\n]+==========\n\n', raw)
pages = {int(parts[i]): re.sub(r'\s+', ' ', parts[i+1]).strip() for i in range(1, len(parts), 2)}
datasets = ['Beijing PM2.5 concentration', 'CSI 500 index', 'Shandong township temperature', 'ETTh1', 'ETTm2', 'Electricity (ECL)', 'Traffic', 'ILI']
models = ['MTF-MSE','ARIMA','NNET-AR','LSTM','PatchTST','TimesNet','DLinear','N-BEATS','Informer','LightGBM','XGBoost','ExtraTrees','Random Forest','GBDT + flattened MTF']
rows=[]
for metric,page,table in [('MAPE',15,'Table 10.'),('MASE',16,'Table 11.')]:
    text=pages[page].split(table,1)[1]
    for name in datasets:
        pattern = re.escape(name) + r'\s+' + r'\s+'.join([r'([0-9]+\.[0-9]{6})']*14)
        matches = list(re.finditer(pattern,text))
        assert len(matches)==3, (metric,name,len(matches))
        for i,m in enumerate(matches,1):
            vals=[float(x) for x in m.groups()]
            best=min(range(1,14),key=lambda j:vals[j])
            rows.append({'metric':metric,'dataset':name,'horizon':i,'values':vals,'best_rival':models[best],
                         'reduction':100*(vals[best]-vals[0])/vals[best]})
assert len(rows)==48
with Path('work/00561-真实数据逐项复算.tsv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f,delimiter='\t'); w.writerow(['metric','dataset','horizon']+models+['best_rival','reduction_percent'])
    for r in rows: w.writerow([r['metric'],r['dataset'],r['horizon']]+r['values']+[r['best_rival'],f"{r['reduction']:.8f}"])
for metric in ('MAPE','MASE'):
    rr=[r for r in rows if r['metric']==metric]
    wins=[r for r in rr if r['values'][0]<min(r['values'][1:])]
    print(metric,'wins',len(wins),'exceptions',[(r['dataset'],r['horizon'],r['values'][0],min(r['values'][1:])) for r in rr if r not in wins])
    print('horizon means', [round(statistics.mean(r['reduction'] for r in rr if r['horizon']==h),6) for h in (1,2,3)])
red=[r['reduction'] for r in rows]
print('pooled reduction mean',statistics.mean(red),'SD',statistics.stdev(red),'95ci_using_t47=2.011741', (statistics.mean(red)-2.011741*statistics.stdev(red)/math.sqrt(48),statistics.mean(red)+2.011741*statistics.stdev(red)/math.sqrt(48)))
ranks=[]
for r in rows:
    v=r['values']; ranks.append([1+sum(x < y for x in v) for y in v])
avgr=[statistics.mean(rank[i] for rank in ranks) for i in range(14)]
friedman=12*len(rows)/(14*15)*sum(x*x for x in avgr)-3*len(rows)*15
print('mean ranks',dict(zip(models,avgr)),'Friedman chi2',friedman)
diff=[min(r['values'][1:])-r['values'][0] for r in rows]
t=statistics.mean(diff)/(statistics.stdev(diff)/math.sqrt(len(diff)))
sorted_abs=sorted((abs(x),i) for i,x in enumerate(diff)); rank_by_i=[0]*len(diff)
for j,(_,i) in enumerate(sorted_abs,1): rank_by_i[i]=j
wplus=sum(rank_by_i[i] for i,x in enumerate(diff) if x>0)
print('raw strongest-rival paired t',t,'W positive',wplus,'negative cases',sum(x<0 for x in diff))
