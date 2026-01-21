use std::io;
use std::collections::HashMap;


// 带记忆化的递归函数，使用 u64 防止 i32 溢出
fn fibonacci_memo(n: u64, memo: &mut HashMap<u64, u64>) -> u64 {
    // 边界条件
    if n <= 1 {
        return n;
    }
    // 先查缓存，存在则直接返回，避免重复计算
    if let Some(&val) = memo.get(&n) {
        return val;
    }
    // 递归计算并缓存结果
    let val = fibonacci_memo(n - 1, memo) + fibonacci_memo(n - 2, memo);
    memo.insert(n, val);
    val
}

// 对外封装的函数
fn fibonacci(n: u64) -> u64 {
    let mut memo = HashMap::new();
    fibonacci_memo(n, &mut memo)
}

// 循环 (迭代) 方式实现 fibonacci
fn fibonacci_iter(n :u64) -> u64 {
    // 边界条件
    if n <= 1 {
        return n;
    }

    let mut a = 0;
    let mut b = 1;

    for _ in 1..n {
        let c = a + b;
        a = b;
        b = c;
    }
    b
}

fn main() {
    // 读取输入
    let mut input_line = String::new();
    io::stdin().read_line(&mut input_line).expect("Failed to read line");

    // 解析输入，一个整数
    let n = input_line.trim().parse::<u64>().unwrap();

    // 解析输入，两个整数
    // let mut iter = input_line.trim().split_whitespace().map(|s| s.parse::<i32>().unwrap());
    // let (a, b) = (iter.next().unwrap(), iter.next().unwrap());

    println!("{:.2}", fibonacci_iter(n) as f64)
}