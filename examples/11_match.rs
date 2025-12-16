//! 11 - 模式匹配

#[derive(Debug)]
enum Coin {
    Penny,
    Nickel,
    Dime,
    Quarter,
}

fn value_in_cents(coin: Coin) -> u8 {
    match coin {
        Coin::Penny => 1,
        Coin::Nickel => 5,
        Coin::Dime => 10,
        Coin::Quarter => 25,
    }
}

fn plus_one(x: Option<i32>) -> Option<i32> {
    match x {
        None => None,
        Some(i) => Some(i + 1),
    }
}

fn main() {
    println!("╔══════════════════════════════════════╗");
    println!("║    Rust 学习系列 11: 模式匹配        ║");
    println!("╚══════════════════════════════════════╝");
    
    let coin = Coin::Quarter;
    println!("\n硬币价值: {} 美分", value_in_cents(coin));
    
    let five = Some(5);
    let six = plus_one(five);
    let none = plus_one(None);
    
    println!("\nOption匹配:");
    println!("  {:?} + 1 = {:?}", five, six);
    println!("  {:?} + 1 = {:?}", None::<i32>, none);
    
    // match 表达式
    let number = 7;
    match number {
        1 => println!("\n一"),
        2 | 3 | 5 | 7 => println!("\n质数"),
        4 | 6 | 8 | 9 | 10 => println!("\n合数"),
        _ => println!("\n其他"),
    }
    
    // if let
    let some_value = Some(3);
    if let Some(3) = some_value {
        println!("\n匹配到 3");
    }
    
    // 解构
    let point = (3, 5);
    match point {
        (0, 0) => println!("原点"),
        (x, 0) => println!("在x轴上: {}", x),
        (0, y) => println!("在y轴上: {}", y),
        (x, y) => println!("点({}, {})", x, y),
    }
    
    println!("\n💡 下一步: 学习 12_vector.rs - Vector集合");
}
