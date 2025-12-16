# 🦀 Rust 语法学习指南

一套系统化的 Rust 学习示例,通过 22 个独立的可运行示例,深入理解 Rust 语言的核心概念和语法特性。

## 📚 项目简介

本项目包含 **22 个完整的学习示例**,每个示例专注于一个核心主题,包含:
- ✅ 详细的概念说明
- ✅ 可运行的示例代码
- ✅ 实际应用场景
- ✅ 常见陷阱和最佳实践

## 🚀 快速开始

### 运行主导航

```bash
cargo run
```

### 运行单个示例

```bash
cargo run --example 01_variables
cargo run --example 02_data_types
# ... 以此类推
```

### 查看所有示例

```bash
ls examples/
```

## 📖 学习路径

### 第一阶段:基础语法和流程控制 (1-2天)

| 序号 | 主题 | 命令 | 核心内容 |
|------|------|------|----------|
| 01 | 变量与可变性 | `cargo run --example 01_variables` | let, mut, const, shadowing |
| 02 | 数据类型 | `cargo run --example 02_data_types` | 整数、浮点、布尔、字符、元组、数组 |
| 03 | 函数 | `cargo run --example 03_functions` | 函数定义、参数、返回值、表达式 |
| 04 | 注释 | `cargo run --example 04_comments` | 行注释、文档注释 |
| 05 | 流程控制 | `cargo run --example 05_control_flow` | if、loop、while、for |

### 第二阶段:所有权系统 (2-3天) ⭐ 重点

| 序号 | 主题 | 命令 | 核心内容 |
|------|------|------|----------|
| 06 | 所有权 | `cargo run --example 06_ownership` | 所有权规则、移动、克隆 |
| 07 | 引用与借用 | `cargo run --example 07_references` | &T, &mut T, 借用规则 |
| 08 | 切片类型 | `cargo run --example 08_slices` | 字符串切片、数组切片 |

> **💡 提示**: 所有权是 Rust 最重要的概念,建议多花时间理解!

### 第三阶段:自定义类型 (2-3天)

| 序号 | 主题 | 命令 | 核心内容 |
|------|------|------|----------|
| 09 | 结构体 | `cargo run --example 09_structs` | struct、方法、关联函数 |
| 10 | 枚举 | `cargo run --example 10_enums` | enum、Option |
| 11 | 模式匹配 | `cargo run --example 11_match` | match、if let、解构 |

### 第四阶段:集合类型 (1-2天)

| 序号 | 主题 | 命令 | 核心内容 |
|------|------|------|----------|
| 12 | Vector集合 | `cargo run --example 12_vector` | Vec创建、读取、遍历 |
| 13 | String字符串 | `cargo run --example 13_string` | String vs &str、操作 |
| 14 | HashMap集合 | `cargo run --example 14_hashmap` | HashMap创建、访问、更新 |

### 第五阶段:错误处理 (1天)

| 序号 | 主题 | 命令 | 核心内容 |
|------|------|------|----------|
| 15 | 错误处理 | `cargo run --example 15_error_handling` | Result、?操作符、panic! |

### 第六阶段:高级特性 (3-4天)

| 序号 | 主题 | 命令 | 核心内容 |
|------|------|------|----------|
| 16 | 泛型 | `cargo run --example 16_generics` | 泛型函数、结构体、方法 |
| 17 | Trait特征 | `cargo run --example 17_traits` | Trait定义、实现、约束 |
| 18 | 生命周期 | `cargo run --example 18_lifetimes` | 生命周期标注、'a |

### 第七阶段:模块和高级功能 (2-3天)

| 序号 | 主题 | 命令 | 核心内容 |
|------|------|------|----------|
| 19 | 包和模块 | `cargo run --example 19_modules` | mod、pub、use |
| 20 | 迭代器 | `cargo run --example 20_iterators` | Iterator、map、filter |
| 21 | 闭包 | `cargo run --example 21_closures` | 闭包语法、捕获环境 |
| 22 | 智能指针 | `cargo run --example 22_smart_pointers` | Box、Rc、RefCell |

## 🎯 学习建议

### 对于初学者

1. **按顺序学习**: 从 01 到 22 依次学习,前面的概念是后面的基础
2. **动手实践**: 不要只看代码,一定要运行并修改示例
3. **重点突破**: 所有权系统(06-08)是重点,多花时间理解
4. **记笔记**: 记录重点概念和疑问点

### 对于有经验的开发者

1. **快速浏览**: 基础部分(01-05)可以快速浏览
2. **重点关注**: 重点学习所有权(06-08)、生命周期(18)等 Rust 特有概念
3. **对比学习**: 与你熟悉的语言对比,理解差异
4. **深入实践**: 尝试用 Rust 重写你的小项目

## 📂 项目结构

```
learn_rust/
├── src/
│   └── main.rs              # 主导航程序
├── examples/                # 所有学习示例
│   ├── 01_variables.rs      # 变量与可变性
│   ├── 02_data_types.rs     # 数据类型
│   ├── ...                  # 其他示例
│   └── 22_smart_pointers.rs # 智能指针
├── Cargo.toml               # 项目配置
└── README.md                # 本文件
```

## 🛠️ 常用命令

```bash
# 运行主程序(查看学习导航)
cargo run

# 运行特定示例
cargo run --example 01_variables

# 查看示例列表
ls examples/

# 生成并查看文档
cargo doc --open

# 检查代码(无需编译)
cargo check

# 格式化代码
cargo fmt

# 运行 Clippy 检查
cargo clippy
```

## 📝 代码示例

每个示例文件都包含完整的可运行代码,例如 `01_variables.rs`:

```rust
fn main() {
    // 不可变变量
    let x = 5;
    println!("x = {}", x);
    
    // 可变变量
    let mut y = 10;
    y = 20;
    println!("y = {}", y);
    
    // 常量
    const MAX_POINTS: u32 = 100_000;
    println!("MAX_POINTS = {}", MAX_POINTS);
    
    // 变量隐藏
    let z = 5;
    let z = z + 1;
    println!("z = {}", z);
}
```

## ✨ 特色功能

- ✅ **22个完整示例**: 涵盖 Rust 核心概念
- ✅ **独立运行**: 每个示例都可以独立编译运行
- ✅ **详细注释**: 关键代码都有中文注释说明
- ✅ **最佳实践**: 包含常见陷阱和推荐做法
- ✅ **渐进式学习**: 从简单到复杂,循序渐进

## 🎓 学习目标

完成所有示例后,你将掌握:

- ✅ Rust 基础语法和数据类型
- ✅ 所有权系统的工作原理
- ✅ 如何使用结构体和枚举
- ✅ 错误处理的最佳实践
- ✅ 泛型、Trait 和生命周期
- ✅ 常用集合类型的使用
- ✅ 迭代器和闭包的应用
- ✅ 智能指针的使用场景

## 🔗 推荐资源

- [Rust 官方文档](https://doc.rust-lang.org/book/)
- [Rust By Example](https://doc.rust-lang.org/rust-by-example/)
- [Rustlings 练习](https://github.com/rust-lang/rustlings)
- [Rust 标准库文档](https://doc.rust-lang.org/std/)

## 📌 注意事项

1. **Rust 版本**: 建议使用最新稳定版 `rustc 1.70+`
2. **编辑器**: 推荐使用 VS Code + rust-analyzer 插件
3. **学习时间**: 建议每天学习 2-4 个示例,约 2 周完成
4. **遇到问题**: 先查看示例中的注释和常见陷阱部分

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进这个学习项目!

## 📄 许可证

本项目采用 MIT 许可证。

---

**🎉 开始你的 Rust 学习之旅吧!**

运行第一个示例:
```bash
cargo run --example 01_variables
```
