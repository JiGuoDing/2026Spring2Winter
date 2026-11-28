from pathlib import Path
import csv
import math

w = Path('work')
# PDF 00553 p.9, Tables 1 and 2: validation accuracy is maximized; FLOPs and
# parameter count are minimized. This comparison uses displayed values only.
models = [
    ('Subnet #1',40.37,9.82,46.35), ('Subnet #2',43.65,10.05,46.87),
    ('Subnet #3',38.98,6.92,47.13), ('Subnet #4',56.57,19.63,65.42),
    ('Subnet #5',58.92,20.87,68.02), ('Subnet #6',60.34,58.03,83.90),
    ('Subnet #7',66.65,52.28,209.74), ('Subnet #8',80.18,55.80,224.15),
    ('Subnet #9',63.84,35.09,305.76),
    ('BiNAS-Prune',63.84,22.68,57.19), ('OFA-NAS',71.16,71.63,128.45),
    ('Shallow CNN',68.86,18.50,19.64), ('LeNet-5',71.47,4.20,59.47),
    ('Depthwise-Bottleneck CNN',55.25,8.10,2.50),
]
def dominates(a,b):
    return a[1]>=b[1] and a[2]<=b[2] and a[3]<=b[3] and (a[1]>b[1] or a[2]<b[2] or a[3]<b[3])
with (w/'00553-三目标支配逐项复算.tsv').open('w',encoding='utf-8-sig',newline='') as f:
    out=csv.writer(f,delimiter='\t')
    out.writerow(['模型','验证准确率百分比','FLOPs百万','参数千','同表2子网中支配者','表1与表2合并后的支配者'])
    for m in models:
        inside=[a[0] for a in models[:9] if a != m and dominates(a,m)]
        combined=[a[0] for a in models if a != m and dominates(a,m)]
        out.writerow([*m,'、'.join(inside) or '无','、'.join(combined) or '无'])

# PDF 00562 p.12 Table 1. These derived figures require the usual R² identity,
# matching sample and weighting, and are not evidence of a continuous target.
reported=[('RF',43.3659,3170.1811,.8973),('SVM',95.3814,16352.2563,.4701),
          ('XGBoost',83.0926,11880.6837,.6150),('CNN',95.3048,13986.1784,.5468)]
intervals=[]
with (w/'00562-Table1条件性反推.tsv').open('w',encoding='utf-8-sig',newline='') as f:
    out=csv.writer(f,delimiter='\t')
    out.writerow(['模型','MAE','MSE','R²','MSE/(1-R²)','平方根','按四位小数舍入时可行方差下界','按四位小数舍入时可行方差上界'])
    for n,mae,mse,r2 in reported:
        v=mse/(1-r2)
        lo=(mse-.00005)/(1-r2+.00005)
        hi=(mse+.00005)/(1-r2-.00005)
        intervals.append((lo,hi))
        out.writerow([n,mae,mse,r2,f'{v:.6f}',f'{math.sqrt(v):.6f}',f'{lo:.6f}',f'{hi:.6f}'])
print('00553 rows',len(models),'within Table 2 dominated',sum(bool([a for a in models[:9] if a!=b and dominates(a,b)]) for b in models[:9]))
print('00553 LeNet dominates',', '.join(b[0] for b in models[:9] if dominates(models[-2],b)))
print('00562 conditional intersection',max(x[0] for x in intervals),min(x[1] for x in intervals))
