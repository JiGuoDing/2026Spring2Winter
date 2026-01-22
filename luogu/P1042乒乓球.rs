use std::io::{self, BufRead};

fn main() {
    let stdin = io::stdin();
    let mut records: Vec<char> = Vec::new();

    // 先把所有有效字符收集到 records，直到遇到 'E'
    'outer: for line in stdin.lock().lines() {
        let line = line.unwrap();
        for ch in line.chars() {
            if ch == 'W' || ch == 'L' {
                records.push(ch);
            } else if ch == 'E' {
                records.push('E');
                break 'outer;
            }
        }
    }

    // 再用你的逻辑处理 records
    let mut score_1: i32 = 0;
    let mut score_2: i32 = 0;

    for &record in records.iter() {
        if record == 'W' {
            score_1 += 1;
        } else if record == 'L' {
            score_2 += 1;
        } else {
            break; // 'E'
        }

        if (score_1 >= 11 || score_2 >= 11) && (score_1 - score_2).abs() >= 2 {
            println!("{}:{}", score_1, score_2);
            score_1 = 0;
            score_2 = 0;
        }
    }
    println!("{}:{}", score_1, score_2);
    println!("");
    score_1 = 0;
    score_2 = 0;

    for &record in records.iter() {
        if record == 'W' {
            score_1 += 1;
        } else if record == 'L' {
            score_2 += 1;
        } else {
            break; // 'E'
        }

        if (score_1 >= 21 || score_2 >= 21) && (score_1 - score_2).abs() >= 2 {
            println!("{}:{}", score_1, score_2);
            score_1 = 0;
            score_2 = 0;
        }
    }
    println!("{}:{}", score_1, score_2);

}
