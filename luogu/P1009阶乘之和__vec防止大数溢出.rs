use std::io;

// 大整数乘法，防止溢出，num (Vec<u8> 存储的大整数) * x (普通整数)，低位在前，方便进位计算
fn multiply(mut num: Vec<u8>, x: i32) -> Vec<u8> {
    // 进位
    let mut carry = 0;

    for ele in &mut num {
        let product = (*ele as i32) * x + carry;
        // 当前位的新值
        *ele = (product % 10) as u8;
        // 更新进位
        carry = product / 10;
    }
    // 处理剩余的进位 (可能进位有多位数)
    while carry > 0 {
        num.push((carry % 10) as u8);
        carry /= 10;
    }
    num
}

// 大整数加法，同样是低位在前
fn add(mut a: Vec<u8>, mut b: Vec<u8>) -> Vec<u8> {
    let mut carry = 0;
    let mut result = Vec::new();
    let max_len = a.len().max(b.len());

    // 补零对齐长度
    while a.len() < max_len {
        a.push(0);
    }
    while b.len() < max_len {
        b.push(0);
    }

    // 逐位相加
    for i in 0..max_len {
        let sum = a[i] as i32 + b[i] as i32 + carry;
        result.push((sum % 10) as u8);
        carry = sum / 10;
    }
    // 处理最后的进位
    if carry > 0 {
        result.push(carry as u8);
    }

    result
}

fn main() {
    // 读取输入
    let mut input_line = String::new();
    io::stdin().read_line(&mut input_line).expect("Failed to read line");

    // 解析出输入整数
    let n = input_line.trim().parse::<i32>().expect("Invalid number");

    // 总和用 Vec<u8> 存储，低位在前
    let mut sum = Vec::<u8>::new();
    sum.push(0);

    // 当前阶乘值  vec![] 与上面显示构造再 push 值效果相同
    let mut factorial = vec![1];

    for i in 1..=n {
        // 计算新阶乘值
        factorial = multiply(factorial, i);
        // 累加得到阶乘和
        sum = add(sum, factorial.clone());
    }

    // 反转数组，并输出每一位
    sum.iter().rev().for_each(|ele| print!("{}", ele));
    println!();
}