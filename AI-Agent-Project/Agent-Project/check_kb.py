import os
from datetime import datetime

def check_kb():
    base_dir = r"c:\workplace\2026Spring2Winter\AI-Agent-Project\Agent-Project"
    data_dir = os.path.join(base_dir, "data")
    
    # 1. 检查目录存在
    assert os.path.exists(data_dir), f"错误：目录 {data_dir} 不存在"
    
    expected_files = {
        "故障排除.txt",
        "扫地机器人100问.txt",
        "扫拖一体机器人100问.txt",
        "维护保养.txt",
        "选购指南.txt"
    }
    
    # 2. 检查目录内文件
    actual_files = set(os.listdir(data_dir))
    assert actual_files == expected_files, f"错误：data 目录内容不符。期望：{expected_files}，实际：{actual_files}"
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    for filename in expected_files:
        filepath = os.path.join(data_dir, filename)
        
        # 3. 检查扩展名
        assert filename.endswith(".txt"), f"错误：文件 {filename} 扩展名不是 .txt"
        
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            content = "".join(lines)
            
            # 4. 检查首字符为 #
            assert content.startswith("#"), f"错误：文件 {filename} 必须以 # 开头"
            
            # 5. 检查末行日期
            last_line = lines[-1].strip()
            expected_prefix = "更新日期："
            assert last_line.startswith(expected_prefix), f"错误：文件 {filename} 末行格式错误。实际：'{last_line}'"
            
            file_date_str = last_line.replace(expected_prefix, "").strip()
            try:
                file_date = datetime.strptime(file_date_str, "%Y-%m-%d")
                today_date = datetime.strptime(today_str, "%Y-%m-%d")
                assert file_date >= today_date, f"错误：文件 {filename} 日期 {file_date_str} 早于今日 {today_str}"
            except ValueError:
                raise AssertionError(f"错误：文件 {filename} 日期格式无效：{file_date_str}")

    print("RAG 知识库初始化完成，5 个文件全部符合规范。")

if __name__ == "__main__":
    try:
        check_kb()
    except AssertionError as e:
        print(f"校验失败：{e}")
        exit(1)
    except Exception as e:
        print(f"运行出错：{e}")
        exit(1)
