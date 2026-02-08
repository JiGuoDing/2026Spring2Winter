#include <iostream>
using namespace std;

int main() {
    size_t n, m, out_cnt = 0; // n是点阵大小，m是当前连续个数，out_cnt是已输出字符数
    cin >> n;
    bool flag = false;        // 初始是0（false对应0，true对应1）
    size_t column = 0;        // 当前列号，0~n-1，满n则换行

    // 只要输出的字符数没到N×N，就持续读取压缩数
    while (out_cnt < n * n) {
        cin >> m;
        // 处理当前连续的m个0/1（逐位输出）
        for (size_t i = 0; i < m; ++i) {
            // 输出当前字符（0/1）
            cout << (flag ? '1' : '0');
            out_cnt++;  // 已输出数+1
            column++;   // 列号+1

            // 列号满n，说明到行尾，换行并重置列号
            if (column == n) {
                cout << endl;
                column = 0;
            }
        }
        flag = !flag; // 切换0/1
    }
    return 0;
}