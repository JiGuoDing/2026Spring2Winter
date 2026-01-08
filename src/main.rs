use std::io::{self, stdin};

fn main() {
    // 读取第一行输入，三个整数
    let mut input_line_1 = String::new();
    io::stdin().read_line(&mut input_line_1).expect("读取第一行输入失败");

    // 解析并转换成数组
    let mut nums: Vec<i32> = input_line_1
    .trim()
    .split_whitespace()
    .map(|s| s.parse().expect("解析整数失败"))
    .collect();

    // 对数组进行升序排序，此时 nums[0]=A, nums[1]=B, nums[2]=C
    nums.sort();

    // 读取第二行输入，三个大写字母
    let mut input_line_2 = String::new();
    io::stdin().read_line(&mut input_line_2).expect("读取第二行输入失败");
    // 去除换行符等空白字符
    let order = input_line_2.trim();

    // 构建结果字符串
    let mut result = Vec::new();
    for ele in order.chars() {
        match ele {
            'A' => result.push(nums[0].to_string()),
            'B' => result.push(nums[1].to_string()),
            'C' => result.push(nums[2].to_string()),
            _ => panic!("输入包含非 ABC 的字符"),
        }
    }

    // 输出结果，用空格分隔
    println!("{}", result.join(" "));
}