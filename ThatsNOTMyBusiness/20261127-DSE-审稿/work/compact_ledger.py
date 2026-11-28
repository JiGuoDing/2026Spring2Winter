from pathlib import Path
import json,re,collections
w=Path('work')
es=json.loads((w/'台账数据.json').read_text(encoding='utf-8'))
for pid in sorted({e['pid'] for e in es}):
 out=[]
 for e in es:
  if e['pid']!=pid: continue
  out.append(f"{e['id']} {e['verdict']} | {e['claim']} | {e['fix']} | "+' '.join(f"p{a[0]} “{a[1]}”" for a in e['anchors']))
 (w/f'检查-{pid}.txt').write_text('\n'.join(out),encoding='utf-8')
print('done')
