#include <iostream>
#include <vector>
#include <unordered_set>

int main() {
    int n, tmp;
    std::cin >> n;

    // 改用int存储数字，符合题目正整数的定义
    std::vector<int> nums(n);
    for (int i = 0; i < n; ++i) {
        std::cin >> tmp;
        nums[i] = tmp;
    }

    // * 用集合存储所有两两之和，自动去重，方便后续查找
    std::unordered_set<int> sum_set;
    // * 用集合存储符合条件的数字，保证每个数只算一次
    std::unordered_set<int> result_set;

    // 第一步：计算所有两个不同数的和，存入sum_set
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            int sum = nums[i] + nums[j];
            sum_set.insert(sum);
        }
    }

    // 第二步：遍历原数组，判断每个数是否在和的集合中
    for (int num : nums) {
        if (sum_set.find(num) != sum_set.end()) {
            result_set.insert(num); // 符合条件的数只存一次
        }
    }

    // 结果集合的大小就是答案
    std::cout << result_set.size() << std::endl;
    return 0;
}