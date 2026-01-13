use std::io;

fn main() {
    // 读取输入
    let mut input_line = String::new();
    io::stdin()
    .read_line(&mut input_line)
    .expect("Failed to read line");

    // 解析出输入的两个整数
    let mut it = input_line
    .split_whitespace()
    .map(|ch| ch.parse::<i32>()
    .unwrap());

    // let (n, x) = (it.next().unwrap(), it.next().unwrap());
    let (n, x) = match (it.next(), it.next()) {
        (Some(n), Some(x)) => (n, x),
        _ => {
            eprintln!("Invalid input");
            return;
        }
    };

    // let mut cnt = 0;

    // 提前将 x 转为字符
    let target_char = match x.to_string().chars().next() {
        Some(c) => c,
        _ => {
            eprintln!("x is invalid");
            return;
        }
    };

    // for i in 1..=n {
    //     let str_i = i.to_string();
    //     str_i.chars().for_each(|ch| if ch == target_char { cnt += 1; });
    // }

    let cnt = (1..=n)
    .flat_map(|num| num.to_string().chars().collect::<Vec<_>>())
    .filter(|&c| c == target_char)
    .count();

    println!("{}", cnt)
}