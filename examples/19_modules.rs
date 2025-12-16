//! 19 - 包和模块

mod front_of_house {
    pub mod hosting {
        pub fn add_to_waitlist() {
            println!("添加到等待列表");
        }
    }
}

use front_of_house::hosting;

fn main() {
    println!("╔══════════════════════════════════════╗");
    println!("║    Rust 学习系列 19: 包和模块        ║");
    println!("╚══════════════════════════════════════╝");
    
    // 绝对路径
    crate::front_of_house::hosting::add_to_waitlist();
    
    // 相对路径
    front_of_house::hosting::add_to_waitlist();
    
    // use 引入
    hosting::add_to_waitlist();
    
    println!("\n模块系统:");
    println!("  - mod 定义模块");
    println!("  - pub 公开可见性");
    println!("  - use 引入路径");
    println!("  - super 访问父模块");
    println!("  - self 当前模块");
    
    println!("\n💡 下一步: 学习 20_iterators.rs - 迭代器");
}
