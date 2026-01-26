use std::io::{self, Read};

fn main() {
    // Read all input
    let mut s = String::new();
    io::stdin().read_to_string(&mut s).unwrap();
    let mut it = s.split_whitespace();

    let w: usize = it.next().unwrap().parse().unwrap();
    let x: usize = it.next().unwrap().parse().unwrap();
    let h: usize = it.next().unwrap().parse().unwrap();

    let q: usize = it.next().unwrap().parse().unwrap();

    // true = still solid, false = removed
    let mut solid = vec![true; w * x * h];

    let idx = |i: usize, j: usize, k: usize, w: usize, x: usize| -> usize {
        // i in [0,w), j in [0,x), k in [0,h)
        (k * x + j) * w + i
    };

    for _ in 0..q {
        let x1: usize = it.next().unwrap().parse().unwrap();
        let y1: usize = it.next().unwrap().parse().unwrap();
        let z1: usize = it.next().unwrap().parse().unwrap();
        let x2: usize = it.next().unwrap().parse().unwrap();
        let y2: usize = it.next().unwrap().parse().unwrap();
        let z2: usize = it.next().unwrap().parse().unwrap();

        // convert to 0-based inclusive ranges
        for k in (z1 - 1)..= (z2 - 1) {
            for j in (y1 - 1)..= (y2 - 1) {
                for i in (x1 - 1)..= (x2 - 1) {
                    solid[idx(i, j, k, w, x)] = false;
                }
            }
        }
    }

    let remaining = solid.iter().filter(|&&b| b).count();
    println!("{}", remaining);
}
