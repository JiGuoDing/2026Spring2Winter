//! # 08 - 切片类型
//!
//! ## 学习目标
//! - 掌握切片的概念和语法
//! - 理解字符串切片 &str
//! - 掌握数组切片
//! - 了解切片的实际应用

/*
 * ================================
 * 核心概念说明
 * ================================
 * 
 * 切片(Slice):对集合部分元素的引用
 * 
 * 特点:
 * - 切片不拥有所有权
 * - 切片是对连续序列的引用
 * - 字符串字面量就是切片 &str
 * 
 * 语法:
 * - &s[start..end]  // 不包含 end
 * - &s[start..]     // 从 start 到末尾
 * - &s[..end]       // 从开头到 end
 * - &s[..]          // 整个序列
 */

/// 演示字符串切片基础
fn demo_string_slice_basics() {
    println!("\n=== 1. 字符串切片基础 ===");
    
    let s = String::from("hello world");
    
    // 创建切片
    let hello = &s[0..5];   // "hello"
    let world = &s[6..11];  // "world"
    
    println!("原字符串: {}", s);
    println!("切片1: {}", hello);
    println!("切片2: {}", world);
    
    // 简化语法
    let hello2 = &s[..5];    // 等同于 &s[0..5]
    let world2 = &s[6..];    // 从索引6到末尾
    let full = &s[..];       // 整个字符串
    
    println!("\n简化语法:");
    println!("&s[..5]: {}", hello2);
    println!("&s[6..]: {}", world2);
    println!("&s[..]: {}", full);
    
    println!("\n✓ 切片语法: &s[start..end]");
    println!("✓ 索引必须在有效的 UTF-8 字符边界");
}

/// 演示字符串切片类型 &str
fn demo_str_type() {
    println!("\n=== 2. 字符串切片类型 &str ===");
    
    // 字符串字面量就是 &str 类型
    let s: &str = "Hello, Rust!";
    println!("字符串字面量: {}", s);
    
    // String 到 &str
    let string = String::from("hello");
    let slice: &str = &string[..];
    println!("String 的切片: {}", slice);
    
    // &str 是不可变引用
    println!("\n&str 特点:");
    println!("✓ 不可变");
    println!("✓ 不拥有数据");
    println!("✓ 固定大小已知");
    println!("✓ 字符串字面量的类型");
}

/// 演示切片作为函数参数
fn demo_slice_as_parameter() {
    println!("\n=== 3. 切片作为函数参数 ===");
    
    let my_string = String::from("hello world");
    
    // String 可以传递整个切片
    let word = first_word(&my_string[..]);
    println!("第一个单词: {}", word);
    
    // 也可以传递部分切片
    let word2 = first_word(&my_string[0..6]);
    println!("部分切片的第一个单词: {}", word2);
    
    // 字符串字面量直接传递
    let my_string_literal = "hello world";
    let word3 = first_word(my_string_literal);
    println!("字面量的第一个单词: {}", word3);
    
    println!("\n✓ 使用 &str 作为参数更灵活");
    println!("✓ 可以接受 String 切片和字符串字面量");
}

fn first_word(s: &str) -> &str {
    let bytes = s.as_bytes();
    
    for (i, &item) in bytes.iter().enumerate() {
        if item == b' ' {
            return &s[0..i];
        }
    }
    
    &s[..]
}

/// 演示数组切片
fn demo_array_slices() {
    println!("\n=== 4. 数组切片 ===");
    
    let a = [1, 2, 3, 4, 5];
    
    // 创建数组切片
    let slice = &a[1..3];  // [2, 3]
    
    println!("原数组: {:?}", a);
    println!("切片 &a[1..3]: {:?}", slice);
    
    // 不同范围的切片
    let slice1 = &a[..2];   // [1, 2]
    let slice2 = &a[2..];   // [3, 4, 5]
    let slice3 = &a[..];    // [1, 2, 3, 4, 5]
    
    println!("\n不同切片:");
    println!("&a[..2]: {:?}", slice1);
    println!("&a[2..]: {:?}", slice2);
    println!("&a[..]: {:?}", slice3);
    
    // 切片类型
    let slice: &[i32] = &a[1..4];
    println!("\n切片类型 &[i32]: {:?}", slice);
    
    println!("\n✓ 数组切片类型: &[T]");
    println!("✓ 不拥有数据,只是引用");
}

/// 演示可变切片
fn demo_mutable_slices() {
    println!("\n=== 5. 可变切片 ===");
    
    let mut arr = [1, 2, 3, 4, 5];
    println!("原数组: {:?}", arr);
    
    // 创建可变切片
    let slice = &mut arr[1..4];
    
    // 修改切片中的值
    slice[0] = 10;
    slice[1] = 20;
    
    println!("修改后数组: {:?}", arr);
    
    // 函数接受可变切片
    let mut numbers = [1, 2, 3, 4, 5];
    double_slice(&mut numbers[..]);
    println!("\n全部翻倍: {:?}", numbers);
    
    println!("\n✓ 可变切片: &mut [T]");
    println!("✓ 可以修改元素值");
}

fn double_slice(slice: &mut [i32]) {
    for item in slice {
        *item *= 2;
    }
}

/// 演示切片的实际应用
fn demo_practical_applications() {
    println!("\n=== 6. 切片的实际应用 ===");
    
    // 应用1: 分割字符串
    let text = "apple,banana,cherry";
    println!("原文本: {}", text);
    
    for word in text.split(',') {
        println!("  - {}", word);
    }
    
    // 应用2: 查找子串
    let sentence = "The quick brown fox";
    if let Some(index) = sentence.find("quick") {
        let found = &sentence[index..index+5];
        println!("\n找到单词: {}", found);
    }
    
    // 应用3: 去除空白
    let s = "  hello  ";
    let trimmed = s.trim();
    println!("\n原字符串: '{}'", s);
    println!("去除空白: '{}'", trimmed);
    
    // 应用4: 数组求和
    let numbers = [1, 2, 3, 4, 5];
    let sum = sum_slice(&numbers[1..4]);
    println!("\n数组 {:?} 中 [1..4] 的和: {}", numbers, sum);
}

fn sum_slice(slice: &[i32]) -> i32 {
    let mut total = 0;
    for &num in slice {
        total += num;
    }
    total
}

/// 演示字符串切片的安全性
fn demo_slice_safety() {
    println!("\n=== 7. 切片的安全性 ===");
    
    let mut s = String::from("hello world");
    
    let word = first_word(&s);
    println!("第一个单词: {}", word);
    
    // 下面会编译错误,因为 word 持有不可变引用
    // s.clear(); // 错误: 不能在有不可变借用时进行可变借用
    
    // 使用 word 后,s 才可以修改
    // println!("{}", word);
    
    s.clear();
    println!("清空后的字符串: '{}'", s);
    
    println!("\n✓ 切片防止数据竞争");
    println!("✓ 编译时检查借用规则");
}

/// 演示多维切片
fn demo_multidimensional_slices() {
    println!("\n=== 8. 多维数据切片 ===");
    
    let matrix = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
    ];
    
    println!("矩阵:");
    for row in &matrix {
        println!("{:?}", row);
    }
    
    // 获取一行的切片
    let row_slice: &[i32] = &matrix[1];
    println!("\n第二行: {:?}", row_slice);
    
    // 处理行
    let sum = sum_slice(row_slice);
    println!("第二行的和: {}", sum);
}

/// 演示字符串方法返回切片
fn demo_string_methods() {
    println!("\n=== 9. 字符串方法与切片 ===");
    
    let s = "  hello world  ";
    
    // trim 返回切片
    let trimmed = s.trim();
    println!("原字符串: '{}'", s);
    println!("trim 后: '{}'", trimmed);
    
    // split 返回切片迭代器
    let words: Vec<&str> = "one two three".split(' ').collect();
    println!("\n分割单词: {:?}", words);
    
    // lines 返回行切片
    let text = "line1\nline2\nline3";
    println!("\n多行文本:");
    for line in text.lines() {
        println!("  {}", line);
    }
    
    // starts_with 和 ends_with
    let filename = "document.txt";
    if filename.ends_with(".txt") {
        println!("\n{} 是文本文件", filename);
    }
}

/// 演示常见陷阱
fn demo_common_pitfalls() {
    println!("\n=== 10. 常见陷阱 ===");
    
    // 陷阱1: UTF-8 边界
    println!("\n陷阱1: 注意 UTF-8 字符边界");
    let s = "你好";
    // let bad = &s[0..1]; // panic: 不在字符边界上
    let good = &s[0..3];  // 一个汉字占3个字节
    println!("正确切片: {}", good);
    
    // 陷阱2: 索引越界
    println!("\n陷阱2: 索引越界");
    let arr = [1, 2, 3];
    let slice = &arr[..2];
    println!("安全切片: {:?}", slice);
    // let bad = &arr[..10]; // panic: 索引越界
    
    // 陷阱3: 可变性冲突
    println!("\n陷阱3: 借用规则");
    let mut data = String::from("hello");
    let r = &data[..];
    // data.push_str(" world"); // 错误: 不能可变借用
    println!("切片: {}", r);
    data.push_str(" world"); // r 不再使用后可以修改
    println!("修改后: {}", data);
    
    println!("\n最佳实践:");
    println!("✓ 使用 &str 而不是 &String 作为参数");
    println!("✓ 注意 UTF-8 字符边界");
    println!("✓ 使用 get 方法避免 panic");
}

/// 主函数
fn main() {
    println!("╔═══════════════════════════════════════╗");
    println!("║     Rust 学习系列 08: 切片类型        ║");
    println!("╚═══════════════════════════════════════╝");
    
    demo_string_slice_basics();
    demo_str_type();
    demo_slice_as_parameter();
    demo_array_slices();
    demo_mutable_slices();
    demo_practical_applications();
    demo_slice_safety();
    demo_multidimensional_slices();
    demo_string_methods();
    demo_common_pitfalls();
    
    println!("\n╔═══════════════════════════════════════╗");
    println!("║              学习小结                 ║");
    println!("╚═══════════════════════════════════════╝");
    println!("1. 切片是对集合部分的引用,不拥有数据");
    println!("2. 字符串切片类型是 &str");
    println!("3. 数组切片类型是 &[T]");
    println!("4. 使用 &str 作为参数更灵活通用");
    println!("5. 注意 UTF-8 字符边界和索引越界");
    
    println!("\n💡 下一步: 学习 09_structs.rs - 结构体");
}
