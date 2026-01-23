//
// Created by 基国鼎（实习） on 2026/1/23.
#include <iostream>
#include <vector>
#include <string>
using namespace std;

int main() {
    // 读取行数n和列数m
    int n, m;
    cin >> n >> m;
    // 忽略换行符，避免影响后续读取
    cin.ignore();

    // 存储雷区布局（用vector替代Java的二维数组，更灵活）
    vector<vector<char>> mineField(n, vector<char>(m));
    for (int i = 0; i < n; i++) {
        string line;
        getline(cin, line);
        // 将字符串转换为字符数组存入二维vector
        for (int j = 0; j < m; j++) {
            mineField[i][j] = line[j];
        }
    }

    // 定义8个方向的偏移量（和Java版本完全一致）
    int directions[8][2] = {
        {-1, -1}, {-1, 0}, {-1, 1},
        {0, -1},          {0, 1},
        {1, -1},  {1, 0},  {1, 1}
    };

    // 遍历每个格子并输出结果
    for (int i = 0; i < n; i++) {
        // C++中用string拼接，替代Java的StringBuilder
        string resultLine;
        for (int j = 0; j < m; j++) {
            if (mineField[i][j] == '*') {
                // 地雷格直接添加*
                resultLine += '*';
            } else {
                int count = 0;
                // 遍历8个方向
                for (int d = 0; d < 8; d++) {
                    int newRow = i + directions[d][0];
                    int newCol = j + directions[d][1];
                    // 检查边界是否合法
                    if (newRow >= 0 && newRow < n && newCol >= 0 && newCol < m) {
                        if (mineField[newRow][newCol] == '*') {
                            count++;
                        }
                    }
                }
                // 将数字转换为字符添加到结果行
                resultLine += (char)('0' + count);
            }
        }
        // 输出当前行结果
        cout << resultLine << endl;
    }

    return 0;
}