def twoSum(nums, target):
    """
    :type nums: List[int]
    :type target: int
    :rtype: List[int]
    """
    seen_nums = {}
    for i, num in enumerate(nums):
        if target - num in seen_nums:
            return [seen_nums[target - num], i]
        seen_nums[num] = i
    return []

if __name__ == "__main__":
    nums = [2, 7, 11, 15]
    target = 9
    print(twoSum(nums, target))