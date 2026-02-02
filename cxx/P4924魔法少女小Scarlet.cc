#include <iostream>
#include <cstddef>
#include <vector>

int main(int argc, const char** argv) {
    size_t n, m;
    std::cin >> n >> m;

    std::vector<std::vector<size_t>> matrix(n, std::vector<size_t>(n));

    size_t num = 0;
    for (size_t i = 0; i < n; i++) {
        for (size_t j = 0; j < n; j++) {
            matrix[i][j] = ++num;
        }
    }

    for (auto& row : matrix) {
        for (auto& elem : row) std::cout << elem << " ";
        std::cout << std::endl;
    }

    for (size_t i = 0; i < m; i++) {

    }
    return 0;
}