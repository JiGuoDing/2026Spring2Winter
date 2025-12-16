//! 14 - HashMap集合

use std::collections::HashMap;

fn main() {
    println!("╔══════════════════════════════════════╗");
    println!("║    Rust 学习系列 14: HashMap集合     ║");
    println!("╚══════════════════════════════════════╝");
    
    // 创建HashMap
    let mut scores = HashMap::new();
    scores.insert(String::from("Blue"), 10);
    scores.insert(String::from("Yellow"), 50);
    
    println!("\nHashMap: {:?}", scores);
    
    // 访问值
    let team_name = String::from("Blue");
    let score = scores.get(&team_name).copied().unwrap_or(0);
    println!("Blue队得分: {}", score);
    
    // 遍历
    println!("\n遍历:");
    for (key, value) in &scores {
        println!("  {}: {}", key, value);
    }
    
    // 更新值
    scores.insert(String::from("Blue"), 25);  // 覆盖
    println!("\n覆盖后: {:?}", scores);
    
    // 只在键不存在时插入
    scores.entry(String::from("Red")).or_insert(50);
    scores.entry(String::from("Blue")).or_insert(50);  // 不插入
    println!("entry: {:?}", scores);
    
    // 基于旧值更新
    let text = "hello world wonderful world";
    let mut map = HashMap::new();
    
    for word in text.split_whitespace() {
        let count = map.entry(word).or_insert(0);
        *count += 1;
    }
    
    println!("\n单词计数: {:?}", map);
    
    println!("\n💡 下一步: 学习 15_error_handling.rs - 错误处理");
}
