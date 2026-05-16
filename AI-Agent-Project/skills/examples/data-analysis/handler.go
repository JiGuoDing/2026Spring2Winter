package main

import (
	"encoding/json"
	"fmt"
)

type SkillError struct {
	Code    string `json:"code"`
	Message string `json:"message"`
	Detail  string `json:"detail,omitempty"`
}

func (e *SkillError) Error() string {
	return fmt.Sprintf("[%s] %s: %s", e.Code, e.Message, e.Detail)
}

type AnalysisInput struct {
	Data       []DataRow `json:"data"`
	Operations []string  `json:"operations"`
	Column     string    `json:"column,omitempty"`
	Format     string    `json:"format,omitempty"`
}

type StatsResult struct {
	Mean   float64 `json:"mean"`
	Median float64 `json:"median"`
	StdDev float64 `json:"std_dev"`
	Min    float64 `json:"min"`
	Max    float64 `json:"max"`
	Count  int     `json:"count"`
}

type AnalysisOutput struct {
	Stats             StatsResult `json:"stats,omitempty"`
	CleanedCount      int         `json:"cleaned_count"`
	OperationsApplied []string    `json:"operations_applied"`
}

type DataAnalysisHandler struct {
	outlierThreshold float64
}

func NewDataAnalysisHandler(outlierThreshold float64) *DataAnalysisHandler {
	return &DataAnalysisHandler{outlierThreshold: outlierThreshold}
}

func (h *DataAnalysisHandler) Validate(input json.RawMessage) error {
	var in AnalysisInput
	if err := json.Unmarshal(input, &in); err != nil {
		return &SkillError{
			Code:    "INVALID_INPUT",
			Message: "无法解析输入参数",
			Detail:  err.Error(),
		}
	}

	if len(in.Data) == 0 {
		return &SkillError{
			Code:    "EMPTY_DATA",
			Message: "数据集不能为空",
		}
	}

	if len(in.Operations) == 0 {
		return &SkillError{
			Code:    "NO_OPERATIONS",
			Message: "操作列表不能为空",
		}
	}

	validOps := map[string]bool{
		"clean": true, "deduplicate": true, "fill_missing": true,
		"remove_outliers": true, "stats": true, "correlation": true,
	}
	for _, op := range in.Operations {
		if !validOps[op] {
			return &SkillError{
				Code:    "INVALID_OPERATION",
				Message: "不支持的操作",
				Detail:  fmt.Sprintf("operation=%s", op),
			}
		}
	}

	return nil
}

func (h *DataAnalysisHandler) Handle(input json.RawMessage) (json.RawMessage, error) {
	if err := h.Validate(input); err != nil {
		return nil, err
	}

	var in AnalysisInput
	_ = json.Unmarshal(input, &in)

	pipeline := NewPipeline("data-analysis")

	for _, op := range in.Operations {
		switch op {
		case "deduplicate":
			pipeline.AddStep("deduplicate", DeduplicateStep())
		case "fill_missing":
			pipeline.AddStep("fill_missing", FillMissingStep(in.Column, func() interface{} {
				return 0.0
			}))
		case "remove_outliers":
			pipeline.AddStep("remove_outliers", RemoveOutliersStep(in.Column, h.outlierThreshold))
		}
	}

	result, err := pipeline.Execute(in.Data)
	if err != nil {
		return nil, &SkillError{
			Code:    "PIPELINE_ERROR",
			Message: "数据处理管道执行失败",
			Detail:  err.Error(),
		}
	}

	output := AnalysisOutput{
		CleanedCount:      len(result),
		OperationsApplied: in.Operations,
	}

	for _, op := range in.Operations {
		if op == "stats" && in.Column != "" {
			values := extractFloatColumn(result, in.Column)
			if len(values) > 0 {
				output.Stats = StatsResult{
					Mean:   Mean(values),
					Median: Median(values),
					StdDev: StdDev(values),
					Min:    Min(values),
					Max:    Max(values),
					Count:  len(values),
				}
			}
		}
	}

	return json.Marshal(output)
}
