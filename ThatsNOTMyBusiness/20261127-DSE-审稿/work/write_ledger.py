from pathlib import Path
from collections import Counter
import csv,json,re,sys
from docx import Document
sys.stdout.reconfigure(encoding='utf-8')
root=Path.cwd(); w=root/'work'
data=json.loads((w/'台账数据.json').read_text(encoding='utf-8'))
cards=(root/'DSE-2026-22-全部10篇论文速览卡片.md').read_text(encoding='utf-8')
report=(root/'DSE-2026-22-推荐继续送审论文价值论证报告.md').read_text(encoding='utf-8')
letter=Document(root/'Decision letter for DSE-2026-22.docx')
loc={
'00526':{2:'摘要',8:'§3.1 / Table 2',10:'§3 方法',11:'§3 / Table 3',12:'§3 方法',14:'§4.1 / Table 4',17:'§4.2 / Table 5 / Fig. 6',19:'§4.3–4.4 / Figs. 8–9'},
'00527':{2:'摘要',9:'§3.1',10:'§3.1–3.2',11:'§3.2 / Eq. 10',13:'§3.4.1 / Eqs. 13、15、17',14:'§3.4.2',15:'§3.4.2 / Eq. 25',16:'Algorithm 1',17:'Algorithm 1 / §4.1–4.2',18:'§4.2 / Table 4',22:'§4 / Fig. 7',23:'§4 / 统计比较表'},
'00544':{3:'摘要',13:'§3.2–3.3',16:'§3.7',17:'§4.1 / Table 1',18:'§4.2–4.3',21:'§4.4 / Fig. 9–10',22:'§4.4.2 / Fig. 11',23:'§4.5 / Fig. 12',24:'§4.5 / Fig. 13 讨论',25:'§4.5–4.6 / Fig. 13',26:'§4.6–4.7 / Fig. 14',27:'§4.7 / Fig. 15'},
'00551':{4:'引言 / 引文 [7]',5:'§2.1',7:'§2.1',8:'§2.2',9:'§2.2',15:'§3 / Table 1',16:'§3 / 历史案例及 Table 3',17:'§3 / Table 3',18:'§3 / 混淆矩阵',19:'§3 / Fig. 3',20:'§3 / 吞吐量比较',22:'参考文献 [7]'},
'00552':{8:'§4.1',10:'§4.3 / Eqs. 10–15',11:'§4.4–4.5 / Table 3 / Eq. 19',12:'§4.5–4.6 / Eqs. 20–25',13:'§4.6 / Eq. 26；§5 / Table 4',14:'§5–6.1 / Table 5 上文',15:'§6.1–6.2 / Tables 5–6',17:'§6.3 / Tables 7–8',18:'§6.4–6.5 / Tables 9–10',19:'§6.4–6.6 / Table 10',23:'Appendix A.1–A.3',24:'Appendix B–D',25:'Appendix D–E / Table E1',26:'Appendix E / Table E1 续表',28:'参考文献',32:'独立 Title Page / Code availability'},
'00553':{9:'§4.1–4.2 / Tables 1–2',10:'§4.2–4.3 / Tables 3–5',11:'§4.4–4.5 / Tables 6–9',13:'§5.2–5.4',14:'§6 / 参考文献'},
'00558':{11:'§3.4 / Eq. 5',12:'§4.1–4.2 / Fig. 4',13:'§4.2–4.3',14:'§4.2–4.3 / Table 1 / Fig. 5',15:'§4.3–4.4 / Fig. 5',16:'§4.5 / Table 2',17:'§4.5–4.6 / Fig. 6',18:'§4.5–4.6 / Tables 3–4'},
'00560':{3:'摘要',13:'§2 / 贡献说明',28:'§5.1.2 / 数据集',29:'§5.1.2 / Table 5',31:'§5.1.4–5.1.5',32:'§5.1.5–5.2.1',33:'§5.2.1 / Table 6',34:'§5.2.1–5.2.2',35:'§5.2.2 / Table 7 说明',36:'§5.2.2 / Tables 7–8',38:'§5.2.3 / Figs. 5–6',40:'§5.2.4 / 消融工作负载',41:'§5.2.4 / Table 11',47:'§5.2.7 / Table 12',50:'§5.2.8 / Table 13',60:'独立声明页 / Data availability'},
'00561':{4:'§2.1–2.2',5:'§2.3',6:'§2.3–2.4',8:'§3 / Simulation 1',9:'§3 / Tables 2–3',10:'§3 / Table 4',11:'§3 / Tables 5–6',12:'§3 / Simulations 2–3',13:'§3 / Tables 7–8',14:'§4 / Table 9',15:'§4.1 / Tables 9–10',16:'§4.1 / Table 11',18:'§4.3 / 统计检验',19:'§4.4 / Table 12',20:'§5 / 数据可用性'},
'00562':{2:'摘要',9:'§4.1–4.2',10:'§4.2 / Figs. 1–2',11:'§4.2 / Figs. 3–4',12:'§4.2 / Table 1 / Fig. 5',13:'§4.2 / Fig. 6',18:'独立声明页 / Data availability'}
}
for paper_locations in loc.values(): paper_locations[1]='投稿信息页 / Article Type'
loc['00526'].update({9:'§3 / K-means',13:'§3 / Algorithm 1',22:'参考文献 [21]–[31]',23:'独立声明页 / 作者声明'})
loc['00527'].update({3:'§1 引言',6:'§2 文献回顾',28:'参考文献 [25]–[33]',29:'独立声明页 / 作者声明'})
loc['00544'].update({19:'§4.3 / Pearson 相关及 Fig. 8'})
loc['00551'].update({14:'§2.4 / Eq. 23'})
loc['00553'].update({6:'§3.2–3.3 / Eq. 5',8:'§3.5–4.1.1 / Algorithm 1',7:'§3.3 / Eqs. 8–15'})
loc['00560'].update({19:'§3.4.2–3.4.3 / Eqs. 7–10',23:'§4.1 / Theorem 1',24:'§4.2–4.3 / Theorems 2–3',25:'§4.4–4.5 / Theorems 4–5',26:'§4.6 / Table 4',46:'§5.2.7 / 样本与查询设置',57:'参考文献 [16]–[27]'})
loc['00561'].update({7:'§3 / 模拟实验设置'})
loc['00562'].update({6:'§3.2.2 / 回归分裂准则',7:'§3.4.1 / Bias-variance decomposition'})
loc['00544'].update({5:'§1.2 / 相关方法',32:'参考文献'})
loc['00551'].update({21:'§4 结论 / 参考文献',22:'参考文献 [3]–[18]'})
loc['00558'].update({19:'§5 结论 / 参考文献'})
loc['00560'].update({58:'参考文献 [27]–[38]'})
loc['00562'].update({16:'参考文献 [11]–[21]',17:'参考文献 [22]–[30]'})
maps={}
with (w/'页码映射-校核.tsv').open(encoding='utf-8',newline='') as f:
 for r in csv.DictReader(f,delimiter='\t'): maps[(r['稿件'][-5:],int(r['PDF物理页']))]=r['原文实际印刷页码']
maps[('00552',32)]='1（独立 Title Page）'
def source(e):
  pid=e['pid']; c=e['claim']; found=[]
  marker=re.search(r'(?m)^### \d+\. `DSEJ-D-26-'+pid+r'`',cards)
  if marker:
    nexthead=re.search(r'(?m)^### ',cards[marker.end():]); end=marker.end()+nexthead.start() if nexthead else len(cards)
    at=cards.find(c,marker.start(),end)
    if at>=0: found.append('速览卡 L'+str(cards.count('\n',0,at)+1))
  # Each matching line in the report is a literal occurrence; one is sufficient for traceability.
  at=report.find(c)
  if at>=0: found.append('价值报告 L'+str(report.count('\n',0,at)+1))
  curr=None
  for i,p in enumerate(letter.paragraphs):
    m=re.search(r'Decision for DSEJ-D-26-(\d+)',p.text)
    if m: curr=m.group(1)
    if c in p.text and (curr==pid or (pid=='00552' and i<=1)): found.append('原决定信段 '+str(i+1)); break
  if not found:
    at=cards.find(c)
    if at>=0: found.append('速览卡首次出现 L'+str(cards.count('\n',0,at)+1))
  assert found,(pid,c)
  return '；'.join(found)
def esc(s): return str(s).replace('|','\\|').replace('\n',' ')
counts=Counter(e['verdict'] for e in data)
out=['# 复审：主张核验台账','',
'本台账依据本地 PDF 抽取文本和一轮材料逐条核验。总计 **%d 条**；CONFIRMED %d、IMPRECISE %d、WRONG %d、UNVERIFIABLE %d、OVERSTATED %d、UNSUPPORTED %d。CONFIRMED 仅表示稿件确实这样报告及所述数值对应正确，不等于原始实验或外部文献已被复现。'%(len(data),counts['CONFIRMED'],counts['IMPRECISE'],counts['WRONG'],counts['UNVERIFIABLE'],counts['OVERSTATED'],counts['UNSUPPORTED']),'',
'**覆盖边界：未完成用户要求的全部数字、表格及三份材料所有独立主张的 100% 核验。** 工作清单含 595 个来源片段（其中 437 个含数字或编号；片段可能含多个主张、重复或仅编号），部分尚未逐项判定。不得把本台账当成完整证据审计或将未检查内容理解为不存在；详细待办见 `work/主张覆盖索引.tsv` 与决策复核。','',
'裁决：CONFIRMED＝原文支持、被核数值和页码正确；IMPRECISE＝事实基础存在但表述或限定不准；WRONG＝可定位内容与其相反或推理本身错误；UNVERIFIABLE＝[UNVERIFIABLE] 当前资料无法确证亦无法证伪；OVERSTATED＝事实基础存在但结论超出证据；UNSUPPORTED＝特定判断缺少支持。章节标识以具体引文所在页为准；同页含多项时列出相关节和图表。引文只合并原始换行及空白，每处不超过 25 词。','',
'页码均先标 PDF 物理页，再标稿件印刷页；“未识别”不等于没有印刷页码。完整映射见 `work/页码映射-校核.tsv`；00552 物理页 32 是单独的 Title Page，其印刷页码重新从 1 开始。','',
'| 编号 | 稿件 | 类别 | 一轮主张摘录及来源 | 裁决 | PDF 证据锚点与逐字引文 | 修正建议 |','|---|---|---|---|---|---|---|']
for e in data:
  ev=[]
  for page,quote in e['anchors']:
    printed=maps.get((e['pid'],page),'未识别')
    sect=loc[e['pid']].get(page,'本页相关段落')
    ev.append(f'物理 p.{page}（印刷 {printed}），{sect}：“{quote}”')
  verdict=e['verdict']+(' [UNVERIFIABLE]' if e['verdict']=='UNVERIFIABLE' else '')
  out.append('| '+' | '.join(esc(x) for x in [e['id'],e['pid'],e['kind'],e['claim']+'（'+source(e)+'）',verdict,'；'.join(ev),e['fix']])+' |')
summary={
'00526':'修正：跨题材方法文字和数据口径疑点成立；拼贴动机、全部结果矛盾及期刊范围不能由现有证据确定。',
'00527':'修正：热故障表述、RBF 式面和样本口径需澄清；不能把这些直接定性为拼贴或断言两个准确率必然矛盾。',
'00544':'修正：[待人工裁决] 两处轨迹数量需解释；生成器存在 Dropout，不能仅凭均值输入推定为确定性或数据泄漏。',
'00551':'修正：模型输入与细粒度结果的关系及 [7] 的改造需说明；不能仅凭标题认定引用误用。',
'00552':'修正：报告的主要数字可定位，五项风险仍需核查；四图平均、样本标准差、预处理计时边界和 RDF-MUTAG 小样本必须明确。',
'00553':'修正：[待人工裁决] 不同训练预算混杂机制归因；LeNet 按三目标支配五个候选，但不支配所有候选，且作者报告的搜索前沿与纳入基线后的前沿须区分。',
'00558':'推翻部分理由：[待人工裁决] 是否维持拒稿。双低于一致率不能推出算术矛盾，且无法把提升全部归因于更换评分器；评分混杂和条件性计数疑点仍需作者解释。',
'00560':'修正：[待人工裁决] 部分成本为示意分析，另有受控 oracle 和消融结果；不能概括多数实验未执行。',
'00561':'修正：测试输入参与选择和数值规律值得追问，但标签泄漏、计算造假及绝对理论不可能尚无足够证据。',
'00562':'修正：文本分类与回归指标、数据描述之间的关系不清；不能据此推断来自另一项时序实验。'
}
extra=[
 ('00552-补01',15,'§6.1 / Table 5','69.94 70.59 76.00 80.61 1.88','SCETRA 的四图 Micro-F1 均值为 80.61；与下列 Simple-HGN 的 81.49 共同说明平均第一需限定指标。'),
 ('00552-补01',15,'§6.1 / Table 5','74.34 81.49 2.38','Simple-HGN 的四图 Micro-F1 均值为 81.49；为作者报告值，不等于独立复现。'),
 ('00552-补02',16,'§6.2 / Fig. 3','Hollow markers indicate incomplete planned repeats','图注注明空心标记代表计划重复未完成，应明确涉及方法、预算和原因。'),
 ('00552-补03',12,'§4.5 / Eq. 25','If any class has fewer than two supports','1-shot 使用预设回退，需要区分由规则选择带来的效果。'),
 ('00552-补03',12,'§4.5 / Eq. 25','uses the ﬁxed combination','这是 Eq. 25 对极少支持样本场景的机制说明。')]
raw=(w/'DSEJ-D-26-00552.txt').read_text(encoding='utf-8')
parts=re.split(r'\n\n========== PDF_PHYSICAL_PAGE (\d+) \|[^\n]+==========\n\n',raw)
pages={int(parts[i]):re.sub(r'\s+',' ',parts[i+1]).strip() for i in range(1,len(parts),2)}
out+=['','## 主动发现的补充证据（不计入一轮主张数量）','','| 编号 | 证据锚点 | 逐字引文 | 意义 |','|---|---|---|---|']
for idx,page,sect,quote,note in extra:
 assert quote in pages[page] and len(quote.split())<=25,(idx,quote)
 out.append('| '+' | '.join(esc(x) for x in [idx,f'00552 物理 p.{page}（印刷 {maps[("00552",page)]}），{sect}',f'“{quote}”',note])+' |')
for idx,pid,page,sect,quote,note in [
 ('00526-补01','00526',8,'§3.1 数据','Respondents were given a month to complete the anonymous questionnaires','问卷填写描述；与声明页的无参与者表述需要作者澄清。'),
 ('00526-补01','00526',23,'独立声明页','This study does not include any human participants.','与问卷描述并列；现有文本不能证明伦理违规，应询问数据来源及声明适用性。'),
 ('00527-补01','00527',9,'§3.1 数据','330 of the 369 distributed surveys are eventually retrieved','问卷发放及回收描述；与声明页的无参与者表述需要作者澄清。'),
 ('00527-补01','00527',29,'独立声明页','There is no human participate involved in this research.','与问卷描述并列；现有文本不能证明伦理违规，应询问数据来源及声明适用性。'),
 ('00561-补01','00561',8,'§3 / 标作 MASE 的指标','MASE measures the forecasting error relative to a naïve forecast benchmark.','目检本页可视公式，其分母为 Σ|y_k−ȳ|，并非相邻时刻差分；若 ȳ 是样本均值，公式对应均值基准而非通常一步朴素预测分母。ȳ 的定义及实际使用的代码需澄清，不能直接套用基于后者的一轮下界。'),
]:
 raw=(w/f'DSEJ-D-26-{pid}.txt').read_text(encoding='utf-8')
 parts=re.split(r'\n\n========== PDF_PHYSICAL_PAGE (\d+) \|[^\n]+==========\n\n',raw)
 pages={int(parts[i]):re.sub(r'\s+',' ',parts[i+1]).strip() for i in range(1,len(parts),2)}
 assert quote in pages[page] and len(quote.split())<=25,(idx,quote)
 out.append('| '+' | '.join(esc(x) for x in [idx,f'{pid} 物理 p.{page}（印刷 {maps[(pid,page)]}），{sect}',f'“{quote}”',note])+' |')
out+=['','## 每篇小结','']+[f'- **{pid}：{summary[pid]}**' for pid in summary]
(root/'复审-主张核验台账.md').write_text('\n'.join(out)+'\n',encoding='utf-8')
# Link source fragments to exact quoted excerpts. A linked fragment may contain further unreviewed claims.
with (w/'一轮主张清单-待逐条核对.tsv').open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f,delimiter='\t'))
for r in rows:
 matches=[e['id'] for e in data if (r['稿件']==e['pid'] or r['稿件']=='全批次') and e['claim'] in r['摘录']]
 r['覆盖状态']='部分摘录已登记；其余内容仍需逐项核验' if matches else '待逐项核验（可能与台账同义或重复）'
 r['关联台账编号']='、'.join(matches)
with (w/'主张覆盖索引.tsv').open('w',encoding='utf-8-sig',newline='') as f:
 fields=list(rows[0]); writer=csv.DictWriter(f,fieldnames=fields,delimiter='\t'); writer.writeheader(); writer.writerows(rows)
print('written ledger',len(data),'fragments',len(rows),'linked at least partly',sum(bool(r['关联台账编号']) for r in rows))
