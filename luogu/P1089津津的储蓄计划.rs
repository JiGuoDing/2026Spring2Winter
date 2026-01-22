use std::io;
use std::io::BufRead;


fn main() {

    // 连续读取 12 行内容
    let stdin = io::stdin();
    let mut lines = stdin.lock().lines();

    let mut nums = Vec::with_capacity(12);
    for _ in 0..12 {
        let x: i64 = lines.next().unwrap().unwrap().trim().parse().unwrap();
        nums.push(x);
    }

    let mut month= 1;
    let mut balance = 0;
    let mut deposit = 0;

    for &num in nums.iter() {
        balance += 300;

        if balance - num >= 100 {
            // 可以存钱
            // 本月末可以剩余 balance - num % 100
            // 本月可以存 balance - num - (balance - num % 100)
            deposit += balance - num - (balance - num) % 100;
            balance = (balance - num) % 100;

        } else if balance - num >= 0 {
            // 不能存钱
            balance = balance - num;

        } else {
            // 钱不够本月预算
            println!("-{}", month);
            return;
        }
        month += 1;
    }


    println!("{}", (deposit as f64 * 1.2 ) as i64 + balance);

}