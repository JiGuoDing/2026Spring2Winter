from pathlib import Path
p=Path('work/页码映射-校核.tsv')
lines=p.read_text(encoding='utf-8').splitlines()
target='DSEJ-D-26-00552\t32\t'
count=0
for i,line in enumerate(lines):
 if line.startswith(target):
  lines[i]=target+'1（独立 Title Page）\t独立声明页页脚原文“1”；与正文印刷页码分开编号'
  count+=1
assert count==1
p.write_text('\n'.join(lines)+'\n',encoding='utf-8')
