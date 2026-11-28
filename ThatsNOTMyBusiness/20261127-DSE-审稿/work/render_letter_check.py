from pathlib import Path
import pymupdf
pdf=pymupdf.open(Path('work')/'决定信视觉检查-定稿.pdf')
for i,page in enumerate(pdf,1):
 pix=page.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),alpha=False)
 path=Path('work')/f'决定信定稿页-{i}.png'
 pix.save(path)
 print(path)
print('pages',len(pdf))
