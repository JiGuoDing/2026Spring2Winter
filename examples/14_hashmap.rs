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
    // * .get(key) 方法接受一个对 key 的引用，返回类型是 Option<&V> (这里即 Option<&i32>)
    // * .copied() 是 Option<&T> 的一个方法，返回类型是 Option<V> (不再是引用而是值本身)
    // * .unwrap_or(0) 是 Option<T> 的方法，安全地把 Option<T> 转成 T 类型，如果是 Some(x) -> 返回 x，如果是 None -> 返回 default (这里就是 0)
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
        // * or_insert(default) 存在则取出来，不存在则插入默认值
        // * 要修改 HashMap，先取出 entry
        let count = map.entry(word).or_insert(0);
        *count += 1;
    }
    
    println!("\n单词计数: {:?}", map);
    
    println!("\n💡 下一步: 学习 15_error_handling.rs - 错误处理");
}
