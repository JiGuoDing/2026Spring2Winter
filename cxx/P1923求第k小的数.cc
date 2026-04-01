#include <bits/stdc++.h>
using namespace std;

/*
 * 题目功能：
 * 给定 n 个整数，输出按从小到大排序后下标为 k 的元素。
 * 这里的 k 按题目约定是 0-based，即 k=0 表示最小值。
 *
 * 解题思路：
 * 使用快速选择（Quick Select）而不是完整排序。
 * 每轮选择一个 pivot，并把数组按 pivot 分成三部分趋势：
 * 1. 左侧元素 <= pivot
 * 2. 中间元素 == pivot
 * 3. 右侧元素 >= pivot
 * 然后根据目标下标 k 所在的位置，只保留可能包含答案的一侧继续处理。
 *
 * 复杂度：
 * 平均时间复杂度 O(n)，最坏时间复杂度 O(n^2)。
 * 额外空间复杂度 O(1)，因为分区过程在原数组上完成。
 */

/*
 * quickSelect:
 * 在 nums 中原地执行快速选择，返回“排序后下标为 k 的元素”。
 *
 * 参数说明：
 * - nums: 待查找的数组，会在函数内部被交换、重排。
 * - k   : 目标下标，使用 0-based 编号。
 *
 * 返回值：
 * - nums 排序后位于第 k 个位置的值。
 */
int quickSelect(vector<int>& nums, int k) {
    // 当前待处理区间为闭区间 [l, r]。
    int l = 0, r = (int)nums.size() - 1;
    while (true) {
        // 区间中只剩一个元素时，它就是答案。
        if (l == r) return nums[l];

        /*
         * 选取主元 pivot。
         * 这里采用“三数取中”策略：从区间左端、中点、右端取三个数，
         * 通过交换让 nums[l] <= nums[m] <= nums[r]，再取 nums[m] 作为 pivot。
         *
         * 这样做通常比直接固定取端点更稳，能在一定程度上降低退化概率。
         */
        int m = (l + r) >> 1;
        if (nums[l] > nums[m]) swap(nums[l], nums[m]);
        if (nums[l] > nums[r]) swap(nums[l], nums[r]);
        if (nums[m] > nums[r]) swap(nums[m], nums[r]);
        int pivot = nums[m];

        /*
         * Hoare 风格分区：
         * - i 从左向右找第一个 >= pivot 的位置
         * - j 从右向左找第一个 <= pivot 的位置
         * 若 i <= j，则交换二者并继续推进指针。
         *
         * 分区结束后：
         * - [l, j] 中的元素都 <= pivot
         * - [i, r] 中的元素都 >= pivot
         * - (j, i) 之间的元素可视为“落在 pivot 附近”的区域
         */
        int i = l, j = r;
        while (i <= j) {
            while (nums[i] < pivot) ++i;
            while (nums[j] > pivot) --j;
            if (i <= j) {
                swap(nums[i], nums[j]);
                ++i;
                --j;
            }
        }

        /*
         * 根据 k 所在的位置缩小搜索区间：
         * 1. 若 k 在左半边 [l, j]，答案一定还在左侧，丢弃右侧。
         * 2. 若 k 在右半边 [i, r]，答案一定还在右侧，丢弃左侧。
         * 3. 否则 k 落在中间区域，说明答案就是 pivot。
         */
        if (k <= j) {
            r = j;
        } else if (k >= i) {
            l = i;
        } else {
            return pivot;
        }
    }
}

int main() {
    // 关闭 iostream 与 stdio 的同步，并解绑 cin/cout，提高输入输出速度。
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // 读入数据规模 n 和目标下标 k。
    int n, k;
    cin >> n >> k;

    // 读入原始数组。
    vector<int> nums(n);
    for (int i = 0; i < n; i++) cin >> nums[i];

    // 输出第 k 小的数。题目中的 k 已经是 0-based，可直接传入。
    cout << quickSelect(nums, k) << "\n";
    return 0;
}
