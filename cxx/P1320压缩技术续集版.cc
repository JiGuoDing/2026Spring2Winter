#include <cstddef>
#include <iostream>
#include <string>

int main() {
    std::string input_line;

    // 读取第一行以确定 N
    std::cin >> input_line;
    size_t n = input_line.length();

    std::cout << n << " "; // 先输出 N

    // 关键修正 1: 题目要求先统计 0 的个数，所以初始目标字符设为 '0'
    char current_target = '0'; 
    // 关键修正 2: 计数器从 0 开始
    size_t current_cnt = 0;

    // 处理 N 行
    for (size_t i = 0; i < n; ++i) {
        // 如果不是第一行，需要继续读入下一行
        // 注意：第一行已经在外面读过了，i=0 时直接处理 input_line
        if (i != 0) {
            std::cin >> input_line;
        }

        for (char c : input_line) {
            if (c == current_target) {
                // 如果当前字符符合当前统计的目标，计数 +1
                current_cnt++;
            } else {
                // 如果字符变了（0变1 或 1变0）
                std::cout << current_cnt << " "; // 输出上一段的计数
                current_cnt = 1;                 // 新的一段从 1 开始
                // 切换目标字符
                if (current_target == '0') current_target = '1';
                else current_target = '0';
            }
        }
    }
    // 输出最后一段的计数
    std::cout << current_cnt;

    return 0;
}
