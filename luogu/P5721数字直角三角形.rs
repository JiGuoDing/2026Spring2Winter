use std::io;

fn format_number(n: i32) -> String {
    format!("{:02}", n)
}

fn main() {
    // 读取输入
    let mut input_line = String::new();
    io::stdin().read_line(&mut input_line).expect("Failed to read line");

    // 解析出输入整数
    let a = input_line.trim().parse::<i32>().expect("Invalid number");

    let mut pt = 1;

    for i in (1..=a).rev() {
        for _ in (1..=i).rev() {
            print!("{}", format_number(pt));
            pt += 1;
        }
        println!("");
    }
}