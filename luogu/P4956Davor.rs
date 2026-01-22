use std::io;


// 给定 X, K，可以得到 52 周存的总库纳数
fn total(x: i32, k: i32) -> i32{
    52 * (7 * x + (1 + 2 + 3 + 4 + 5 + 6) * k)
}

fn main() {
    // 读取输入
    let mut input_line1 = String::new();
    io::stdin().read_line(&mut input_line1).expect("Failed to read line");
    // 解析输入，一个整数
    let n = input_line1.trim().parse::<i32>().unwrap();

    let mut final_x = 0;
    let mut final_k = i32::MAX;

    for x in (1..=100).rev() {
        for k in 1..=10000 {
            if total(x, k) == n {
                if x > final_x || (x == final_x && k < final_k) {
                    final_x = x;
                    final_k = k;
                }
            }
        }
    }

    println!("{}", final_x);
    println!("{}", final_k);
}