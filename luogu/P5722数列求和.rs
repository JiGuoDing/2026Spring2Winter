use std::io;

fn main() {
    // 读取输入
    let mut input_line = String::new();
    io::stdin().read_line(&mut input_line).expect("Failed to read line");

    // 解析输入
    let k = input_line.trim().parse::<i32>().expect("Invalid input");

    let mut sum = 0;

    for i in 1..=k {
        sum += i;
    }

    println!("{}", sum);
}