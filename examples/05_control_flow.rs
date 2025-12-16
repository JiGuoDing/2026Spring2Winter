//! # 05 - 流程控制
//!
//! ## 学习目标
//! - 掌握 if 表达式的使用
//! - 掌握三种循环结构(loop、while、for)
//! - 理解循环标签和跳出机制
//! - 理解 if 作为表达式的特性

/*
 * ================================
 * 核心概念说明
 * ================================
 * 
 * Rust 的控制流:
 * 1. if 表达式: 条件分支
 * 2. loop: 无限循环
 * 3. while: 条件循环
 * 4. for: 遍历循环
 * 
 * 特点:
 * - if 是表达式,可以返回值
 * - 循环可以返回值
 * - 支持循环标签
 */

/// 演示 if 表达式
fn demo_if_expressions() {
    println!("\n=== 1. if 表达式 ===");
    
    let number = 7;
    
    // 基本 if 表达式
    if number < 5 {
        println!("{} 小于 5", number);
    } else {
        println!("{} 大于等于 5", number);
    }
    
    // else if 分支
    let score = 85;
    if score >= 90 {
        println!("成绩: 优秀");
    } else if score >= 80 {
        println!("成绩: 良好");
    } else if score >= 60 {
        println!("成绩: 及格");
    } else {
        println!("成绩: 不及格");
    }
    
    // 多个条件
    let age = 25;
    let has_license = true;
    
    if age >= 18 && has_license {
        println!("可以开车");
    } else {
        println!("不能开车");
    }
    
    println!("\n✓ if 条件不需要括号");
    println!("✓ 代码块需要花括号");
    println!("✓ 条件必须是 bool 类型");
}

/// 演示 if 作为表达式
fn demo_if_as_expression() {
    println!("\n=== 2. if 作为表达式 ===");
    
    let condition = true;
    
    // if 可以赋值给变量
    let number = if condition { 5 } else { 6 };
    println!("number = {}", number);
    
    // 三元运算符的替代
    let x = 10;
    let result = if x > 5 { "大" } else { "小" };
    println!("x 是 {}", result);
    
    // 复杂的条件表达式
    let score = 75;
    let grade = if score >= 90 {
        'A'
    } else if score >= 80 {
        'B'
    } else if score >= 70 {
        'C'
    } else if score >= 60 {
        'D'
    } else {
        'F'
    };
    println!("分数 {} 对应等级 {}", score, grade);
    
    // 注意: if 和 else 分支必须返回相同类型
    // let bad = if condition { 5 } else { "six" }; // 错误!
    
    println!("\n✓ if 是表达式,可以返回值");
    println!("✓ 所有分支必须返回相同类型");
}

/// 演示 loop 循环
fn demo_loop() {
    println!("\n=== 3. loop 无限循环 ===");
    
    // 基本 loop
    let mut counter = 0;
    loop {
        counter += 1;
        println!("计数: {}", counter);
        
        if counter >= 3 {
            break;  // 跳出循环
        }
    }
    
    // loop 可以返回值
    let mut count = 0;
    let result = loop {
        count += 1;
        
        if count == 10 {
            break count * 2;  // 返回值
        }
    };
    println!("loop 返回值: {}", result);
    
    println!("\n✓ loop 创建无限循环");
    println!("✓ 使用 break 退出循环");
    println!("✓ break 可以返回值");
}

/// 演示 while 循环
fn demo_while() {
    println!("\n=== 4. while 条件循环 ===");
    
    // 基本 while 循环
    let mut number = 3;
    while number != 0 {
        println!("倒计时: {}!", number);
        number -= 1;
    }
    println!("发射!");
    
    // while 条件判断
    let mut count = 0;
    while count < 5 {
        println!("count = {}", count);
        count += 1;
    }
    
    // 使用 while 遍历(不推荐)
    let a = [10, 20, 30, 40, 50];
    let mut index = 0;
    
    println!("\n使用 while 遍历数组:");
    while index < a.len() {
        println!("值: {}", a[index]);
        index += 1;
    }
    
    println!("\n✓ while 在条件为 true 时循环");
    println!("✓ 条件为 false 时自动退出");
}

/// 演示 for 循环
fn demo_for() {
    println!("\n=== 5. for 遍历循环 ===");
    
    // 遍历数组
    let numbers = [10, 20, 30, 40, 50];
    println!("遍历数组:");
    for element in numbers {
        println!("值: {}", element);
    }
    
    // 遍历 Range
    println!("\n使用 Range:");
    for i in 1..5 {  // 1 到 4 (不包含 5)
        println!("i = {}", i);
    }
    
    println!("\n使用包含结束的 Range:");
    for i in 1..=5 {  // 1 to 5 (包含 5)
        println!("i = {}", i);
    }
    
    // 反向遍历
    println!("\n反向遍历:");
    for i in (1..=5).rev() {
        println!("倒计时: {}", i);
    }
    
    // 遍历带索引
    println!("\n遍历带索引:");
    let names = ["Alice", "Bob", "Carol"];
    for (index, name) in names.iter().enumerate() {
        println!("{}: {}", index, name);
    }
    
    println!("\n✓ for 是最常用的循环方式");
    println!("✓ 遍历安全,不会越界");
    println!("✓ 使用 .. 或 ..= 创建范围");
}

/// 演示循环控制: break 和 continue
fn demo_loop_control() {
    println!("\n=== 6. 循环控制: break 和 continue ===");
    
    // break: 退出循环
    println!("使用 break:");
    for i in 1..10 {
        if i == 5 {
            println!("遇到 5,退出循环");
            break;
        }
        println!("i = {}", i);
    }
    
    // continue: 跳过当前迭代
    println!("\n使用 continue:");
    for i in 1..10 {
        if i % 2 == 0 {
            continue;  // 跳过偶数
        }
        println!("奇数: {}", i);
    }
    
    println!("\n✓ break 退出整个循环");
    println!("✓ continue 跳过当前迭代");
}

/// 演示循环标签
fn demo_loop_labels() {
    println!("\n=== 7. 循环标签 ===");
    
    let mut count = 0;
    
    // 外层循环标签
    'outer: loop {
        println!("外层循环 count = {}", count);
        let mut remaining = 10;
        
        // 内层循环
        loop {
            println!("  内层循环 remaining = {}", remaining);
            
            if remaining == 7 {
                break;  // 只退出内层循环
            }
            
            if count == 2 {
                break 'outer;  // 退出外层循环
            }
            
            remaining -= 1;
        }
        
        count += 1;
    }
    
    println!("循环结束");
    
    // 嵌套循环示例
    println!("\n嵌套循环查找:");
    'search: for i in 1..=5 {
        for j in 1..=5 {
            if i * j > 10 {
                println!("找到: {} * {} = {}", i, j, i * j);
                break 'search;  // 退出外层循环
            }
        }
    }
    
    println!("\n✓ 使用标签区分多层循环");
    println!("✓ 标签以单引号开头");
}

/// 演示实际应用场景
fn demo_practical_examples() {
    println!("\n=== 8. 实际应用场景 ===");
    
    // 场景1: 查找元素
    let numbers = vec![1, 3, 5, 7, 9, 11];
    let target = 7;
    let mut found = false;
    
    for (index, &num) in numbers.iter().enumerate() {
        if num == target {
            println!("找到 {} 在索引 {}", target, index);
            found = true;
            break;
        }
    }
    
    if !found {
        println!("{} 不在数组中", target);
    }
    
    // 场景2: 计算总和
    let scores = vec![85, 92, 78, 95, 88];
    let mut total = 0;
    
    for score in &scores {
        total += score;
    }
    
    let average = total / scores.len() as i32;
    println!("\n总分: {}, 平均分: {}", total, average);
    
    // 场景3: 过滤和收集
    println!("\n偶数:");
    for num in 1..=10 {
        if num % 2 == 0 {
            print!("{} ", num);
        }
    }
    println!();
    
    // 场景4: 九九乘法表
    println!("\n九九乘法表:");
    for i in 1..=9 {
        for j in 1..=i {
            print!("{} × {} = {}\t", j, i, i * j);
        }
        println!();
    }
}

/// 演示常见模式
fn demo_common_patterns() {
    println!("\n=== 9. 常见循环模式 ===");
    
    // 模式1: 累加器
    let mut sum = 0;
    for i in 1..=100 {
        sum += i;
    }
    println!("1 到 100 的和: {}", sum);
    
    // 模式2: 计数器
    let data = vec![1, 2, 3, 4, 5, 6, 7, 8, 9];
    let mut even_count = 0;
    for &num in &data {
        if num % 2 == 0 {
            even_count += 1;
        }
    }
    println!("偶数个数: {}", even_count);
    
    // 模式3: 查找最大值
    let numbers = vec![23, 56, 12, 89, 34, 67];
    let mut max = numbers[0];
    for &num in &numbers {
        if num > max {
            max = num;
        }
    }
    println!("最大值: {}", max);
    
    // 模式4: 条件退出
    let mut attempts = 0;
    let max_attempts = 5;
    let target = 7;
    
    loop {
        attempts += 1;
        println!("尝试 #{}", attempts);
        
        // 模拟某种检查
        if attempts == target {
            println!("成功!");
            break;
        }
        
        if attempts >= max_attempts {
            println!("达到最大尝试次数");
            break;
        }
    }
}

/// 常见陷阱和最佳实践
fn demo_common_pitfalls() {
    println!("\n=== 10. 常见陷阱和最佳实践 ===");
    
    // 陷阱1: 无限循环
    println!("\n陷阱1: 注意循环终止条件");
    let mut count = 0;
    while count < 3 {
        println!("count = {}", count);
        count += 1;  // 别忘了更新条件!
    }
    
    // 陷阱2: 循环中修改索引
    println!("\n陷阱2: for 比 while 更安全");
    let arr = [1, 2, 3, 4, 5];
    // 推荐使用 for
    for element in arr {
        println!("{}", element);
    }
    
    // 最佳实践: 优先使用 for
    println!("\n最佳实践:");
    println!("✓ 优先使用 for 循环");
    println!("✓ 需要无限循环时使用 loop");
    println!("✓ 循环标签用于复杂嵌套");
    println!("✓ 避免在循环中做太多工作");
}

/// 主函数:运行所有示例
fn main() {
    println!("╔═══════════════════════════════════════╗");
    println!("║     Rust 学习系列 05: 流程控制        ║");
    println!("╚═══════════════════════════════════════╝");
    
    demo_if_expressions();
    demo_if_as_expression();
    demo_loop();
    demo_while();
    demo_for();
    demo_loop_control();
    demo_loop_labels();
    demo_practical_examples();
    demo_common_patterns();
    demo_common_pitfalls();
    
    println!("\n╔═══════════════════════════════════════╗");
    println!("║              学习小结                 ║");
    println!("╚═══════════════════════════════════════╝");
    println!("1. if 是表达式,可以返回值");
    println!("2. loop 无限循环,while 条件循环,for 遍历循环");
    println!("3. break 退出循环,continue 跳过当前迭代");
    println!("4. 循环标签用于嵌套循环控制");
    println!("5. 优先使用 for 循环,更安全");
    
    println!("\n💡 下一步: 学习 06_ownership.rs - 所有权系统");
}
