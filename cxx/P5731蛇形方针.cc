#include <cstddef>
#include <iostream>
#include <ostream>
#include <vector>

int main(){
    size_t n, x = 0, y = 0;
    std::cin >> n;

    // [INFO] 标记前进方向，0 代表向右，1 代表向下，2 代表向左，3 代表向右
    size_t flag = 0;

    std::vector<std::vector<size_t>> matrix(n, std::vector<size_t>(n, 0));
    for (size_t i = 1; i <= n * n; ++i) {
        matrix[x][y] = i;
        // [INFO] 判断接下来的方向
        switch (flag) {
            case 0:
                // 向右
                // 如果到达边界，直接变向
                if (y == n-1){
                    flag = 1;
                    // 变向向下移动一格
                    ++x;
                    break;
                }
                // 右侧非 0，说明走过了，直接变向
                if (matrix[x][y+1] != 0) {
                    flag = 1;
                    ++x;
                    break;
                }
                // 否则向右移动一位
                ++y;
                break;

            case 1:
                // 向下
                // 如果到达边界，直接变向
                if (x == n-1) {
                    flag = 2;
                    --y;
                    break;
                }
                // 下侧非 0，说明走过了，直接变向
                if (matrix[x+1][y] != 0) {
                    flag = 2;
                    --y;
                    break;
                }
                // 否则向下移动一位
                ++x;
                break;

            case 2:
                // 向左
                // 如果到达边界，直接变向
                if (y == 0) {
                    flag = 3;
                    --x;
                    break;
                }
                // 左侧非 0，说明走过了，直接变向
                if (matrix[x][y-1] != 0) {
                    flag = 3;
                    --x;
                    break;
                }
                // 否则向下移动一位
                --y;
                break;
            case 3:
                // 向上
                // 如果到达边界，直接变向
                if (x == 0) {
                    flag = 0;
                    ++y;
                    break;
                }
                // 上侧非 0，说明走过了，直接变向
                if (matrix[x-1][y] != 0) {
                    flag = 0;
                    ++y;
                    break;
                }
                // 否则向上移动一位
                --x;
                break;
            default:
                break;
        }
    }

    for(auto row : matrix) {
        for (auto num: row) {
            printf("%3d", static_cast<int>(num));
        }
        std::cout << std::endl;
    }
    return 0;
}