use std::io;

fn main() {
    let mut input_line = String::new();
    io::stdin().read_line(&mut input_line).expect("Failed to read line");
    // 解析出整数
    let mut n = input_line.trim().parse::<i32>().expect("Invalid number");

    let mut nums = Vec::<i32>::new();

    nums.push(n);

    while n > 1 {
        if n % 2 == 0{
            // 偶数
            n /= 2;
            nums.push(n);
        } else {
            // 奇数
            n = 3 * n + 1;
            nums.push(n);
        }
    }

    nums.iter().rev().for_each(|ele| print!("{} ", ele));
}
