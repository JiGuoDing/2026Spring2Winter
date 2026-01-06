//! 15 - 错误处理

use std::fs::File;
use std::io::{self, Read};

fn read_username_from_file() -> Result<String, io::Error> {
    let mut username = String::new();
    File::open("hello.txt")?.read_to_string(&mut username)?;
    Ok(username)
}

fn main() {
    println!("╔══════════════════════════════════════╗");
    println!("║    Rust 学习系列 15: 错误处理        ║");
    println!("╚══════════════════════════════════════╝");
    
    // panic! 不可恢复错误
    println!("\n使用 Result 处理可恢复错误");
    
    let result: Result<i32, &str> = Ok(10);
    match result {
        Ok(value) => println!("成功: {}", value),
        Err(e) => println!("错误: {}", e),
    }
    
    // * unwrap 从 Result 中强行取出 Ok 里的值，如果 Result 是 Ok(value) → 返回 value，如果是 Err(error) → 立即 panic！程序崩溃
    let value = result.unwrap();
    println!("unwrap: {}", value);
    
    // * expect 从 Result 中强行取出 Ok 里的值，如果 Result 是 Ok(value) → 返回 value，如果是 Err(error) → panic！但可以提供自定义的错误消息 msg
    let value2 = result.expect("应该包含值");
    println!("expect: {}", value2);
    
    // ? 操作符
    match read_username_from_file() {
        Ok(username) => println!("用户名: {}", username),
        Err(e) => println!("读取失败: {}", e),
    }
    
    // 自定义错误
    #[derive(Debug)]
    struct CustomError {
        message: String,
    }
    
    let err = CustomError {
        message: String::from("自定义错误"),
    };
    println!("\n自定义错误: {:?}", err);
    
    println!("\n💡 下一步: 学习 16_generics.rs - 泛型");
}
