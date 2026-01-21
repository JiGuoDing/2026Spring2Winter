use std::io;


fn main() {
    // 读取输入
    let mut input_line1 = String::new();
    io::stdin().read_line(&mut input_line1).expect("Failed to read line");
    // 解析输入，一个整数
    let n = input_line1.trim().parse::<u64>().unwrap();

    // ! 算术基本定理可表述为：任何一个大于 1 的自然数 N,如果 N 不为质数，那么 N 可以唯一分解成有限个质数的乘积
    for i in 2..n {
        if n % i == 0 {
            println!("{}", n/i);
            break;
        }
    }
}