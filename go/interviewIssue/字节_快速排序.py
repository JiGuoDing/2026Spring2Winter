# 快速排序 — 两种实现方式


# 方式一：Lomuto 分区
# 思路：
# 1. 选取最右元素作为 pivot。
# 2. 维护指针 i，表示"小于等于 pivot 的区间"的右边界。
# 3. 用 j 从左到右扫描：遇到 arr[j] <= pivot，就扩大 i 并交换 arr[i] 和 arr[j]，
#    把小数"挤"到左边。
# 4. 扫描完后，i+1 就是 pivot 应放的位置，交换 pivot 过去，返回该位置。
# 5. 对 pivot 左右两侧递归。
# 特点：实现简单直观，但交换次数较多（每次都把小元素往左搬）。
# def quicksort_lomuto(arr, low, high):
#     if low < high:
#         pivot_idx = _lomuto_partition(arr, low, high)
#         quicksort_lomuto(arr, low, pivot_idx - 1)
#         quicksort_lomuto(arr, pivot_idx + 1, high)


# def _lomuto_partition(arr, low, high):
#     pivot = arr[high]
#     i = low - 1  # i 指向小于 pivot 的最后一个元素
#     for j in range(low, high):
#         if arr[j] <= pivot:
#             i += 1
#             arr[i], arr[j] = arr[j], arr[i]
#     arr[i + 1], arr[high] = arr[high], arr[i + 1]
#     return i + 1

def _lomuto_partition(arr, left, right):
    pivot = arr[right]
    i = left - 1
    for j in range(left, right):
        if arr[j] <= pivot:
            i += 1
            arr[i], arr[j] = arr[j], arr[i]
    arr[i+1], arr[right] = arr[right], arr[i+1]
    return i+1

def _lomuto_quicksort(arr, left, right):
    if left < right:
        pivot_idx = _lomuto_partition(arr, left, right)
        _lomuto_quicksort(arr, left, pivot_idx-1)
        _lomuto_quicksort(arr, pivot_idx+1, right)


# 方式二：Hoare 分区
# 思路：
# 1. 选取中间元素作为 pivot。
# 2. 左右双指针 i, j：i 从左往右找第一个 >= pivot 的元素，
#    j 从右往左找第一个 <= pivot 的元素。
# 3. 若 i >= j，说明左右已经划分完毕，返回 j 作为分界点。
# 4. 否则交换 arr[i] 和 arr[j]，让左边是小数、右边是大数，继续扫描。
# 5. 注意：递归区间是 [low, pivot_idx] 和 [pivot_idx+1, high]，
#    与 Lomuto 不同，因为 pivot 不一定落在最终位置。
# 特点：比 Lomuto 交换次数少约 3 倍，实际效率更高。
# def quicksort_hoare(arr, low, high):
#     if low < high:
#         pivot_idx = _hoare_partition(arr, low, high)
#         # 注意：Hoare 分区下左区间是 [low, pivot_idx]，右区间是 [pivot_idx+1, high]
#         quicksort_hoare(arr, low, pivot_idx)
#         quicksort_hoare(arr, pivot_idx + 1, high)


# def _hoare_partition(arr, low, high):
#     pivot = arr[(low + high) // 2]
#     i = low - 1
#     j = high + 1
#     while True:
#         i += 1
#         while arr[i] < pivot:
#             i += 1
#         j -= 1
#         while arr[j] > pivot:
#             j -= 1
#         if i >= j:
#             return j
#         arr[i], arr[j] = arr[j], arr[i]

def quickSort_hoare(arr, left, right):
    if left < right:
        pivot_id = _hoare_partition(arr, left, right)
        quickSort_hoare(arr, left ,pivot_id)
        quickSort_hoare(arr, pivot_id+1, right)
        
def _hoare_partition(arr, left, right):
    pivot = arr[(left + right) // 2]
    i = left - 1
    j = right + 1
    while True:
        i += 1
        while arr[i] < pivot:
            i += 1
        j -= 1
        while arr[j] > pivot:
            j -= 1
        if i >= j:
            return j
        arr[i], arr[j] = arr[j], arr[i]


# 测试
if __name__ == "__main__":
    test1 = [3, 6, 8, 10, 1, 2, 1]
    test2 = test1[:]

    quicksort_lomuto(test1, 0, len(test1) - 1)
    print("Lomuto:", test1)

    quicksort_hoare(test2, 0, len(test2) - 1)
    print("Hoare: ", test2)
