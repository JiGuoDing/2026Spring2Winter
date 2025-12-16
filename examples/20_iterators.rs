//! 20 - 迭代器

fn main() {
    println!("╔══════════════════════════════════════╗");
    println!("║    Rust 学习系列 20: 迭代器          ║");
    println!("╚══════════════════════════════════════╝");
    
    // 创建迭代器
    let v1 = vec![1, 2, 3];
    let v1_iter = v1.iter();
    
    println!("\n遍历迭代器:");
    for val in v1_iter {
        println!("  {}", val);
    }
    
    // 迭代器适配器
    let v2: Vec<i32> = vec![1, 2, 3];
    let v3: Vec<_> = v2.iter().map(|x| x + 1).collect();
    println!("\nmap: {:?} -> {:?}", v2, v3);
    
    // filter
    let v4: Vec<_> = v2.iter().filter(|x| **x > 1).collect();
    println!("filter: {:?}", v4);
    
    // sum
    let total: i32 = v2.iter().sum();
    println!("sum: {}", total);
    
    // 链式调用
    let result: Vec<_> = vec![1, 2, 3, 4, 5, 6]
        .iter()
        .filter(|x| **x % 2 == 0)
        .map(|x| x * 2)
        .collect();
    println!("\n链式调用: {:?}", result);
    
    // enumerate
    println!("\n带索引:");
    for (i, v) in vec!["a", "b", "c"].iter().enumerate() {
        println!("  {}: {}", i, v);
    }
    
    println!("\n💡 下一步: 学习 21_closures.rs - 闭包");
}
