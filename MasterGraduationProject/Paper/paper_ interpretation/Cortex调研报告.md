# Cortex 调研报告 - Semantic-Aware Knowledge Caching for LLM Agents

> 调研日期：2026-08-13  
> 调研对象：Cortex，NSDI 2026 正式 proceedings 版本（pp. 2407-2421）  
> 证据边界：只使用 USENIX 正式页面/PDF/视频、arXiv 版本历史与 TeX 源码、作者官方论文页，以及本仓库 Design 资料；未采用二手解读  
> 页码约定：下文“PDF 第 n 页”均指 [USENIX 正式 PDF](https://www.usenix.org/system/files/nsdi26-ruan-cortex.pdf) 的文件页码，含第 1 页 USENIX 封面；正文印刷页码为 2407-2421  
> 本地论文：[Cortex.pdf](../paper_source/Cortex.pdf)

---

## 0. 一句话结论（TL;DR）

Cortex 缓存的不是 token KV，也不是整段 LLM 回答，而是 **Agent 发往远端搜索、RAG 或数据服务的“工具查询 -> 返回知识”**。它把一次语义命中拆成两关：先由 ANN 找高召回候选，再由 0.6B 级 semantic judge 判断旧结果是否足以回答新查询；验证通过才算 cache hit。其上再叠加成本/时延/静态性感知淘汰、一阶 Markov 预取，以及主 Agent 与 judge 的单 GPU 共置。

在作者构造的高语义复用、远端访问慢且受 API 限流影响的负载中，Cortex 报告搜索吞吐最高 **3.6x**、命中率 **>85%**、代码任务吞吐 **+20%**；并发高压下相对无缓存达到 **5.7x**（正式 PDF 第 2、3、10-13 页）。这些不是任意部署的固定收益：论文自己的受控实验显示，去掉 API 限流后收益只有 **1.5x**，有限流时才升至 **4.16x**（PDF 第 12 页，Table 4）。

论文最有价值的思想是：**不能把 embedding 相似直接当缓存命中，必须把“候选召回、语义验证、新鲜度和每字节收益”一起纳入缓存语义。** 但“without compromising correctness”只是 5 个 QA 数据集上最终 Exact Match 基本不降的经验结果；论文没有形式化错误率保证、时效性/ACL/副作用工具实验，也没有官方代码、trace 或 checkpoint。Algorithm 1 的新标注数据未进入后续阈值计算等多处正式稿不一致，进一步限制了可复现性。

对当前 InferTuner 毕设的关键判断是：Cortex 已经覆盖了“外部知识结果的语义缓存 + 淘汰 + 预取 + judge 共置”，因此不能再笼统写成“现有工作只做单机静态语义缓存”。真正仍清晰的空间是：**Flink 流处理层的 checkpoint/扩缩容一致性、语义记忆与 `(p,b,S,TTL)` 的 SLO 联合控制、跨轮 KV 生命周期，以及漂移下可验证的在线校准。**

---

## 1. 论文基本信息与版本关系

| 项 | 内容 |
|---|---|
| 正式题名 | *Cortex: Achieving Low-Latency, Cost-Efficient Remote Data Access For LLM via Semantic-Aware Knowledge Caching* |
| 作者 | Chaoyi Ruan, Chao Bi, Kaiwen Zheng, Ziji Shi, Xinyi Wan, Jialin Li |
| 机构 | National University of Singapore、USTC、University of Toronto、Sea AI Lab |
| 会议 | 23rd USENIX Symposium on Networked Systems Design and Implementation（NSDI 2026） |
| 出版信息 | USENIX Association，May 4-6, 2026，Renton, WA，pp. 2407-2421，ISBN 978-1-939133-54-0 |
| 正式页面 | [USENIX paper page](https://www.usenix.org/conference/nsdi26/presentation/ruan-cortex) |
| 正式 PDF | [nsdi26-ruan-cortex.pdf](https://www.usenix.org/system/files/nsdi26-ruan-cortex.pdf) |
| arXiv | [2509.17360](https://arxiv.org/abs/2509.17360)：v1 2025-09-22；v2 2026-02-03 |
| 官方视频 | [USENIX presentation video](https://www.youtube.com/watch?v=QVm8eRfAxSY) |
| 作者页 | [Chaoyi Ruan publications](https://franchyi.github.io/publications/)；[Jialin Li publications](https://www.comp.nus.edu.sg/~lijl/) |
| 代码 / artifact | 截至 2026-08-13，未发现可核验的官方代码、数据/trace、checkpoint、slides 或运行 demo；USENIX 页仅提供 PDF 与视频 |
| DOI 边界 | [10.48550/arXiv.2509.17360](https://doi.org/10.48550/arXiv.2509.17360) 是 arXiv DOI；USENIX 正式 BibTeX 未列会议论文 DOI |

### 1.1 先消歧：用户说的简称不是正式题名

“Cortex: Semantic-Aware Knowledge Caching for LLM Agents”是便于交流的简称。正式题名必须使用上表中的完整标题；以 `arXiv:2509.17360`、USENIX 路径 `ruan-cortex` 和第一作者 Chaoyi Ruan 可排除其他同名 Cortex 系统。

### 1.2 从 Asteria 到 Cortex

版本变化不是单纯排版：

- arXiv v1 的题名是 *Asteria: Semantic-Aware Cross-Region Caching for Agentic LLM Tool Access*，系统叫 **Asteria**，语义索引叫 **Sine**；
- arXiv v2 改为当前正式题名，系统改叫 **Cortex**，索引改叫 **Seri**；同时补强了外部访问成本、TTL/静态性、阈值回源重校准和高并发行为的表述；
- v1 到 v2 的摘要 headline 数字仍是 3.6x、>85%、20%；
- 对 arXiv v2 与 USENIX 正式正文做规范化文本核对后，除水印、页眉页脚、页码和分页版式外，未发现词汇内容差异。正式 PDF 多出 1 页 USENIX 封面，共 16 个文件页。

因此本报告以 USENIX 正式 PDF 为准，arXiv 只用于核验版本历史和公开 TeX 伪代码。

### 1.3 官方网页有两个会误导引用的单位错误

USENIX HTML 摘要把正式 PDF 中的：

- “cache hit rates of over **85%**”显示成了“over **85x**”；
- “coding throughput by **20%**”显示成了“by **20x**”。

正式 PDF、arXiv v2、arXiv TeX 源码均明确是 **85%** 和 **20%**。引用论文结论时必须以正式 PDF 为准。

---

## 2. 问题背景与 workload：远端工具调用才是瓶颈

### 2.1 Agent 与普通一次性生成的差异

Agent 反复执行：

```text
think -> 生成 tool query -> 跨区调用搜索/RAG/API -> observe -> 继续 think
```

远端访问位于推理关键路径。论文测得 Search-R1-7B 在 H100 上，外部检索约占每一步总时延的 **40%-50%**；其部署动机使用 300-500 ms 端到端远端调用、按次计费和 API 限流（PDF 第 2-4 页，§1-§2.2，Figure 1）。

这意味着单纯提高 GPU batch 并不能消除单请求必须等待远端结果的时延下界；当 API 限流触发重试时，增加并发甚至只会扩大排队。

### 2.2 为什么作者认为存在可缓存性

论文给出两类局部性：

1. **搜索兴趣**：少数热点主题占据大部分访问，呈近似 Zipf 分布；突发新闻又会产生短时间相关查询（PDF 第 4-5 页，Figures 2-3）。
2. **代码 Agent**：同一仓库的多个 issue 会反复读取核心文件；论文对 SWE-Bench `sqlfluff` 子集的文件访问统计也呈头部集中（PDF 第 4-5 页，Table 2）。

但这里要区分“动机观测”和“正式评测”：搜索实验不是生产 Agent query trace，而是把公开 QA 数据按 Zipf-0.99 重采样，或把 12 小时 Google Trends 映射到 HotpotQA 后压缩成 10 分钟。收益依赖作者人为注入的热点与相关性。

### 2.3 Cortex 缓存的对象边界

| 机制 | 缓存对象 | 命中后省掉什么 | Cortex 的关系 |
|---|---|---|---|
| Cortex | 工具查询 `q` 与远端结果 `r` | 一次搜索/RAG/API 远端调用 | 本文对象 |
| Semantic prompt cache | 用户 prompt 与完整 LLM response | 整次 LLM 生成 | 不是 Cortex 的缓存对象 |
| Transformer KV / prefix cache | attention K/V 中间张量 | 重复 prefill/部分 decode 计算 | 与 Cortex 正交 |
| 传统 RAG | 文档向量/倒排索引 | 不一定省调用；为每次请求检索知识并注入上下文 | Cortex 可缓存一次 RAG 工具调用的结果 |
| Agent memory | 会话摘要、偏好、实体等 | 改善后续推理/行动选择 | Cortex 主要降工具执行成本，不以增强推理为目标 |

所以 Cortex 最适合“不同表述会访问同一稳定知识/文件”的场景。对写操作、实时行情、用户权限敏感结果或有副作用的 API，论文没有证明可安全复用。

---

## 3. 系统总览

```text
Agent 生成结构化工具查询 q
          |
          v
Data Client：在真正跨区调用前透明拦截
          |
          v
Seri 两阶段检索
  1. Embedding + Faiss ANN：高召回候选
  2. 0.6B Semantic Judge：验证旧结果能否回答 q
          |
          +-- judge 通过且未过期 --> 返回缓存结果，记为 hit
          |
          +-- 无候选/未通过 ------> 调远端工具，返回并写入 SE
          |
          v
Agent-aware Cache Manager
  - TTL + LCFU 淘汰
  - 一阶 Markov 预取
  - 阈值回源重校准
          |
          v
Agent/Judge 单 GPU 共置：MPS 80/20 + Agent 优先准入
```

对应正式 PDF 第 6 页 Figure 4。Cortex 的贡献不是某一个 embedding 模型，而是把“概率相似检索”封装成一个具有二元 hit/miss、容量、过期、淘汰、预取和资源管理的缓存系统。

---

## 4. 核心抽象、架构与算法

### 4.1 Semantic Element（SE）

一个 SE 可以写成：

```text
SE = {
  key:        agent tool query / action,
  value:      remote tool response,
  embedding:  E(key),
  metadata: {
    frequency, cost, latency, size,
    staticity, expiration_time
  }
}
```

- `key` 和 `value` 从 Agent 的结构化 `<search>/<info>`、工具标签或 API 交互中解析；
- embedding 是未来近邻检索的语义指纹；
- semantic judge 还给出 1-10 的 `staticity`：10 表示长期稳定，1 表示强时效；
- 论文示例中“谁画了蒙娜丽莎”为 10，“现任美国总统”为 5，“今天巴黎天气”为 1（PDF 第 7 页，Figure 5、§4.1）。

这里的未决点是：论文没有给出 staticity 的 prompt/训练标签，也没有定义 `staticity -> TTL` 的映射；随后又称 TTL 为用户配置。因此 staticity 和实际失效时间之间的工程关系无法从论文重建。

### 4.2 Seri：ANN 负责召回，judge 负责命中

设新查询为 `q`，缓存项 `i` 的旧查询和结果为 `(q_i,r_i)`。第一阶段候选条件为：

```text
C(q) = { i | cosine(E(q), E(q_i)) >= tau_sim }
```

论文实验示例 `tau_sim=0.9`。第二阶段由语义 judge 输出 `S_lsm(q,r_i)`，确认条件为：

```text
semantic_valid(q,i) = 1[ S_lsm(q,r_i) >= tau_lsm ]
```

加入时效条件后，可把完整命中语义概括为：

```text
hit(q,i) = 1[i in C(q)]
           * 1[S_lsm(q,r_i) >= tau_lsm]
           * 1[now < expiration_time_i]
```

这不是论文原样给出的单行公式，而是按 §4.1-§4.3 合并后的等价表达。论文示例 `tau_lsm=0.9`（PDF 第 7-8 页，§4.2）。

ANN 可以找出“Apple nutrition facts”和“Apple stock price”这种词面相近的候选，但 judge 应拒绝“旧答案不能回答新问题”的假阳性。需要注意，论文没有公开 ANN `top-k`、多候选验证顺序、judge prompt、batch 方式或 score 标定方法。

### 4.3 期望时延目标，以及遗漏的约束

论文定义：

```text
L_cache = L_ANN + L_LSM
L_hit   = L_agent + L_cache
L_miss  = L_agent + L_cache + L_tool
```

并写出：

```text
minimize E[L] = P_hit * L_hit + (1-P_hit) * L_miss
          over tau_sim, tau_lsm
```

文字称这是“在目标 precision 约束下”最小化时延，但正式公式没有印出：

```text
Precision(tau_sim,tau_lsm) >= P_target
```

如果只按印刷公式求解，最优解会倾向把阈值放得很松、最大化命中，而不关心错误；真正的质量约束只在后续周期校准文字中出现（PDF 第 8 页，§4.2）。因此它是一个工程目标描述，不是完整可求解的优化问题。

相对无缓存的单次工具调用时延 `L_vanilla=L_agent+L_tool`，由上述式子可推得 Cortex 有正收益的必要直觉：

```text
P_hit * L_tool > L_cache
```

即被避免的期望远端时延必须大于每次都要支付的 ANN+judge 开销。这也解释了为什么远端只有几毫秒、语义复用很低时，Cortex 可能得不偿失。

### 4.4 周期阈值重校准

论文声称固定 `tau_lsm` 会随 workload 漂移失效，因而周期回源取 ground truth：

```text
input: judge J_lsm, target precision P_target,
       recent log L_recent, validation set D_val

D_sample     = sample(L_recent)
D_annotated  = []
for (q, r_cached) in D_sample:
    r_ground = live_tool(q)
    label    = EvaluateGT((q,r_cached), r_ground)
    D_annotated.append(q,r_cached,label)

scores          = PredictScores(J_lsm, D_val)
precision_curve = CalcPrecisionCurve(scores)
tau_lsm'        = FindThreshold(precision_curve, P_target)
deploy(tau_lsm')
```

目标 precision 示例为 0.99；部署描述为每分钟抽 5 条近期请求，离开关键路径执行。实验称相对无重校准版本吞吐只降 **2%**（PDF 第 8、13 页，Algorithm 1、§6.6）。

正式伪代码存在关键断裂：新构造的 `D_annotated` 后续完全未使用，`PredictScores` 仍读取原有 `D_val`，`CalcPrecisionCurve` 也未显式接收 labels。按字面执行，刚回源取得的 ground truth 无法改变新阈值。合理实现可能会把 `D_annotated` 合并进 `D_val` 或用于微调，但论文没有写出，不能替作者补全为既成事实。

### 4.5 LCFU：按“可避免代价/字节”而非纯命中率淘汰

论文的 Least Cost-Efficient and Frequently Used（LCFU）分数是：

```text
score(se) = log(Freq+1)
            * log(Cost*10^3+1)
            * log(Latency+1)
            * log(Staticity+1)
            / Size
```

流程为：

```text
1. 先删除 TTL 已过期项
2. 超容量时为每个 SE 计算 score
3. 从低到高淘汰，直到 Usage <= capacity
```

其意图是保留“更常用、回源更贵/更慢、更稳定、单位大小收益更高”的对象（PDF 第 8-9 页，Algorithm 2、§4.3）。Table 6 中 LCFU 的命中 0.86 低于 LFU 的 0.89，但吞吐 2.35 高于 2.16 req/s，说明优化 hit rate 本身不是目标。

需要谨慎的工程细节：

- `Cost*10^3` 是手工单位缩放，Latency 用毫秒还是秒会改变排名；分数并非量纲不变；
- 任一乘积因子接近 0 都会把整体拉到 0，表达的是强“与”关系而非可替代收益；
- Algorithm 2 使用 `items.PopFirst()`，正式稿没有定义 `items` 或执行排序；arXiv TeX 里仅有未渲染的注释“Assumes items are sorted by score”。

### 4.6 一阶 Markov 预取

Cortex 只用已确认 hit 序列估计：

```text
P(q_next | q_current)
```

若概率超过置信阈值，就异步回源并把预测项写入缓存。预取项初始 `frequency=0`，所以未被真实请求使用时会因低 LCFU 分数较早淘汰；命中后才增加频次（PDF 第 9 页，§4.3）。

论文没有公开转移窗口、平滑方式、置信阈值或预取 budget，也没有单独的 prefetch on/off 消融。因而预取是完整设计的一部分，但不是被实验独立证明的贡献。

### 4.7 Agent/Judge 共置与优先调度

Cortex 用两层资源保护：

1. **粗粒度**：CUDA MPS 将 GPU compute 静态按约 80%/20% 分给 Agent/Judge；
2. **细粒度**：在动态显存池的两个队列 `Q_A`、`Q_J` 间严格优先 Agent：

```text
if Q_A has a dispatchable batch:
    dispatch Agent batch
elif Q_J has a batch and memory is sufficient:
    dispatch Judge batch
else:
    wait / fall back
```

Judge 是 prefill 为主、只生成 1 token 的分类任务，KV 占用较小。论文称 judge 延迟时不阻塞用户，而将该请求退化为 miss、走远端回源（PDF 第 9-10 页，Figure 6、§4.4）。但 timeout、取消 judge、并发回源去重和“多晚算延迟”的边界没有公开；这与“必须经 judge 才能命中”之间仍缺少实现细节。

---

## 5. 实现与 artifact 边界

论文只给出高层实现信息：

- 基于 vLLM，透明拦截 Search-R1 等 Agent 的工具调用；
- Faiss ANN；
- Qwen3-Embedding-0.6B 与 Qwen3-Reranker-0.6B 分别承担 embedding/judge；
- CUDA MPS 让 Agent 与 judge 多进程共享 GPU；
- 更细粒度的动态 GPU partition（如 Green Contexts）留作未来工作（PDF 第 10 页，§5）。

截至 2026-08-13，本次在 USENIX 页面、arXiv 正文/TeX、第一作者和 Jialin Li 官方论文页均未找到 Cortex 官方仓库、数据/trace、checkpoint、容器、安装文档或 slides。GitHub 上的 vLLM、Search-R1、Faiss、Qwen、GPTCache 是依赖/相关工作，不能当作 Cortex artifact。

因此目前能做到的是“按论文重新实现”，不能做到“运行作者代码复现实验”。缺失的关键配置包括：

- judge prompt/微调数据/score 生成和 calibration labels；
- staticity prompt、TTL 映射；
- ANN top-k、索引参数与多候选策略；
- cache-size-ratio 的精确定义；
- prefetch 阈值与窗口；
- 到达过程、warm-up、随机种子、重复次数；
- SWE-Bench issue 清单；
- H100 数量、CPU/内存、具体地域与网络；
- 成本统计时间窗。

---

## 6. 实验设置与全部关键定量结果

### 6.1 实验设置

| 项 | 设置 | 论文位置 |
|---|---|---|
| 部署 | Agent/Cortex 在 on-prem H100 cluster；远端数据服务在另一 region | PDF 第 10 页 / proceedings p.2415，§6.1 |
| 搜索远端 | Google Cloud Search API，作者测得平均 300-500 ms | 同上 |
| 代码远端 | 自部署 Faiss RAG，固定约 300 ms | 同上 |
| 搜索 Agent | Search-R1-7B，基于 Qwen2.5-7B 后训练 | 同上 |
| 代码 Agent | Qwen3-8B | 同上 |
| Cortex 小模型 | Qwen3-Embedding-0.6B + Qwen3-Reranker-0.6B | 同上 |
| Skewed search | Zilliz-GPT、HotpotQA、Musique、2Wiki；每数据集约 250 问题、10 clusters，合计 1000；Zipf-0.99 | PDF 第 10-11 页，§6.1、Figure 7 |
| Trend trace | 4 个主题的 12 小时 Google Trends，映射到 HotpotQA 并压缩为 10 分钟 | PDF 第 10-11 页，§6.1、Figure 8 |
| Coding | SWE-Bench Oracle 的 `sqlfluff` 仓库子集 | PDF 第 10-11 页，§6.1、Figure 9 |
| 主要基线 | `Agent_vanilla`、`Agent_exact`、`Agent_Cortex`；ANN-only 仅做正确性消融 | PDF 第 10 页，§6.1 |
| 指标 | throughput、latency、cache hit、API+GPU cost、最终 Exact Match | PDF 第 10-13 页 |

`Agent_exact` 在这里是“外部工具结果按精确查询键缓存”，不是 Transformer KV cache；论文用“exact-match KV cache”这一叫法容易混淆。

### 6.2 主要性能、成本与质量结果

| 结论 | 作者报告值 | 正式论文位置 |
|---|---:|---|
| Skewed search（Musique） | 相对 exact cache 最高 **3.6x** throughput；Cortex hit **>85%**，exact **<20%**；时延最高约降 **4x** | PDF 第 10-11 页，§6.2、Figure 7 / p.2416 |
| Trend-driven | 相对 vanilla 最高 **3.8x**；hit 近 **95%** | PDF 第 10-11 页，§6.2、Figure 8 / p.2416 |
| SWE-Bench/sqlfluff | throughput **+20%**；hit 近 **45%** | PDF 第 11 页，§6.2、Figure 9 / p.2416 |
| 并发扩展 | request rate=8 时 Cortex **4.89 req/s**、exact **1.09**、vanilla **0.86**，即 **4.5x/5.7x** | PDF 第 11 页，§6.3、Figure 10 / p.2416 |
| 更高并发 | request rate 至 32 时约维持 **5 req/s**，最高负载退化 **<3%** | PDF 第 11-12 页，§6.3 |
| 单请求 breakdown | **1.08 s -> 0.61 s**；远端约 **0.48 s**；cache lookup **0.02 s**、judge **0.03 s** | PDF 第 12 页，§6.4、Figure 11 / p.2417 |
| API 调用与重试 | calls 约 **1300 -> 103**（-92%）；retry **25% -> 0.50%** | PDF 第 12 页，§6.4、Figure 12 / p.2417 |
| 限流影响 | 无 API rate limit：**1.5x**；有限流：**4.16x** normalized throughput | PDF 第 12 页，Table 4 / p.2417 |
| 成本 | vanilla / separate judge GPU / co-located 总成本：**$82.5 / $158.5 / $76.64**；吞吐：**0.87 / 4.74 / 4.89 req/s** | PDF 第 12 页，Table 5 / p.2417 |
| 作者汇总的成本效率 | co-located throughput/$ 约为 vanilla 的 **6x**；同成本附近性能约 **5.6x** | PDF 第 12-13 页，§6.5 |
| ANN-only 正确性退化 | StrategyQA Exact Match **0.79 -> 0.69**；完整 Cortex 回到 **0.79** | PDF 第 13 页，Figure 13 / p.2418 |
| LCFU | LRU/LFU/LCFU hit **0.88/0.89/0.86**；throughput **2.14/2.16/2.35 req/s** | PDF 第 13 页，Table 6 / p.2418 |
| 共置 | Dedicated-2GPU vs MPS 80/20：**2.89 vs 2.72 req/s**；p99 **6601 vs 7230 ms**（+9.5%） | PDF 第 13 页，Table 7 / p.2418 |
| 重校准开销 | 相对无重校准版本 throughput **-2%** | PDF 第 13 页，§6.6 |

### 6.3 Figure 13 的完整 Exact Match 读数

| 数据集 | Search-R1 | Cortex w/o judge | Cortex |
|---|---:|---:|---:|
| Musique | 0.20 | 0.18 | 0.20 |
| NQ | 0.42 | 0.38 | 0.41 |
| 2Wiki | 0.37 | 0.32 | 0.37 |
| HotpotQA | 0.43 | 0.38 | 0.43 |
| StrategyQA | 0.79 | 0.69 | 0.79 |

完整 Cortex 与无缓存基线“几乎一致”，但并非每个数都字面相等：NQ 是 0.41 vs 0.42。更重要的是，Figure 13 测的是 **Agent 最终答案 Exact Match**，不是 semantic judge 的 precision/recall、陈旧命中率或权限安全性。

### 6.4 如何谨慎理解 headline 数字

1. **3.6x/5.7x 不可脱离远端限流。** Table 4 明确显示无 rate limit 时是 1.5x，有 rate limit 才到 4.16x。
2. **高命中来自人为构造的语义局部性。** Zipf-0.99、cluster 重采样和压缩 Trends 都有利于缓存；低复用或个性化流量不一定成立。
3. **代码外部有效性很窄。** SWE-Bench 只报告 `sqlfluff` 子集，未给 issue 数或清单，也未报告代码任务正确性。
4. **没有方差。** 主要图表没有报告重复次数、置信区间或 error bars，无法判断运行噪声。
5. **“正确性不降”不是形式化保证。** 只证明上述 5 个 QA 数据集的最终 EM 基本不降。

---

## 7. 局限、独立批判与正式稿矛盾

### 7.1 作者明确留下的边界

- semantic judge 是可替换、可微调组件；其准确性依赖具体 workload；
- 更先进的动态 GPU partition 留作未来工作；
- judge 拥塞时可退化为远端 miss，而非保证每次都能利用语义命中（PDF 第 9-10 页，§4.4-§5）。

### 7.2 本调研补充的批评

1. **没有 judge 本身的 precision/recall 曲线。** 论文给最终 EM，却没给 target precision 是否达到 0.99、false-hit/false-miss、阈值覆盖或 workload drift 下校准轨迹。
2. **“deterministic hit”仍由概率模型决定。** 二元输出不等于确定正确；judge 误判仍会把错误知识作为正式 hit 返回。
3. **时效性只停留在 staticity+TTL 机制。** 没有高频更新、陈旧数据、撤回、地域副本不一致或权限变更实验。
4. **缓存副作用工具的安全边界未定义。** 对支付、写数据库、发消息等工具，复用旧“结果”可能语义上错误甚至危险；论文只测读取型 search/RAG。
5. **没有与成熟 semantic cache 正面对比。** 主性能基线只有无缓存和 exact cache，ANN-only 也只做质量消融；不能据此推出优于 vCache、VectorQ、GPTCache 等所有语义缓存方案。
6. **LCFU 单位敏感且经验化。** 美元、毫秒、字节的缩放改变分数，`10^3` 没有跨服务标定理论。
7. **Trend 收益没有对应消融。** 作者将突发收益归因于 LCFU，但没有在同一 trend 场景中给 LRU/LFU 对照；预取完全没有 on/off 消融。
8. **GPU 共置实现信息不足。** 论文没有解释多 vLLM 进程如何形成所谓统一动态 HBM 池，也没有给 memory fragmentation、OOM 或不同 Agent/Judge 模型组合结果。
9. **成本表不可复算。** 没有统计时窗、请求总量和 GPU 计价细节；API/GPU 价格还会随时间漂移。
10. **artifact 缺失。** 论文是系统工作，却没有公开实现、配置或 trace；核心结果只能重新实现而不能复跑。

### 7.3 正式稿、网页与伪代码中的不一致

| 位置 | 不一致 | 影响 |
|---|---|---|
| USENIX HTML vs PDF 摘要 | 网页写 85x/20x，PDF 是 85%/20% | 引用必须按正式 PDF |
| Algorithm 1 | 构造 `D_annotated` 后从未使用，后续仍对 `D_val` 打分 | 新 ground truth 按字面无法参与阈值更新 |
| Algorithm 2 | `items.PopFirst()`，但未定义 `items` 或排序 | 无法直接执行；TeX 仅有未渲染的排序假设注释 |
| §4.2 优化目标 | 文字称有 target precision 约束，公式未写该约束 | 印刷公式本身会偏向无限放松阈值 |
| Table 7 vs 同段正文 | 表题写 H100，正文写 single A100 | 共置硬件无法唯一确定 |
| Table 5 vs 正文 | separate judge GPU 吞吐表中 4.74，正文写 4.79 | 小数值漂移 |
| Table 5 解释 | “Cortex w/o Sharing”理论上仍有缓存，但 API cost 与 vanilla 同为 $6.5；完整 Cortex 是 $0.64 | 固定时间/固定请求边界不明，成本含义无法复算 |
| Table 6 | 列名 `Cache hit (%)`，数值为 0.88/0.89/0.86 | 应是比例或 88/89/86%，单位标注错误 |
| Figure 11 文字 | inference 0.6s + cache 0.02s + judge 0.03s = 0.65s，却写总时延 0.61s | 算术不闭合，可能为严重四舍五入但未解释 |
| §6.5 | 2.72/2.89=94.1%，前文写 94%，随后又写 `>=95%` | 同一共置保留率不一致 |
| Judge 调度描述 | “judge 延迟不阻塞，最坏按 miss”与“必须 judge 验证才命中”并存 | 缺 timeout、取消与回源竞态语义 |

这些问题不足以否定总体思路或所有实验，但说明论文伪代码和汇总数字不能直接当成完整实现规范。

---

## 8. 与 vCache、JITServe、传统 RAG、KV cache 的区别

| 工作 | 缓存/优化对象 | 命中或决策机制 | 主要目标 | 关键边界 |
|---|---|---|---|---|
| **Cortex** | 外部工具查询 -> 远端知识结果 | ANN + 0.6B judge + TTL；LCFU/预取 | 降跨区工具时延、API 费和限流压力 | 无形式化错误保证；不跳过 Agent 主推理 |
| **vCache** | 用户 prompt -> 完整 LLM response | 每缓存条目在线学习阈值；随机 explore/exploit；用户设 `delta` | 在错误率约束下最大化语义响应复用 | 不负责工具结果时效、容量/淘汰、跨区数据面 |
| **JITServe** | LLM 请求的 GPU 生成带宽/批次 | 输出长度上界、pattern graph、GMAX | 异构 SLO 下最大化按时 goodput | 不缓存语义知识，也不减少外部工具调用 |
| **传统 RAG** | 文档/向量索引 | 每次 query 检索 top-k 文档并注入 prompt | 提供外部知识、改善答案 | 通常仍要每次访问检索服务；不是历史工具结果复用 |
| **Transformer KV cache** | token attention K/V 张量 | 精确/共享 prefix | 省 prefill/部分 decode GPU 计算 | 不理解语义等价，不能省搜索/API 调用 |

### 8.1 Cortex vs vCache

二者都拒绝“全局相似度直接命中”，但控制点不同：

- vCache 在**输出侧**复用完整 LLM 回答，强调用户可设错误率 `delta` 和逐条目在线阈值；
- Cortex 在**工具/知识边界**复用远端结果，强调时效元数据、成本感知容量管理、预取和跨区/限流收益；
- Cortex 的 `P_target` 是经验校准目标，没有 vCache 式形式化保证；vCache 则没有 Cortex 的 TTL/LCFU/跨区工具成本系统层能力。

它们可组合：先用 Cortex 省远端工具调用，再由 vCache 式输出缓存决定是否连 Agent 主推理也跳过，但这会叠加两层错误与新鲜度风险。

### 8.2 Cortex vs JITServe

JITServe 关注“已决定执行的 LLM 请求如何在 GPU 上刚好按 SLO 完成”；Cortex 关注“某次外部数据访问是否根本不必发生”。一个在生成调度面，一个在 Agent 数据面。Cortex 的 judge 共置调度只是保护内部验证模型，不等价于 JITServe 对混合 SLO 请求的 goodput 调度。

### 8.3 Cortex vs RAG / KV cache

- RAG 回答“从知识库取什么”；Cortex 回答“之前一次相同意图的远端检索结果是否还能直接复用”。
- KV cache 回答“相同 token 前缀如何少算 attention”；Cortex 可跨改写命中，但必须承担语义误判和陈旧知识风险。
- 三者省掉的成本不同，可同时存在，不能用一个命中率直接横比。

---

## 9. 对当前 InferTuner 毕设方向的谨慎启发

本节只依据本仓库的[毕业设计选题研究全记录](../../Design/design_prototype/毕业设计选题研究全记录.md)中已记录的 InferTuner 基底，不假设尚未实现的能力。

### 9.1 先修正当前资料里的一个过强定位

当前资料将 vCache/Cortex 概括为“在引擎内或单机打补丁”。对 Cortex 不够准确：它明确面向**跨区域** Agent 与远端数据服务，并系统化处理 external knowledge cache、TTL/淘汰/预取、API rate limit 和 GPU 共置。

更准确的差异是：

- Cortex 的 cache engine 仍是 Agent 侧本地组件，未处理 Flink operator state、checkpoint、并行度重配置和跨分区状态迁移；
- Cortex 只缓存工具结果，不管理跨轮 attention KV 驻留，也不联合优化 Flink 的 `(p,b)`；
- Cortex 的阈值/淘汰是局部机制，没有把语义 memory tax 与端到端 SLO、operator queue/backpressure 纳入统一控制问题。

### 9.2 与项目“语义记忆升级”存在的真实重叠

项目计划把 `InferenceStateFetcherProcessor` 升级为“embedding 索引 + 语义检索 + 命中快路径”，这一形态与 Cortex 的 data client + Seri 已经明显相邻。若再加入 staticity、cost-aware eviction 和 Markov prefetch，则机制重叠更高。

仍需保留两个对象差异：

1. Cortex 命中后省掉**一次远端工具调用**，Agent 还要继续推理；
2. 项目资料中的输出侧语义记忆命中可能直接短路 Batcher+Inferencer，省掉**整次 LLM 推理**。

论文写作应明确选择哪一种，或把二者建模成不同层级的 action；不能把“工具结果 cache hit”和“完整响应 cache hit”混用为一个命中率。

### 9.3 可直接借鉴但要改进的机制

1. **SE 数据模式**：`query/result/embedding/frequency/cost/latency/size/staticity/TTL` 可作为 Flink state schema 起点。
2. **两阶段门控**：BGE-m3/ANN 做召回，cross-encoder 或小 judge 做验证；但需要报告 judge precision/recall 和校准覆盖，而不只看最终 EM。
3. **价值而非命中率**：把“可避免的 GPU/远端成本 - embedding/judge/状态访问税”作为统一收益，比直接照搬 LCFU 对数乘积更稳健。
4. **后台任务让步**：校准、预取、索引重建都应受 SLO budget 控制；Flink 可把它们显式建成低优先级 side flow。
5. **时效性显式化**：staticity 不能只让 LLM 打 1-10 分；应按工具类型、事件时间、source version/ETag 和观测失效率校准 TTL。
6. **把重校准断裂补完整**：新回源 labels 必须进入 validation/calibration state，并随 checkpoint 恢复；这正是 Cortex 没有给出的状态语义。

### 9.4 更稳妥的差异化边界

| 维度 | Cortex | InferTuner 可主张的新增问题 |
|---|---|---|
| 系统层 | Agent/vLLM 邻近的本地 cache engine | Flink operator/pipeline 控制层 |
| 状态容错 | 论文未给 checkpoint/恢复/扩缩容语义 | 语义索引与校准状态的 checkpoint、reshard、恢复一致性 |
| 控制变量 | `tau_sim/tau_lsm`、TTL、eviction、prefetch、80/20 | `(S_sem,tau,p,b,TTL,M_kv)` 联合配置和机会约束 |
| 复用层级 | 外部工具结果 | 工具结果 + 完整响应 + 跨轮 KV 的分层选择 |
| 动态负载 | 周期阈值重校准；无 drift 实验 | 漂移检测、在线 conformal/coverage 恢复、背压联动 |
| 会话 | 工具调用序列用于一阶预取 | 轮间隔、剩余轮数、上下文增长、会话亲和与 KV 生命周期 |
| 评测故障 | 未覆盖 | checkpoint、operator failover、rescale、索引重建时 SLO |

### 9.5 建议加入的 baseline 和实验

最少应有：

1. `No-cache`；
2. `Exact-key tool cache`；
3. `ANN-only`；
4. `Cortex-style`：ANN + judge + TTL + LCFU，无 Flink 联合控制；
5. `vCache-style output cache`：区分完整响应复用；
6. `Ours w/o state semantics`：无 checkpoint/reshard 一致性；
7. `Ours w/o joint optimization`：固定 `(p,b,S,tau)`；
8. `Oracle`：知道真实复用、时效和远端代价。

除 throughput/hit rate 外，必须报告：tool-result precision/recall、陈旧命中、最终答案质量、API 调用/费用、P95/P99、memory tax、GPU 时数、checkpoint 大小/耗时、failover 恢复、rescale 状态迁移和各层命中贡献。

---

## 10. 复现建议

### 10.1 层 1：论文机制的最小重实现

1. 使用 Qwen3-Embedding-0.6B + Qwen3-Reranker-0.6B，或项目已有 BGE-m3 + 小 cross-encoder；
2. 先用本地 Faiss RAG 加可控 300 ms delay，避免真实 API 价格/限流漂移；
3. 实现 exact、ANN-only、ANN+judge 三条路径；
4. 明确定义 `top-k`、多候选顺序、judge prompt、threshold、TTL；
5. 用 HotpotQA/Musique 的释义簇先复现“ANN-only 质量下降、judge 恢复”的方向性，而不是追 3.6x 绝对值。

### 10.2 层 2：缓存策略与资源实验

1. 扫 `tau_sim/tau_lsm`，画 precision-recall-hit-latency 四维曲线；
2. 比较 LRU、LFU、论文 LCFU 与量纲归一的 expected-value policy；
3. 单独消融 prefetch，报告覆盖率、误预取率、污染和额外远端费用；
4. 注入更新频率与 ACL 变化，测 stale/unauthorized reuse；
5. 对 MPS 80/20、独占 GPU、串行共享作对照；由于当前机器和权限条件与论文不同，应先验证 MPS 是否可用，不把它设为毕设主链路前提。

### 10.3 层 3：接入 InferTuner

1. 将 SE、阈值校准统计、Markov/热度状态放入 Flink state；向量索引视为可重建数据面，state 作为可恢复控制面；
2. 注入 checkpoint、task failover 和 rescale，验证“命中判定、频次、TTL、校准样本”恢复前后一致；
3. 把 `S_sem/tau` 与现有 `(p,b)` 一起择优，显式计入 embedding、judge、状态访问和 checkpoint 的 memory tax；
4. 工具结果、完整响应、KV 三层 cache 使用分开的 hit/quality 指标；
5. 2-4 GPU 条件下主张相对趋势和机制消融，不声称复现论文 H100 绝对吞吐。

### 10.4 复现报告必须记录的假设

由于官方 artifact 缺失，至少固定并公开：

- 模型 revision、GPU、CUDA、vLLM、Faiss 和 MPS 配置；
- cache ratio 的分母定义、capacity 单位；
- arrival trace、随机种子、warm-up、运行时长、重复次数；
- judge prompt/label 规则、calibration split；
- TTL/staticity 映射与 source-version 语义；
- 远端延迟/限流/失败注入参数；
- 成本统计时间窗和单价；
- 原始日志和置信区间。

---

## 11. 一手来源清单

1. USENIX 正式页面：<https://www.usenix.org/conference/nsdi26/presentation/ruan-cortex>
2. USENIX 正式 proceedings PDF：<https://www.usenix.org/system/files/nsdi26-ruan-cortex.pdf>
3. arXiv abstract / version history：<https://arxiv.org/abs/2509.17360>
4. arXiv v1（Asteria）：<https://arxiv.org/abs/2509.17360v1>
5. arXiv v2 PDF：<https://arxiv.org/pdf/2509.17360v2>
6. arXiv v2 HTML：<https://arxiv.org/html/2509.17360v2>
7. arXiv v2 TeX source：<https://arxiv.org/src/2509.17360v2>
8. USENIX 官方演讲视频：<https://www.youtube.com/watch?v=QVm8eRfAxSY>
9. 第一作者论文页：<https://franchyi.github.io/publications/>
10. Jialin Li 官方论文页：<https://www.comp.nus.edu.sg/~lijl/>
11. 作者镜像 PDF：<https://www.comp.nus.edu.sg/~lijl/papers/cortex_nsdi26.pdf>

> 调研声明：本报告的机制、公式、实验数字和作者自述边界均回到正式 PDF 逐页核对；16 个文件页已完整提取并渲染检查。USENIX HTML 的 85x/20x 单位错误、Asteria -> Cortex 版本改名、Algorithm 1/2 的伪代码断裂、硬件/表格/算术不一致和官方 artifact 缺失均已明确标注。对 InferTuner 的启发只引用本仓库现有 Design 资料，不把尚未实现的能力写成事实。
