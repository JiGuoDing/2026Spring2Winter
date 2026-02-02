#include <iostream>
#include <vector>
using namespace std;

int main() {
    size_t n, m;
    cin >> n >> m;

    vector<vector<size_t>> matrix(n, vector<size_t>(n));
    size_t num = 0;
    for (size_t i = 0; i < n; i++)
        for (size_t j = 0; j < n; j++)
            matrix[i][j] = ++num;

    for (size_t op = 0; op < m; op++) {
        size_t x, y, r, z;
        cin >> x >> y >> r >> z;
        --x; --y; // 0-based

        vector<size_t> temp(2 * r + 1);

        for (size_t j = r; j > 0; --j) {
            // ! 每层处理 2*j 个位置（不包含最后一个角，避免重复），这里是关键点
            const size_t len = 2 * j;

            // 暂存当前层的上边：top row, col = (y-j) .. (y+j-1)
            for (size_t k = 0; k < len; ++k) {
                temp[k] = matrix[x - j][y - j + k];
            }

            for (size_t k = 0; k < len; ++k) {
                // 四个点（环上的对应位置）
                // top    : (x-j, y-j+k)
                // right  : (x-j+k, y+j)
                // bottom : (x+j, y+j-k)
                // left   : (x+j-k, y-j)

                const size_t top_r = x - j;
                const size_t top_c = y - j + k;
                const size_t right_r = x - j + k;
                const size_t right_c = y + j;
                const size_t bot_r = x + j;
                const size_t bot_c = y + j - k;
                const size_t left_r = x + j - k;
                const size_t left_c = y - j;

                if (z == 0) {
                    // 顺时针：left -> top -> right -> bottom -> left
                    const size_t leftVal  = matrix[left_r][left_c];
                    const size_t botVal   = matrix[bot_r][bot_c];
                    const size_t rightVal = matrix[right_r][right_c];

                    matrix[top_r][top_c] = leftVal;
                    matrix[right_r][right_c] = temp[k];
                    matrix[bot_r][bot_c] = rightVal;
                    matrix[left_r][left_c] = botVal;
                } else {
                    // 逆时针：right -> top -> left -> bottom -> right
                    const size_t rightVal = matrix[right_r][right_c];
                    const size_t botVal   = matrix[bot_r][bot_c];
                    const size_t leftVal  = matrix[left_r][left_c];

                    matrix[top_r][top_c] = rightVal;
                    matrix[left_r][left_c] = temp[k];
                    matrix[bot_r][bot_c] = leftVal;
                    matrix[right_r][right_c] = botVal;
                }
            }
        }
    }

    for (const auto &row : matrix) {
        for (size_t j = 0; j < row.size(); ++j) {
            if (j) cout << ' ';
            cout << row[j];
        }
        cout << '\n';
    }
    return 0;
}
