use std::io;

// 【核心优化】用纯数字运算判断回文数（替代字符串操作，性能提升10倍+）
fn is_palindrome(n: i32) -> bool {
    // 负数、以0结尾的非0数不可能是回文数（直接排除）
    if n < 0 || (n % 10 == 0 && n != 0) {
        return false;
    }
    let mut original = n;
    let mut reversed = 0;
    // 只反转一半数字（性能更高）
    while original > reversed {
        reversed = reversed * 10 + original % 10;
        original /= 10;
    }
    // 偶数位：original == reversed；奇数位：original == reversed / 10（去掉中间位）
    original == reversed || original == reversed / 10
}

// 【极致优化】质数判断函数
fn is_prime(n: i32) -> bool {
    if n < 2 {
        return false;
    }
    if n == 2 {
        return true;
    }
    // 偶数直接排除
    if n % 2 == 0 {
        return false;
    }
    // 提前计算平方根（只算一次，避免循环内乘法）
    let sqrt_n = (n as f64).sqrt() as i32;
    let mut i = 3;
    while i <= sqrt_n {
        if n % i == 0 {
            return false;
        }
        i += 2;
    }
    true
}

fn main() {
    // 读取输入
    let mut input_line = String::new();
    io::stdin().read_line(&mut input_line).expect("Failed to read line");

    // 解析输入
    let mut iter = input_line.trim().split_whitespace().map(|s| s.parse::<i32>().unwrap());
    let (a, b) = (iter.next().unwrap(), iter.next().unwrap());

    for i in a..=b {
        if is_palindrome(i) {
            if is_prime(i) {
                println!("{}", i);
            }
        }
    }
}