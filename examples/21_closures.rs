//! 21 - 闭包

fn main() {
    println!("╔══════════════════════════════════════╗");
    println!("║      Rust 学习系列 21: 闭包          ║");
    println!("╚══════════════════════════════════════╝");
    
    // 基本闭包
    let add_one = |x: i32| x + 1;
    println!("\n闭包结果: {}", add_one(5));
    
    // 类型推断
    let add = |x, y| x + y;
    println!("类型推断: {}", add(1, 2));
    
    // 捕获环境
    let x = 4;
    let equal_to_x = |z| z == x;
    let y = 4;
    println!("\n捕获环境: {}", equal_to_x(y));
    
    // 不可变借用
    let list = vec![1, 2, 3];
    let only_borrows = || println!("列表: {:?}", list);
    only_borrows();
    println!("仍可使用: {:?}", list);
    
    // 可变借用
    let mut list2 = vec![1, 2, 3];
    let mut borrows_mutably = || list2.push(7);
    borrows_mutably();
    println!("\n修改后: {:?}", list2);
    
    // move 关键字
    let list3 = vec![1, 2, 3];
    let consume = move || {
        println!("移动: {:?}", list3);
    };
    consume();
    // println!("{:?}", list3); // 错误: list3 已移动
    
    // 闭包作为参数
    let numbers = vec![1, 2, 3, 4, 5];
    let doubled: Vec<_> = numbers.iter().map(|x| x * 2).collect();
    println!("\n映射: {:?}", doubled);
    
    println!("\n💡 下一步: 学习 22_smart_pointers.rs - 智能指针");
}
