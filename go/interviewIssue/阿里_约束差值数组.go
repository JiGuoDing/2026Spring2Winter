package interviewIssue

import (
	"bufio"
	"fmt"
	"os"
)

const LIMIT int64 = 1000000000000000000

func ConstraintDifferenceArray() {
	reader, writer := bufio.NewReaderSize(os.Stdin, 1<<20), bufio.NewWriterSize(os.Stdout, 1<<20)
	defer writer.Flush()

	var T int
	fmt.Fscan(reader, &T)

	for ; T > 0; T-- {
		var n, m int
		fmt.Fscan(reader, &n, &m)

		// 邻接表定义
		type adjEdge struct {
			to     int
			weight int
		}
		graph := make([][]adjEdge, n+1)

		for ; m > 0; m-- {
			var i, j, k int
			fmt.Fscan(reader, &i, &j, &k)
			// a[i] - a[j] = k 转换为图关系
			graph[j] = append(graph[j], adjEdge{to: i, weight: k})
			graph[i] = append(graph[i], adjEdge{to: j, weight: -k})
		}

		// 初始化变量
		dist := make([]int64, n+1)
		visited := make([]bool, n+1)
		ans := make([]int64, n+1)
		possible := true

		// 遍历所有连通块
		for start := 1; start <= n; start++ {
			if visited[start] || !possible {
				continue
			}

			// BFS 队列
			queue := []int{start}
			visited[start] = true
			dist[start] = 0

			component := []int{}
			minDist := int64(0)
			maxDist := int64(0)

			for len(queue) > 0 && possible {
				u := queue[0]
				queue = queue[1:]
				component = append(component, u)

				// 更新最小最大相对值
				if dist[u] < minDist {
					minDist = dist[u]
				}
				if dist[u] > maxDist {
					maxDist = dist[u]
				}

				// 遍历邻接边
				for _, edge := range graph[u] {
					v := edge.to
					w := edge.weight
					newDist := dist[u] + int64(w)

					if !visited[v] {
						visited[v] = true
						dist[v] = newDist
						queue = append(queue, v)
					} else {
						// 检查一致性
						if dist[v] != newDist {
							possible = false
							break
						}
					}
				}
			}

			if !possible {
				break
			}

			// 计算平移量
			offset := 1 - minDist
			if maxDist+offset > LIMIT {
				possible = false
				break
			}

			// 填充答案
			for _, u := range component {
				ans[u] = dist[u] + offset
			}
		}

		// 输出结果
		if !possible {
			fmt.Fprintln(writer, "-1")
		} else {
			for i := 1; i <= n; i++ {
				if i > 1 {
					fmt.Fprint(writer, " ")
				}
				fmt.Fprint(writer, ans[i])
			}
			fmt.Fprintln(writer)
		}
	}
}
