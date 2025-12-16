//! 16 - 泛型

fn largest<T: PartialOrd>(list: &[T]) -> &T {
    let mut largest = &list[0];
    for item in list {
        if item > largest {
            largest = item;
        }
    }
    largest
}

struct Point<T> {
    x: T,
    y: T,
}

impl<T> Point<T> {
    fn x(&self) -> &T {
        &self.x
    }
}

fn main() {
    println!("╔══════════════════════════════════════╗");
    println!("║      Rust 学习系列 16: 泛型          ║");
    println!("╚══════════════════════════════════════╝");
    
    // 泛型函数
    let numbers = vec![34, 50, 25, 100, 65];
    let result = largest(&numbers);
    println!("\n最大数字: {}", result);
    
    let chars = vec!['y', 'm', 'a', 'q'];
    let result = largest(&chars);
    println!("最大字符: {}", result);
    
    // 泛型结构体
    let integer = Point { x: 5, y: 10 };
    let float = Point { x: 1.0, y: 4.0 };
    
    println!("\n整数点: ({}, {})", integer.x(), integer.y);
    println!("浮点点: ({}, {})", float.x(), float.y);
    
    // 多个泛型参数
    struct Point2<T, U> {
        x: T,
        y: U,
    }
    
    let both_integer = Point2 { x: 5, y: 10 };
    let both_float = Point2 { x: 1.0, y: 4.0 };
    let integer_and_float = Point2 { x: 5, y: 4.0 };
    
    println!("\n混合类型点: ({}, {})", integer_and_float.x, integer_and_float.y);
    
    println!("\n💡 下一步: 学习 17_traits.rs - Trait特征");
}
