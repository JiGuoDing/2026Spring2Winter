from fractions import Fraction as F
from pathlib import Path
import csv

W = Path(__file__).resolve().parent

# Table 10, PDF physical p.12: class, TP, FN, FP, TN.
rows = [
    ('ADI', 274, 3, 27, 1696), ('BACK', 218, 14, 25, 1743),
    ('DEB', 126, 66, 59, 1749), ('LYM', 182, 10, 10, 1798),
    ('MUC', 163, 52, 44, 1741), ('MUS', 157, 67, 42, 1734),
    ('NORM', 129, 65, 41, 1765), ('STR', 105, 61, 83, 1751),
    ('TUM', 252, 56, 63, 1629),
]
assert all(tp + fn + fp + tn == 2000 for _, tp, fn, fp, tn in rows)
assert sum(tp for _, tp, *_ in rows) == 1606
assert sum(fn for _, _, fn, _, _ in rows) == 394
assert sum(fp for _, _, _, fp, _ in rows) == 394
calc = []
for name, tp, fn, fp, tn in rows:
    precision = F(tp, tp + fp)
    recall = F(tp, tp + fn)
    specificity = F(tn, tn + fp)
    f1 = F(2 * tp, 2 * tp + fn + fp)
    calc.append((name, tp, fn, fp, tn, precision, recall, specificity, f1))
with (W / '00553-Table10指标逐项复算.tsv').open('w', encoding='utf-8-sig', newline='') as f:
    out = csv.writer(f, delimiter='\t')
    out.writerow(['类别', 'TP', 'FN', 'FP', 'TN', 'precision', 'recall', 'specificity', 'F1'])
    for row in calc:
        out.writerow([*row[:5], *(f'{float(x):.10f}' for x in row[5:])])
    out.writerow(['Macro', '', '', '', '', *(f'{float(sum(row[j] for row in calc) / 9):.10f}' for j in range(5, 9))])

# Eqs. (19)–(22), one exact rational example, deleting each support in turn.
z = [(F(0), F(0)), (F(2), F(4)), (F(3), F(2)), (F(5), F(6))]
labels = [0, 0, 1, 1]
P = [
    (F(1, 2), F(1, 2), F(0)), (F(0), F(1, 3), F(2, 3)),
    (F(1), F(0), F(0)), (F(0), F(1, 4), F(3, 4)),
]
assert all(sum(row) == 1 for row in P)
C = 2

def vector_mean(vs):
    return tuple(sum(v[d] for v in vs) / len(vs) for d in range(2))

def m2(vs):
    mean = vector_mean(vs)
    return sum(sum((v[d] - mean[d]) ** 2 for d in range(2)) for v in vs)

n = len(z)
mean = vector_mean(z)
M2 = m2(z)
for s in range(n):
    remain = [i for i in range(n) if i != s]
    for c in range(C):
        ids = [i for i in range(n) if labels[i] == c]
        new_ids = [i for i in remain if labels[i] == c]
        mu = vector_mean([z[i] for i in ids])
        deleted_mu = tuple((len(ids) * mu[d] - (z[s][d] if labels[s] == c else 0)) /
                           (len(ids) - (labels[s] == c)) for d in range(2))
        assert deleted_mu == vector_mean([z[i] for i in new_ids])
    updated_M2 = M2 - F(n, n - 1) * sum((z[s][d] - mean[d]) ** 2 for d in range(2))
    assert updated_M2 == m2([z[i] for i in remain])
    assert max(updated_M2 / ((n - 1) * 2), F(1, 100)) == max(m2([z[i] for i in remain]) / ((n - 1) * 2), F(1, 100))
    for e in range(3):
        mass = sum(P[i][e] for i in range(n))
        assert mass - P[s][e] == sum(P[i][e] for i in remain)
        for c in range(C):
            class_mass = sum(P[i][e] for i in range(n) if labels[i] == c)
            assert class_mass - (P[s][e] if labels[s] == c else 0) == sum(P[i][e] for i in remain if labels[i] == c)

# Eq. (15), explicit finite example with row-sum 1; a proof is recorded below.
alpha = F(1)
mass = [sum(P[i][e] for i in range(n)) for e in range(3)]
class_mass = [[sum(P[i][e] for i in range(n) if labels[i] == c) for c in range(C)] for e in range(3)]
theta = [[(class_mass[e][c] + alpha / C) / (mass[e] + alpha) for c in range(C)] for e in range(3)]
q = (F(1, 5), F(1, 2), F(3, 10))
evidence = [sum(q[e] * theta[e][c] for e in range(3)) for c in range(C)]
r = sum(q[e] * mass[e] / (mass[e] + alpha) for e in range(3))
distance = sum(abs(x - F(1, C)) for x in evidence)
bound = 2 * (1 - F(1, C)) * r
assert distance <= bound
note = f'''# 00552 公式与 00553 Table 10 复算

## 00552：可核实的代数范围

证据锚点为 PDF 物理页 9–13（印刷页 8–12）§4.2–4.6。此处核对数学式，不代表验证了代码、输入或实验。

- Eq. (15)：对非零且行和为 1 的路径行，代入式 (11)–(13) 得到 e-u = Σ_e P(v,e) λ_e (f_e-u)。当每个 f_e 是 C 类概率分布、λ_e ≥ 0 时，三角不等式及 max ||f-u||₁ = 2(1−1/C) 得出原式。零质量实体按文中 λ=0 处理；零路径行不在此推导条件内。一个有理数例子：左端 {distance}，右端 {bound}。
- Eq. (19)：删除所属类的样本后，新类别和为 n_jc μ_jc − 1[y_s=c] z_s，类数作相同扣减，因此当删除后该类仍有样本时公式成立。除数为零时，文中称专家不可用；不能将其当作可直接计算的有效值。
- Eq. (20)：设 n>1，删除前未截断的中心矩 M₂=Σ||z_i−mean||²；展开可得 M₂^(−s)=M₂−n/(n−1)||z_s−mean||²，再除以 (n−1)d 并施加 0.01 下限。这里必须使用未截断的 M₂，不能从已截断的 σ² 逆推原始中心矩。
- Eqs. (21)–(22)：根据 N=PᵀY 与 m=Pᵀb，删除 s 的 one-hot 标签和支持指示，分别减 P(s,e)1[y_s=c] 与 P(s,e)。删除后仍须重算平滑、覆盖和可用性。物理页 11 保留节点、属性与图边，删除的是标签贡献，不能等同删除节点或验证实现无其他泄漏。
- 对四个支持、两个类别、三个实体的有理数例子，逐一删除四个支持并对每类与实体直接重算，式 (19)–(22) 均精确相等。示例不覆盖所有边界或浮点实现。
- Eq. (26) 报告 O(Σ_p[E_p|S|+n_a(p)|S|C])；逐支持通过稀疏因子获得所需路径权重可给出前项、每个支持逐实体逐类别形成/求和残差可给出后项。该计数依赖已声明的实现、固定平滑配置及稀疏乘法与数组初始化口径；未有实现和性能数据时不能证明实际运行时间、峰值空间或大图可扩展性。

## 00553：PathMNIST 指标

Table 10 每类 TP/FN/FP/TN 的分母均为 2,000，合计 TP=1,606、FN=FP=394。由逐类计数计算准确率 {1606/2000:.4%}、宏 F1 {float(sum(x[8] for x in calc)/9):.10f}、宏召回 {float(sum(x[6] for x in calc)/9):.10f}、宏特异性 {float(sum(x[7] for x in calc)/9):.10f}；与作者报告的 80.30%、0.7898、78.97%、97.54% 在显示精度上一致。逐类记录见 `00553-Table10指标逐项复算.tsv`。ROC-AUC 需要分数及标签，不能从固定阈值的混淆矩阵独立复算。
'''
(W / '00552公式与00553指标复算.md').write_text(note, encoding='utf-8')
print('00552 exact deletion examples passed; 00553 table metrics written')
