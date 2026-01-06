//! 13 - String字符串

fn main() {
    println!("╔══════════════════════════════════════╗");
    println!("║    Rust 学习系列 13: String字符串    ║");
    println!("╚══════════════════════════════════════╝");
    
    // 创建字符串
    let mut s = String::new();
    s.push_str("hello");
    println!("\nString::new(): {}", s);
    
    let s1 = "initial contents".to_string();
    let s2 = String::from("initial contents");
    println!("to_string(): {}", s1);
    println!("String::from(): {}", s2);
    
    // 更新字符串
    let mut s3 = String::from("foo");
    s3.push_str("bar");
    s3.push('!');
    println!("\npush_str/push: {}", s3);
    
    // 拼接
    let s4 = String::from("Hello, ");
    let s5 = String::from("world!");
    let s6 = s4 + &s5;  // s4 被移动
    // println!("s4: {}", s4);
    // println!("s5: {}", s5);
    println!("使用 +: {}", s6);
    
    let s7 = String::from("tic");
    let s8 = String::from("tac");
    let s9 = String::from("toe");
    let s10 = format!("{}-{}-{}", s7, s8, s9);
    println!("format!: {}", s10);
    
    // 遍历
    println!("\n按字符遍历:");
    for c in "नमस्ते".chars() {
        println!("  {}", c);
    }
    
    println!("\n按字节遍历:");
    for b in "नमस्ते".bytes() {
        println!("  {}", b);
    }
    
    // 切片
    let hello = "Здравствуйте";
    // 一个俄文字符占两个字节
    let s = &hello[0..6];
    println!("\n切片: {}", s);
    
    println!("\n💡 下一步: 学习 14_hashmap.rs - HashMap集合");
}
