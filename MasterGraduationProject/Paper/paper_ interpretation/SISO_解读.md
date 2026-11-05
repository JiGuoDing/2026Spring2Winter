---
template: doc
theme: auto
lang: zh
title: SISO：用质心缓存和语义局部性替代 LRU
subtitle: arXiv 2025 · resp
source: Jungwoo Kim et al., "Rethinking Caching for LLM Serving Systems: Beyond Traditional Heuristics," arXiv:2508.18736v1, 2025.
outline: right
---

SISO 把语义缓存的存储单位从“单条查询”换成“质心”：一个质心代表一簇语义相近的查询，缓存它等于缓存一整片查询空间。再叠加语义局部性淘汰和按 SLO 动态调整的相似度阈值，论文报告平均 1.71× 的命中率提升。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | Rethinking Caching for LLM Serving Systems: Beyond Traditional Heuristics |
| 作者 | Jungwoo Kim、Minsang Kim、Jaeheon Lee、Chanwoo Moon、Heejin Kim、Taeho Hwang、Woosuk Chung、Yeseong Kim、Sungjin Lee |
| 机构 | DGIST；POSTECH；SK hynix（均为韩国） |
| 发表 | arXiv 预印本，2025 |
| 正式版本 | 未发现正式会议/期刊版本；本地 PDF 为 arXiv v1 |
| arXiv / DOI | arXiv:2508.18736v1 [cs.DB]（2025-08-26）；论文未印 DOI |
| 本地原文 | `paper_source/SISO_arXiv2508.18736.pdf` |
| 代码/数据 | 未发现公开代码；数据集为 Quora、Reddit、MSMARCO、Natural Questions、ShareGPT |
| 版本边界 | 只有 v1；摘要写“up to 1.71×”，引言同时出现“1.54× average”和“1.71× average”，两者分别对应质心缓存与局部性替换的增益，引用时需说明口径 |

## B 问题与动机

论文把现有语义缓存的问题归为三条：

1. **以单条查询为缓存单位**：语义相近的查询被重复存储，浪费空间。
2. **用 LRU/LFU 淘汰**：按最近使用或频率淘汰，会误删“代表一大片查询空间”的高价值条目。
3. **所有请求都经过缓存层**：语义缓存用相似回答换性能，天然牺牲准确性；应在“性能优先于准确性”时才启用，例如负载可能违反 SLO 时。

作者的前提假设是“相似输入产生相似输出”。论文用 QQP、MRPC、MQP 等数据集观察到：重复问题对的余弦相似度中位数平均 0.82，非重复对平均 0.62；因此高阈值下可以把“同义”与“不同义”分开。

## C 方法机制

**质心缓存。** 离线把查询按余弦相似度聚类，每个簇只保留一个质心、对应输出和簇大小。论文在 Quora 与 Reddit 各 600K 问题上，以 0.86 为聚类阈值，得到 60K 个质心。在线时新查询先找最近质心；相似度超过检索阈值 `τ'` 就命中。

质心不是某条具体查询，而是“一片查询空间”的代表。缓存 60K 质心与缓存 600K 单条向量相比，论文报告约 10× 的内存节省；代价是输出与原始答案的余弦相似度从 0.92 降到 0.85。

**语义局部性替换。** 语义局部性指一个质心能代表多少语义相近的查询。密集簇的质心代表范围大，应优先常驻；稀疏簇的质心价值低，应优先淘汰。

作者跟踪四周的质心排名变化：26.5%（Quora）和 78.8%（Reddit）的质心排名变化小于 1%；96.1% 的质心排名变化不超过 10%；只有不到 4% 发生大变化。若缓存 10% 的质心，仅约 2.4% 需要替换。因此 SISO 不做频繁替换，只在长期监控触发时调整。

**动态阈值。** 阈值 `τ'` 控制“多相似才算命中”。论文给出两端：`τ'=0.98` 时命中率降到 0.24；`τ'=0.60` 时命中率升到 0.85，但回答质量下降。SISO 根据系统负载和目标 SLO 动态调整：负载重时放松阈值，增加命中、减轻 LLM 压力；负载轻时收紧阈值，优先质量。

**实现。** 离线路径做嵌入与聚类，在线路径查质心；用 HNSW，并把语义局部性强的质心放在更高层以减少遍历；用 T2H 表把查询映射到簇；SLO 监视器把系统负载反馈给阈值控制器。

## D 关键实验

| 实验 | 设置 | 结果 | 读法 |
|:--|:--|:--|:--|
| 测试平台 | Intel Core i5-8600K、1.5 TB DRAM、28 TB NVMe、8×48 GB A6000；vLLM 为基线；LLaMA-3.1-8B 与 70B | — | SISO 跑在 CPU/DRAM，vLLM 用 GPU |
| 数据与负载 | Quora、Reddit、MSMARCO、NQ、ShareGPT；95% 训练 / 5% 测试；Poisson 到达，变 RPS 与 CV；缓存容量为向量的 6% | — | 6% 是作者按生产部署保守选取的比例 |
| 质心 vs 单条缓存 | 60K 质心 vs GPTCache LRU 60K 向量 vs 全量 600K oracle | Centroid 输出相似度 0.85，Optimal 0.92；命中率比 GPTCache 高 1.27×（Quora）、1.14×（Reddit）；GPTCache 要达到可比命中率需多 1.85×/1.89× 内存 | 质心用少量精度换内存与命中；0.92 是 oracle，不是 GPTCache |
| 总体命中率 | 与 GPTCache 对比 | 质心缓存平均 1.54×；加入语义局部性替换后平均 1.71× | 两个数字口径不同，不要混用 |
| 替换策略 | 6% 容量；RR/FIFO/LFU/LRU vs SISO | SISO 比次优的 LFU 平均高 43% 命中率 | 语义局部性比时间/频率更稳 |
| 命中延迟 | LLaMA-3.1-8B | 命中 17 ms，GPTCache 27 ms；查找快 1.7× | 质心让 HNSW 遍历更短 |
| SLO | 目标 SLO 为 1.3× 端到端时延；RPS 扫描 | SISO 在 RPS 接近 30 时仍满足 SLO；其他系统更早失效 | 动态阈值把命中率换成 SLO |
| 负载波动 | CV 2–10 | 除 ShareGPT 外，SISO 在高 CV 下仍保持较高 SLO 达成率 | ShareGPT 长输入、代码/调试类查询削弱语义复用 |
| 质量 | Alpaca-eval，GPT-4 评判；F1 对比 GPT-4 参考答案 | 高负载下平均 Win rate 42.2%；F1 比 SISO-NoDTA / GPTCache / vLLM 高 1.17× / 1.26× / 1.71×；边际准确率下降 6.9% | 质量代价是“边际”的，但并非零 |

## E 对第一章的用法

| 维度 | 可用点 |
|:--|:--|
| 缓存对象 | `resp`：查询到回答，但存储单位是“质心 + 代表的一片查询空间”，不是单条历史回答。它把“缓存条目”从点变成区域 |
| 价值建模 | 簇大小近似未来复用概率；语义局部性近似“这条缓存能覆盖多少未来请求”；`τ'` 是质量—延迟旋钮。价值函数没有显式成本项，也没有正确率约束，而是用 SLO 达成率做系统级目标 |
| 生命周期 | 写入：离线聚类后写入质心；保留：局部性强的质心长期驻留；驱逐：按语义局部性，低频替换；刷新：依赖长期监控触发重聚类，论文未给具体周期；TTL/预取：无 |
| Flink 映射 | 以质心 id 为 key：`MapState` 存质心向量、输出、簇大小、局部性分数；broadcast state 下发当前 RPS/SLO/`τ'`；timer 触发周期性重聚类或替换评估；checkpoint 保存质心与簇统计。HNSW 索引作为可重建数据面 |
| 可写缺口 | 质心是离线批构建的，论文假设语义局部性在四周内稳定。流式 Agent 的话题漂移会让簇边界和“高价值质心”同时变化。可写“在线质心维护 + 漂移触发的重聚类”，并定义重聚类期间 Flink 状态的一致性；SISO 没有覆盖这一点 |

## F 局限与边界

- 只支持单轮查询；作者明确说多轮上下文查询不适用。对编码、调试、头脑风暴等“输入小变化导致输出大变化”的任务效果差。
- 依赖“相似输入产生相似输出”的假设；没有形式化正确率或错误率保证，质量用 Alpaca-eval 的 Win rate 与 F1 近似。
- 高负载下仍有 6.9% 的边际准确率下降；这是用质量换 SLO，不是无损。
- 评测是模拟到达（Poisson、可变 CV），不是生产 trace；缓存容量固定为 6%，只做了容量扫描，没有做故障、checkpoint、扩缩容实验。
- 质心聚类与替换策略都在单机 CPU/DRAM 上实现，没有流处理状态语义；也没有与 vCache 这类逐条目阈值方法正面对比。
- 未发现公开代码，复现需要自行实现聚类、HNSW 布局和 SLO 控制器。

## G 引用信息

```bibtex
@article{kim2025siso,
  title   = {Rethinking Caching for LLM Serving Systems: Beyond Traditional Heuristics},
  author  = {Kim, Jungwoo and Kim, Minsang and Lee, Jaeheon and Moon, Chanwoo and Kim, Heejin and Hwang, Taeho and Chung, Woosuk and Kim, Yeseong and Lee, Sungjin},
  journal = {arXiv preprint arXiv:2508.18736},
  year    = {2025},
  note    = {v1, 26 Aug 2025}
}
```

来源页面：arXiv 摘要页 `https://arxiv.org/abs/2508.18736`；本地 PDF `paper_source/SISO_arXiv2508.18736.pdf`。
