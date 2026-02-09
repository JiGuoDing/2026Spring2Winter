#include <iostream>
#include <vector>

using namespace std;

int main() {
    // 10x10网格，初始化所有格子为'.'
    vector<vector<char>> grid(10, vector<char>(10, '.'));
    
    // 方向定义：东、南、西、北（dx, dy），对应索引0、1、2、3
    vector<pair<int, int>> directions = {{0, 1}, {1, 0}, {0, -1}, {-1, 0}};
    
    // 初始方向为正北（索引3），用int避免无符号溢出
    int dir_idx_F = 3;  // Farmer的初始方向：北
    int dir_idx_C = 3;  // Cow的初始方向：北
    
    // 用int存储坐标（关键！避免无符号数溢出）
    int xf = -1, yf = -1;  // Farmer的位置
    int xc = -1, yc = -1;  // Cow的位置
    
    // 读取10行地图
    for (int i = 0; i < 10; i++) {
        for (int j = 0; j < 10; j++) {
            cin >> grid[i][j];
            if (grid[i][j] == 'F') {
                xf = i;
                yf = j;
            } else if (grid[i][j] == 'C') {
                xc = i;
                yc = j;
            }
        }
    }
    
    int elapsed_time = 0;
    const int MAX_TIME = 100000;  // 设定最大循环次数，防止无限循环
    
    // 循环条件：位置不同 且 未超过最大时间
    while ((xf != xc || yf != yc) && elapsed_time < MAX_TIME) {
        // ===== Farmer的移动逻辑 =====
        int next_xf = xf + directions[dir_idx_F].first;
        int next_yf = yf + directions[dir_idx_F].second;
        // 检查边界（0<=x<10, 0<=y<10）且不是障碍物
        bool f_can_move = (next_xf >= 0 && next_xf < 10) && 
                          (next_yf >= 0 && next_yf < 10) && 
                          (grid[next_xf][next_yf] != '*');
        
        if (f_can_move) {
            // 可以移动，更新位置
            xf = next_xf;
            yf = next_yf;
        } else {
            // 不能移动，顺时针转90度（索引+1后模4）
            dir_idx_F = (dir_idx_F + 1) % 4;
        }
        
        // ===== Cow的移动逻辑 =====
        int next_xc = xc + directions[dir_idx_C].first;
        int next_yc = yc + directions[dir_idx_C].second;
        bool c_can_move = (next_xc >= 0 && next_xc < 10) && 
                          (next_yc >= 0 && next_yc < 10) && 
                          (grid[next_xc][next_yc] != '*');
        
        if (c_can_move) {
            xc = next_xc;
            yc = next_yc;
        } else {
            dir_idx_C = (dir_idx_C + 1) % 4;
        }
        
        elapsed_time++;  // 时间+1分钟
    }
    
    // 输出结果：相遇则输出时间，否则输出0
    if (xf == xc && yf == yc) {
        cout << elapsed_time << endl;
    } else {
        cout << 0 << endl;
    }
    
    return 0;
}