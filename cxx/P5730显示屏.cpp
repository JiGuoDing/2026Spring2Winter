//
// Created by 基国鼎（实习） on 2026/1/29.
//

#include <iostream>
#include <vector>

int main() {
    int n;
    std::cin >> n;
    size_t cnt = 0;

    std::string num;
    // 读入一个长度为 n 的自然数
    std::cin >> num;

    // 用一个二维数组表示
    std::vector<std::vector<char>> screen(5);

    for (const char & ch : num) {
        switch (ch) {
            case '0':
                screen[0].emplace_back('X');
                screen[0].emplace_back('X');
                screen[0].emplace_back('X');

                screen[1].emplace_back('X');
                screen[1].emplace_back('.');
                screen[1].emplace_back('X');

                screen[2].emplace_back('X');
                screen[2].emplace_back('.');
                screen[2].emplace_back('X');

                screen[3].emplace_back('X');
                screen[3].emplace_back('.');
                screen[3].emplace_back('X');

                screen[4].emplace_back('X');
                screen[4].emplace_back('X');
                screen[4].emplace_back('X');
                break;
            case '1':
                screen[0].emplace_back('.');
                screen[0].emplace_back('.');
                screen[0].emplace_back('X');

                screen[1].emplace_back('.');
                screen[1].emplace_back('.');
                screen[1].emplace_back('X');

                screen[2].emplace_back('.');
                screen[2].emplace_back('.');
                screen[2].emplace_back('X');

                screen[3].emplace_back('.');
                screen[3].emplace_back('.');
                screen[3].emplace_back('X');

                screen[4].emplace_back('.');
                screen[4].emplace_back('.');
                screen[4].emplace_back('X');
                break;
            case '2':
                screen[0].emplace_back('X');
                screen[0].emplace_back('X');
                screen[0].emplace_back('X');

                screen[1].emplace_back('.');
                screen[1].emplace_back('.');
                screen[1].emplace_back('X');

                screen[2].emplace_back('X');
                screen[2].emplace_back('X');
                screen[2].emplace_back('X');

                screen[3].emplace_back('X');
                screen[3].emplace_back('.');
                screen[3].emplace_back('.');

                screen[4].emplace_back('X');
                screen[4].emplace_back('X');
                screen[4].emplace_back('X');
                break;
            case '3':
                screen[0].emplace_back('X');
                screen[0].emplace_back('X');
                screen[0].emplace_back('X');

                screen[1].emplace_back('.');
                screen[1].emplace_back('.');
                screen[1].emplace_back('X');

                screen[2].emplace_back('X');
                screen[2].emplace_back('X');
                screen[2].emplace_back('X');

                screen[3].emplace_back('.');
                screen[3].emplace_back('.');
                screen[3].emplace_back('X');

                screen[4].emplace_back('X');
                screen[4].emplace_back('X');
                screen[4].emplace_back('X');
                break;
            case '4':
                screen[0].emplace_back('X');
                screen[0].emplace_back('.');
                screen[0].emplace_back('X');

                screen[1].emplace_back('X');
                screen[1].emplace_back('.');
                screen[1].emplace_back('X');

                screen[2].emplace_back('X');
                screen[2].emplace_back('X');
                screen[2].emplace_back('X');

                screen[3].emplace_back('.');
                screen[3].emplace_back('.');
                screen[3].emplace_back('X');

                screen[4].emplace_back('.');
                screen[4].emplace_back('.');
                screen[4].emplace_back('X');
                break;
            case '5':
                screen[0].emplace_back('X');
                screen[0].emplace_back('X');
                screen[0].emplace_back('X');

                screen[1].emplace_back('X');
                screen[1].emplace_back('.');
                screen[1].emplace_back('.');

                screen[2].emplace_back('X');
                screen[2].emplace_back('X');
                screen[2].emplace_back('X');

                screen[3].emplace_back('.');
                screen[3].emplace_back('.');
                screen[3].emplace_back('X');

                screen[4].emplace_back('X');
                screen[4].emplace_back('X');
                screen[4].emplace_back('X');
                break;
            case '6':
                screen[0].emplace_back('X');
                screen[0].emplace_back('X');
                screen[0].emplace_back('X');

                screen[1].emplace_back('X');
                screen[1].emplace_back('.');
                screen[1].emplace_back('.');

                screen[2].emplace_back('X');
                screen[2].emplace_back('X');
                screen[2].emplace_back('X');

                screen[3].emplace_back('X');
                screen[3].emplace_back('.');
                screen[3].emplace_back('X');

                screen[4].emplace_back('X');
                screen[4].emplace_back('X');
                screen[4].emplace_back('X');
                break;
            case '7':
                screen[0].emplace_back('X');
                screen[0].emplace_back('X');
                screen[0].emplace_back('X');

                screen[1].emplace_back('.');
                screen[1].emplace_back('.');
                screen[1].emplace_back('X');

                screen[2].emplace_back('.');
                screen[2].emplace_back('.');
                screen[2].emplace_back('X');

                screen[3].emplace_back('.');
                screen[3].emplace_back('.');
                screen[3].emplace_back('X');

                screen[4].emplace_back('.');
                screen[4].emplace_back('.');
                screen[4].emplace_back('X');
                break;
            case '8':
                screen[0].emplace_back('X');
                screen[0].emplace_back('X');
                screen[0].emplace_back('X');

                screen[1].emplace_back('X');
                screen[1].emplace_back('.');
                screen[1].emplace_back('X');

                screen[2].emplace_back('X');
                screen[2].emplace_back('X');
                screen[2].emplace_back('X');

                screen[3].emplace_back('X');
                screen[3].emplace_back('.');
                screen[3].emplace_back('X');

                screen[4].emplace_back('X');
                screen[4].emplace_back('X');
                screen[4].emplace_back('X');
                break;
            case '9':
                screen[0].emplace_back('X');
                screen[0].emplace_back('X');
                screen[0].emplace_back('X');

                screen[1].emplace_back('X');
                screen[1].emplace_back('.');
                screen[1].emplace_back('X');

                screen[2].emplace_back('X');
                screen[2].emplace_back('X');
                screen[2].emplace_back('X');

                screen[3].emplace_back('.');
                screen[3].emplace_back('.');
                screen[3].emplace_back('X');

                screen[4].emplace_back('X');
                screen[4].emplace_back('X');
                screen[4].emplace_back('X');

                break;
            default: break;
        }

        if (++cnt < n) {
            screen[0].emplace_back('.');
            screen[1].emplace_back('.');
            screen[2].emplace_back('.');
            screen[3].emplace_back('.');
            screen[4].emplace_back('.');
        }
    }

    for (const auto & line : screen) {
        for (const char & ch : line) {
            std::cout << ch;
        }
        std::cout << std::endl;
    }

    return 0;
}