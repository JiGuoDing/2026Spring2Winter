use std::io;

fn main() {
    // 读取输入
    let mut input_line = String::new();
    io::stdin().read_line(&mut input_line).expect("Failed to read line");

    // 解析输入
    let k = input_line.trim().parse::<i32>().expect("Invalid input");

    let mut sum = 0;
    // 找到最后的 n
    let mut last_day_idx = 0;

    for i in 1..=k {
        if i * (i + 1) / 2 >= k {
            last_day_idx = i;
            break;
        }
    }

    // 前 n-1 的级数和的天数的钱的和
    for i in 1..last_day_idx {
        sum += i * i;
    }

    sum += (k - last_day_idx * (last_day_idx - 1) / 2) * last_day_idx;

    print!("{}", sum)
}