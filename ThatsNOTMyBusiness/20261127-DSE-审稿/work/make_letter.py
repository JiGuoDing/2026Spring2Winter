from pathlib import Path
from docx import Document
import re,sys
sys.stdout.reconfigure(encoding='utf-8')
root=Path.cwd()
original=root/'Decision letter for DSE-2026-22.docx'
output=root/'Decision letter for DSE-2026-22 (复审修订).docx'
doc=Document(original)
replacement={
0:'This paper is recommended for further peer review:',
5:'The methods section refers to painting students and weather observations without explaining their connection to the survey. The relationship between the reported sample size and the confusion matrix, as well as the different accuracy figures, also requires clarification. Furthermore, the presentation and experimental rigor need substantial improvement.',
7:'Thanks for submitting your paper to DSE. However, the paper in its current form is not ready for publication in DSE. This paper proposes EEWSO-ILSVM, a hybrid model combining White Shark Optimization with a Least Squares Support Vector Machine, to assess entrepreneurial competencies and support personalized learning paths based on a student survey.',
8:'The methods and algorithm include descriptions of gas prediction and thermal fault detection whose relationship to the education task is unclear. The radial-basis kernel in Eq. (25) is written using the same input twice, and the reported sample and accuracy figures require clarification.',
11:'The description of the mean-trace input does not clearly explain the source of diversity in the generated traces. The CHES CTF evaluation also reports 5,000 attack traces and 10,000 test traces without clearly explaining their relationship.',
14:'The relationship between the model inputs and the detailed recognition results needs clearer explanation. Figure 2 reports eight abnormal classes but no normal-traffic class. The manuscript also needs to clarify how the method in reference [7] was adapted for the network anomaly comparisons.',
17:'The mentorship comparison uses different fine-tuning durations (6 epochs for evolved mentorship, 3 for static mentorship, and 2 for the unmentored control), and some baseline comparisons use different search generations, making it difficult to attribute performance differences to the mentorship mechanism. The main CIFAR-10 comparison reports validation accuracy, and independent test evaluation requires further clarification.',
20:'The evaluation compares original benchmarks scored by exact match with cleaned subsets scored using an LLM judge, making the effect of dataset corrections difficult to isolate. The relationship between the examiner-based acceptance rule and the examiner’s reported accuracy on the generated questions also requires clarification.',
23:'The manuscript describes some runtime profiles as preliminary and its memory comparison as analytical. It also reports timing results in the ablation study; the measurement and validation protocols need clearer explanation.',
26:'The ensemble-selection procedure uses predictions on the test set and fits Lasso to their mean; the information available at selection time and the rationale for this target need clarification. The manuscript also needs to reconcile its transition-matrix image construction with the description of a time-indexed field. The simulation results require additional detail on the evaluation protocol and the calculation of the reported errors.',
29:'The paper describes a text classification task, while Table 1 reports MAE, MSE, and R²; the target and the relationship between these metrics and the stated task are not clear. The manuscript also needs to explain the dataset used and how local mean decomposition is applied to the text features.'
}
for i,text in replacement.items():
 assert len(doc.paragraphs[i].runs)==1, i
 doc.paragraphs[i].runs[0].text=text
for paragraph in doc.paragraphs:
 if paragraph.text.strip():
  paragraph.paragraph_format.keep_together=True
  if paragraph.text.startswith('Decision for '):
   paragraph.paragraph_format.keep_with_next=True
doc.save(output)
def split(s):
 s=s.replace('i.i.d.', 'IID_ABBR')
 s=re.sub(r'(?<=[.!?])\s+(?=[A-Z])','\n',s)
 return [x.replace('IID_ABBR','i.i.d.') for x in s.split('\n') if x]
notes={
0:['状态无证据：原材料仅提出推荐，改为 recommended。'],
5:['期刊范围、绝对原创性未得现行政策或完整先行文献支持；删去，见 00526-11。','混淆矩阵数量和准确率数字可复算，但统计口径未明；跨题材文字存在，来源/诚信定性不足。路径分析缺失和引文错配未充分核验；改写，见 00526-02～08、12。','属于一般编辑意见，保留。'],
7:['礼貌用语，保留。','编辑意见，保留；决定仍待编辑确认。','摘要称 330 有效，正文称回收 330 且有效率 81.7%；为避免把有争议口径写死，去掉数量，见 00527-01。'],
8:['范围和绝对原创性离线不可核实，删除，见 00527-09、10。','领域描述及 Eq.25 均有文本证据；92.1 与 91.0 数值存在但统计口径未明。广泛引文错配未完成核验；改写，见 00527-02～08、11。','DSE 标准未提供，删除笼统断言。'],
11:['期刊范围及“不具任何贡献”需政策/文献比较，删除，见 00544-10。','均值输入、5,000 与 10,000 可核；Dropout 排除不了随机性，泄漏、完全矛盾与基线缺失未经充分证明；改写，见 00544-01～09、11。'],
14:['范围和原创性不能离线断定，删除，见 00551-08。','模型输入与结果的映射需要解释；“彻底断裂”、损失等全篇缺失未充分证明，改写，见 00551-06、07、09。','五类历史案例与八类混淆矩阵未必为同一集合；Fig. 2 无正常流量类别的原有意见予以保留；[7] 标题与正文应用的关系待澄清，其余缺失项未完成穷尽搜索，见 00551-01～05、10、13。'],
17:['32×32 主题可以确认，期刊范围由编辑裁决；预算混杂成立，改写，见 00553-02～04、11。','6/3/2 轮及不同搜索代数可核实，但不能据此宣称 p 值本身无效；改写，见 00553-02～06。','80.18 是验证准确率；LeNet 的 Pareto 支配判断不完整、缺失测试/新文献须进一步搜索，改写，见 00553-01、07～13。'],
20:['存在严重评价混杂，但公式与表格的直接矛盾须区分运行条件；改为可定位问题，见 00558-03～09。','评分器切换、分数及变化可核；10–11% 并非已证明受评分器变化影响样本的上界，31.1 pp 不能据此称不可能；改写，见 00558-01～05。','30.3% 与接受规则存在需澄清张力；由“两者准确率低于一致率”不能推出算术不可能。无自动基线等全篇断言未完成核验；改写，见 00558-07～15。'],
23:['绝对原创性离线未核实；部分结果与不同负载范围须区分，改写，见 00560-05、06、09。','组件可核，但对有限离散数据和扩展性作绝对失败判断的证据不足；删除，见 00560-09。','初步耗时曲线、解析内存与概念比较需分开；其他实验仍有受控结果，删除“多数未实测”等笼统表述，见 00560-01～08、13～16。','数据声明与主要数据集关系需澄清；“大量无关引用”未完成核验，删去，见 00560-11、12。'],
26:['存在方法和数值疑点；避免未经原始记录证实的真实性定性，改写。','测试输入参与选择及均值作为目标有文本证据；未显示测试标签使用，不能断言标签泄漏或所有推断必然退化；改写，见 00561-01～04、12。','近似比例可复算但“全部精确”、贝叶斯下界和结果来源未建立；保留协议/计算需澄清，见 00561-05～09、13～15。'],
29:['范围和绝对原创性需编辑及领域文献判断；保留指标与任务对应疑点，见 00562-01、08、10。','公式及绝对缺乏新意未完成对比，删除。','Table 1 与数据声明可核；不能由回归指标推断错误来源，也不能仅凭局部搜索证实全部基线/引用缺失；改写，见 00562-01～07、10。']
}
introrefs={4:'00526-01～02、06～07',10:'00544-01～05',13:'00551-01～02、06～07',16:'00553-01～04、11',19:'00558-03、08',22:'00560-01、09',25:'00561-01～02、12',28:'00562-01～04、10'}
audit=['# 决定信逐句对照','', '输入段落按原 DOCX 的零起始段落编号标识。礼貌句与篇号不作为论文事实主张；每段的结论仍由编辑确认。对未完成穷尽搜索的断言一律删除或改为澄清请求。','','| 位置 | 原句 | 核验及处理 |','|---|---|---|']
for i,p in enumerate(Document(original).paragraphs):
 text=p.text.strip()
 if not text: continue
 if i in (1,2) or text.startswith('Decision for '):
  assessment='篇号与一轮包一致；原决定保留为待编辑确认的草稿。' if 'Decision for ' in text else '篇号或结构标签，与一轮包一致；保留。'
  audit.append(f'| P{i:02} | {text} | {assessment} |')
  continue
 sentences=split(text)
 if i in notes:
  assessments=notes[i]
  assert len(sentences)==len(assessments),(i,len(sentences),len(assessments))
 else:
  assert i in introrefs
  assessments=['礼貌用语，保留。','编辑意见，保留；最终决定需编辑确认。',f'方法概述主要内容与稿件一致；保留，关联 {introrefs[i]}；该句未逐项验证实现。']
 for j,(sentence,assessment) in enumerate(zip(sentences,assessments),1):
  audit.append(f'| P{i:02}.{j} | {sentence.replace("|","/")} | {assessment} |')
(root/'work'/'决定信逐句对照.md').write_text('\n'.join(audit)+'\n',encoding='utf-8')
print('Created',output.name)
print('Audited sentences',len(audit)-5)
