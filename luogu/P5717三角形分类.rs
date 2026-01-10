use std::io;

fn is_triangle(a: i32, b: i32, c: i32) -> bool {
    a + b > c && a + c > b && b + c > a
}

fn main() {
    // 读取输入的三个整数
    let mut input_line = String::new();
    io::stdin().read_line(&mut input_line).expect("输入错误");

    // 将输入转为三个整数
    let mut numbers = input_line.split_whitespace()
    .map(|s| s.parse::<i32>().expect("输入错误")).collect::<Vec<i32>>();

    // 首先判断三条边是否能构成三角形
    if !is_triangle(numbers[0], numbers[1], numbers[2]) {
        println!("Not triangle");
        return;
    }

    numbers.sort();

    let square_sum_of_2short = numbers[0].pow(2) + numbers[1].pow(2);

    // 判断锐角直角钝角
    if square_sum_of_2short == numbers[2].pow(2) {
        println!("Right triangle");
    } else if square_sum_of_2short > numbers[2].pow(2) {
        println!("Acute triangle");
    } else {
        println!("Obtuse triangle");
    }

    // 判断等腰
    if numbers[0] == numbers[1] || numbers[1] == numbers[2] || numbers[0] == numbers[2] {
        println!("Isosceles triangle");
        // 判断等腰
        if numbers[0] == numbers[1] && numbers[1] == numbers[2] {
            println!("Equilateral triangle");
        }
    }
}