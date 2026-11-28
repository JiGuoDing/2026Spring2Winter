import pymupdf
from pathlib import Path
p=Path.cwd()
with pymupdf.open(p/'DSE-2026-22'/'DSEJ-D-26-00544.pdf') as d:
 d[18].get_pixmap(matrix=pymupdf.Matrix(2,2)).save(p/'work'/'00544-page19-复核.png')
