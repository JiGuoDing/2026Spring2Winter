//! 12 - Vector集合

fn main() {
    println!("╔══════════════════════════════════════╗");
    println!("║    Rust 学习系列 12: Vector集合      ║");
    println!("╚══════════════════════════════════════╝");
    
    // 创建Vector
    let mut v: Vec<i32> = Vec::new();
    v.push(1);
    v.push(2);
    v.push(3);
    println!("\nVector: {:?}", v);
    
    // 使用宏创建
    let v2 = vec![1, 2, 3, 4, 5];
    println!("vec!宏: {:?}", v2);
    
    // 读取元素
    let third = &v2[2];
    println!("\n第三个元素: {}", third);
    
    match v2.get(2) {
        Some(value) => println!("get方法: {}", value),
        None => println!("越界"),
    }
    
    // 遍历
    println!("\n遍历:");
    for i in &v2 {
        println!("  {}", i);
    }
    
    // 可变遍历
    let mut v3 = vec![1, 2, 3];
    for i in &mut v3 {
        *i += 10;
    }
    // 另一种遍历的写法 (函数式编程风格，使用迭代器和闭包)
    // * iter_mut() 返回一个可变引用迭代器
    // * |x| 是闭包的参数部分，*x += 10 是闭包的函数体
    // * |参数1, 参数2, ...| -> 返回类型 {函数体 (如果是单表达式则可省略大括号)}
    v3.iter_mut().for_each(|x| *x += 10);
    println!("\n修改后: {:?}", v3);
    
    // 使用枚举存储多种类型
    #[derive(Debug)]
    enum SpreadsheetCell {
        Int(i32),
        Float(f64),
        Text(String),
    }
    
    let row = vec![
        SpreadsheetCell::Int(3),
        SpreadsheetCell::Float(10.12),
        SpreadsheetCell::Text(String::from("blue")),
    ];
    println!("\n多类型: {:?}", row);
    
    println!("\n💡 下一步: 学习 13_string.rs - String字符串");
}
