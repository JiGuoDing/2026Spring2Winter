from pathlib import Path
p=Path('work/build_ledger.py')
s=p.read_text(encoding='utf-8')
s=s.replace("A('00551','判断','数学模型与实验输出彻底断裂','OVERSTATED',[(17,'5 types of high-incidence abnormal scenarios in the industrial Internet of Things')]","A('00551','判断','数学模型与实验输出彻底断裂','OVERSTATED',[(8,'dynamic connection feature matrix'),(17,'PC-05 hijacked → intermediate switch → horizontal connection path of SCADA server')]")
s=s.replace("# Verify each PDF quotation against the extracted text and each review excerpt against an input.","A('00562','文本','public database of English learning materials','CONFIRMED',[(9,'a public database of English learning materials'),(18,'Data Availability Not applicable')],'§4.1 只以此称呼数据来源，声明写不适用；请求补充数据集名称、规模、标签及获取方式。')\n# Verify each PDF quotation against the extracted text and each review excerpt against an input.")
p.write_text(s,encoding='utf-8')
