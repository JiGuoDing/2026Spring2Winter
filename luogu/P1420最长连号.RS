use std::io;


fn main() {
    // 读取输入
    let mut input_line1 = String::new();
    io::stdin().read_line(&mut input_line1).expect("Failed to read line");
    // 解析输入，一个整数
    let _ = input_line1.trim().parse::<u64>().unwrap();
    // 解析输入，若干个整数
    let mut input_line2 = String::new();
    io::stdin().read_line(&mut input_line2).expect("Failed to read line");
    let nums = input_line2.trim().split_whitespace().map(|s| s.parse::<i32>().unwrap()).collect::<Vec<i32>>();

    // 解析输入，两个整数
    // let mut iter = input_line.trim().split_whitespace().map(|s| s.parse::<i32>().unwrap());
    // let (a, b) = (iter.next().unwrap(), iter.next().unwrap());

    // 最大连号数
    let mut max_seq_cnt = 1;
    // 当前连号数
    let mut crt_seq_cnt = 1;
    // 上一个数字
    let mut last_one = -1;
    for &num in nums.iter() {
        if num == last_one + 1 {
            crt_seq_cnt += 1;
            max_seq_cnt = max_seq_cnt.max(crt_seq_cnt);
        } else {
            crt_seq_cnt = 1;
        }
            last_one = num;
    }

    println!("{}", max_seq_cnt);
}