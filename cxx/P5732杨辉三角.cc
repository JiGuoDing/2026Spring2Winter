#include <cstddef>
#include <iostream>
#include <ostream>
#include <vector>


int main() {
    size_t n;
    std::cin >> n;

    std::vector<std::vector<size_t>> matrix(n, std::vector<size_t>(n, 0));
    for (size_t i = 0; i < n; ++i) {
        matrix[i][0] = 1;
    }

    for (size_t i = 1; i < n; ++i) {
        for (size_t j = 1; j < n; ++j) {
            matrix[i][j] = matrix[i-1][j-1] + matrix[i-1][j];
        }
    }

    for (auto const& row : matrix) {
        for (auto const& num : row) {
            if (num == 0)
                break;
            std::cout << num << " ";
        }
        std::cout << std::endl;
    }
    return 0;
}