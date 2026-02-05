#include <iostream>
#include <cstring> // 用于memset初始化数组
using namespace std;

const int MAXN = 105; // 题目中n≤100，定义稍大的数组避免越界
int grid[MAXN][MAXN]; // 地图矩阵：0=黑暗无物品(生怪)，1=有光照，2=有物品(火把/萤石)

// 火把的照明偏移量：存储(行偏移, 列偏移)，共12个光照位置（不含自身）
int torch_off[12][2] = {
    {-2, 0}, {2, 0}, {0, -2}, {0, 2},
    {-1, -1}, {-1, 0}, {-1, 1},
    {1, -1}, {1, 0}, {1, 1},
    {0, -1}, {0, 1}
};

// 萤石的照明偏移量：5×5全区域，共24个光照位置（不含自身）
int glow_off[24][2];

// 预处理萤石的偏移量（提前生成，避免重复代码）
void initGlowOff() {
    int idx = 0;
    for (int i = -2; i <= 2; i++) {
        for (int j = -2; j <= 2; j++) {
            if (i == 0 && j == 0) continue; // 跳过自身位置
            glow_off[idx][0] = i;
            glow_off[idx][1] = j;
            idx++;
        }
    }
}

int main() {
    initGlowOff(); // 初始化萤石偏移量
    int n, m, k;
    cin >> n >> m >> k;

    // 初始化矩阵：所有位置设为0（黑暗无物品）
    memset(grid, 0, sizeof(grid));

    // 处理火把：标记物品位置 + 标记光照区域
    for (int i = 0; i < m; i++) {
        int x, y;
        cin >> x >> y;
        int rx = x - 1, ry = y - 1; // 转换为数组下标（从0开始）
        grid[rx][ry] = 2; // 标记为有物品
        // 遍历火把的所有照明偏移量，标记光照
        for (int j = 0; j < 12; j++) {
            int nx = rx + torch_off[j][0];
            int ny = ry + torch_off[j][1];
            // 确保坐标在矩阵范围内，且未被物品占据（物品位置无需标记光照）
            if (nx >= 0 && nx < n && ny >= 0 && ny < n && grid[nx][ny] != 2) {
                grid[nx][ny] = 1;
            }
        }
    }

    // 处理萤石：标记物品位置 + 标记光照区域
    for (int i = 0; i < k; i++) {
        int o, p;
        cin >> o >> p;
        int ro = o - 1, rp = p - 1; // 转换为数组下标
        grid[ro][rp] = 2; // 标记为有物品
        // 遍历萤石的所有照明偏移量，标记光照
        for (int j = 0; j < 24; j++) {
            int nx = ro + glow_off[j][0];
            int ny = rp + glow_off[j][1];
            if (nx >= 0 && nx < n && ny >= 0 && ny < n && grid[nx][ny] != 2) {
                grid[nx][ny] = 1;
            }
        }
    }

    // 统计生怪位置：值为0的位置数量
    int ans = 0;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            if (grid[i][j] == 0) {
                ans++;
            }
        }
    }

    cout << ans << endl;
    return 0;
}