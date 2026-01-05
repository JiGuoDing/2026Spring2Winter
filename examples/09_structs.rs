//! 09 - 结构体

// * #[derive(Debug)] 是 Rust 的属性 (attribute) 语法，用于给代码项 (如 struct, enum, 函数等) 附加元信息或指令。
// * derive 是一个内置的派生宏（derive macro），它能自动为类型实现某些标准 trait，而无需手写实现代码。
// * Debug 是一个用于调试输出的 trait，实现了 Debug 的类型可以用 {:?} 在 println! 中打印。

/// 定义结构体
#[derive(Debug)]
struct User {
    username: String,
    email: String,
    age: u32,
    active: bool,
}

/// 元组结构体
#[derive(Debug)]
struct Color(i32, i32, i32);

/// 单元结构体
struct UnitStruct;

/// 结构体方法
#[derive(Debug)]
struct Rectangle {
    width: u32,
    height: u32,
}

impl Rectangle {
    // 关联函数(构造器)
    fn new(width: u32, height: u32) -> Self {
        Rectangle { width, height }
    }
    
    // 方法
    fn area(&self) -> u32 {
        self.width * self.height
    }
    
    fn can_hold(&self, other: &Rectangle) -> bool {
        self.width > other.width && self.height > other.height
    }
}

fn main() {
    println!("╔══════════════════════════════════════╗");
    println!("║    Rust 学习系列 09: 结构体          ║");
    println!("╚══════════════════════════════════════╝");
    
    // 创建结构体实例
    let user1 = User {
        username: String::from("alice"),
        email: String::from("alice@example.com"),
        age: 30,
        active: true,
    };
    
    println!("\n用户信息: {:?}", user1);
    
    // 字段初始化简写
    let username = String::from("bob");
    let email = String::from("bob@example.com");
    let user2 = User {
        username,
        email,
        age: 25,
        active: true,
    };
    println!("用户2: {:?}", user2);
    
    // 结构体更新语法
    let user3 = User {
        email: String::from("charlie@example.com"),
        // * ..user2 表示：除了显式指定的字段（如 email），其余字段从 user2 中复制过来。
        ..user2
    };
    println!("用户3: {:?}", user3);
    
    // 元组结构体
    let black = Color(0, 0, 0);
    println!("\n黑色: {:?}", black);
    
    // 使用方法
    let rect = Rectangle::new(30, 50);
    println!("\n矩形: {:?}", rect);
    println!("面积: {}", rect.area());
    
    let rect2 = Rectangle::new(20, 40);
    println!("rect 能容纳 rect2: {}", rect.can_hold(&rect2));
    
    println!("\n💡 下一步: 学习 10_enums.rs - 枚举");
}
