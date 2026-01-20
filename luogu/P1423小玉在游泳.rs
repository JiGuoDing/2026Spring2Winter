use std::io;

fn main() {
    // 读取输入
    let mut input_line = String::new();
    io::stdin().read_line(&mut input_line).expect("Failed to read line");

    // 解析输入，一个浮点数
    let s = input_line.trim().parse::<f64>().unwrap();

    // 解析输入，两个整数
    // let mut iter = input_line.trim().split_whitespace().map(|s| s.parse::<i32>().unwrap());
    // let (a, b) = (iter.next().unwrap(), iter.next().unwrap());

    // 当前已经游的距离
    let mut distance = 0.0;
    // 每一步游的距离
    let mut step = 2.0;
    // 记录已经游的步数
    let mut cnt = 0;

    while distance < s {
        distance += step;
        cnt += 1;
        step *= 0.98;
    }

    println!("{}", cnt)
}