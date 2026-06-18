def groupAnagrams(self, strs):
    """
    :type strs: List[str]
    :rtype: List[List[str]]
    """
    res_dict = {}
    for ele_str in strs:
        # 将字符串排序，作为字典的键
        # 例如 "tea" -> "aet"
        key = "".join(sorted(ele_str))
        
        # 如果该键不存在，则初始化一个空列表
        if key not in res_dict:
            res_dict[key] = []
            
        # 将原字符串加入对应的组
        res_dict[key].append(ele_str)
        
    # 返回字典的 values，并转换为列表
    return list(res_dict.values())