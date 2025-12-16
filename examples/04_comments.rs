//! # 04 - 注释
//!
//! ## 学习目标
//! - 掌握行注释和块注释
//! - 了解文档注释的写法
//! - 理解注释的最佳实践

/*
 * ================================
 * 核心概念说明
 * ================================
 * 
 * Rust 中的注释类型:
 * 1. 行注释: // 
 * 2. 块注释: /* ... */
 * 3. 文档注释: /// 或 //!
 * 4. 模块文档注释: //! 位于文件或模块开头
 */

/// 演示行注释
/// 
/// 这是一个文档注释,用于生成文档
/// 可以包含多行说明
fn demo_line_comments() {
    println!("\n=== 1. 行注释 ===");
    
    // 这是一个单行注释
    // 行注释使用双斜杠 //
    let x = 5; // 也可以在代码后面添加注释
    
    println!("x = {}", x);
    
    // 多行注释可以用多个 //
    // 第一行
    // 第二行
    // 第三行
    let y = 10;
    
    println!("y = {}", y);
    
    println!("\n✓ 使用 // 创建行注释");
    println!("✓ 可以在代码后或代码上方");
}

/// 演示块注释
fn demo_block_comments() {
    println!("\n=== 2. 块注释 ===");
    
    /* 这是一个块注释 */
    
    /*
     * 块注释可以跨越多行
     * 通常用于注释大段代码
     * 或者详细的说明
     */
    let value = 42;
    
    println!("value = {}", value);
    
    /* 块注释可以嵌套
       /* 内层注释 */
       外层注释
    */
    
    println!("\n✓ 使用 /* */ 创建块注释");
    println!("✓ 支持嵌套");
}

/// 演示文档注释
/// 
/// 文档注释使用三斜杠 ///
/// 用于生成 API 文档
/// 
/// # 示例
/// 
/// ```
/// let result = add_numbers(2, 3);
/// assert_eq!(result, 5);
/// ```
/// 
/// # 参数
/// 
/// - `a`: 第一个数字
/// - `b`: 第二个数字
/// 
/// # 返回值
/// 
/// 返回两个数字的和
fn add_numbers(a: i32, b: i32) -> i32 {
    a + b
}

/// 演示文档注释的使用
fn demo_doc_comments() {
    println!("\n=== 3. 文档注释 ===");
    
    let result = add_numbers(10, 20);
    println!("add_numbers(10, 20) = {}", result);
    
    println!("\n文档注释可以包含:");
    println!("- Markdown 格式");
    println!("- 代码示例");
    println!("- 参数说明");
    println!("- 返回值说明");
    
    println!("\n✓ 使用 /// 创建文档注释");
    println!("✓ 支持 Markdown 语法");
    println!("✓ 可以运行 cargo doc 生成文档");
}

/// 计算矩形面积
/// 
/// # 示例
/// 
/// ```
/// let area = calculate_area(5.0, 3.0);
/// ```
/// 
/// # Panics
/// 
/// 当宽度或高度为负数时会 panic
fn calculate_area(width: f64, height: f64) -> f64 {
    assert!(width > 0.0, "宽度必须大于 0");
    assert!(height > 0.0, "高度必须大于 0");
    width * height
}

/// 演示模块级文档注释
fn demo_module_doc_comments() {
    println!("\n=== 4. 模块级文档注释 ===");
    
    println!("查看文件顶部的 //! 注释");
    println!("这种注释用于描述整个模块或文件");
    
    println!("\n✓ 使用 //! 创建模块级文档注释");
    println!("✓ 通常放在文件开头");
}

/// 演示注释的最佳实践
fn demo_comment_best_practices() {
    println!("\n=== 5. 注释最佳实践 ===");
    
    // ✓ 好的注释: 解释为什么这样做
    // 使用二分查找因为数组已排序,时间复杂度 O(log n)
    let numbers = vec![1, 2, 3, 4, 5];
    
    // ✗ 不好的注释: 重复代码的意思
    // 将 x 设置为 5
    let x = 5;
    
    // ✓ 好的注释: 解释复杂逻辑
    // 计算斐波那契数列的第 n 项
    // 使用动态规划优化,避免重复计算
    let fib_10 = calculate_fibonacci(10);
    
    println!("数组: {:?}", numbers);
    println!("x = {}", x);
    println!("fib(10) = {}", fib_10);
    
    println!("\n注释最佳实践:");
    println!("✓ 解释为什么,而不是做什么");
    println!("✓ 注释复杂的业务逻辑");
    println!("✓ 保持注释和代码同步");
    println!("✗ 避免废话注释");
    println!("✗ 避免注释掉的代码(使用版本控制)");
}

fn calculate_fibonacci(n: u32) -> u32 {
    if n <= 1 {
        n
    } else {
        let mut prev = 0;
        let mut curr = 1;
        for _ in 2..=n {
            let next = prev + curr;
            prev = curr;
            curr = next;
        }
        curr
    }
}

/// 演示不同场景的注释
fn demo_comment_scenarios() {
    println!("\n=== 6. 不同场景的注释 ===");
    
    // TODO: 需要优化这个算法
    let simple_result = simple_calculation(10);
    
    // FIXME: 这里可能会溢出
    let potential_overflow = 1000;
    
    // NOTE: 这个值是根据业务需求设定的
    const MAX_RETRIES: u32 = 3;
    
    // HACK: 临时解决方案,等待上游库修复
    let workaround = true;
    
    println!("结果: {}", simple_result);
    println!("值: {}", potential_overflow);
    println!("最大重试次数: {}", MAX_RETRIES);
    println!("使用临时方案: {}", workaround);
    
    println!("\n常用注释标记:");
    println!("- TODO: 待办事项");
    println!("- FIXME: 需要修复的问题");
    println!("- NOTE: 重要说明");
    println!("- HACK: 临时解决方案");
    println!("- XXX: 警告或注意事项");
}

fn simple_calculation(x: i32) -> i32 {
    x * 2 + 5
}

/// 演示文档测试
/// 
/// 文档注释中的代码示例会被当作测试运行
/// 
/// # 示例
/// 
/// ```
/// // 这个代码会在 cargo test 时运行
/// let x = 5;
/// let y = 10;
/// assert_eq!(x + y, 15);
/// ```
fn demo_doc_tests() {
    println!("\n=== 7. 文档测试 ===");
    
    println!("文档注释中的代码示例会被测试");
    println!("运行 cargo test 会执行这些示例");
    
    println!("\n✓ 文档示例保证代码正确性");
    println!("✓ 同时提供了使用示例");
}

/*
 * ================================
 * 复杂算法示例 - 展示注释的重要性
 * ================================
 */

/// 快速排序算法
/// 
/// 使用分治法对数组进行排序
/// 
/// # 算法复杂度
/// 
/// - 时间复杂度: 平均 O(n log n), 最坏 O(n²)
/// - 空间复杂度: O(log n)
/// 
/// # 示例
/// 
/// ```
/// let mut arr = vec![3, 1, 4, 1, 5, 9, 2, 6];
/// quick_sort(&mut arr);
/// assert_eq!(arr, vec![1, 1, 2, 3, 4, 5, 6, 9]);
/// ```
fn quick_sort(arr: &mut [i32]) {
    if arr.len() <= 1 {
        return;
    }
    
    let pivot_index = partition(arr);
    
    // 递归排序左右两部分
    quick_sort(&mut arr[0..pivot_index]);
    quick_sort(&mut arr[pivot_index + 1..]);
}

/// 分区函数: 将数组分为小于和大于基准值的两部分
fn partition(arr: &mut [i32]) -> usize {
    let len = arr.len();
    let pivot = arr[len - 1]; // 选择最后一个元素作为基准
    let mut i = 0;
    
    for j in 0..len - 1 {
        if arr[j] <= pivot {
            arr.swap(i, j);
            i += 1;
        }
    }
    
    arr.swap(i, len - 1);
    i
}

/// 演示复杂代码的注释
fn demo_complex_code_comments() {
    println!("\n=== 8. 复杂代码注释示例 ===");
    
    let mut data = vec![3, 1, 4, 1, 5, 9, 2, 6];
    println!("排序前: {:?}", data);
    
    quick_sort(&mut data);
    println!("排序后: {:?}", data);
    
    println!("\n✓ 复杂算法需要详细注释");
    println!("✓ 说明算法思路和复杂度");
}

/// 主函数:运行所有示例
fn main() {
    println!("╔═══════════════════════════════════════╗");
    println!("║       Rust 学习系列 04: 注释          ║");
    println!("╚═══════════════════════════════════════╝");
    
    demo_line_comments();
    demo_block_comments();
    demo_doc_comments();
    demo_module_doc_comments();
    demo_comment_best_practices();
    demo_comment_scenarios();
    demo_doc_tests();
    demo_complex_code_comments();
    
    println!("\n╔═══════════════════════════════════════╗");
    println!("║              学习小结                 ║");
    println!("╚═══════════════════════════════════════╝");
    println!("1. 行注释: //  块注释: /* */");
    println!("2. 文档注释: /// 和 //!");
    println!("3. 文档注释支持 Markdown");
    println!("4. 注释应该解释为什么,不是做什么");
    println!("5. 使用 cargo doc 生成文档");
    
    println!("\n💡 提示: 运行 cargo doc --open 查看生成的文档");
    println!("💡 下一步: 学习 05_control_flow.rs - 流程控制");
}
