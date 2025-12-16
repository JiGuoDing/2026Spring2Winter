//! # 03 - 函数
//!
//! ## 学习目标
//! - 掌握函数定义和调用语法
//! - 理解参数和返回值
//! - 理解语句和表达式的区别
//! - 掌握提前返回

/*
 * ================================
 * 核心概念说明
 * ================================
 * 
 * 函数是 Rust 代码的基本构建块
 * 
 * 关键概念:
 * 1. 使用 fn 关键字定义函数
 * 2. 参数必须声明类型
 * 3. 返回类型使用 -> 声明
 * 4. 函数体由一系列语句和可选的表达式组成
 * 5. 表达式的值可以作为返回值
 * 6. 语句不返回值,表达式返回值
 */

/// 演示基础函数
fn demo_basic_functions() {
    println!("\n=== 1. 基础函数 ===");
    
    // 调用无参数无返回值的函数
    hello_world();
    
    // 调用有参数的函数
    greet("Alice");
    greet("Bob");
    
    println!("\n✓ 使用 fn 关键字定义函数");
    println!("✓ 函数名使用 snake_case 命名");
}

// 无参数无返回值的函数
fn hello_world() {
    println!("Hello, World!");
}

// 有参数的函数
fn greet(name: &str) {
    println!("你好, {}!", name);
}

/// 演示函数参数
fn demo_function_parameters() {
    println!("\n=== 2. 函数参数 ===");
    
    // 单个参数
    print_value(42);
    
    // 多个参数
    print_sum(10, 20);
    print_person_info("Charlie", 25);
    
    // 不同类型的参数
    calculate_and_print(5, 3);
    
    println!("\n✓ 参数必须声明类型");
    println!("✓ 多个参数使用逗号分隔");
}

fn print_value(x: i32) {
    println!("值: {}", x);
}

fn print_sum(a: i32, b: i32) {
    println!("{} + {} = {}", a, b, a + b);
}

fn print_person_info(name: &str, age: u32) {
    println!("姓名: {}, 年龄: {}", name, age);
}

fn calculate_and_print(x: i32, y: i32) {
    let sum = x + y;
    let product = x * y;
    println!("和: {}, 积: {}", sum, product);
}

/// 演示函数返回值
fn demo_return_values() {
    println!("\n=== 3. 函数返回值 ===");
    
    let result1 = add(5, 3);
    println!("add(5, 3) = {}", result1);
    
    let result2 = multiply(4, 7);
    println!("multiply(4, 7) = {}", result2);
    
    let result3 = divide(10.0, 3.0);
    println!("divide(10.0, 3.0) = {}", result3);
    
    println!("\n✓ 使用 -> 声明返回类型");
    println!("✓ 最后一个表达式作为返回值");
}

// 返回两数之和
fn add(a: i32, b: i32) -> i32 {
    a + b  // 没有分号,这是表达式,作为返回值
}

fn multiply(x: i32, y: i32) -> i32 {
    x * y
}

fn divide(x: f64, y: f64) -> f64 {
    x / y
}

/// 演示语句和表达式
fn demo_statements_vs_expressions() {
    println!("\n=== 4. 语句 vs 表达式 ===");
    
    // 语句: 执行操作但不返回值
    let x = 5;  // 这是一个语句
    
    // 表达式: 计算并返回值
    let y = {
        let z = 3;
        z + 1  // 没有分号,这是表达式,返回 4
    };
    println!("y = {}", y);
    
    // 带分号的是语句,不返回值
    let a = {
        let b = 10;
        b + 5;  // 有分号,这是语句,不返回值
        // 隐式返回 ()
    };
    println!("a = {:?}", a);
    
    // 函数调用是表达式
    let result = add(10, 20);
    println!("result = {}", result);
    
    // if 是表达式
    let number = if x < 10 { 1 } else { 0 };
    println!("number = {}", number);
    
    println!("\n✓ 语句以分号结尾,不返回值");
    println!("✓ 表达式不加分号,会返回值");
    println!("✓ 代码块 {{}} 可以作为表达式");
}

/// 演示提前返回
fn demo_early_return() {
    println!("\n=== 5. 提前返回 ===");
    
    let result1 = check_positive(10);
    println!("check_positive(10) = {}", result1);
    
    let result2 = check_positive(-5);
    println!("check_positive(-5) = {}", result2);
    
    let result3 = divide_safe(10.0, 2.0);
    println!("divide_safe(10.0, 2.0) = {}", result3);
    
    let result4 = divide_safe(10.0, 0.0);
    println!("divide_safe(10.0, 0.0) = {}", result4);
    
    println!("\n✓ 使用 return 关键字提前返回");
    println!("✓ 可以在函数任何位置返回");
}

fn check_positive(n: i32) -> bool {
    if n <= 0 {
        return false;  // 提前返回
    }
    true  // 默认返回
}

fn divide_safe(x: f64, y: f64) -> f64 {
    if y == 0.0 {
        println!("⚠️  除数为零,返回 0.0");
        return 0.0;  // 提前返回
    }
    x / y
}

/// 演示多个返回值(使用元组)
fn demo_multiple_return_values() {
    println!("\n=== 6. 多个返回值 ===");
    
    let (sum, product) = calculate(4, 5);
    println!("calculate(4, 5): 和 = {}, 积 = {}", sum, product);
    
    let (min, max) = find_min_max(vec![3, 7, 1, 9, 2]);
    println!("find_min_max([3, 7, 1, 9, 2]): 最小值 = {}, 最大值 = {}", min, max);
    
    println!("\n✓ 使用元组返回多个值");
    println!("✓ 调用时使用解构获取多个值");
}

// 返回两数的和与积
fn calculate(a: i32, b: i32) -> (i32, i32) {
    let sum = a + b;
    let product = a * b;
    (sum, product)
}

// 返回数组的最小值和最大值
fn find_min_max(numbers: Vec<i32>) -> (i32, i32) {
    let mut min = numbers[0];
    let mut max = numbers[0];
    
    for &num in &numbers {
        if num < min {
            min = num;
        }
        if num > max {
            max = num;
        }
    }
    
    (min, max)
}

/// 演示递归函数
fn demo_recursive_functions() {
    println!("\n=== 7. 递归函数 ===");
    
    let result1 = factorial(5);
    println!("factorial(5) = {}", result1);
    
    let result2 = fibonacci(10);
    println!("fibonacci(10) = {}", result2);
    
    println!("\n✓ 函数可以调用自身(递归)");
    println!("✓ 注意递归终止条件");
}

// 计算阶乘
fn factorial(n: u32) -> u32 {
    if n == 0 {
        1
    } else {
        n * factorial(n - 1)
    }
}

// 计算斐波那契数列
fn fibonacci(n: u32) -> u32 {
    if n == 0 {
        0
    } else if n == 1 {
        1
    } else {
        fibonacci(n - 1) + fibonacci(n - 2)
    }
}

/// 演示函数作为参数
fn demo_functions_as_parameters() {
    println!("\n=== 8. 函数作为参数 ===");
    
    apply_operation(10, 5, add);
    apply_operation(10, 5, multiply);
    apply_operation(10, 5, subtract);
    
    println!("\n✓ 函数可以作为参数传递");
    println!("✓ 这是高阶函数的基础");
}

fn subtract(a: i32, b: i32) -> i32 {
    a - b
}

// 接受函数作为参数
fn apply_operation(a: i32, b: i32, op: fn(i32, i32) -> i32) {
    let result = op(a, b);
    println!("操作结果: {}", result);
}

/// 演示方法链
fn demo_method_chaining() {
    println!("\n=== 9. 表达式链式调用 ===");
    
    let result = calculate_complex(10);
    println!("复杂计算结果: {}", result);
    
    println!("\n✓ 表达式可以链式调用");
}

fn calculate_complex(x: i32) -> i32 {
    let step1 = x * 2;
    let step2 = step1 + 10;
    let step3 = step2 / 3;
    step3
}

/// 常见陷阱和最佳实践
fn demo_common_pitfalls() {
    println!("\n=== 10. 常见陷阱和最佳实践 ===");
    
    // 陷阱1: 忘记返回值
    println!("\n陷阱1: 表达式加分号变成语句");
    let val1 = returns_value();
    println!("正确返回: {}", val1);
    
    let val2 = returns_unit();
    println!("返回单元类型: {:?}", val2);
    
    // 陷阱2: 参数类型不匹配
    println!("\n陷阱2: 注意参数类型匹配");
    let x = 10i32;
    print_value(x);
    // print_value(10u32); // 错误: 类型不匹配
    
    // 最佳实践: 函数应该简短、功能单一
    println!("\n✓ 函数应该简短、功能单一");
    println!("✓ 使用有意义的函数名");
    println!("✓ 避免过深的递归");
}

fn returns_value() -> i32 {
    42  // 没有分号,返回值
}

fn returns_unit() -> () {
    42;  // 有分号,返回 ()
}

/// 主函数:运行所有示例
fn main() {
    println!("╔═══════════════════════════════════════╗");
    println!("║       Rust 学习系列 03: 函数          ║");
    println!("╚═══════════════════════════════════════╝");
    
    demo_basic_functions();
    demo_function_parameters();
    demo_return_values();
    demo_statements_vs_expressions();
    demo_early_return();
    demo_multiple_return_values();
    demo_recursive_functions();
    demo_functions_as_parameters();
    demo_method_chaining();
    demo_common_pitfalls();
    
    println!("\n╔═══════════════════════════════════════╗");
    println!("║              学习小结                 ║");
    println!("╚═══════════════════════════════════════╝");
    println!("1. 使用 fn 定义函数,参数必须声明类型");
    println!("2. 使用 -> 声明返回类型");
    println!("3. 最后一个表达式(无分号)作为返回值");
    println!("4. 语句不返回值,表达式返回值");
    println!("5. 使用 return 可以提前返回");
    
    println!("\n💡 下一步: 学习 04_comments.rs - 注释");
}
