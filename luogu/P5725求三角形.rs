use std::io;


fn main() {
    // 读取输入
    let mut input_line1 = String::new();
    io::stdin().read_line(&mut input_line1).expect("Failed to read line");
    // 解析输入，一个整数
    let n = input_line1.trim().parse::<u64>().unwrap();

    let mut idx = 1;

    for _ in 0..n {
        for _ in 0..n {
            print!("{:02}", idx);
            idx += 1;
        }
        println!("");
    }

    println!("");

    idx = 1;

    for i in 0..n {
        for _ in 0..n - i - 1 {
            print!("  ")
        }
        for _ in n - i - 1..n {
            print!("{:02}", idx);
            idx += 1;
        }
        println!("");
    }
}