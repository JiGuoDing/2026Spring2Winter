#include <cstddef>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

using namespace std;

int main(int argc, const char** argv) {
    size_t n;
    cin >> n;
    vector<int> coefficients(n+1, 0);
    string result;

    for (size_t j = 0; j <= n; ++j) {
        cin >> coefficients[j];
    }


    for (int i = 0; i <= n; ++i) {
        int coefficient = coefficients[i];
        int abs_coefficient = abs(coefficient);
        if (coefficient == 0)
            continue;

        if (coefficient < 0) {
            if (abs_coefficient == 1) {

            }
            result.append("-");
            result.append(to_string(abs_coefficient));
        } else {
            if (abs_coefficient == 1) {
                
            }
            if (i != 0)
                result.append("+");
            result.append(to_string(coefficient));
        }

        if (i != n) {
            result.append("x");
            result.append("^");   
            result.append(to_string(n-i));
        }
    }

    cout << result << endl;
    return 0;
}