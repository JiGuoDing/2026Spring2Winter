//! 10 - 枚举

#[derive(Debug)]
enum IpAddr {
    V4(u8, u8, u8, u8),
    V6(String),
}

#[derive(Debug)]
enum Message {
    Quit,
    Move { x: i32, y: i32 },
    Write(String),
    ChangeColor(i32, i32, i32),
}

impl Message {
    fn call(&self) {
        println!("调用消息: {:?}", self);
    }
}

fn main() {
    println!("╔══════════════════════════════════════╗");
    println!("║      Rust 学习系列 10: 枚举          ║");
    println!("╚══════════════════════════════════════╝");
    
    let home = IpAddr::V4(127, 0, 0, 1);
    let loopback = IpAddr::V6(String::from("::1"));
    
    println!("\nIP地址:");
    println!("  {:?}", home);
    println!("  {:?}", loopback);
    
    let msg = Message::Write(String::from("hello"));
    msg.call();
    
    // Option 枚举
    let some_number = Some(5);
    let some_string = Some("a string");
    let absent_number: Option<i32> = None;
    
    println!("\nOption:");
    println!("  {:?}", some_number);
    println!("  {:?}", some_string);
    println!("  {:?}", absent_number);
    
    if let Some(value) = some_number {
        println!("  值是: {}", value);
    }
    
    println!("\n💡 下一步: 学习 11_match.rs - 模式匹配");
}
