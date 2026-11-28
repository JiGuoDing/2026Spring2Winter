from docx import Document
import re,sys
sys.stdout.reconfigure(encoding='utf-8')
d=Document('Decision letter for DSE-2026-22.docx')
def split(s):
 s=s.replace('i.i.d.', 'IID_ABBR')
 s=re.sub(r'(?<=[.!?])\s+(?=[A-Z])','\n',s)
 return [x.replace('IID_ABBR','i.i.d.') for x in s.split('\n') if x]
for i in [0,4,5,7,8,10,11,13,14,16,17,19,20,22,23,25,26,28,29]:
 arr=split(d.paragraphs[i].text)
 print(f'P{i:02} N{len(arr)}')
 for j,v in enumerate(arr,1): print(j,v)
