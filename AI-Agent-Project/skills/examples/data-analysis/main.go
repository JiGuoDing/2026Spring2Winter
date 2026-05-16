package main

import (
	"encoding/json"
	"fmt"
)

func main() {
	handler := NewDataAnalysisHandler(3.0)

	input := AnalysisInput{
		Data: []DataRow{
			{"value": 10.0, "name": "a"},
			{"value": 20.0, "name": "b"},
			{"value": 30.0, "name": "c"},
			{"value": 10.0, "name": "a"},
			{"value": 500.0, "name": "outlier"},
		},
		Operations: []string{"deduplicate", "remove_outliers", "stats"},
		Column:     "value",
	}

	inputJSON, _ := json.Marshal(input)
	outputJSON, err := handler.Handle(inputJSON)

	if err != nil {
		fmt.Printf("❌ 分析失败: %v\n", err)
		return
	}

	var output AnalysisOutput
	_ = json.Unmarshal(outputJSON, &output)

	fmt.Printf("✅ 数据分析完成\n")
	fmt.Printf("   清洗后数据条数: %d\n", output.CleanedCount)
	fmt.Printf("   执行操作: %v\n", output.OperationsApplied)
	if output.Stats.Count > 0 {
		fmt.Printf("   统计结果:\n")
		fmt.Printf("     均值: %.2f\n", output.Stats.Mean)
		fmt.Printf("     中位数: %.2f\n", output.Stats.Median)
		fmt.Printf("     标准差: %.2f\n", output.Stats.StdDev)
		fmt.Printf("     最小值: %.2f\n", output.Stats.Min)
		fmt.Printf("     最大值: %.2f\n", output.Stats.Max)
		fmt.Printf("     数据量: %d\n", output.Stats.Count)
	}
}
