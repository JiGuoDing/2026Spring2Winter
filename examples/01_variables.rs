//! # 01 - 变量与可变性
//!
//! ## 学习目标
//! - 理解 Rust 默认不可变的设计理念
//! - 掌握 let 和 mut 关键字的使用
//! - 理解常量 const 的使用场景
//! - 掌握变量隐藏(shadowing)机制

/*
 * ================================
 * 核心概念说明
 * ================================
 * 
 * Rust 的变量系统有以下特点:
 * 1. 变量默认是不可变的(immutable)
 * 2. 使用 mut 关键字可以声明可变变量
 * 3. 常量使用 const 声明,必须标注类型,且永远不可变
 * 4. 变量隐藏(shadowing)允许重新声明同名变量,甚至可以改变类型
 */

// 常量:全局作用域,命名规范使用大写字母和下划线
const MAX_POINTS: u32 = 100_000;
const PI: f64 = 3.14159265359;

/// 演示不可变变量
fn demo_immutable_variables() {
    println!("\n=== 1. 不可变变量 ===");
    
    let x = 5;
    println!("x 的值是: {}", x);
    
    // 下面这行会报错,因为 x 是不可变的
    // x = 6; // 错误: cannot assign twice to immutable variable
    
    println!("✓ Rust 默认变量是不可变的,这提供了安全性和并发性的保证");
}

/// 演示可变变量
fn demo_mutable_variables() {
    println!("\n=== 2. 可变变量 ===");
    
    let mut y = 5;
    println!("y 的初始值是: {}", y);
    
    y = 6; // 使用 mut 关键字后可以修改
    println!("y 修改后的值是: {}", y);
    
    // 可变变量可以多次修改
    y = y + 10;
    println!("y 再次修改后的值是: {}", y);
    
    println!("✓ 使用 mut 关键字声明可变变量");
}

/// 演示常量
fn demo_constants() {
    println!("\n=== 3. 常量 ===");
    
    println!("MAX_POINTS 常量的值: {}", MAX_POINTS);
    println!("PI 常量的值: {}", PI);
    
    // 常量和不可变变量的区别:
    // 1. 常量使用 const 关键字,必须标注类型
    // 2. 常量可以在任何作用域中声明,包括全局作用域
    // 3. 常量只能被设置为常量表达式,不能是运行时计算的值
    // 4. 常量在整个程序运行期间都有效
    
    const HOURS_IN_DAY: u32 = 24;
    println!("一天有 {} 小时", HOURS_IN_DAY);
    
    println!("✓ 常量使用 const 声明,命名使用全大写,必须标注类型");
}

/// 演示变量隐藏(shadowing)
fn demo_shadowing() {
    println!("\n=== 4. 变量隐藏(Shadowing) ===");
    
    let x = 5;
    println!("第一次声明 x: {}", x);
    
    // 可以重新声明同名变量,这叫做"隐藏"(shadowing)
    let x = x + 1;
    println!("第二次声明 x (x + 1): {}", x);
    
    // 在内部作用域中隐藏外部变量
    {
        let x = x * 2;
        println!("内部作用域中的 x (x * 2): {}", x);
    }
    
    println!("外部作用域的 x 不受影响: {}", x);
    
    println!("\n--- 隐藏允许改变变量类型 ---");
    
    let spaces = "   ";
    println!("spaces 是字符串: '{}'", spaces);
    
    let spaces = spaces.len();
    println!("spaces 现在是数字: {}", spaces);
    
    // 如果使用 mut,则不能改变类型
    // let mut spaces2 = "   ";
    // spaces2 = spaces2.len(); // 错误: expected `&str`, found `usize`
    
    println!("✓ 使用 let 重新声明变量称为隐藏,可以改变类型");
    println!("✓ mut 只能修改值,不能改变类型");
}

/// 演示作用域和隐藏
fn demo_scope_and_shadowing() {
    println!("\n=== 5. 作用域和变量隐藏 ===");
    
    let x = 10;
    println!("外部作用域 x: {}", x);
    
    {
        println!("\n进入内部作用域");
        let x = 20;
        println!("内部作用域 x (隐藏外部): {}", x);
        
        let y = 30;
        println!("内部作用域独有的 y: {}", y);
        
        {
            println!("\n进入更内层作用域");
            let x = 40;
            println!("更内层作用域 x: {}", x);
        }
        
        println!("\n返回内部作用域,x 恢复为: {}", x);
    }
    
    println!("\n返回外部作用域,x 恢复为: {}", x);
    // println!("{}", y); // 错误: y 已经离开作用域
    
    println!("✓ 变量的作用域是其所在的代码块 {{}}");
}

/// 演示命名规范
fn demo_naming_conventions() {
    println!("\n=== 6. 命名规范 ===");
    
    // Rust 命名规范:
    // 变量名和函数名: snake_case (小写字母,下划线分隔)
    let user_name = "Alice";
    let user_age = 30;
    
    // 常量: SCREAMING_SNAKE_CASE (全大写,下划线分隔)
    const MAX_USER_COUNT: u32 = 1000;
    
    // 类型名和 trait 名: PascalCase (大驼峰)
    // struct UserProfile { ... }
    
    println!("用户名: {}", user_name);
    println!("用户年龄: {}", user_age);
    println!("最大用户数: {}", MAX_USER_COUNT);
    
    println!("✓ 变量和函数使用 snake_case");
    println!("✓ 常量使用 SCREAMING_SNAKE_CASE");
    println!("✓ 类型使用 PascalCase");
}

/// 常见陷阱和最佳实践
fn demo_common_pitfalls() {
    println!("\n=== 7. 常见陷阱和最佳实践 ===");
    
    // 陷阱1: 忘记使用 mut
    println!("\n陷阱1: 需要修改的变量忘记加 mut");
    let mut counter = 0;
    counter += 1; // 如果没有 mut,这里会报错
    println!("计数器: {}", counter);
    
    // 陷阱2: 过度使用 mut
    println!("\n最佳实践: 默认使用不可变变量,只在必要时使用 mut");
    let result = calculate_sum(10, 20); // 不需要 mut
    println!("计算结果: {}", result);
    
    // 陷阱3: 混淆隐藏和可变性
    println!("\n隐藏 vs 可变性:");
    let value = 5;
    let value = value + 1; // 隐藏:创建新变量
    println!("隐藏后的 value: {}", value);
    
    let mut value2 = 5;
    value2 = value2 + 1; // 可变性:修改原变量
    println!("修改后的 value2: {}", value2);
    
    println!("\n✓ 优先使用不可变变量,提高代码安全性");
    println!("✓ 使用隐藏来转换类型或在不同阶段使用不同值");
    println!("✓ 只在确实需要修改时使用 mut");
}

fn calculate_sum(a: i32, b: i32) -> i32 {
    a + b
}

/// 主函数:运行所有示例
fn main() {
    println!("╔═══════════════════════════════════════╗");
    println!("║    Rust 学习系列 01: 变量与可变性     ║");
    println!("╚═══════════════════════════════════════╝");
    
    demo_immutable_variables();
    demo_mutable_variables();
    demo_constants();
    demo_shadowing();
    demo_scope_and_shadowing();
    demo_naming_conventions();
    demo_common_pitfalls();
    
    println!("\n╔═══════════════════════════════════════╗");
    println!("║              学习小结                 ║");
    println!("╚═══════════════════════════════════════╝");
    println!("1. Rust 变量默认不可变,需要 mut 才能修改");
    println!("2. 常量使用 const,必须标注类型,永远不可变");
    println!("3. 变量隐藏允许重新声明同名变量,可以改变类型");
    println!("4. 变量有作用域限制,离开作用域后自动释放");
    println!("5. 优先使用不可变变量,提高代码安全性");
    
    println!("\n💡 下一步: 学习 02_data_types.rs - 数据类型");
}
