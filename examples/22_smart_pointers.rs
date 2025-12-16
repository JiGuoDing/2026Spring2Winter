//! 22 - 智能指针

use std::rc::Rc;
use std::cell::RefCell;

fn main() {
    println!("╔══════════════════════════════════════╗");
    println!("║    Rust 学习系列 22: 智能指针        ║");
    println!("╚══════════════════════════════════════╝");
    
    // Box<T> - 堆分配
    let b = Box::new(5);
    println!("\nBox: {}", b);
    
    // Box 用于递归类型
    #[derive(Debug)]
    enum List {
        Cons(i32, Box<List>),
        Nil,
    }
    
    use List::{Cons, Nil};
    
    let list = Cons(1, Box::new(Cons(2, Box::new(Cons(3, Box::new(Nil))))));
    println!("递归类型: {:?}", list);
    
    // Rc<T> - 引用计数
    let a = Rc::new(Cons(5, Box::new(Cons(10, Box::new(Nil)))));
    println!("\n引用计数: {}", Rc::strong_count(&a));
    
    let b = Rc::clone(&a);
    println!("克隆后: {}", Rc::strong_count(&a));
    
    {
        let c = Rc::clone(&a);
        println!("内部作用域: {}", Rc::strong_count(&a));
    }
    
    println!("作用域外: {}", Rc::strong_count(&a));
    
    // RefCell<T> - 内部可变性
    let value = RefCell::new(5);
    
    *value.borrow_mut() += 10;
    println!("\nRefCell: {}", value.borrow());
    
    // Rc<RefCell<T>> 组合
    let shared_value = Rc::new(RefCell::new(5));
    let a = Rc::clone(&shared_value);
    let b = Rc::clone(&shared_value);
    
    *a.borrow_mut() += 10;
    *b.borrow_mut() += 5;
    
    println!("共享可变: {}", shared_value.borrow());
    
    println!("\n╔══════════════════════════════════════╗");
    println!("║          恭喜完成全部学习!           ║");
    println!("╚══════════════════════════════════════╝");
    println!("\n你已经学习了 Rust 的核心概念:");
    println!("✓ 01-05: 基础语法和流程控制");
    println!("✓ 06-08: 所有权系统");
    println!("✓ 09-11: 自定义类型");
    println!("✓ 12-14: 集合类型");
    println!("✓ 15: 错误处理");
    println!("✓ 16-18: 泛型、Trait、生命周期");
    println!("✓ 19-22: 模块、迭代器、闭包、智能指针");
    println!("\n继续深入学习 Rust 的高级特性!");
}
