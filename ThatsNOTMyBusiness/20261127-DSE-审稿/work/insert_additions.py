from pathlib import Path
p=Path('work/build_ledger.py')
s=p.read_text(encoding='utf-8')
extra=Path('work/ledger_additions.txt').read_text(encoding='utf-8-sig')
s=s.replace('# Verify each PDF quotation against the extracted text and each review excerpt against an input.',extra+'\n# Verify each PDF quotation against the extracted text and each review excerpt against an input.')
p.write_text(s,encoding='utf-8')
