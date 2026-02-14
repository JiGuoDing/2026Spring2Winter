#include <iostream>
#include <algorithm>
#include <cctype>
#include <vector>

using namespace std;

int main(int argc, char const *argv[]) {
    size_t p1, p2, p3;
    cin >> p1 >> p2 >> p3;
    // p2 = k 表示同一个字符要连续填充 k 个
    // p3 表示是否改为逆序，1 表示维持原来顺序，2 表示采用逆序
    vector<char> alphabet_lowercase({'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't','u', 'v', 'w', 'x', 'y', 'z'});
    vector<char> alphabet_uppercase({'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'});
    vector<char> digits({'0', '1', '2', '3', '4', '5', '6', '7', '8', '9'});

    string input_line;
    vector<char> output;

    cin >> input_line;
    output.emplace_back(input_line[0]); // 将第一个字符直接加入输出

    for (size_t i = 1; i < input_line.size() - 1; ++i) {
        const char &current_char = input_line[i];
        if (current_char == '-') {
            // 需要展开
            const char &prev_char = input_line[i - 1];
            const char &next_char = input_line[i + 1];

            // 判断前后是否同为字母或数字
            if (isalpha(prev_char) != isalpha(next_char) || isdigit(prev_char) != isdigit(next_char) || (prev_char >= next_char)) {
                // 不满足条件，直接加入输出
                output.emplace_back(current_char);
                continue;
            }

            if (isalpha(prev_char) && isalpha(next_char)) {

                size_t prev_index = find(alphabet_lowercase.begin(), alphabet_lowercase.end(), prev_char) - alphabet_lowercase.begin();
                size_t next_index = find(alphabet_lowercase.begin(), alphabet_lowercase.end(), next_char) - alphabet_lowercase.begin();
                
                switch (p1){
                    case 1:
                        // 对于字母子串，填写小写字母
                        if (p3 == 1){
                            // p3 = 1 表示维持原来顺序，p3 = 2 表示采用逆序
                            for (size_t j = prev_index + 1; j < next_index; ++j) {
                                for (size_t k = 0; k < p2; ++k) {
                                    output.emplace_back(alphabet_lowercase[j]);
                                }
                            }
                            
                        } else if (p3 == 2) {
                            for (size_t j = next_index - 1; j > prev_index; --j) {
                                for (size_t k = 0; k < p2; ++k) {
                                    output.emplace_back(alphabet_lowercase[j]);
                                }
                            }
                        }
                        break;
                    case 2:
                        // 对于字母子串，填写大写字母
                        if (p3 == 1) {
                            for (size_t j = prev_index + 1; j < next_index; ++j) {
                                for (size_t k = 0; k < p2; ++k) {
                                    output.emplace_back(alphabet_uppercase[j]);
                                }
                            }
                        } else if (p3 == 2) {
                            for (size_t j = next_index - 1; j > prev_index; --j) {
                                for (size_t k = 0; k < p2; ++k) {
                                    output.emplace_back(alphabet_uppercase[j]);
                                }
                            }
                        }
                        break;
                    case 3:
                        // 无论字母子串还是数字子串，都用与要填充的字母个数相同的 * 填充
                        for (size_t j = prev_index + 1; j < next_index; ++j) {
                            for (size_t k = 0; k < p2; ++k) {
                                output.emplace_back('*');
                            }
                        }
                        break;
                        default:
                        break;
                }
            } else {
                // 数字子串
                size_t prev_index = find(digits.begin(), digits.end(), prev_char) - digits.begin();
                size_t next_index = find(digits.begin(), digits.end(), next_char) - digits.begin();

                // 直接填写数字
                if (p3 == 1) {
                    if (p1 == 3) {
                        for (size_t j = prev_index + 1; j < next_index; ++j) {
                            for (size_t k = 0; k < p2; ++k) {
                                output.emplace_back('*');
                            }
                        }
                    } else {
                        for (size_t j = prev_index + 1; j < next_index; ++j) {
                            for (size_t k = 0; k < p2; ++k) {
                                output.emplace_back(digits[j]);
                            }
                        }
                    }
                } else if (p3 == 2) {
                    if (p1 == 3) {
                        for (size_t j = prev_index + 1; j < next_index; ++j) {
                            for (size_t k = 0; k < p2; ++k) {
                                output.emplace_back('*');
                            }
                        }
                    } else {
                        for (size_t j = next_index - 1; j > prev_index; --j) {
                            for (size_t k = 0; k < p2; ++k) {
                                output.emplace_back(digits[j]);
                            }
                        }
                    }
                }
            }
        }
        else {
            // 不需要展开，直接加入输出
            output.emplace_back(current_char);
        }
    }

    output.emplace_back(input_line.back()); // 将最后一个字符直接加入输出

    for (const auto& c : output) {
        cout << c;
    }

    return 0;
}
