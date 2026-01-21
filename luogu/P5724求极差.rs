use std::io;


// 求一个 vector 中最大值和最小值的差
fn max2min (nums: Vec<u64>) -> u64 {
    let max_num = nums.iter().max().unwrap();
    let min_num = nums.iter().min().unwrap();
    return max_num - min_num;
}

// 使用临时变量存储最大值和最小值，然后用迭代器简化比较逻辑
fn max2min_iter(nums: Vec<u64>) -> Result<u64, &'static str> {
    // 先检查数组是否为空，避免越界
    if nums.is_empty() {
        return Err("输入的数组不能为空");
    }

    let mut max_num = nums[0];
    let mut min_num = nums[0];

    // 简化比较逻辑：直接用 *num 或利用 Rust 自动解引用
    for &num in nums.iter() {
        if num > max_num {
            max_num = num;
        }
        if num < min_num {
            min_num = num;
        }
    }

    // 无需 return，直接返回表达式结果
    Ok(max_num - min_num)
}
fn main() {
    // 读取输入
    let mut input_line1 = String::new();
    io::stdin().read_line(&mut input_line1).expect("Failed to read line");
    // 解析输入，一个整数
    let _ = input_line1.trim().parse::<u64>().unwrap();
    
    let mut input_line2 = String::new();
    io::stdin().read_line(&mut input_line2).expect("Failed to read line");
    let nums = input_line2.trim().split_whitespace().map(|s| s.parse::<u64>().unwrap()).collect::<Vec<u64>>();

    // 解析输入，两个整数
    // let mut iter = input_line.trim().split_whitespace().map(|s| s.parse::<i32>().unwrap());
    // let (a, b) = (iter.next().unwrap(), iter.next().unwrap());

    println!("{}", max2min(nums))
}