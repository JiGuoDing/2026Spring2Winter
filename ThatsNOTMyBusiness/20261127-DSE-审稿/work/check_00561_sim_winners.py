from pathlib import Path
import re,csv
raw=(Path('work')/'DSEJ-D-26-00561.txt').read_text(encoding='utf-8')
parts=re.split(r'\n\n========== PDF_PHYSICAL_PAGE (\d+) \|[^\n]+==========\n\n',raw)
text=re.sub(r'\s+',' ','\n'.join(parts[2::2]))
titles=['Table 2. One-step-ahead forecasting results for Simulation 1','Table 3. Two-step-ahead forecasting results for Simulation 1','Table 4. Three-step-ahead forecasting results for Simulation 1','Table 5. One-step-ahead forecasting results for Simulation 2','Table 6. Multi-step-ahead (h = 2, 3) forecasting results for Simulation 2','Table 7. One-step-ahead forecasting results for Simulation 3','Table 8. Multi-step-ahead (h = 2, 3) forecasting results for Simulation 3']
names=['MTF-MSE','ARIMA','NNET-AR','LSTM','PatchTST','TimesNet','DLinear','N-BEATS','Informer','LightGBM','XGBoost','ExtraTrees','Random Forest','GBDT + flattened MTF']
records=[]
for i,title in enumerate(titles):
 start=text.index(title)
 end=text.index(titles[i+1],start+len(title)) if i+1<len(titles) else len(text)
 body=text[start:end]
 width=4 if i in (4,6) else 2
 vals={}
 for model in names:
  match=re.search(re.escape(model)+r'\s+'+r'\s+'.join([r'(\d+\.\d{6})']*width),body)
  assert match,(title,model)
  vals[model]=list(map(float,match.groups()))
 for k in range(0,width,2):
  h={2:[1],3:[2],4:[3],5:[1],6:[2,3],7:[1],8:[2,3]}[i+2][k//2]
  for j,metric in enumerate(['MAPE','MASE']):
   best=min(vals,key=lambda m:vals[m][k+j])
   records.append([i+2,h,metric,best,f'{vals[best][k+j]:.6f}',f'{vals["MTF-MSE"][k+j]:.6f}'])
with (Path('work')/'00561-模拟结果逐项复算.tsv').open('w',encoding='utf-8-sig',newline='') as f:
 out=csv.writer(f,delimiter='\t');out.writerow(['表','步长','指标','最优方法','最优值','MTF-MSE']);out.writerows(records)
for row in records:print(*row)
