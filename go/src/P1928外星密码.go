package src

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"
)

// 将一个字符串解析为数字加普通字符串
// 例如 "3FUN" 解析为 (3, "FUN")
func ParseString(str string) (int, string, error) {
	splitIdx := len(str)

	// 1. 寻找切割点
	for i, r := range str {
		// 如果字符不是 '0' 到 '9' 之间的数字
		if r < '0' || r > '9' {
			splitIdx = i
			break
		}
	}

	// 2. 字符串切片提取
	numStr := str[:splitIdx]
	subStr := str[splitIdx:]

	// 3. 边界情况，如果没有数字
	if numStr == "" {
		return 1, subStr, nil
	}

	// 4. 将数字部分转为 int
	num, err := strconv.Atoi(numStr)
	if err != nil {
		return 0, subStr, err
	}

	return num, subStr, nil
}

// 解压被压缩的字符串，例如 [3FUN] 解压为 FUNFUNFUN
// 每调用一次 unzip 展开一层
func unzipStr(zippedStr string) string {
	num, str, err := ParseString(zippedStr)
	if err != nil {
		fmt.Println(err)
		return str
	}

	var unzippedStr string
	for i := 0; i < num; i++ {
		unzippedStr += str
	}
	return unzippedStr
}

// 方法二：递归解析
var idx int
var globZippedStr string

func Parse() string {
	var res string
	for _, ch := range globZippedStr {
		switch ch {
		case '[':
			idx++
			// 提取数字
			num := 0
			for idx < len(globZippedStr) && globZippedStr[idx] >= '0' && globZippedStr[idx] <= '9' {
				num = num*10 + int(globZippedStr[idx]-'0')
				idx++
			}

			// 递归调用 Parse()，获取括号内部解析好的字符串
			// 不论里面嵌套多少压缩的字符串，返回最终的字符串
			innerStr := Parse()
			// 将内部字符串重复 num 次，拼接到当前结果中
			res += strings.Repeat(innerStr, num)
		case ']':
			// 遇到 "]" 说明当前这一层的括号结束了
			idx++
			// 将当前层解析的结果返回给上一层
			return res
		default:
			// 普通字符，直接拼接
			res += string(ch)
			idx++
		}
	}

	return res
}

func P1928() {
	reader := bufio.NewReaderSize(os.Stdin, 1<<20)
	writer := bufio.NewWriterSize(os.Stdout, 1<<20)
	defer writer.Flush()

	var zippedStr string
	fmt.Fscan(reader, &zippedStr)

	// 只要字符串中还有 "["，就说吗还需要解压 (就像剥洋葱一样，从内而外解压缩)
	for strings.Contains(zippedStr, "[") {
		// 找到最后一个 [ 的位置 (这保证了它是最内层的左括号)
		lastLeftIdx := strings.LastIndex(zippedStr, "[")
		// 找到与最后一个 [ 对应的 ] 的位置
		// rightOffset 是相对于 lastLeftIdx 的偏移量
		rightOffset := strings.Index(zippedStr[lastLeftIdx:], "]")
		rightIdx := lastLeftIdx + rightOffset

		// 提取最内层括号里的内容
		innerStr := zippedStr[lastLeftIdx+1 : rightIdx]
		unzippedStr := unzipStr(innerStr)

		zippedStr = zippedStr[:lastLeftIdx] + unzippedStr + zippedStr[rightIdx+1:]
	}

	fmt.Fprintln(writer, zippedStr)
}
