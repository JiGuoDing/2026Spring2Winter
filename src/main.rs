//! Rust 学习系列 - 主导航
//!
//! 这个项目包含22个示例,涵盖Rust的核心概念

fn main() {
    println!("╔══════════════════════════════════════════════════════╗");
    println!("║                                                      ║");
    println!("║          🦀 Rust 语法学习指南 🦀                    ║");
    println!("║                                                      ║");
    println!("╚══════════════════════════════════════════════════════╝");
    
    println!("\n本项目包含 22 个学习示例,按以下顺序学习:");
    
    println!("\n📚 第一阶段:基础语法和流程控制 (1-2天)");
    println!("  01. 变量与可变性     - cargo run --example 01_variables");
    println!("  02. 数据类型         - cargo run --example 02_data_types");
    println!("  03. 函数             - cargo run --example 03_functions");
    println!("  04. 注释             - cargo run --example 04_comments");
    println!("  05. 流程控制         - cargo run --example 05_control_flow");
    
    println!("\n📚 第二阶段:所有权系统 (2-3天,重点)");
    println!("  06. 所有权           - cargo run --example 06_ownership");
    println!("  07. 引用与借用       - cargo run --example 07_references");
    println!("  08. 切片类型         - cargo run --example 08_slices");
    
    println!("\n📚 第三阶段:自定义类型 (2-3天)");
    println!("  09. 结构体           - cargo run --example 09_structs");
    println!("  10. 枚举             - cargo run --example 10_enums");
    println!("  11. 模式匹配         - cargo run --example 11_match");
    
    println!("\n📚 第四阶段:集合类型 (1-2天)");
    println!("  12. Vector集合       - cargo run --example 12_vector");
    println!("  13. String字符串     - cargo run --example 13_string");
    println!("  14. HashMap集合      - cargo run --example 14_hashmap");
    
    println!("\n📚 第五阶段:错误处理 (1天)");
    println!("  15. 错误处理         - cargo run --example 15_error_handling");
    
    println!("\n📚 第六阶段:高级特性 (3-4天)");
    println!("  16. 泛型             - cargo run --example 16_generics");
    println!("  17. Trait特征        - cargo run --example 17_traits");
    println!("  18. 生命周期         - cargo run --example 18_lifetimes");
    
    println!("\n📚 第七阶段:模块和高级功能 (2-3天)");
    println!("  19. 包和模块         - cargo run --example 19_modules");
    println!("  20. 迭代器           - cargo run --example 20_iterators");
    println!("  21. 闭包             - cargo run --example 21_closures");
    println!("  22. 智能指针         - cargo run --example 22_smart_pointers");
    
    println!("\n╔══════════════════════════════════════════════════════╗");
    println!("║                    快速开始                          ║");
    println!("╚══════════════════════════════════════════════════════╝");
    println!("\n1. 运行第一个示例:");
    println!("   cargo run --example 01_variables");
    println!("\n2. 按顺序学习所有示例:");
    println!("   从 01 到 22 依次运行");
    println!("\n3. 查看源码:");
    println!("   所有示例在 examples/ 目录下");
    println!("\n4. 生成文档:");
    println!("   cargo doc --open");
    
    println!("\n💡 建议:边学习边动手修改代码,加深理解!");
    println!("\n📖 详细信息请查看 README.md");
}