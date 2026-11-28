from pathlib import Path
import sys
import fitz

root=Path.cwd()
pid=sys.argv[1]
with fitz.open(root/'DSE-2026-22'/f'DSEJ-D-26-{pid}.pdf') as pdf:
    for item in sys.argv[2:]:
        page=int(item)
        dest=root/'work'/f'{pid}-物理页{page}-补核.png'
        pdf[page-1].get_pixmap(matrix=fitz.Matrix(1.8,1.8),alpha=False).save(dest)
        print(dest)
