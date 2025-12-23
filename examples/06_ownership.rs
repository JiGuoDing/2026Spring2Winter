// ! # 06 - 所有权系统
// !
// ! ## 学习目标
// ! - 理解所有权的三条规则
// ! - 理解移动(move)语义
// ! - 理解克隆(clone)
// ! - 理解栈和堆的区别
// ! - 掌握函数参数和返回值的所有权转移

/*
 * ================================
 * 核心概念说明
 * ================================
 * 
 * 所有权是 Rust 最独特和最重要的特性
 * 
 * 所有权规则:
 * 1. Rust 中的每一个值都有一个所有者(owner)
 * 2. 值在任一时刻有且只有一个所有者
 * 3. 当所有者(变量)离开作用域,这个值将被丢弃
 * 
 * 内存管理:
 * - 栈(Stack): 固定大小,先进后出,速度快
 * - 堆(Heap): 动态大小,需要分配器,速度相对慢
 */

/// 演示所有权基础
fn demo_ownership_basics() {
    println!("\n=== 1. 所有权基础 ===");
    
    {
        // s 在作用域内有效
        let s = "hello";
        println!("s = {}", s);
    } // s 离开作用域,不再有效
    
    // println!("{}", s); // 错误: s 已经离开作用域

    /*
    let mut s = "foo";
    let mut s = String::from("foo");
    以上两行代码的区别:
    - 第一行创建了一个不可变的字符串切片(&str),存储在栈上,变量绑定本身可以被重新赋值,但内容不可修改
    - 第二行创建了一个可变的 String 类型,存储在堆上,拥有所有权,内容可以修改
    */
    
    // String 类型: 在堆上分配
    let mut s = String::from("hello");
    println!("初始字符串: {}", s);
    
    s.push_str(", world!");
    println!("修改后字符串: {}", s);
    
    println!("\n✓ 变量离开作用域时自动释放内存");
    println!("✓ String 在堆上分配,可以修改");
}

/// 演示移动(Move)语义
fn demo_move_semantics() {
    println!("\n=== 2. 移动语义 ===");
    
    // 简单类型的复制
    let x = 5;
    let y = x;  // 整数是 Copy 类型,这里是复制
    println!("x = {}, y = {} (都有效)", x, y);
    
    // String 的移动
    let s1 = String::from("hello");
    let s2 = s1;  // s1 的所有权移动到 s2
    
    println!("s2 = {}", s2);
    // println!("{}", s1); // 错误: s1 已经失效
    
    println!("\n所有权移动后:");
    println!("- s1 不再有效");
    println!("- s2 拥有数据");
    println!("- 避免了双重释放(double free)");
    
    println!("\n✓ 堆数据默认是移动,不是复制");
    println!("✓ 移动后原变量失效");
}

/// 演示克隆(Clone)
fn demo_clone() {
    println!("\n=== 3. 克隆(深拷贝) ===");
    
    let s1 = String::from("hello");
    let s2 = s1.clone();  // * 深拷贝
    
    println!("s1 = {}", s1);
    println!("s2 = {}", s2);
    println!("两个变量都有效!");
    
    // * 克隆是昂贵的操作
    let large_string = String::from("这是一个很长的字符串...");
    let cloned = large_string.clone();
    
    println!("\nlarge_string = {}", large_string);
    println!("cloned = {}", cloned);
    
    println!("\n✓ clone() 创建数据的深拷贝");
    println!("✓ 两个变量都拥有各自的数据");
    println!("⚠️  克隆是昂贵的操作");
}

/// 演示 Copy trait
fn demo_copy_trait() {
    println!("\n=== 4. Copy Trait ===");
    
    // 实现了 Copy trait 的类型会自动复制
    
    // 整数类型
    let x = 5;
    let y = x;
    println!("整数: x = {}, y = {}", x, y);
    
    // 浮点类型
    let a = 3.14;
    let b = a;
    println!("浮点: a = {}, b = {}", a, b);
    
    // 布尔类型
    let flag1 = true;
    let flag2 = flag1;
    println!("布尔: flag1 = {}, flag2 = {}", flag1, flag2);
    
    // 字符类型
    let c1 = 'A';
    let c2 = c1;
    println!("字符: c1 = {}, c2 = {}", c1, c2);
    
    // 元组(所有元素都是 Copy)
    let tup1 = (1, 2, 3);
    let tup2 = tup1;
    println!("元组: tup1 = {:?}, tup2 = {:?}", tup1, tup2);
    
    // 数组(元素是 Copy)
    let arr1 = [1, 2, 3];
    let arr2 = arr1;
    println!("数组: arr1 = {:?}, arr2 = {:?}", arr1, arr2);
    
    println!("\nCopy 类型:");
    println!("✓ 所有整数类型");
    println!("✓ 浮点类型");
    println!("✓ 布尔类型");
    println!("✓ 字符类型");
    println!("✓ 元组(如果所有元素都是 Copy)");
    println!("✓ 数组(如果元素是 Copy)");
}

/// 演示所有权与函数
fn demo_ownership_and_functions() {
    println!("\n=== 5. 所有权与函数 ===");
    
    let s = String::from("hello");
    println!("调用前: s = {}", s);
    
    takes_ownership(s);  // * s 的所有权移动到函数中
    // println!("{}", s); // 错误: s 已经失效
    
    let x = 5;
    println!("调用前: x = {}", x);
    
    makes_copy(x);  // * x 是 Copy 类型,传递的是副本
    println!("调用后: x = {} (仍然有效)", x);
    
    println!("\n✓ 传递参数会转移或复制所有权");
    println!("✓ 函数结束时,参数的值被丢弃");
}

fn takes_ownership(some_string: String) {
    println!("  函数内: some_string = {}", some_string);
} // * some_string 离开作用域并被丢弃

fn makes_copy(some_integer: i32) {
    println!("  函数内: some_integer = {}", some_integer);
}

/// 演示返回值与所有权
fn demo_return_values_and_ownership() {
    println!("\n=== 6. 返回值与所有权 ===");
    
    let s1 = gives_ownership();
    println!("s1 = {}", s1);
    
    let s2 = String::from("hello");
    let s3 = takes_and_gives_back(s2);
    // println!("{}", s2); // 错误: s2 已失效
    println!("s3 = {}", s3);
    
    // 返回多个值
    let s4 = String::from("world");
    let (s5, len) = calculate_length(s4);
    println!("字符串 '{}' 的长度是 {}", s5, len);
    
    println!("\n✓ 返回值可以转移所有权");
    println!("✓ 可以返回元组来返回多个值");
}

fn gives_ownership() -> String {
    let some_string = String::from("yours");
    some_string  // * 返回并移动所有权
}

fn takes_and_gives_back(a_string: String) -> String {
    a_string  // 返回并移动所有权
}

fn calculate_length(s: String) -> (String, usize) {
    let length = s.len();
    (s, length)  // 返回字符串和长度
}

/// 演示栈和堆
fn demo_stack_and_heap() {
    println!("\n=== 7. 栈和堆 ===");
    
    // 栈上的数据: 固定大小
    let x = 5;              // i32, 4 字节
    let y = true;           // bool, 1 字节
    let z = 3.14;           // f64, 8 字节
    
    println!("栈上的数据:");
    println!("x = {} (i32)", x);
    println!("y = {} (bool)", y);
    println!("z = {} (f64)", z);
    
    // 堆上的数据: 动态大小
    let s1 = String::from("hello");
    let s2 = String::from("rust programming");
    
    println!("\n堆上的数据:");
    println!("s1 = '{}' (长度: {})", s1, s1.len());
    println!("s2 = '{}' (长度: {})", s2, s2.len());
    
    // Vector 也在堆上
    let v = vec![1, 2, 3, 4, 5];
    println!("\nVector: {:?} (容量: {})", v, v.capacity());
    
    println!("\n栈(Stack):");
    println!("✓ 固定大小");
    println!("✓ 自动管理");
    println!("✓ 访问速度快");
    println!("✓ 存储简单数据");
    
    println!("\n堆(Heap):");
    println!("✓ 动态大小");
    println!("✓ 需要分配和释放");
    println!("✓ 访问速度相对慢");
    println!("✓ 存储复杂数据");
}

/// 演示所有权转移的实际场景
fn demo_ownership_scenarios() {
    println!("\n=== 8. 实际应用场景 ===");
    
    // 场景1: 构建器模式
    let message = build_message()
        .add_greeting("Hello")
        .add_name("Alice")
        .build();
    
    println!("消息: {}", message);
    
    // 场景2: 处理数据并返回
    let data = vec![1, 2, 3, 4, 5];
    let processed = process_data(data);
    println!("处理后的数据: {:?}", processed);
    // println!("{:?}", data); // 错误: data 已移动
    
    // 场景3: 取得所有权进行修改
    let mut text = String::from("hello");
    text = append_exclamation(text);
    println!("修改后: {}", text);
}

fn build_message() -> MessageBuilder {
    MessageBuilder::new()
}

struct MessageBuilder {
    greeting: String,
    name: String,
}

impl MessageBuilder {
    fn new() -> Self {
        MessageBuilder {
            greeting: String::new(),
            name: String::new(),
        }
    }
    
    fn add_greeting(mut self, greeting: &str) -> Self {
        self.greeting = greeting.to_string();
        self
    }
    
    fn add_name(mut self, name: &str) -> Self {
        self.name = name.to_string();
        self
    }
    
    fn build(self) -> String {
        format!("{}, {}!", self.greeting, self.name)
    }
}

fn process_data(data: Vec<i32>) -> Vec<i32> {
    data.into_iter().map(|x| x * 2).collect()
}

fn append_exclamation(mut s: String) -> String {
    s.push_str("!!!");
    s
}

/// 演示常见陷阱
fn demo_common_pitfalls() {
    println!("\n=== 9. 常见陷阱 ===");
    
    // 陷阱1: 使用已移动的变量
    println!("\n陷阱1: 使用已移动的变量");
    let s1 = String::from("hello");
    let s2 = s1;
    // let s3 = s1; // 错误: s1 已移动
    println!("s2 = {}", s2);
    
    // 陷阱2: 函数参数移动
    println!("\n陷阱2: 函数参数移动");
    let text = String::from("data");
    print_string(text.clone());  // 使用 clone
    println!("原始数据仍有效: {}", text);
    
    // 陷阱3: 循环中的移动
    println!("\n陷阱3: 循环中注意所有权");
    let strings = vec![
        String::from("a"),
        String::from("b"),
        String::from("c"),
    ];
    
    // 使用引用遍历,不移动所有权
    for s in &strings {
        println!("  {}", s);
    }
    
    println!("strings 仍然有效: {:?}", strings);
    
    println!("\n最佳实践:");
    println!("✓ 理解何时会发生移动");
    println!("✓ 需要保留原值时使用 clone 或引用");
    println!("✓ 优先使用引用而不是移动");
}

fn print_string(s: String) {
    println!("  {}", s);
}

/// 演示所有权的优势
fn demo_ownership_advantages() {
    println!("\n=== 10. 所有权的优势 ===");
    
    println!("所有权系统的优势:");
    println!("\n1. 内存安全:");
    println!("   ✓ 无需垃圾回收器");
    println!("   ✓ 无内存泄漏");
    println!("   ✓ 无悬垂指针");
    println!("   ✓ 无数据竞争");
    
    println!("\n2. 性能:");
    println!("   ✓ 零成本抽象");
    println!("   ✓ 编译时确定内存管理");
    println!("   ✓ 无运行时开销");
    
    println!("\n3. 并发安全:");
    println!("   ✓ 编译时保证线程安全");
    println!("   ✓ 防止数据竞争");
    
    // 示例: 自动清理
    {
        let _temp = String::from("临时数据");
        println!("\n临时作用域中的数据");
    } // _temp 自动释放
    
    println!("离开作用域,内存自动释放");
}

/// 主函数:运行所有示例
fn main() {
    println!("╔═══════════════════════════════════════╗");
    println!("║    Rust 学习系列 06: 所有权系统       ║");
    println!("╚═══════════════════════════════════════╝");
    
    demo_ownership_basics();
    demo_move_semantics();
    demo_clone();
    demo_copy_trait();
    demo_ownership_and_functions();
    demo_return_values_and_ownership();
    demo_stack_and_heap();
    demo_ownership_scenarios();
    demo_common_pitfalls();
    demo_ownership_advantages();
    
    println!("\n╔═══════════════════════════════════════╗");
    println!("║              学习小结                 ║");
    println!("╚═══════════════════════════════════════╝");
    println!("1. 每个值有唯一所有者,离开作用域自动释放");
    println!("2. 赋值/传参会移动所有权(非 Copy 类型)");
    println!("3. clone() 创建深拷贝,两个变量独立");
    println!("4. Copy 类型(整数等)自动复制,不移动");
    println!("5. 所有权保证内存安全,无需 GC");
    
    println!("\n💡 下一步: 学习 07_references.rs - 引用与借用");
}
