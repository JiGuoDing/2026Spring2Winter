use std::io;

fn main() {
    // 读取输入
    let mut input_line = String::new();
    io::stdin().read_line(&mut input_line).expect("Failed to read line");

    // 解析输入，一个整数
    let n = input_line.trim().parse::<i32>().unwrap();

    // 解析输入，两个整数
    // let mut iter = input_line.trim().split_whitespace().map(|s| s.parse::<i32>().unwrap());
    // let (a, b) = (iter.next().unwrap(), iter.next().unwrap());

    // 用来标记 n 是否是负数
    let is_negative = n < 0;
    let n = n.abs();

    let mut n_str = n.to_string();
    // [ERROR] 错误记录：这里虽然用了 mut，但是修饰的是引用本身 (引用可以指向不同的 Vec)，而不是引用指向的 Vec<char>。& 标识不可变借用，因此后续尝试修改 chars[i] 会直接报错
    // let mut chars = &n_str.chars().collect::<Vec<char>>();
    let mut chars = n_str.chars().collect::<Vec<char>>();
    let len = chars.len();
    for i in 0..len / 2 {
        let tmp = chars[i];
        // 交换对称位置的字符
        chars[i] = chars[len - i - 1];
        chars[len - i - 1] = tmp;
    }

    // 去除前导零
    while chars[0] == '0' && chars.len() > 1 {
        chars.remove(0);
    }
    // 将修改后的 Vec<char> 转回 String
    n_str = chars.iter().collect::<String>();
    if is_negative {
        n_str = format!("-{}", n_str);
    }
    println!("{}", n_str);
}