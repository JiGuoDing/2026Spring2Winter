//
// Created by 基国鼎（实习） on 2026/1/29.
//

#include <iostream>
#include <vector>
// 包含 std::reverse() 方法
#include <algorithm>

int main() {
    std::string a, b;
    std::cin >> a >> b;

    size_t length = std::max(a.length(), b.length());
    // 在较短的字符串前补零
    while (a.length() < length) a = '0' + a;
    while (b.length() < length) b = '0' + b;

    // 将 a, b 反置，便于从低位开始相加
    std::vector<int> vec_a = std::vector<int>(length);
    std::vector<int> vec_b = std::vector<int>(length);
    std::vector<int> result = std::vector<int>(length + 1, 0); // 结果数组，长度多一位以防进位
    for (size_t i = 0; i < length; ++i) {
        vec_a[i] = a[length - 1 - i] - '0';
        vec_b[i] = b[length - 1 - i] - '0';
    }

    // 逐位相加
    for (size_t i = 0; i < length; ++i) {
        int sum = vec_a[i] + vec_b[i] + result[i];
        result[i] = sum % 10; // 当前位
        result[i + 1] += sum / 10; // 进位
    }

    // 输出结果
    std::reverse(result.begin(), result.end());
    for (const int & result1 : result) {
        // 跳过前导零
        if (!(result1 == 0 && &result1 == &result[0])) {
            std::cout << result1;
        }
    }

    return 0;
}