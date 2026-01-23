#include <iostream>
#include <vector>
#include <utility>
// 用于排序的头文件
#include <algorithm>

int main() {
    int l, m, u, v;
    std::vector<std::pair<int, int>> regions;
    std::cin >> l >> m;

    // 读取所有需要移除树木的区域
    for (int i = 0; i < m; i++) {
        std::cin >> u >> v;
        regions.emplace_back(u, v);
    }

    // 初始化剩余树木数量（道路长度l，树木数量是l+1）
    int treeCount = l + 1;

    // 处理空区间的特殊情况（没有需要移除的区域）
    if (!regions.empty()) {
        // 第一步：按区间的起始点从小到大排序
        std::sort(regions.begin(), regions.end());

        // 第二步：合并重叠/相邻的区间
        std::vector<std::pair<int, int>> mergedRegions;
        // 先把第一个区间加入合并列表
        mergedRegions.push_back(regions[0]);

        for (size_t i = 1; i < regions.size(); i++) {
            // 获取合并列表中最后一个区间
            auto& last = mergedRegions.back();
            // 当前区间的起始点 <= 最后一个合并区间的结束点 → 重叠/相邻，需要合并
            if (regions[i].first <= last.second) {
                // 合并后的结束点取两个区间的最大值
                last.second = std::max(last.second, regions[i].second);
            } else {
                // 不重叠，直接加入合并列表
                mergedRegions.push_back(regions[i]);
            }
        }

        // 第三步：用合并后的区间计算需要移除的树木数量
        for (const auto& p : mergedRegions) {
            int removedCount = p.second - p.first + 1;
            treeCount -= removedCount;
        }
    }

    // 输出剩余树木数量
    std::cout << treeCount << std::endl;
    return 0;
}