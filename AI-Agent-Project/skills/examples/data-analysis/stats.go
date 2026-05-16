package main

import "math"

func Mean(values []float64) float64 {
	if len(values) == 0 {
		return 0
	}
	sum := 0.0
	for _, v := range values {
		sum += v
	}
	return sum / float64(len(values))
}

func Median(values []float64) float64 {
	n := len(values)
	if n == 0 {
		return 0
	}

	sorted := make([]float64, n)
	copy(sorted, values)
	sortFloat64(sorted)

	if n%2 == 0 {
		return (sorted[n/2-1] + sorted[n/2]) / 2
	}
	return sorted[n/2]
}

func StdDev(values []float64) float64 {
	if len(values) < 2 {
		return 0
	}
	m := Mean(values)
	sum := 0.0
	for _, v := range values {
		diff := v - m
		sum += diff * diff
	}
	return math.Sqrt(sum / float64(len(values)-1))
}

func Min(values []float64) float64 {
	if len(values) == 0 {
		return 0
	}
	m := values[0]
	for _, v := range values[1:] {
		if v < m {
			m = v
		}
	}
	return m
}

func Max(values []float64) float64 {
	if len(values) == 0 {
		return 0
	}
	m := values[0]
	for _, v := range values[1:] {
		if v > m {
			m = v
		}
	}
	return m
}

func Correlation(x, y []float64) float64 {
	n := len(x)
	if n != len(y) || n < 2 {
		return 0
	}

	mx := Mean(x)
	my := Mean(y)

	var sumXY, sumXX, sumYY float64
	for i := 0; i < n; i++ {
		dx := x[i] - mx
		dy := y[i] - my
		sumXY += dx * dy
		sumXX += dx * dx
		sumYY += dy * dy
	}

	if sumXX == 0 || sumYY == 0 {
		return 0
	}
	return sumXY / math.Sqrt(sumXX*sumYY)
}

func RemoveOutliers(values []float64, threshold float64) []float64 {
	if len(values) < 4 {
		return values
	}

	m := Mean(values)
	sd := StdDev(values)
	if sd == 0 {
		return values
	}

	result := make([]float64, 0, len(values))
	for _, v := range values {
		z := math.Abs(v-m) / sd
		if z <= threshold {
			result = append(result, v)
		}
	}
	return result
}

func sortFloat64(a []float64) {
	for i := 1; i < len(a); i++ {
		key := a[i]
		j := i - 1
		for j >= 0 && a[j] > key {
			a[j+1] = a[j]
			j--
		}
		a[j+1] = key
	}
}
