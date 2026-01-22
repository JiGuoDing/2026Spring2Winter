use std::io;


fn main() {
    let mut input_line2 = String::new();
    io::stdin().read_line(&mut input_line2).expect("Failed to read line");
    let mut nums = input_line2.trim().split_whitespace().map(|ch| ch.parse::<i32>().unwrap()).collect::<Vec::<i32>>();

    nums.remove(nums.len()-1);
    for &num in nums.iter().rev() {
        print!("{} ", num);
    }
}