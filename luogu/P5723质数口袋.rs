use std::io;

// 判断一个数是否为质数
fn is_prime(n: i32) -> bool {
    if n <= 1 {
        return false;
    }
    for i in 2..=(n as f64).sqrt() as i32 {
        if n % i == 0 {
            return false;
        }
    }
    true
}

fn main() {
    // 读取输入
    let mut input_line = String::new();
    io::stdin().read_line(&mut input_line).expect("Failed to read line");

    // 解析输入
    let k = input_line.trim().parse::<i32>().expect("Invalid input");

    let mut tmp_sum = 0;
    let mut cnt = 0;

    for i in 1..=k {
        if is_prime(i) {
            tmp_sum += i;
            if tmp_sum <= k {
                println!("{}", i);
                cnt += 1;
            } else {
                break;
            }
        }
    }

    println!("{}", cnt);
}