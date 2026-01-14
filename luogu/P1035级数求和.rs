use std::io;

fn main() {
    // 读取输入
    let mut input_line = String::new();
    io::stdin().read_line(&mut input_line).expect("Failed to read line");

    // 解析输入
    let k = input_line.trim().parse::<i32>().expect("Invalid input");

    let mut tmp = 0.0;
    let mut idx = 0;

    while tmp <= k as f64 {
        idx += 1;
        tmp += 1.0 / (idx as f64);
    }

    println!("{}", idx);
}