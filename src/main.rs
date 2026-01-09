use std::io;

fn is_triangle(a: i32, b: i32, c: i32) -> bool {
    a + b > c && a + c > b && b + c > a
}

fn main() {
    // 读取输入的三个整数
    let mut input_line = String::new();
    io::stdin().read_line(&mut input_line).expect("输入错误");

    // 将输入转为三个整数
    let numbers = input_line.split_whitespace()
    .map(|s| s.parse::<i32>().expect("输入错误")).collect::<Vec<i32>>();

    if is_triangle(numbers[0], numbers[1], numbers[2]) {
        println!("Not triangle");
    }

    
}