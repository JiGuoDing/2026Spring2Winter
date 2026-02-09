#include <cstddef>
#include <iostream>
#include <vector>

std::vector<std::vector<char>> rotate90(const std::vector<std::vector<char>>& square) {
    size_t n = square.size();
    std::vector<std::vector<char>> rotated_square(n, std::vector<char>(n, ' '));

    // [INFO] 旋转 90 度可以拆解成两步操作：转置 (行列互换) 和水平翻转
    for (size_t i = 0; i < n; ++i) {
        for (size_t j = 0; j < n; ++j) {
            // 旋转 90 度
            rotated_square[j][n-1-i] = square[i][j];
        }
    }
    return rotated_square;
}

std::vector<std::vector<char>> rotate180(const std::vector<std::vector<char>>& square) {
    size_t n = square.size();
    std::vector<std::vector<char>> rotated_square(n, std::vector<char>(n, ' '));

    // [INFO] 旋转 180 度可以拆解成两步操作：水平翻转和垂直翻转
    for (size_t i = 0; i < n; ++i) {
        for (size_t j = 0; j < n; ++j) {
            // 旋转 180 度
            rotated_square[n-1-i][n-1-j] = square[i][j];
        }
    }
    return rotated_square;
}

std::vector<std::vector<char>> rotate270(const std::vector<std::vector<char>>& square) {
    size_t n = square.size();
    std::vector<std::vector<char>> rotated_square(n, std::vector<char>(n, ' '));

    // [INFO] 旋转 270 度可以拆解成两步操作：转置矩阵和垂直翻转
    for (size_t i = 0; i < n; ++i) {
        for (size_t j = 0; j < n; ++j) {
            // 旋转 270 度
            rotated_square[n-1-j][i] = square[i][j];
        }
    }
    return rotated_square;
}

std::vector<std::vector<char>> mirror(const std::vector<std::vector<char>>& square) {
    size_t n = square.size();
    std::vector<std::vector<char>> mirrored_square(n, std::vector<char>(n, ' '));

    // [INFO] 水平翻转
    for (size_t i = 0; i < n; ++i) {
        for (size_t j = 0; j < n; ++j) {
            // 水平翻转
            mirrored_square[i][n-1-j] = square[i][j];
        }
    }
    return mirrored_square;
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

    if (rotate90(original_square) == final_square)
        std::cout << "1" << std::endl;
    else if (rotate180(original_square) == final_square)
        std::cout << "2" << std::endl;
    else if (rotate270(original_square) == final_square)
        std::cout << "3" << std::endl;
    else if (mirror(original_square) == final_square)
        std::cout << "4" << std::endl;
    else if (rotate90(mirror(original_square)) == final_square || rotate270(mirror(original_square)) == final_square || rotate180(mirror(original_square)) == final_square)
        std::cout << "5" << std::endl;
    else if (original_square == final_square)
        std::cout << "6" << std::endl;
    else std::cout << "7" << std::endl;

    return 0;
}