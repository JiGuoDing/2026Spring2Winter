#include <iostream>
#include <vector>
#include <algorithm>
#include <string>

int main() {
    std::string a, b;
    std::cin >> a >> b;

    // 特殊情况：如果有一个数是0，直接输出0
    if (a == "0" || b == "0") {
        std::cout << 0 << std::endl;
        return 0;
    }

    int len_a = a.length(), len_b = b.length();
    // 结果数组大小：两个n位数相乘最多2n位
    std::vector<int> result(len_a + len_b, 0);

    // 将字符串反转并转换为数字数组（低位在前）
    for (int i = 0; i < len_a; ++i) {
        int num_a = a[len_a - 1 - i] - '0';
        for (int j = 0; j < len_b; ++j) {
            int num_b = b[len_b - 1 - j] - '0';
            // 累加乘积到对应位置
            result[i + j] += num_a * num_b;
        }
    }

    // 统一处理所有进位（最后处理，效率更高）
    for (int i = 0; i < result.size() - 1; ++i) {
        if (result[i] >= 10) {
            result[i + 1] += result[i] / 10;
            result[i] %= 10;
        }
    }

    // 找到第一个非零位（跳过前导零）
    int start = result.size() - 1;
    while (start >= 0 && result[start] == 0) {
        start--;
    }

    // 从高位到低位输出
    for (int i = start; i >= 0; --i) {
        std::cout << result[i];
    }
    std::cout << std::endl;

    return 0;
}