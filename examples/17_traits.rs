//! 17 - Trait特征

trait Summary {
    fn summarize(&self) -> String;
    
    // 默认实现
    fn author(&self) -> String {
        String::from("Unknown")
    }
}

struct NewsArticle {
    headline: String,
    author: String,
}

impl Summary for NewsArticle {
    fn summarize(&self) -> String {
        format!("{}, by {}", self.headline, self.author)
    }
    
    fn author(&self) -> String {
        self.author.clone()
    }
}

struct Tweet {
    username: String,
    content: String,
}

impl Summary for Tweet {
    fn summarize(&self) -> String {
        format!("{}: {}", self.username, self.content)
    }
}

fn notify(item: &impl Summary) {
    println!("新内容: {}", item.summarize());
}

fn main() {
    println!("╔══════════════════════════════════════╗");
    println!("║    Rust 学习系列 17: Trait特征       ║");
    println!("╚══════════════════════════════════════╝");
    
    let article = NewsArticle {
        headline: String::from("Rust 1.0 发布"),
        author: String::from("Mozilla"),
    };
    
    let tweet = Tweet {
        username: String::from("@rustlang"),
        content: String::from("学习Rust很棒!"),
    };
    
    println!("\n文章: {}", article.summarize());
    println!("推文: {}", tweet.summarize());
    
    notify(&article);
    notify(&tweet);
    
    println!("\n作者: {}", article.author());
    
    println!("\n💡 下一步: 学习 18_lifetimes.rs - 生命周期");
}
