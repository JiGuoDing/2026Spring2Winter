use std::io;


fn main() {
    // 读取输入
    let mut input_line1 = String::new();
    io::stdin().read_line(&mut input_line1).expect("Failed to read line");
    // 解析输入，一个整数
    let _ = input_line1.trim().parse::<u64>().unwrap();

    // 读取输入
    let mut input_line2 = String::new();
    io::stdin().read_line(&mut input_line2).expect("Failed to read line");
    // 解析输入，若干个整数
    let nums = input_line2.trim().split_whitespace().map(|ch| ch.parse::<i32>().unwrap()).collect::<Vec<i32>>();

    let min = nums.iter().min().unwrap();
    let max = nums.iter().max().unwrap();
    
    let avg = (nums.iter().sum::<i32>() - min - max) as f32 / (nums.len() - 2) as f32;

    println!("{:.2}", avg);
}