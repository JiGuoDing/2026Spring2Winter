// package interviewIssue 存放面试算法题的解法和工具函数。
//
// 本文件实现了一个灵活的JSON解析器，用于处理值类型不确定的JSON字符串。
// 核心挑战：Go标准库的json.Unmarshal要求目标类型在编译期确定，
// 而本题中JSON值的类型（int/string/[]int/struct）在运行时才能知晓。
//
// 设计思路：
//  1. 第一趟解析：将整个JSON反序列化为 map[string]json.RawMessage，
//     拿到外层键名，同时保留值的原始JSON字节，暂不解析具体类型。
//  2. 第二趟解析：检查原始JSON的首字节，根据JSON语法的确定性特征分派：
//     - '"' → 字符串
//     - '[' → 数组
//     - '{' → 对象
//     - 其他（数字、负号）→ 整型
//     这种方式比"依次尝试每种类型的Unmarshal直到成功"更高效，也更精确。
package interviewIssue

import (
	"encoding/json"
	"fmt"
)

// ParseFlexibleJSON 解析一个包含不确定类型值的JSON字符串。
//
// 输入约束：
//   - jsonStr 必须是一个合法的JSON对象字符串
//   - 该对象必须包含恰好一个键值对
//   - 键必须是字符串类型（JSON标准要求）
//   - 值必须是以下四种类型之一：
//
// 支持的值类型及其Go映射：
//
//   JSON值                Go类型           示例
//   ─────────────────────────────────────────────
//   整型数字              int              25
//   字符串                string           "hello"
//   整型数组              []int            [1, 2, 3]
//   单键值对对象          map[string]int   {"id": 100}
//
// 参数：
//   - jsonStr: 待解析的JSON字符串，如 `{"age": 25}`
//
// 返回值：
//   - key:   JSON对象中的键名，如 "age"
//   - value: 解析后的值，具体类型为 int / string / []int / map[string]int 之一
//   - err:   解析失败时返回错误，成功时为 nil
//
// 错误场景：
//   - 输入不是合法的JSON格式（如缺少引号、多余的逗号等）
//   - 顶层对象包含0个或多个键值对（而非恰好1个）
//   - 嵌套结构体包含0个或多个键值对（而非恰好1个）
//   - 数组元素不是整型（如包含字符串或浮点数）
//   - 数字不是整型（如浮点数 12.5）
//
// 使用示例：
//
//	k, v, err := ParseFlexibleJSON(`{"score": 95}`)
//	// k = "score", v = 95 (int)
//
//	k, v, err = ParseFlexibleJSON(`{"data": [1, 2, 3]}`)
//	// k = "data", v = []int{1, 2, 3}
func ParseFlexibleJSON(jsonStr string) (key string, value any, err error) {
	// ── 第一趟解析：分离键名与原始值 ──
	// json.RawMessage 是 []byte 的别名，实现了 json.Unmarshaler 接口。
	// 当Unmarshal的目标类型包含 json.RawMessage 字段时，该字段会保留原始的JSON字节，
	// 不做任何类型转换。这让我们可以"延迟"对值的解析，等到确定类型后再处理。
	//
	// 为什么不直接用 map[string]any？
	//   json.Unmarshal 到 map[string]any 时，Go会自动推断类型：
	//   - JSON数字 → float64（这是个大坑，整数会变成浮点）
	//   - JSON数组 → []interface{}
	//   - JSON对象 → map[string]interface{}
	//   这种自动推断不仅丢失了"这是整数"的语义，还要求我们对 []interface{}
	//   再做一次类型断言循环，代码更啰嗦。
	var raw map[string]json.RawMessage
	if err := json.Unmarshal([]byte(jsonStr), &raw); err != nil {
		return "", nil, fmt.Errorf("JSON解析失败: %w", err)
	}

	// ── 校验：恰好一个键值对 ──
	// 根据题目要求，顶层JSON对象只能有一个键值对。
	// raw 的类型是 map，len(raw)==0 表示空对象 {}，
	// len(raw)>=2 表示多余键值对，这两种情况都应该报错。
	if len(raw) != 1 {
		return "", nil, fmt.Errorf("期望恰好一个键值对，实际有 %d 个", len(raw))
	}

	// ── 提取唯一的键值对 ──
	// 由于map只有一个元素，range循环只会执行一次。
	// 这是Go中从单元素map取值的惯用写法。
	for k, v := range raw {
		parsed, parseErr := parseValue(v)
		if parseErr != nil {
			return "", nil, parseErr
		}
		return k, parsed, nil
	}

	// 这行代码理论上不可达（空map已被len检查拦截），
	// 保留作为防御性编程的安全网。
	return "", nil, fmt.Errorf("意外的空JSON对象")
}

// parseValue 根据原始JSON的首字节判断值类型，然后反序列化为对应的Go类型。
//
// 设计原理——为什么用首字节分派而不是依次尝试？
//
//   JSON的语法规则保证了每种值类型有唯一的前缀字符：
//     "..."  → 字符串（首字节必为双引号）
//     [...]  → 数组（首字节必为左方括号）
//     {...}  → 对象（首字节必为左花括号）
//     数字   → 数字字符 '0'-'9' 或负号 '-'
//
//   这个特性是JSON RFC 7159 的确定性保证，不是巧合。
//   因此只需读取 raw[0] 即可100%确定值类型，无需尝试-失败-重试。
//
//   依次尝试的做法（先unmarshal到int，失败再试string...）有两个问题：
//     1. 性能浪费：每次失败的Unmarshal都会走完整的反射路径
//     2. 歧义风险：如 json.Unmarshal([]byte("123"), &str) 在Go中会失败，
//        但如果将目标设为interface{}则会成功但得到float64——类型判断逻辑会变复杂
//
// 参数：
//   - raw: 值的原始JSON字节（不含外层键名），如 []byte(`25`) 或 []byte(`"hello"`)
//
// 返回值：
//   - 解析后的Go值，类型为 int / string / []int / map[string]int 之一
//   - 解析失败时返回错误
func parseValue(raw json.RawMessage) (any, error) {
	// 防御性检查：理论上不会出现长度为0的情况
	// （合法的JSON对象值至少有一个字符），但保留此检查以防边界情况。
	if len(raw) == 0 {
		return nil, fmt.Errorf("值为空")
	}

	// 根据首字节分派到对应的解析分支
	switch raw[0] {
	case '"':
		// ── 分支一：JSON字符串 ──
		// 示例输入: "hello world"
		// Go的json.Unmarshal会正确处理转义字符（如 \"、\\、\n 等），
		// 将JSON字符串转换为Go的原生string。
		// 注意：只有用双引号包裹的才是JSON字符串，数字不会被归入此分支。
		var s string
		if err := json.Unmarshal(raw, &s); err != nil {
			return nil, fmt.Errorf("字符串解析失败: %w", err)
		}
		return s, nil

	case '[':
		// ── 分支二：JSON数组（整型切片） ──
		// 示例输入: [1, 2, 3]
		// 由于题目要求切片元素必须是整型，我们直接反序列化为 []int。
		// 如果数组中包含非整型元素（如字符串、浮点数、嵌套数组），
		// json.Unmarshal 会因为类型不匹配而返回错误，这正是我们期望的行为。
		// 空数组 [] 会被解析为 []int{}（非nil的空切片），是合法的。
		var arr []int
		if err := json.Unmarshal(raw, &arr); err != nil {
			return nil, fmt.Errorf("整型切片解析失败: %w", err)
		}
		return arr, nil

	case '{':
		// ── 分支三：JSON对象（单键值对结构体） ──
		// 示例输入: {"id": 100}
		// 题目要求嵌套结构体包含恰好一个键值对，且值必须是整型。
		// 我们将其解析为 map[string]int，然后校验长度是否为1。
		//
		// 为什么用 map[string]int 而不是定义struct？
		//   因为键名是运行时动态的（如 "id"、"age"、任意字符串），
		//   Go的struct字段名必须在编译期确定，无法应对动态键名。
		//   map[string]int 可以接受任意字符串键，完美匹配需求。
		var m map[string]int
		if err := json.Unmarshal(raw, &m); err != nil {
			return nil, fmt.Errorf("结构体解析失败: %w", err)
		}
		// 额外校验：嵌套结构体也必须恰好包含一个键值对
		if len(m) != 1 {
			return nil, fmt.Errorf("嵌套结构体期望恰好一个键值对，实际有 %d 个", len(m))
		}
		return m, nil

	default:
		// ── 分支四：JSON数字（整型） ──
		// 示例输入: 25, -10, 0
		// 首字节为 '0'-'9' 或 '-' 的数字落入此分支。
		//
		// 注意：Go的json.Unmarshal将JSON数字解析到int目标时，
		// 如果数字包含小数点（如 12.5）或科学计数法（如 1e5），
		// 会因为无法无损转为int而报错，这恰好满足了"值必须是整型"的约束。
		//
		// 为什么不使用 json.Number？
		//   json.Number 可以接受任意精度的数字（包括浮点数），
		//   但它只是一个字符串包装，调用方还需要自己决定转为 int64 还是 float64。
		//   题目明确要求值是整型，直接用 int 更简洁，类型信息也更精确。
		var n int
		if err := json.Unmarshal(raw, &n); err != nil {
			return nil, fmt.Errorf("整型解析失败: %w", err)
		}
		return n, nil
	}
}
