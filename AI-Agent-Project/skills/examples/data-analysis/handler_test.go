package main

import (
	"encoding/json"
	"errors"
	"testing"
)

func TestDataAnalysisHandler_Validate(t *testing.T) {
	handler := NewDataAnalysisHandler(3.0)

	tests := []struct {
		name    string
		input   string
		wantErr bool
		errCode string
	}{
		{
			name:    "有效输入",
			input:   `{"data":[{"value":1},{"value":2}],"operations":["stats"],"column":"value"}`,
			wantErr: false,
		},
		{
			name:    "空数据集",
			input:   `{"data":[],"operations":["stats"]}`,
			wantErr: true,
			errCode: "EMPTY_DATA",
		},
		{
			name:    "空操作列表",
			input:   `{"data":[{"value":1}],"operations":[]}`,
			wantErr: true,
			errCode: "NO_OPERATIONS",
		},
		{
			name:    "无效操作",
			input:   `{"data":[{"value":1}],"operations":["predict"]}`,
			wantErr: true,
			errCode: "INVALID_OPERATION",
		},
		{
			name:    "无效JSON",
			input:   `{invalid}`,
			wantErr: true,
			errCode: "INVALID_INPUT",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := handler.Validate(json.RawMessage(tt.input))
			if tt.wantErr {
				if err == nil {
					t.Fatal("期望错误，但未返回")
				}
				var skillErr *SkillError
				if errors.As(err, &skillErr) && skillErr.Code != tt.errCode {
					t.Errorf("错误码 = %s, 期望 %s", skillErr.Code, tt.errCode)
				}
				return
			}
			if err != nil {
				t.Errorf("未期望错误: %v", err)
			}
		})
	}
}

func TestDataAnalysisHandler_Handle_Deduplicate(t *testing.T) {
	handler := NewDataAnalysisHandler(3.0)

	input, _ := json.Marshal(AnalysisInput{
		Data: []DataRow{
			{"value": 10.0, "name": "a"},
			{"value": 20.0, "name": "b"},
			{"value": 10.0, "name": "a"},
		},
		Operations: []string{"deduplicate"},
	})

	outputJSON, err := handler.Handle(input)
	if err != nil {
		t.Fatalf("Handle() error = %v", err)
	}

	var output AnalysisOutput
	_ = json.Unmarshal(outputJSON, &output)

	if output.CleanedCount != 2 {
		t.Errorf("去重后数量 = %d, 期望 2", output.CleanedCount)
	}
}

func TestDataAnalysisHandler_Handle_Stats(t *testing.T) {
	handler := NewDataAnalysisHandler(3.0)

	input, _ := json.Marshal(AnalysisInput{
		Data: []DataRow{
			{"value": 10.0},
			{"value": 20.0},
			{"value": 30.0},
			{"value": 40.0},
			{"value": 50.0},
		},
		Operations: []string{"stats"},
		Column:     "value",
	})

	outputJSON, err := handler.Handle(input)
	if err != nil {
		t.Fatalf("Handle() error = %v", err)
	}

	var output AnalysisOutput
	_ = json.Unmarshal(outputJSON, &output)

	if output.Stats.Count != 5 {
		t.Errorf("Count = %d, 期望 5", output.Stats.Count)
	}
	if output.Stats.Mean != 30.0 {
		t.Errorf("Mean = %f, 期望 30.0", output.Stats.Mean)
	}
	if output.Stats.Median != 30.0 {
		t.Errorf("Median = %f, 期望 30.0", output.Stats.Median)
	}
	if output.Stats.Min != 10.0 {
		t.Errorf("Min = %f, 期望 10.0", output.Stats.Min)
	}
	if output.Stats.Max != 50.0 {
		t.Errorf("Max = %f, 期望 50.0", output.Stats.Max)
	}
}

func TestStats(t *testing.T) {
	values := []float64{2, 4, 4, 4, 5, 5, 7, 9}

	if m := Mean(values); m != 5.0 {
		t.Errorf("Mean = %f, 期望 5.0", m)
	}

	if m := Median(values); m != 4.5 {
		t.Errorf("Median = %f, 期望 4.5", m)
	}

	if m := Min(values); m != 2.0 {
		t.Errorf("Min = %f, 期望 2.0", m)
	}

	if m := Max(values); m != 9.0 {
		t.Errorf("Max = %f, 期望 9.0", m)
	}
}

func TestCorrelation(t *testing.T) {
	x := []float64{1, 2, 3, 4, 5}
	y := []float64{2, 4, 6, 8, 10}

	corr := Correlation(x, y)
	if corr < 0.99 {
		t.Errorf("Correlation = %f, 期望接近 1.0", corr)
	}
}

func TestRemoveOutliers(t *testing.T) {
	values := []float64{1, 2, 3, 4, 5, 100}

	cleaned := RemoveOutliers(values, 3.0)
	if len(cleaned) >= len(values) {
		t.Errorf("应去除异常值100，清洗后len=%d，原来len=%d", len(cleaned), len(values))
	}
}
