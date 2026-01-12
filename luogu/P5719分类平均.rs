use std::io;

fn main() {
    // 读取输入
    let mut input_line = String::new();
    io::stdin().read_line(&mut input_line).expect("Failed to read line");
    
    // 创建迭代器，处理输入字符
    // unwrap() 方法表示如果成功就取到结果，如果失败，程序直接 panic
    let mut it = input_line.split_whitespace().map(|ch| ch.parse::<i32>().unwrap());
    // 从迭代器中取出两个整数，元组结构，把右边的两个值分别赋给 n, k
    let (n, k) = (it.next().unwrap(), it.next().unwrap());

    let mut cnt_a = 0;
    let mut sum_a = 0;
    let mut cnt_b = 0;
    let mut sum_b = 0;

    for i in 1..=n {
        if i % k == 0 {
            cnt_a += 1;
            sum_a += i;
        } else {
            cnt_b += 1;
            sum_b += i;
        }
    }

    let avg_a = sum_a as f64 / cnt_a as f64;
    let avg_b = sum_b as f64 / cnt_b as f64;

    // {0:.1} 表示第一个参数保留 1 位小数，{1:.1} 表示第二个参数保留 1 位小数
    println!("{0:.1} {1:.1}", avg_a, avg_b);
}