//
// Created by 基国鼎（实习） on 2026/1/29.
//

#include <iostream>
#include <vector>

int main() {
    int m, n;
    std::cin >> m >> n;

    std::vector<size_t> digit_counter(10, 0);

    size_t num;
    for (int i = m; i <=n; ++i) {
        num = i;
        while (num) {
            ++digit_counter[num % 10];
            num /= 10;
        }
    }

    for (const size_t & counter : digit_counter)
        std::cout << counter << " ";

    return 0;
}