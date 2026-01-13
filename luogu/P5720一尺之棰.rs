use std::io;

fn main() {
    // 读取输入
    let mut input_line = String::new();
    io::stdin().read_line(&mut input_line).expect("Failed to read line");

    // 解析出输入整数
    let mut a = input_line.trim().parse::<i32>().expect("Invalid number");

    let mut cnt = 1;
    while a > 1 {
        a /= 2;
        cnt += 1;

        if a == 1 {
            break;
        }
    }

    println!("{}", cnt)
}