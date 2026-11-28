from pathlib import Path
from collections import Counter
import hashlib,json,re,sys
import pymupdf
from docx import Document
sys.stdout.reconfigure(encoding='utf-8')
root=Path.cwd(); w=root/'work'
expected=json.loads((w/'输入文件校验.json').read_text(encoding='utf-8'))
hashes=[]
for path,old in expected.items():
 p=root/path
 sha=hashlib.sha256(p.read_bytes()).hexdigest()
 hashes.append((path,sha==old))
entries=json.loads((w/'台账数据.json').read_text(encoding='utf-8'))
counts=Counter(e['pid'] for e in entries); verdict=Counter(e['verdict'] for e in entries)
assert len(hashes)==14 and all(ok for _,ok in hashes)
assert min(counts.values())>=8
errors=[]
cache={}
for e in entries:
 pid=e['pid']
 if pid not in cache: cache[pid]=pymupdf.open(root/'DSE-2026-22'/f'DSEJ-D-26-{pid}.pdf')
 for page,quote in e['anchors']:
  p=cache[pid][page-1]
  texts=[re.sub(r'\s+',' ',p.get_text(sort=s)).strip() for s in (False,True)]
  if not any(quote in t for t in texts): errors.append((e['id'],page,quote))
  if len(quote.split())>25: errors.append((e['id'],page,'quote exceeds 25 words'))
letter=Document(root/'Decision letter for DSE-2026-22 (复审修订).docx')
text='\n'.join(p.text for p in letter.paragraphs)
for x in ['136 Chinese businesses','Eq. (25)','5,000 attack','10,000 test traces','reference [7]','Table 1','6 epochs for evolved mentorship, 3 for static mentorship, and 2 for the unmentored control']:
 assert x in text,x
for x in ['deterministic mean-trace generator','introduces test-time leakage','arithmetically inconsistent','has passed the preliminary review']:
 assert x not in text,x
assert len(re.findall(r'Decision for DSEJ-D-26-\d+: Desk reject',text))==9
assert 'recommended for further peer review' in text
summary=(root/'复审-执行摘要.md').read_text(encoding='utf-8')
assert len(summary)<=400, len(summary)
assert f'{len(entries)} 条' in summary and f"WRONG {verdict['WRONG']} 条" in summary and f"OVERSTATED {verdict['OVERSTATED']} 条" in summary
assert f'{len(entries)} 条' in (root/'复审-决策复核.md').read_text(encoding='utf-8')
pdf=pymupdf.open(w/'决定信视觉检查-定稿.pdf')
lines=['# 交付前抽查','',f'原始输入 SHA-256：{sum(ok for _,ok in hashes)}/{len(hashes)} 未变化。',
 f'已登记主张 {len(entries)} 条；每篇至少 {min(counts.values())} 条；PDF 原文逐字回查失败 {len(errors)} 处。',
 '修订信六个定量数字与页号核对（页均为 PDF 物理页）：',
 '- 00526：136 家企业，p.2 摘要，台账 00526-01。',
 '- 00544：5,000 条攻击轨迹，p.26 §4.7，台账 00544-01。',
 '- 00544：10,000 条测试轨迹，p.27 §4.7，台账 00544-02。',
 '- 00553：evolved、static、none 的微调分别为 6、3、2 轮，p.13 §5.4，台账 00553-02。',
 '另核对编号：00527 的 Eq. (25) 在 p.15；00562 的 Table 1 在 p.12；00551 的参考文献 [7] 于 p.19 用于比较，题名见 p.22。',
 f'修订信 Word 导出 PDF 共 {len(pdf)} 页；已逐页查看。未发现原信的直接标签泄漏、确定性生成和一致率算术矛盾断言。',
 '摘要字符数：'+str(len(summary))+'（含 Markdown 标记和换行）。',
 '范围限制：逐字回查只验证已登记证据，不表示一轮全部数字、表格和主张已经覆盖。']
if errors:
 lines+=['','## 尚需处理的原文回查失败']+[str(x) for x in errors]
(w/'交付前核对.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('inputs_unchanged',sum(ok for _,ok in hashes),'/',len(hashes),'entries',len(entries),'PDF_quote_errors',len(errors),'summary_chars',len(summary),'pages',len(pdf))
for x in errors[:30]: print('ERROR',x)
if errors: raise SystemExit(2)
