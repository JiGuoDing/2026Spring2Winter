from pathlib import Path
import csv

# Transcribed from the visually inspected Figure 2, PDF physical page 18.
matrix = [
 [995,0,1,2,2,0,0,0],
 [1,993,0,1,0,2,1,2],
 [0,2,992,0,1,2,3,0],
 [1,0,4,991,0,2,1,1],
 [0,2,2,0,992,2,0,2],
 [1,0,2,0,3,993,0,1],
 [3,0,3,0,2,0,991,1],
 [0,2,0,3,0,2,1,992],
]
total = sum(map(sum,matrix))
diagonal = sum(matrix[i][i] for i in range(8))
assert [sum(row) for row in matrix]==[1000]*8
assert total==8000 and diagonal==7939
with (Path('work')/'00551-混淆矩阵核算.tsv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f,delimiter='\t')
    w.writerow(['实际类别','预测1','预测2','预测3','预测4','预测5','预测6','预测7','预测8','行合计'])
    w.writerows([[i+1,*row,sum(row)] for i,row in enumerate(matrix)])
print('n=',total,'correct=',diagonal,'accuracy=',diagonal/total)
