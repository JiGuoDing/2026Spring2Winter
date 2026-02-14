#include <iostream>
#include <vector>

using namespace std;

int main(int argc, char const *argv[]) {
    // m 个机器，n 个工件
    size_t m, n;
    cin >> m >> n;

    // 总操作数 = 工件数 * 机器数
    size_t total_ops = m * n;

    // 读取安排顺序：长度为 m * n 的工件号序列
    vector<size_t> seq(total_ops);
    for (size_t i = 0; i < total_ops; ++i) {
        cin >> seq[i];
    }

    // 机器分配表：machine_of[i][k] = 工件 i 的第 k 道工序分配给哪个机器
    vector<vector<size_t>> machine_of(n + 1, vector<size_t>(m + 1, 0));
    for (size_t i = 1; i <= n; ++i) {
        for (size_t j = 1; j <= m; ++j) {
            cin >> machine_of[i][j];
        }
    }

    // 加工时间表：time_of[i][k] = 工件 i 的第 k 道工序在对应机器上的加工时间
    vector<vector<size_t>> time_of(n + 1, vector<size_t>(m + 1, 0));
    for (size_t i = 1; i <= n; ++i) {
        for (size_t j = 1; j <= m; ++j) {
            cin >> time_of[i][j];
        }
    }

    // 每台机器的时间段列表：索引 1~m，每个元素都是 (start, end) 对，按 start 升序
    vector<vector<pair<size_t, size_t>>> machine_schedule(m + 1);

    // last_end[i]：工件 i 上一道工序的完成时间 (初始为 0)
    vector<size_t> last_end(n + 1, 0);

    // cur_step[i]: 工件 i 当前已安排的工序数 (下一道工序号 = cur_step[i] + 1)
    vector<size_t> cur_step(n + 1, 0);

    size_t makespan = 0; // 全局最短完成时间

    // 按照给定的工件顺序安排工序
    for (size_t idx = 0; idx < total_ops; ++idx) {
        // 当前工件号
        size_t j = seq[idx];
        // 当前要安排的工序号
        size_t k = cur_step[j] + 1;
        // 该工序所需的机器号
        size_t mac = machine_of[j][k];
        // 该工序的加工时间
        size_t t = time_of[j][k];
        // 工件约束：不能早于上一道工序完成时间
        size_t pre = last_end[j];

        // 引用当前机器的时间段列表
        auto& schedule = machine_schedule[mac];
        size_t start_use = 0, end_use = 0;
        // 标记是否已安排
        bool placed = false;

        // 情况 1：检查起始空档 [0, 第一个操作.start]
        if (!schedule.empty()) {
            size_t gap_start = 0;
            // 第一个已安排操作的开始时间
            size_t gap_end = schedule[0].first;
            // 实际可用开始时间
            start_use = max(pre, gap_start);
            // 空档足够容纳
            if (start_use + t <= gap_end) {
                // 插入到列表开头，保持有序
                end_use = start_use + t;
                schedule.insert(schedule.begin(), make_pair(start_use, end_use));
                placed = true;
            }
        }

        // 情况 2：检查中间空档 (操作之间的间隙)
        if (!placed && !schedule.empty()) {
            // 遍历所有相邻操作对：[i] 和 [i+1]
            for (size_t i = 0; i + 1 < schedule.size(); ++i) {
                size_t gap_start = schedule[i].second; // 前一个操作的结束时间
                size_t gap_end = schedule[i + 1].first; // 后一个操作的开始时间
                start_use = max(pre, gap_start);
                if (start_use + t <= gap_end) {
                    end_use = start_use + t;
                    // 插入到 [i] 和 [i+1] 之间
                    schedule.insert(schedule.begin() + i + 1, make_pair(start_use, end_use));
                    placed = true;
                    // 找到低一个满足条件的空档就停止检查
                    break;
                }
            }
        }

        // ---------- 情况3：安排在末尾空档 [最后一个操作.end, +∞) ----------
        if (!placed)
        {
            size_t gap_start = schedule.empty() ? 0 : schedule.back().second;
            start_use = max(gap_start, pre); // 取机器空闲起点和工件约束的最大值
            end_use = start_use + t;
            schedule.push_back(make_pair(start_use, end_use)); // 末尾插入自然有序
            // placed = true; // 末尾必可安排，无需标记
        }

        // ========== 更新状态 ==========
        last_end[j] = end_use;                 // 更新工件j的最新完成时间
        cur_step[j] = k;                       // 更新工件j的已安排工序数
        makespan = max(makespan, end_use); // 更新全局最晚完成时间
    }

    cout << makespan << endl;
    return 0;
}
