use std::io;

fn main() {
    // 读取输入
    let mut input_line = String::new();
    io::stdin().read_line(&mut input_line).expect("Failed to read line");

    // 解析输入，一个整数
    let n = input_line.trim().parse::<i32>().unwrap();

    // 解析输入，两个整数
    // let mut iter = input_line.trim().split_whitespace().map(|s| s.parse::<i32>().unwrap());
    // let (a, b) = (iter.next().unwrap(), iter.next().unwrap());


}