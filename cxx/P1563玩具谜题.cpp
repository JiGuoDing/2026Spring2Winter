//
// Created by 基国鼎（实习） on 2026/1/26.
//

#include <iostream>
#include <vector>

namespace jgd {
    class ToyMan {
    public:
        int direction;
        std::string occupation;

        ToyMan(int _direction, const std::string& _occupation) : direction(_direction), occupation(_occupation) {}
    };
}

int main() {
    size_t n, m, step;
    std::cin >> n >> m;

    std::vector<jgd::ToyMan> toy_men;

    int direction;
    std::string occupation;
    for (int i = 0; i < n; i++) {
        std::cin >> direction >> occupation;
        toy_men.emplace_back(direction, occupation);
    }

    size_t idx = 0;
    for (int i = 0; i < m; i++) {
        std::cin >> direction >> step;
        if (direction == 0) {
            if (toy_men[idx].direction == 0) {
                // 面向圈内向左数
                idx = (idx + n - step) % n;
            } else {
                // 面向圈内向右数
                idx = (idx + step) % n;
            }
        } else {
            if (toy_men[idx].direction == 0) {
                // 面向圈外向左数
                idx = (idx + step) % n;
            } else {
                // 面向圈外向右数
                idx = (idx + n - step) % n;
            }
        }
    }
    std::cout << toy_men[idx].occupation;
    return 0;
}