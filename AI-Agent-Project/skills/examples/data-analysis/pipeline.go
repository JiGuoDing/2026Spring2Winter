package main

import "fmt"

type DataRow = map[string]interface{}

type PipelineStep func([]DataRow) ([]DataRow, error)

type Pipeline struct {
	steps []PipelineStep
	name  string
}

func NewPipeline(name string) *Pipeline {
	return &Pipeline{name: name}
}

func (p *Pipeline) AddStep(name string, step PipelineStep) *Pipeline {
	p.steps = append(p.steps, step)
	return p
}

func (p *Pipeline) Execute(data []DataRow) ([]DataRow, error) {
	var err error
	result := data

	for i, step := range p.steps {
		result, err = step(result)
		if err != nil {
			return nil, err
		}
		_ = i
	}

	return result, nil
}

func (p *Pipeline) StepCount() int {
	return len(p.steps)
}

func DeduplicateStep() PipelineStep {
	return func(data []DataRow) ([]DataRow, error) {
		seen := make(map[string]bool)
		result := make([]DataRow, 0, len(data))

		for _, row := range data {
			key := rowKey(row)
			if !seen[key] {
				seen[key] = true
				result = append(result, row)
			}
		}
		return result, nil
	}
}

func FillMissingStep(column string, filler func() interface{}) PipelineStep {
	return func(data []DataRow) ([]DataRow, error) {
		for _, row := range data {
			if _, exists := row[column]; !exists || row[column] == nil {
				row[column] = filler()
			}
		}
		return data, nil
	}
}

func RemoveOutliersStep(column string, threshold float64) PipelineStep {
	return func(data []DataRow) ([]DataRow, error) {
		values := extractFloatColumn(data, column)
		cleaned := RemoveOutliers(values, threshold)
		cleanedSet := make(map[float64]bool)
		for _, v := range cleaned {
			cleanedSet[v] = true
		}

		result := make([]DataRow, 0)
		for _, row := range data {
			if val, ok := row[column]; ok {
				if fv, ok := toFloat64(val); ok {
					if cleanedSet[fv] {
						result = append(result, row)
					}
				}
			} else {
				result = append(result, row)
			}
		}
		return result, nil
	}
}

func rowKey(row DataRow) string {
	key := ""
	for k, v := range row {
		key += k + "=" + toString(v) + ";"
	}
	return key
}

func toString(v interface{}) string {
	switch val := v.(type) {
	case string:
		return val
	case float64:
		return fmt.Sprintf("%f", val)
	case int:
		return fmt.Sprintf("%d", val)
	case bool:
		return fmt.Sprintf("%t", val)
	default:
		return fmt.Sprintf("%v", val)
	}
}

func extractFloatColumn(data []DataRow, column string) []float64 {
	values := make([]float64, 0, len(data))
	for _, row := range data {
		if val, ok := row[column]; ok {
			if fv, ok := toFloat64(val); ok {
				values = append(values, fv)
			}
		}
	}
	return values
}

func toFloat64(v interface{}) (float64, bool) {
	switch val := v.(type) {
	case float64:
		return val, true
	case int:
		return float64(val), true
	case int64:
		return float64(val), true
	default:
		return 0, false
	}
}
