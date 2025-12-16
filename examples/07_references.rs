//! # 07 - 引用与借用
//!
//! ## 学习目标
//! - 掌握引用的创建和使用
//! - 理解借用规则
//! - 避免悬垂引用
//! - 理解可变引用和不可变引用的区别

/*
 * ================================
 * 核心概念说明
 * ================================
 * 
 * 引用(Reference):允许你使用值但不获取其所有权
 * 
 * 借用规则:
 * 1. 在任意给定时间,要么只能有一个可变引用,要么只能有多个不可变引用
 * 2. 引用必须总是有效的(不能是悬垂引用)
 * 
 * 引用类型:
 * - 不可变引用: &T
 * - 可变引用: &mut T
 */

/// 演示不可变引用
fn demo_immutable_references() {
    println!("\n=== 1. 不可变引用 ===");
    
    let s1 = String::from("hello");
    
    // 创建引用,不获取所有权
    let len = calculate_length(&s1);
    
    println!("'{}'的长度是 {}", s1, len);
    println!("s1 仍然有效!");
    
    // 可以有多个不可变引用
    let r1 = &s1;
    let r2 = &s1;
    let r3 = &s1;
    
    println!("r1: {}", r1);
    println!("r2: {}", r2);
    println!("r3: {}", r3);
    println!("s1: {}", s1);
    
    println!("\n✓ 使用 & 创建不可变引用");
    println!("✓ 引用不获取所有权");
    println!("✓ 可以有多个不可变引用");
}

fn calculate_length(s: &String) -> usize {
    s.len()
}  // s 离开作用域,但因为没有所有权,不会释放数据

/// 演示可变引用
fn demo_mutable_references() {
    println!("\n=== 2. 可变引用 ===");
    
    let mut s = String::from("hello");
    println!("修改前: {}", s);
    
    // 创建可变引用
    change(&mut s);
    println!("修改后: {}", s);
    
    // 可变引用示例2
    let mut num = 10;
    println!("\n修改前: num = {}", num);
    
    add_ten(&mut num);
    println!("修改后: num = {}", num);
    
    println!("\n✓ 使用 &mut 创建可变引用");
    println!("✓ 可以通过引用修改值");
}

fn change(some_string: &mut String) {
    some_string.push_str(", world");
}

fn add_ten(num: &mut i32) {
    *num += 10;  // 使用 * 解引用
}

/// 演示借用规则
fn demo_borrowing_rules() {
    println!("\n=== 3. 借用规则 ===");
    
    // 规则1: 多个不可变引用
    let s = String::from("hello");
    let r1 = &s;
    let r2 = &s;
    println!("✓ 多个不可变引用: r1 = {}, r2 = {}", r1, r2);
    
    // 规则2: 只能有一个可变引用
    let mut s2 = String::from("world");
    let r3 = &mut s2;
    println!("✓ 一个可变引用: r3 = {}", r3);
    // let r4 = &mut s2; // 错误: 不能同时有两个可变引用
    
    // 规则3: 不能同时有可变和不可变引用
    let mut s3 = String::from("rust");
    let r5 = &s3;       // 不可变引用
    let r6 = &s3;       // 不可变引用
    println!("不可变引用: {}, {}", r5, r6);
    // let r7 = &mut s3; // 错误: 已有不可变引用
    
    // 引用的作用域从声明开始到最后一次使用
    let mut s4 = String::from("example");
    let r8 = &s4;
    let r9 = &s4;
    println!("{} and {}", r8, r9);
    // r8 和 r9 不再使用
    
    let r10 = &mut s4;  // 现在可以创建可变引用
    println!("{}", r10);
    
    println!("\n借用规则:");
    println!("✓ 多个不可变引用 OR 一个可变引用");
    println!("✓ 引用必须总是有效的");
}

/// 演示引用作用域(NLL)
fn demo_reference_scope() {
    println!("\n=== 4. 引用作用域(NLL) ===");
    
    let mut s = String::from("hello");
    
    let r1 = &s;  // 不可变引用
    let r2 = &s;  // 不可变引用
    println!("{} and {}", r1, r2);
    // r1 和 r2 的作用域在这里结束
    
    let r3 = &mut s;  // 可变引用,此时已无不可变引用
    r3.push_str(" world");
    println!("{}", r3);
    
    println!("\n✓ NLL (非词法作用域生命周期)");
    println!("✓ 引用的作用域到最后一次使用");
}

/// 演示悬垂引用
fn demo_dangling_references() {
    println!("\n=== 5. 防止悬垂引用 ===");
    
    // 下面的代码会编译错误
    // let reference_to_nothing = dangle();
    
    // 正确的做法:返回所有权
    let s = no_dangle();
    println!("有效的字符串: {}", s);
    
    println!("\n✓ Rust 编译器防止悬垂引用");
    println!("✓ 引用必须总是有效的");
}

// 这个函数会产生悬垂引用(编译错误)
// fn dangle() -> &String {
//     let s = String::from("hello");
//     &s  // 错误: s 离开作用域被释放,返回的引用无效
// }

// 正确做法:返回所有权
fn no_dangle() -> String {
    let s = String::from("hello");
    s  // 移动所有权
}

/// 演示解引用
fn demo_dereferencing() {
    println!("\n=== 6. 解引用 ===");
    
    let x = 5;
    let y = &x;
    
    println!("x = {}", x);
    println!("y 指向的值 = {}", *y);  // 使用 * 解引用
    
    // 比较值
    assert_eq!(5, x);
    assert_eq!(5, *y);
    
    // 可变引用的解引用
    let mut num = 10;
    let r = &mut num;
    *r += 5;  // 通过解引用修改值
    println!("修改后: num = {}", num);
    
    println!("\n✓ 使用 * 解引用获取值");
}

/// 演示引用作为函数参数
fn demo_references_as_parameters() {
    println!("\n=== 7. 引用作为函数参数 ===");
    
    let s = String::from("hello");
    
    // 传递不可变引用
    print_string(&s);
    println!("s 仍然有效: {}", s);
    
    // 传递可变引用
    let mut text = String::from("world");
    append_suffix(&mut text);
    println!("修改后的 text: {}", text);
    
    // 多个引用参数
    let s1 = String::from("hello");
    let s2 = String::from("world");
    let result = combine_strings(&s1, &s2);
    println!("组合结果: {}", result);
    println!("s1 和 s2 仍然有效: {}, {}", s1, s2);
    
    println!("\n✓ 使用引用避免所有权转移");
    println!("✓ 函数可以读取而不获取所有权");
}

fn print_string(s: &String) {
    println!("  打印: {}", s);
}

fn append_suffix(s: &mut String) {
    s.push_str("!!!");
}

fn combine_strings(s1: &String, s2: &String) -> String {
    format!("{} {}", s1, s2)
}

/// 演示引用的实际应用
fn demo_practical_uses() {
    println!("\n=== 8. 实际应用场景 ===");
    
    // 场景1: 查找最长的字符串
    let s1 = String::from("hello");
    let s2 = String::from("rust programming");
    
    let longest = find_longest(&s1, &s2);
    println!("最长的字符串: {}", longest);
    
    // 场景2: 就地修改
    let mut numbers = vec![1, 2, 3, 4, 5];
    println!("原始数据: {:?}", numbers);
    
    double_values(&mut numbers);
    println!("翻倍后: {:?}", numbers);
    
    // 场景3: 只读访问
    let data = vec![10, 20, 30, 40, 50];
    let sum = calculate_sum(&data);
    println!("总和: {} (数据未移动)", sum);
    println!("原始数据: {:?}", data);
}

fn find_longest<'a>(x: &'a String, y: &'a String) -> &'a String {
    if x.len() > y.len() {
        x
    } else {
        y
    }
}

fn double_values(vec: &mut Vec<i32>) {
    for item in vec.iter_mut() {
        *item *= 2;
    }
}

fn calculate_sum(vec: &Vec<i32>) -> i32 {
    let mut sum = 0;
    for &item in vec {
        sum += item;
    }
    sum
}

/// 演示切片引用
fn demo_slice_references() {
    println!("\n=== 9. 切片引用 ===");
    
    let s = String::from("hello world");
    
    // 字符串切片
    let hello = &s[0..5];
    let world = &s[6..11];
    
    println!("完整字符串: {}", s);
    println!("切片1: {}", hello);
    println!("切片2: {}", world);
    
    // 数组切片
    let numbers = [1, 2, 3, 4, 5];
    let slice = &numbers[1..4];
    
    println!("\n数组: {:?}", numbers);
    println!("切片: {:?}", slice);
    
    println!("\n✓ 切片是对集合部分的引用");
}

/// 演示常见错误
fn demo_common_pitfalls() {
    println!("\n=== 10. 常见陷阱 ===");
    
    // 陷阱1: 可变和不可变引用冲突
    println!("\n陷阱1: 借用规则冲突");
    let mut s = String::from("hello");
    let r1 = &s;
    // let r2 = &mut s; // 错误: 不能同时存在
    println!("r1 = {}", r1);
    drop(r1); // r1 不再使用
    let r2 = &mut s;
    r2.push_str(" world");
    println!("r2 = {}", r2);
    
    // 陷阱2: 忘记解引用
    println!("\n陷阱2: 需要解引用时");
    let x = 5;
    let y = &x;
    // assert_eq!(5, y); // 错误: 类型不匹配
    assert_eq!(5, *y); // 正确: 解引用
    
    // 陷阱3: 引用生命周期
    println!("\n陷阱3: 注意引用的生命周期");
    // let r;
    // {
    //     let x = 5;
    //     // r = &x; // 错误: x 会先离开作用域
    // }
    // println!("{}", r); // 错误: r 是悬垂引用
    println!("这种代码会导致悬垂引用,Rust 编译器会阻止");
    
    println!("\n最佳实践:");
    println!("✓ 优先使用不可变引用");
    println!("✓ 理解借用检查器的规则");
    println!("✓ 让引用的作用域尽可能短");
}

/// 主函数:运行所有示例
fn main() {
    println!("╔═══════════════════════════════════════╗");
    println!("║    Rust 学习系列 07: 引用与借用       ║");
    println!("╚═══════════════════════════════════════╝");
    
    demo_immutable_references();
    demo_mutable_references();
    demo_borrowing_rules();
    demo_reference_scope();
    demo_dangling_references();
    demo_dereferencing();
    demo_references_as_parameters();
    demo_practical_uses();
    demo_slice_references();
    demo_common_pitfalls();
    
    println!("\n╔═══════════════════════════════════════╗");
    println!("║              学习小结                 ║");
    println!("╚═══════════════════════════════════════╝");
    println!("1. 引用允许使用值而不获取所有权");
    println!("2. &T 不可变引用, &mut T 可变引用");
    println!("3. 多个不可变引用 OR 一个可变引用");
    println!("4. 引用必须总是有效(无悬垂引用)");
    println!("5. 使用 * 解引用获取值");
    
    println!("\n💡 下一步: 学习 08_slices.rs - 切片类型");
}
