//
// Created by 基国鼎（实习） on 2026/1/26.
//

#include <iostream>
#include <vector>

namespace jgd {
    class Student {
    public:
        uint cn;
        uint math;
        uint en;

        explicit Student(uint cn, uint math, uint en) : cn(cn), math(math), en(en) {}

        uint abs(uint num1, uint num2) {
            return (num1 > num2) ? num1 - num2 : num2 - num1;
        };

        bool is_comparable(const Student& s1) {
            const uint diff1 = abs(this->cn, s1.cn);
            const uint diff2 = abs(this->math, s1.math);
            const uint diff3 = abs(this->en, s1.en);
            const uint diff4 = abs(this->cn + this->math + this->en, s1.cn + s1.math + s1.en);
            if ( diff1 <= 5 && diff2 <= 5 && diff3 <= 5 && diff4 <= 10) {
                return true;
            }
            return false;
        }
    };
}

int main() {
    int n, cn, math, en;
    uint cnt = 0;
    std::vector<jgd::Student> students;
    std::cin >> n;
    for (int i = 0; i < n; i++) {
        std::cin >> cn >> math >> en;
        students.push_back(jgd::Student(cn, math, en));
    }

    for (int i = 0; i < students.size(); i++) {
        for (int j = i+1; j < students.size(); j++) {
            // 判读是否是旗鼓相当的对手
            if (students[i].is_comparable(students[j])) {
                cnt++;
            }
        }
    }
    std::cout << cnt << std::endl;
    return 0;
}
