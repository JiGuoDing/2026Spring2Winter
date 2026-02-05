#include <iostream>
#include <vector>
#include <cmath>
#include <map>

using namespace std;

int main(int argc, const char **argv) {
    size_t n, t, a_z;
    double a;
    std::cin >> n;

    // 位置，状态
    map<size_t, bool> lights;

    for (size_t i = 0; i < n; ++i) {
        std::cin >> a >> t;

        for (size_t j = 1; j <= t; ++j) {
            a_z = floor(a * j);
            // 如果这个灯已经被操作过了
            if (lights.count(a_z))
                lights.at(a_z) = !lights.at(a_z);
            else
                lights.insert(make_pair(a_z, true));
        }
    }

    for (auto &light : lights) {
        if (light.second) {
            std::cout << light.first;
            break;
        }
    }

    return 0;
}