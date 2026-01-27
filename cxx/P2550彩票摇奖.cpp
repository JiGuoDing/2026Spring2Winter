//
// Created by 基国鼎（实习） on 2026/1/26.
//

#include <iostream>
#include <vector>

int main() {
    uint n, num;
    std::cin >> n;
    std::vector<uint> prize_ticket;
    std::vector<uint> prizes(7, 0);

    // 输入中奖号码
    for (int i = 0; i < 7; i++) {
        std::cin >> num;
        prize_ticket.push_back(num);
    }

    for (int i = 0; i < n; i++) {
        // 输入买的号码
        uint matched_nums = 0;
        for (int j = 0; j < 7; j++) {
            std::cin >> num;
            for (const uint ticket : prize_ticket) {
                if (ticket == num) {
                    matched_nums++;
                    break;
                }
            }
        }
        prizes[matched_nums]++;
    }

    for (auto it = prizes.end(); it != prizes.begin(); --it) {
        std::cout << *it << " ";
    }
    return 0;
}