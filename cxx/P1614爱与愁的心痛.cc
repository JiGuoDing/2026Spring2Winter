#include <iostream>
#include <vector>


size_t prefix_sum(const std::vector<int>& a, size_t i){
    size_t sum = 0;
    for(size_t j = 0; j < i; j++){
        sum += a[j];
    }
    return sum;
}

int main(){
    size_t n, m;
    std::cin >> n >> m;
    std::vector<int> a(n, 0);
    for(size_t i = 0; i < n; i++){
        std::cin >> a[i];
    }

    size_t min_sum = prefix_sum(a, m);

    size_t last_sum = min_sum;
    for (size_t i = 0; i < n - m; i++) {
        if (last_sum - a[i] + a[i + m] < min_sum) {
            min_sum = last_sum - a[i] + a[i + m];
        }
        last_sum = last_sum - a[i] + a[i + m];
    }

    std::cout << min_sum << std::endl;

    return 0;
}