from pathlib import Path
import pymupdf

root = Path.cwd()
for pid, pages in {'00552': [9, 12], '00561': [5], '00562': [6, 7]}.items():
    doc = pymupdf.open(root / 'DSE-2026-22' / f'DSEJ-D-26-{pid}.pdf')
    for number in pages:
        pix = doc[number - 1].get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
        pix.save(root / 'work' / f'{pid}-p{number}-round4.png')
