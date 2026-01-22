use std::io;


fn main() {
    let mut input_line1 = String::new();
    io::stdin().read_line(&mut input_line1).expect("Failed to read line");

    let mut input_line2 = String::new();
    io::stdin().read_line(&mut input_line2).expect("Failed to read line");
    let nums = input_line2.trim().split_whitespace().map(|ch| ch.parse::<i32>().unwrap()).collect::<Vec::<i32>>();

    print!("{} ", 0);
    for i in 1..nums.len() {
        let mut cnt = 0;
        for j in 0..i {
            if nums[i] > nums[j] {
                cnt += 1;
            }
        }
        print!("{} ", cnt);
    }
}