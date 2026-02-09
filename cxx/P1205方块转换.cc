#include <cstddef>
#include <iostream>
#include <vector>

void rotate90(const std::vector<std::vector<char>>& square) {
    size_t n = square.size();
    std::vector<std::vector<char>> rotated_square(n, std::vector<char>(n, ' '));

    // [INFO] 旋转 90 度可以拆解成两步操作：转置矩阵和水平翻转
    for (size_t i = 0; i < n; ++i) {
        for (size_t j = 0; j < n; ++j) {
            // 旋转 90 度
            rotated_square[j][n-1-i] = square[i][j];
        }
    }
}

int main(int argc, const char** argv) {
    size_t n;
    std::cin >> n;
    char ch;

    // 定义初始和最终正方形
    std::vector<std::vector<char>> original_square(n, std::vector<char>(n, ' '));
    std::vector<std::vector<char>> final_square(n, std::vector<char>(n, ' '));

    for (size_t i = 0; i < n; ++i) {
        for (size_t j = 0; j < n; ++j) {
            std::cin >> ch;
            original_square[i][j] = ch;
        }
    }
    
    for (size_t i = 0; i < n; ++i) {
        for (size_t j = 0; j < n; ++j) {
            std::cin >> ch;
            final_square[i][j] = ch;
        }
    }


    return 0;
}