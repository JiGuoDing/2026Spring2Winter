#include <bits/stdc++.h>
using namespace std;

// 返回 nums 中“排序后下标为 k 的元素”(k 为 0-based)
int quickSelect(vector<int>& nums, int k) {
    int l = 0, r = (int)nums.size() - 1;
    while (true) {
        if (l == r) return nums[l];

        // 三数取中选 pivot：取 nums[l], nums[m], nums[r] 的中位数
        int m = (l + r) >> 1;
        if (nums[l] > nums[m]) swap(nums[l], nums[m]);
        if (nums[l] > nums[r]) swap(nums[l], nums[r]);
        if (nums[m] > nums[r]) swap(nums[m], nums[r]);
        int pivot = nums[m];

        // Hoare 风格 partition
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

        // 现在 [l..j] <= pivot，[i..r] >= pivot
        // 中间 (j, i) 区间为 == pivot（可能为空）
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
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, k;
    cin >> n >> k;

    vector<int> nums(n);
    for (int i = 0; i < n; i++) cin >> nums[i];

    cout << quickSelect(nums, k) << "\n";
    return 0;
}
