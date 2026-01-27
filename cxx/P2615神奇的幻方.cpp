//
// Created by 48520 on 2026/1/27.
//
#include <cstdint>
#include <iostream>
#include <vector>


int main() {
    int n;
    std::cin >> n;

    // 创建一个 n x n 的二维向量，初始化为 0
    std::vector<std::vector<uint32_t>> grid(n, std::vector<uint32_t>(n, 0));

    grid[0][n/2] = 1;
    int row = 0, col = n / 2;

    for (int i = 2; i <= n * n; i++) {
        // 计算 i-1 在第几行第几列

        // 若 i-1 在第一行但不在最后一列，则将 i 填在最后一行，i-1 所在列的右一列
        if (row == 0 && col != n - 1) {
            grid[n - 1][col + 1] = i;
            row = n - 1;
            col = col + 1;
        }
        
        // 若 i-1 在最后一列单不在第一行，则将 i 填在第一列，i-1 所在行的上一行
        else if (col == n - 1 && row != 0) {
            grid[row - 1][0] = i;
            row = row - 1;
            col = 0;
        }

        // 若 i-1 在第一行最后一列，则将 i 填在 i-1 的正下方
        else if (row == 0 && col == n - 1) {
            grid[row + 1][col] = i;
            row = row + 1;
        }

        // 若 i-1 几不在第一行，也不在最后一列，如果 i-1 的右上方还未填数，则将 i 填在 i-1 的右上方，否则将 i 填在 i-1 的正下方
        else if (row != 0 && col != n - 1) {
            if (grid[row - 1][col + 1] == 0) {
                grid[row - 1][col + 1] = i;
                row = row - 1;
                col = col + 1;
            }
            else {
                grid[row + 1][col] = i;
                row = row + 1;
            }
        }
    }
    for (auto &row : grid) {
        for (auto &num : row) {
            std::cout << num << " ";
        }
        std::cout << std::endl;
    }
    return 0;
}