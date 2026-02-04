#include <cstddef>
#include <iostream>
#include <vector>

int main(){
    size_t s1, s2, s3;
    std::cin >> s1 >> s2 >> s3;

    // 用于统计各个和出现次数的数组
    std::vector<size_t> sum_counter(s1+s2+s3+1, 0);

    // 暴力循环遍历
    for (size_t i = 1; i <= s1; ++i)
        for (size_t j = 1; j <= s2; ++j)
            for (size_t k = 1; k <= s3; ++k) {
                ++sum_counter[i+j+k];
            }

    // 当前出现最频繁的最小的和
    size_t min_sum = s1 + s2 + s3 + 1;
    // 当前出现次数最多的和的出现次数
    size_t max_counter = 0;
    for (size_t i = 3; i < sum_counter.size(); i++) {
        if (sum_counter[i] > max_counter) {
            max_counter = sum_counter[i];
            min_sum = i;
        }
    }

    std::cout << min_sum << std::endl;

    return 0;
}