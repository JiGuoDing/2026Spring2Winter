//! 18 - 生命周期

fn longest<'a>(x: &'a str, y: &'a str) -> &'a str {
    if x.len() > y.len() {
        x
    } else {
        y
    }
}

struct ImportantExcerpt<'a> {
    part: &'a str,
}

impl<'a> ImportantExcerpt<'a> {
    fn level(&self) -> i32 {
        3
    }
    
    fn announce_and_return_part(&self, announcement: &str) -> &str {
        println!("注意: {}", announcement);
        self.part
    }
}

fn main() {
    println!("╔══════════════════════════════════════╗");
    println!("║    Rust 学习系列 18: 生命周期        ║");
    println!("╚══════════════════════════════════════╝");
    
    // 生命周期标注
    let string1 = String::from("long string");
    let string2 = "short";
    
    let result = longest(string1.as_str(), string2);
    println!("\n最长字符串: {}", result);
    
    // 结构体生命周期
    let novel = String::from("Call me Ishmael. Some years ago...");
    let first_sentence = novel.split('.').next().expect("找不到'.'");
    
    let excerpt = ImportantExcerpt {
        part: first_sentence,
    };
    
    println!("\n摘录: {}", excerpt.part);
    println!("级别: {}", excerpt.level());
    
    let announcement = "今日推荐";
    let part = excerpt.announce_and_return_part(announcement);
    println!("部分: {}", part);
    
    // 静态生命周期
    let s: &'static str = "我有静态生命周期";
    println!("\n{}", s);
    
    println!("\n💡 下一步: 学习 19_modules.rs - 包和模块");
}
