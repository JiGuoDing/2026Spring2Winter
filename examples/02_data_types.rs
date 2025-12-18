//! # 02 - 数据类型
//!
//! ## 学习目标
//! - 掌握 Rust 的标量类型(整数、浮点、布尔、字符)
//! - 掌握复合类型(元组、数组)
//! - 理解类型推断和显式类型标注

/*
 * ================================
 * 核心概念说明
 * ================================
 * 
 * Rust 是静态类型语言,在编译时必须知道所有变量的类型
 * 
 * 数据类型分为两大类:
 * 1. 标量类型(Scalar Types): 表示单个值
 *    - 整数(Integer)
 *    - 浮点数(Floating-Point)
 *    - 布尔值(Boolean)
 *    - 字符(Character)
 * 
 * 2. 复合类型(Compound Types): 可以将多个值组合成一个类型
 *    - 元组(Tuple)
 *    - 数组(Array)
 */

/// 演示整数类型
fn demo_integer_types() {
    println!("\n=== 1. 整数类型 ===");
    
    // 有符号整数: i8, i16, i32, i64, i128, isize
    // 无符号整数: u8, u16, u32, u64, u128, usize
    
    let a: i8 = -128;        // 8位有符号整数: -128 到 127
    let b: u8 = 255;         // 8位无符号整数: 0 到 255
    let c: i32 = -100_000;   // 32位有符号整数(默认类型)
    let d: u64 = 1_000_000;  // 64位无符号整数
    
    println!("i8 类型: {}", a);
    println!("u8 类型: {}", b);
    println!("i32 类型: {}", c);
    println!("u64 类型: {}", d);
    
    // 不同进制的字面量表示
    let decimal = 98_222;           // 十进制
    let hex = 0xff;                 // 十六进制
    let octal = 0o77;               // 八进制
    let binary = 0b1111_0000;       // 二进制
    let byte = b'A';                // 字节(仅限 u8)
    
    println!("\n--- 不同进制表示 ---");
    println!("十进制: {}", decimal);
    println!("十六进制 0xff: {}", hex);
    println!("八进制 0o77: {}", octal);
    println!("二进制 0b1111_0000: {}", binary);
    println!("字节 b'A': {}", byte);
    
    // isize 和 usize: 取决于运行程序的计算机架构
    let size: usize = 100;
    println!("\nusize 类型(取决于架构): {}", size);
    
    println!("\n✓ 整数默认类型是 i32");
    println!("✓ 使用下划线 _ 提高数字可读性");
}

/// 演示浮点类型
fn demo_float_types() {
    println!("\n=== 2. 浮点类型 ===");
    
    // f32: 32位浮点数(单精度)
    // f64: 64位浮点数(双精度,默认类型)
    
    let x = 2.0;         // f64 默认类型
    let y: f32 = 3.0;    // f32 明确标注
    
    println!("f64 类型: {}", x);
    println!("f32 类型: {}", y);
    
    // 浮点数运算
    let sum = 5.5 + 10.2;
    let difference = 95.5 - 4.3;
    let product = 4.0 * 30.0;
    let quotient = 56.7 / 32.2;
    
    println!("\n--- 浮点数运算 ---");
    println!("加法: 5.5 + 10.2 = {}", sum);
    println!("减法: 95.5 - 4.3 = {}", difference);
    println!("乘法: 4.0 * 30.0 = {}", product);
    println!("除法: 56.7 / 32.2 = {}", quotient);
    
    // 浮点数精度问题
    let a = 0.1 + 0.2;
    println!("\n⚠️  浮点数精度: 0.1 + 0.2 = {} (不精确等于 0.3)", a);
    
    println!("\n✓ 浮点数默认类型是 f64");
    println!("✓ 注意浮点数精度问题");
}

/// 演示数值运算
fn demo_numeric_operations() {
    println!("\n=== 3. 数值运算 ===");
    
    // 基本数学运算
    let sum = 5 + 10;
    let difference = 95 - 4;
    let product = 4 * 30;
    let quotient = 56 / 32;       // 整数除法,结果为 1
    let remainder = 43 % 5;        // 取余
    
    println!("加法: 5 + 10 = {}", sum);
    println!("减法: 95 - 4 = {}", difference);
    println!("乘法: 4 * 30 = {}", product);
    println!("除法: 56 / 32 = {} (整数除法)", quotient);
    println!("取余: 43 % 5 = {}", remainder);
    
    // 浮点数除法
    let float_quotient = 56.0 / 32.0;
    println!("浮点除法: 56.0 / 32.0 = {}", float_quotient);
    
    println!("\n✓ 整数除法会截断小数部分");
}

/// 演示布尔类型
fn demo_boolean_type() {
    println!("\n=== 4. 布尔类型 ===");
    
    let t = true;
    let f: bool = false;
    
    println!("真值: {}", t);
    println!("假值: {}", f);
    
    // 布尔运算
    let and = true && false;    // 与运算
    let or = true || false;     // 或运算
    let not = !true;            // 非运算
    
    println!("\n--- 布尔运算 ---");
    println!("true && false = {}", and);
    println!("true || false = {}", or);
    println!("!true = {}", not);
    
    // 比较运算
    let greater = 5 > 3;
    let less_equal = 2 <= 5;
    let equal = 10 == 10;
    let not_equal = 5 != 3;
    
    println!("\n--- 比较运算 ---");
    println!("5 > 3 = {}", greater);
    println!("2 <= 5 = {}", less_equal);
    println!("10 == 10 = {}", equal);
    println!("5 != 3 = {}", not_equal);
    
    println!("\n✓ 布尔类型占用 1 字节");
    println!("✓ 常用于条件判断和控制流");
}

/// 演示字符类型
fn demo_char_type() {
    println!("\n=== 5. 字符类型 ===");
    
    // char 类型使用单引号,占用 4 字节,表示 Unicode 标量值
    let c = 'z';
    let z = 'ℤ';
    let heart = '❤';
    let emoji = '😻';
    let chinese = '中';
    
    println!("英文字符: {}", c);
    println!("数学符号: {}", z);
    println!("特殊符号: {}", heart);
    println!("Emoji: {}", emoji);
    println!("中文字符: {}", chinese);
    
    println!("\n✓ char 类型占用 4 字节");
    println!("✓ 使用单引号表示");
    println!("✓ 支持 Unicode 字符");
}

/// 演示元组类型
fn demo_tuple_type() {
    println!("\n=== 6. 元组类型 ===");
    
    // 元组:可以将多个不同类型的值组合在一起
    let tup: (i32, f64, u8) = (500, 6.4, 1);
    // 不需要显示指出变量类型
    // let _tup = (500, 6.4, 1);
    
    println!("完整元组: {:?}", tup);
    
    // 解构元组
    let (x, y, z) = tup;
    println!("\n--- 解构元组 ---");
    println!("x = {}", x);
    println!("y = {}", y);
    println!("z = {}", z);
    
    // 使用索引访问元组元素
    let five_hundred = tup.0;
    let six_point_four = tup.1;
    let one = tup.2;
    
    println!("\n--- 使用索引访问 ---");
    println!("tup.0 = {}", five_hundred);
    println!("tup.1 = {}", six_point_four);
    println!("tup.2 = {}", one);
    
    // 不同类型的元组
    let person: (&str, i32, bool) = ("Alice", 30, true);
    println!("\n用户信息: {:?}", person);
    println!("姓名: {}, 年龄: {}, 活跃: {}", person.0, person.1, person.2);
    
    // 空元组(单元类型)
    let unit: () = ();
    println!("\n单元类型: {:?}", unit);
    
    println!("\n✓ 元组可以包含不同类型的值");
    println!("✓ 元组长度固定");
    println!("✓ 使用 . 和索引访问元素");
}

/// 演示数组类型
fn demo_array_type() {
    println!("\n=== 7. 数组类型 ===");
    
    // 数组:所有元素必须是相同类型,长度固定
    let a = [1, 2, 3, 4, 5];
    println!("数组: {:?}", a);
    
    // 显式类型标注: [类型; 长度]
    let b: [i32; 5] = [1, 2, 3, 4, 5];
    println!("显式类型数组: {:?}", b);
    
    // 使用相同值初始化数组
    // * 语法糖
    let c = [3; 5]; // 等同于 [3, 3, 3, 3, 3]
    println!("重复值数组: {:?}", c);
    
    // 访问数组元素
    let first = a[0];
    let second = a[1];
    println!("\n--- 访问数组元素 ---");
    println!("第一个元素: {}", first);
    println!("第二个元素: {}", second);
    
    // 数组长度
    println!("数组长度: {}", a.len());
    
    // 遍历数组
    println!("\n--- 遍历数组 ---");

    // for 循环语法解释：
    // 1. for 是循环关键字
    // 2. element 是迭代变量名（可以自定义）
    // 3. in 关键字连接迭代变量和可迭代对象
    // 4. &a 表示对数组 a 的不可变引用
    //    - 使用 &a 而不是 a，避免数组所有权转移
    //    - element 的类型是 &i32（元素的引用）
    // 5. 循环体用 {} 包裹
    
    // 方式1：遍历引用（推荐，不转移所有权）
    for element in &a {
        println!("元素: {}", element);
    }
    
    // 方式2：遍历索引和值
    for (index, element) in a.iter().enumerate() {
        println!("索引 {}: 元素 {}", index, element);
    }
    
    // 方式3：使用范围遍历索引
    for i in 0..a.len() {
        println!("a[{}] = {}", i, a[i]);
    }
    
    // 多维数组
    let matrix: [[i32; 3]; 2] = [
        [1, 2, 3],
        [4, 5, 6],
    ];
    println!("\n二维数组: {:?}", matrix);
    println!("访问元素 matrix[1][2]: {}", matrix[1][2]);
    
    println!("\n✓ 数组在栈上分配");
    println!("✓ 数组长度固定,编译时确定");
    println!("✓ 访问越界会导致运行时 panic");
}

/// 演示类型推断和显式标注
fn demo_type_inference() {
    println!("\n=== 8. 类型推断和显式标注 ===");
    
    // 类型推断
    let x = 5;              // 编译器推断为 i32
    let y = 2.5;            // 编译器推断为 f64
    let flag = true;        // 编译器推断为 bool
    
    println!("推断类型:");
    println!("x (i32): {}", x);
    println!("y (f64): {}", y);
    println!("flag (bool): {}", flag);
    
    // 显式类型标注
    let a: u8 = 255;
    let b: f32 = 3.14;
    let c: char = 'A';
    
    println!("\n显式标注:");
    println!("a (u8): {}", a);
    println!("b (f32): {}", b);
    println!("c (char): {}", c);
    
    // 有时需要显式标注避免歧义
    let guess: u32 = "42".parse().expect("不是数字!");
    println!("\n解析字符串为数字: {}", guess);
    
    println!("\n✓ Rust 编译器会尽可能推断类型");
    println!("✓ 在有歧义时需要显式标注");
}

/// 演示类型转换
fn demo_type_conversion() {
    println!("\n=== 9. 类型转换 ===");
    
    // Rust 不会自动进行类型转换,需要显式转换
    let x = 10i32;
    let y = 3.5f64;
    
    // 使用 as 关键字进行转换
    let z = x as f64 + y;
    println!("i32 转 f64: {} + {} = {}", x, y, z);
    // * 不转换会报错，i32 无法与 f64 直接相加
    // let w = x + y;
    // println!("i32 转 f64: {} + {} = {}", x, y, w);
    
    let a = 256u16;
    let b = a as u8;  // 注意:可能会截断
    println!("\nu16 转 u8: {} -> {} (发生截断)", a, b);
    
    let c = 3.9f64;
    let d = c as i32;  // 截断小数部分
    println!("f64 转 i32: {} -> {}", c, d);
    
    println!("\n✓ 使用 as 关键字进行类型转换");
    println!("⚠️  注意转换可能导致数据丢失");
}

/// 常见陷阱和最佳实践
fn demo_common_pitfalls() {
    println!("\n=== 10. 常见陷阱和最佳实践 ===");
    
    // 陷阱1: 整数溢出
    println!("\n陷阱1: 整数溢出");
    let mut x: u8 = 255;
    // x += 1; // 在 debug 模式下会 panic,release 模式下会回绕为 0
    println!("u8 最大值: {}", x);
    
    // 使用 wrapping, checked, saturating 方法处理溢出
    x = x.wrapping_add(1);  // 回绕
    println!("wrapping_add 后: {}", x);
    
    // 陷阱2: 浮点数比较
    println!("\n陷阱2: 浮点数不精确比较");
    let a: f64 = 0.1 + 0.2;
    // if a == 0.3 { ... } // 不建议直接比较
    let epsilon: f64 = 1e-10;
    if (a - 0.3).abs() < epsilon {
        println!("浮点数近似相等");
    }
    
    // 陷阱3: 数组越界
    println!("\n陷阱3: 数组越界访问");
    let arr = [1, 2, 3, 4, 5];
    // let index = 10;
    // let element = arr[index]; // 运行时 panic
    println!("安全访问: 使用 get 方法");
    match arr.get(10) {
        // * match 可以返回值 (所有分支需要返回相同类型的值)
        // Some(val) => val,
        Some(val) => println!("值: {}", val),
        
        // None => {
        //     println!("索引越界");
        //     0
        // }
        None => println!("索引越界"),
    }
    
    println!("\n✓ 使用合适的整数类型避免溢出");
    println!("✓ 浮点数比较使用误差范围");
    println!("✓ 访问数组时注意边界检查");
}

/// 主函数:运行所有示例
fn main() {
    println!("╔═══════════════════════════════════════╗");
    println!("║      Rust 学习系列 02: 数据类型       ║");
    println!("╚═══════════════════════════════════════╝");
    
    demo_integer_types();
    demo_float_types();
    demo_numeric_operations();
    demo_boolean_type();
    demo_char_type();
    demo_tuple_type();
    demo_array_type();
    demo_type_inference();
    demo_type_conversion();
    demo_common_pitfalls();
    
    println!("\n╔═══════════════════════════════════════╗");
    println!("║              学习小结                 ║");
    println!("╚═══════════════════════════════════════╝");
    println!("1. 标量类型: 整数、浮点、布尔、字符");
    println!("2. 复合类型: 元组(不同类型)、数组(相同类型)");
    println!("3. 整数默认 i32,浮点默认 f64");
    println!("4. 数组长度固定,在栈上分配");
    println!("5. 使用 as 关键字进行类型转换");
    
    println!("\n💡 下一步: 学习 03_functions.rs - 函数");
}
