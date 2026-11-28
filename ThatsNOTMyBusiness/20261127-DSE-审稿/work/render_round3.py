from pathlib import Path
import pymupdf
root=Path.cwd()
for pid,pages in [('00544',[12,15,17]),('00551',[6,7,10])]:
    with pymupdf.open(root/'DSE-2026-22'/f'DSEJ-D-26-{pid}.pdf') as doc:
        for n in pages:
            page=doc[n-1]
            pix=page.get_pixmap(matrix=pymupdf.Matrix(1.8,1.8),alpha=False)
            pix.save(root/'work'/f'{pid}-page{n}-复核.png')
            print(pid,n,page.rect)

