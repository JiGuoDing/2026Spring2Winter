# 论文出处总表

本表是 31 篇论文的出处基准。每篇解读页的 A 面板给出同一组字段的简版；若两者冲突，以本表和正式版为准。

## 使用约定

- “本地 PDF”列是 `paper_source/` 中的文件。部分文件是 arXiv 版，不是正式排版版；A 面板会写明版本边界。
- “DOI / URL”优先给正式出版页；没有正式 DOI 时给 arXiv 摘要页或会议页面。
- 预印本、workshop、invited talk 都在“发表”列明确标注，不与正式会议/期刊混用。

## 清单

### 1. vCache

- **完整题名**: vCache: Verified Semantic Prompt Caching
- **作者**: Luis Gaspar Schroeder、Aditya Desai、Alejandro Cuadron、Kyle Chu、Shu Liu、Mark Zhao、Stephan Krusche、Alfons Kemper、Matei Zaharia、Joseph E. Gonzalez
- **发表**: ICLR 2026（International Conference on Learning Representations）
- **页码 / 文章号**: ICLR 2026 会议论文；本地 PDF 无页码
- **DOI / URL**: https://arxiv.org/abs/2502.03771
- **arXiv**: arXiv:2502.03771v5
- **本地 PDF**: `paper_source/vCache.pdf`
- **解读**: `vCache_解读.html` / `vCache_解读.md`
- **版本边界**: v5 的 §5 正文写 Llama-3-8B-Instruct / GPT-4o-mini，Figure 4/5 图注出现 Llama 3.1-8B / GPT-4.1-nano；§3 概述与 Algorithm 1 对“是否总是入库”的写法也不完全一致。本文以正文和算法为准

### 2. Cortex

- **完整题名**: Cortex: Achieving Low-Latency, Cost-Efficient Remote Data Access For LLM via Semantic-Aware Knowledge Caching
- **作者**: Chaoyi Ruan、Chao Bi、Kaiwen Zheng、Ziji Shi、Xinyi Wan、Jialin Li
- **发表**: 23rd USENIX Symposium on Networked Systems Design and Implementation（NSDI 2026），2026-05-04 至 05-06，Renton, WA
- **页码 / 文章号**: pp. 2407–2421
- **DOI / URL**: https://www.usenix.org/conference/nsdi26/presentation/ruan-cortex
- **arXiv**: arXiv:2509.17360v2
- **本地 PDF**: `paper_source/Cortex.pdf`
- **解读**: `Cortex_解读.html` / `Cortex_解读.md`
- **版本边界**: arXiv v1 题名为 *Asteria: Semantic-Aware Cross-Region Caching for Agentic LLM Tool Access*，系统名 Asteria、索引名 Sine；v2 改为 Cortex / Seri。正式 PDF 与 v2 正文基本一致，仅多 USENIX 封面与版式

### 3. Krites

- **完整题名**: Asynchronous Verified Semantic Caching for Tiered LLM Architectures
- **作者**: Asmit Kumar Singh、Haozhe Wang、Santosh Attaluri、Tak Chiam、Weihua Zhu
- **发表**: arXiv 预印本，2026；本地 PDF 无正式会议/期刊信息
- **页码 / 文章号**: arXiv 预印本，7 页
- **DOI / URL**: https://arxiv.org/abs/2602.13165
- **arXiv**: arXiv:2602.13165
- **本地 PDF**: `paper_source/Krites_arXiv2602.13165.pdf`
- **解读**: `Krites_解读.html` / `Krites_解读.md`
- **版本边界**: 摘要写“up to 3.9 times”，正文与 Table 1 写 +136%（对话）与 +290%（搜索）。3.9× 与 +290% 是同一相对增益的不同表述，不能同时套到两个负载上

### 4. SISO

- **完整题名**: Rethinking Caching for LLM Serving Systems: Beyond Traditional Heuristics
- **作者**: Jungwoo Kim、Minsang Kim、Jaeheon Lee、Chanwoo Moon、Heejin Kim、Taeho Hwang、Woosuk Chung、Yeseong Kim、Sungjin Lee
- **发表**: arXiv 预印本，2025
- **页码 / 文章号**: arXiv 预印本，16 页
- **DOI / URL**: https://arxiv.org/abs/2508.18736
- **arXiv**: arXiv:2508.18736
- **本地 PDF**: `paper_source/SISO_arXiv2508.18736.pdf`
- **解读**: `SISO_解读.html` / `SISO_解读.md`
- **版本边界**: 只有 v1；摘要写“up to 1.71×”，引言同时出现“1.54× average”和“1.71× average”，两者分别对应质心缓存与局部性替换的增益，引用时需说明口径

### 5. GenCache

- **完整题名**: Generative Caching for Structurally Similar Prompts and Responses
- **作者**: Sarthak Chakraborty、Suman Nath、Xuchao Zhang、Chetan Bansal、Indranil Gupta
- **发表**: 39th Conference on Neural Information Processing Systems（NeurIPS 2025）
- **页码 / 文章号**: NeurIPS 2025；DOI 10.52202/085713-0162
- **DOI / URL**: https://proceedings.neurips.cc/paper_files/paper/2025/hash/07024f0479ae2f4981ed6cb3ebd81620-Abstract-Conference.html
- **arXiv**: 无 arXiv 版本；本地为 NeurIPS 正式 PDF
- **本地 PDF**: `paper_source/GenCache_NeurIPS2025.pdf`
- **解读**: `GenCache_解读.html` / `GenCache_解读.md`
- **版本边界**: 本地 PDF 为 NeurIPS 2025 版本；论文中的 FLASH 数据只覆盖 298 个事故、5 类场景，不能外推到全部云运维负载

### 6. IC-Cache

- **完整题名**: IC-Cache: Efficient Large Language Model Serving via In-context Caching
- **作者**: Yifan Yu、Yu Gan、Nikhil Sarda、Lillian Tsai、Jiaming Shen、Yanqi Zhou、Arvind Krishnamurthy、Fan Lai、Henry M. Levy、David E. Culler
- **发表**: ACM SIGOPS 31st Symposium on Operating Systems Principles（SOSP 2025），2025-10-13 至 10-16，Seoul
- **页码 / 文章号**: SOSP 2025, pp. 375–398
- **DOI / URL**: https://doi.org/10.1145/3731569.3764829
- **arXiv**: arXiv:2501.12689v3
- **本地 PDF**: `paper_source/IC-Cache_arXiv2501.12689.pdf`
- **解读**: `IC-Cache_解读.html` / `IC-Cache_解读.md`
- **版本边界**: 本地 PDF 为 arXiv v3，页眉标注 SOSP '25；正式版 24 页。实验覆盖数百万条公开请求，但不是生产 trace

### 7. AgenticPlanCaching

- **完整题名**: Agentic Plan Caching: Test-Time Memory for Fast and Cost-Efficient LLM Agents
- **作者**: Qizheng Zhang、Michael Wornow、Kunle Olukotun（NeurIPS 2025 版）；arXiv v2 增加 Gerry Wan
- **发表**: 39th Conference on Neural Information Processing Systems（NeurIPS 2025）
- **页码 / 文章号**: NeurIPS 2025；27 页
- **DOI / URL**: https://arxiv.org/abs/2506.14852
- **arXiv**: arXiv:2506.14852v2
- **本地 PDF**: `paper_source/AgenticPlanCaching_NeurIPS2025.pdf`
- **解读**: `AgenticPlanCaching_解读.html` / `AgenticPlanCaching_解读.md`
- **版本边界**: 本地 PDF 为 NeurIPS 版本（3 位作者）；arXiv v2 增加 Gerry Wan，并含更多附录。引用会议版时不要误加第四作者

### 8. MeanCache

- **完整题名**: MeanCache: User-Centric Semantic Caching for LLM Web Services
- **作者**: Waris Gill、Mohamed Elidrisi、Pallavi Kalapatapu、Ammar Ahmed、Ali Anwar、Muhammad Ali Gulzar
- **发表**: 2025 IEEE 39th International Parallel and Distributed Processing Symposium（IPDPS 2025），2025-06-03 至 06-07，Milan
- **页码 / 文章号**: IPDPS 2025, pp. 1298–1310
- **DOI / URL**: https://arxiv.org/abs/2403.02694
- **arXiv**: arXiv:2403.02694v4
- **本地 PDF**: `paper_source/MeanCache_arXiv2403.02694.pdf`
- **解读**: `MeanCache_解读.html` / `MeanCache_解读.md`
- **版本边界**: 本地 PDF 为 arXiv v4，页眉标注 Accepted at IPDPS 2025；正式版页码为 1298–1310，排版可能与本地 PDF 不同

### 9. CachedAttention

- **完整题名**: Cost-Efficient Large Language Model Serving for Multi-turn Conversations with CachedAttention
- **作者**: Bin Gao, Zhuomin He, Puru Sharma, Qingxuan Kang, Djordje Jevdjic, Junbo Deng, Xingkun Yang, Zhou Yu, Pengfei Zuo
- **发表**: 2024 USENIX Annual Technical Conference（USENIX ATC '24），pp. 111–126
- **页码 / 文章号**: USENIX ATC 2024, pp. 111–126
- **DOI / URL**: https://www.usenix.org/conference/atc24/presentation/gao-bin-cost
- **arXiv**: arXiv:2403.19708；本地 PDF 为 arXiv 版
- **本地 PDF**: `paper_source/CachedAttention_ATC2024.pdf`
- **解读**: `CachedAttention_解读.html` / `CachedAttention_解读.md`
- **版本边界**: 正式版与 arXiv v3 的题名一致；本地 PDF 为 arXiv v3，正式版页码据 ATC '24  proceedings

### 10. Pensieve

- **完整题名**: Stateful Large Language Model Serving with Pensieve
- **作者**: Lingfan Yu, Jinkun Lin, Jinyang Li
- **发表**: Twentieth European Conference on Computer Systems（EuroSys '25），2025-03-30 至 04-03，Rotterdam；pp. 144–158
- **页码 / 文章号**: EuroSys 2025, pp. 144–158
- **DOI / URL**: https://doi.org/10.1145/3689031.3696086
- **arXiv**: arXiv:2312.05516v3；本地 PDF 为 arXiv 版
- **本地 PDF**: `paper_source/Pensieve_arXiv2312.05516.pdf`
- **解读**: `Pensieve_解读.html` / `Pensieve_解读.md`
- **版本边界**: 本地 PDF 为 arXiv v3；EuroSys 正式版页码 144–158。论文注明早期草稿于 2023-12-09 上传 arXiv

### 11. Mooncake

- **完整题名**: Mooncake: Trading More Storage for Less Computation — A KVCache-centric Architecture for Serving LLM Chatbot
- **作者**: Ruoyu Qin, Zheming Li, Weiran He, Jialei Cui, Feng Ren, Mingxing Zhang, Yongwei Wu, Weimin Zheng, Xinran Xu
- **发表**: 23rd USENIX Conference on File and Storage Technologies（FAST '25），2025-02-25 至 02-27，Santa Clara；pp. 155–170；Best Paper
- **页码 / 文章号**: FAST 2025, pp. 155–170；ACM TOS 2025, DOI 10.1145/3773772
- **DOI / URL**: https://www.usenix.org/conference/fast25/presentation/qin
- **arXiv**: arXiv:2407.00079
- **本地 PDF**: `paper_source/Mooncake_FAST2025.pdf`
- **解读**: `Mooncake_解读.html` / `Mooncake_解读.md`
- **版本边界**: 实验用模拟 LLaMA3-70B 架构的 dummy model 与 Kimi 真实 trace 回放；生产统计与回放实验分开报告

### 12. Pie

- **完整题名**: Pie: A Programmable Serving System for Emerging LLM Applications
- **作者**: In Gim, Zhiyao Ma, Seung-seob Lee, Lin Zhong
- **发表**: ACM SIGOPS 31st Symposium on Operating Systems Principles（SOSP '25），2025-10-13 至 10-16，Seoul；pp. 415–430，16 页
- **页码 / 文章号**: SOSP 2025, pp. 415–430
- **DOI / URL**: https://doi.org/10.1145/3731569.3764814
- **arXiv**: arXiv:2510.24051v1；本地 PDF 为 arXiv 版
- **本地 PDF**: `paper_source/Pie_arXiv2510.24051.pdf`
- **解读**: `Pie_解读.html` / `Pie_解读.md`
- **版本边界**: 本地 PDF 为 arXiv v1；SOSP 正式版页码 415–430；两者技术内容一致

### 13. KVFlow

- **完整题名**: KVFlow: Efficient Prefix Caching for Accelerating LLM-Based Multi-Agent Workflows
- **作者**: Zaifeng Pan, Ajjkumar Patel, Yipeng Shen, Zhengding Hu, Yue Guan, Wan-Lu Li, Lianhui Qin, Yida Wang, Yufei Ding
- **发表**: 39th Conference on Neural Information Processing Systems（NeurIPS 2025）
- **页码 / 文章号**: NeurIPS 2025；页码未印
- **DOI / URL**: https://arxiv.org/abs/2507.07400
- **arXiv**: arXiv:2507.07400
- **本地 PDF**: `paper_source/KVFlow_NeurIPS2025.pdf`
- **解读**: `KVFlow_解读.html` / `KVFlow_解读.md`
- **版本边界**: 本地 PDF 为 NeurIPS 2025 排版版；无 arXiv 版本可对照

### 14. SmartCache

- **完整题名**: SmartCache: Context-aware Semantic Cache for Efficient Multi-turn LLM Inference
- **作者**: Chengye Yu, Tianyu Wang, Zili Shao, Song Jiang
- **发表**: 39th Conference on Neural Information Processing Systems（NeurIPS 2025）
- **页码 / 文章号**: NeurIPS 2025；页码未印
- **DOI / URL**: https://papers.nips.cc/paper_files/paper/2025/hash/fb74b63d225f846e6032bf3e3ab0f4ec-Abstract-Conference.html
- **arXiv**: 未发现 arXiv 版本；本地为 NeurIPS 正式 PDF
- **本地 PDF**: `paper_source/SmartCache_NeurIPS2025.pdf`
- **解读**: `SmartCache_解读.html` / `SmartCache_解读.md`
- **版本边界**: 本地 PDF 为 NeurIPS 2025 排版版；无 arXiv 版本可对照

### 15. Continuum

- **完整题名**: Continuum: Efficient and Robust Multi-Turn LLM Agent Scheduling with KV Cache Time-to-Live（正文标题栏拼作 “Continnum”）
- **作者**: Hanchen Li, Runyuan He, Qiuyang Mang, Qizheng Zhang, Huanzhi Mao, Xiaokun Chen, Hangrui Zhou, Huanchen Zhang, Alvin Cheung, Joseph Gonzalez, Ion Stoica
- **发表**: arXiv 2025；论文标注 PVLDB 20(1): XXX–XXX, 2027
- **页码 / 文章号**: arXiv 2025；论文标注 PVLDB 20(1), 2027（页码占位）
- **DOI / URL**: https://arxiv.org/abs/2511.02230
- **arXiv**: arXiv:2511.02230v7
- **本地 PDF**: `paper_source/Continuum_arXiv2511.02230.pdf`
- **解读**: `Continuum_解读.html` / `Continuum_解读.md`
- **版本边界**: 正文标题与正文均拼作 “Continnum”；任务说明确认正式名为 “Continuum”。本稿按正式名引用，正文事实取自 v7

### 16. Marconi

- **完整题名**: Marconi: Prefix Caching for the Era of Hybrid LLMs
- **作者**: Rui Pan, Zhuang Wang, Zhen Jia, Can Karakus, Luca Zancato, Tri Dao, Yida Wang, Ravi Netravali
- **发表**: 8th Conference on Machine Learning and Systems（MLSys 2025），Santa Clara
- **页码 / 文章号**: MLSys 2025；Outstanding Paper Honorable Mention
- **DOI / URL**: https://proceedings.mlsys.org/paper_files/paper/2025/hash/7c180af017258d239bac6248d1eb26ac-Abstract-Conference.html
- **arXiv**: 无 arXiv 版本；本地为 MLSys 正式 PDF
- **本地 PDF**: `paper_source/Marconi_MLSys2025.pdf`
- **解读**: `Marconi_解读.html` / `Marconi_解读.md`
- **版本边界**: 本地 PDF 为 MLSys 2025 排版版；实验模型为 7B Hybrid 与 Jamba-1.5-Mini

### 17. MemoryOS

- **完整题名**: Memory OS of AI Agent
- **作者**: Jiazheng Kang, Mingming Ji, Zhe Zhao, Ting Bai
- **发表**: 2025 Conference on Empirical Methods in Natural Language Processing（EMNLP 2025），pp. 25961–25970
- **页码 / 文章号**: EMNLP 2025, pp. 25961–25970
- **DOI / URL**: https://doi.org/10.18653/v1/2025.emnlp-main.1318
- **arXiv**: arXiv:2506.06326
- **本地 PDF**: `paper_source/MemoryOS_EMNLP2025.pdf`
- **解读**: `MemoryOS_解读.html` / `MemoryOS_解读.md`
- **版本边界**: 本地 PDF 为 EMNLP 2025 正式排版版；实验模型为 GPT-4o-mini、Qwen2.5-3B/7B

### 18. RAGCache

- **完整题名**: RAGCache: Efficient Knowledge Caching for Retrieval-Augmented Generation
- **作者**: Chao Jin, Zili Zhang, Xuanlin Jiang, Fangyue Liu, Xin Liu, Xuanzhe Liu, Xin Jin
- **发表**: ACM Transactions on Computer Systems（TOCS），2025，Vol. 44，No. 1，Article 2
- **页码 / 文章号**: ACM TOCS 2025, Vol. 44, No. 1, Article 2
- **DOI / URL**: https://doi.org/10.1145/3768628
- **arXiv**: arXiv:2404.12457v2；本地 PDF 为 arXiv 版
- **本地 PDF**: `paper_source/RAGCache_arXiv2404.12457.pdf`
- **解读**: `RAGCache_解读.html` / `RAGCache_解读.md`
- **版本边界**: 本文数字均取自 arXiv v2；TOCS 排版版可能有差异

### 19. Cache-Craft

- **完整题名**: Cache-Craft: Managing Chunk-Caches for Efficient Retrieval-Augmented Generation
- **作者**: Shubham Agarwal, Sai Sundaresan, Subrata Mitra, Debabrata Mahapatra, Archit Gupta, Rounak Sharma, Nirmal Joshua Kapu, Tong Yu, Shiv Saini
- **发表**: ACM SIGMOD 2025
- **页码 / 文章号**: SIGMOD 2025；页码未印
- **DOI / URL**: https://arxiv.org/abs/2502.15734
- **arXiv**: arXiv:2502.15734v1；本地 PDF 为 arXiv 版
- **本地 PDF**: `paper_source/CacheCraft_arXiv2502.15734.pdf`
- **解读**: `Cache-Craft_解读.html` / `Cache-Craft_解读.md`
- **版本边界**: 数字来自 arXiv v1；SIGMOD 正式版可能有排版与数字差异

### 20. TurboRAG

- **完整题名**: TurboRAG: Accelerating Retrieval-Augmented Generation with Precomputed KV Caches for Chunked Text
- **作者**: Songshuo Lu, Hua Wang, Yutian Rong, Zhi Chen, Yaohua Tang
- **发表**: EMNLP 2025，pp. 6588–6601
- **页码 / 文章号**: EMNLP 2025, pp. 6588–6601
- **DOI / URL**: https://doi.org/10.18653/v1/2025.emnlp-main.334
- **arXiv**: 无 arXiv 正式引用；本地为 ACL 正式 PDF
- **本地 PDF**: `paper_source/TurboRAG_EMNLP2025.pdf`
- **解读**: `TurboRAG_解读.html` / `TurboRAG_解读.md`
- **版本边界**: 数字来自 EMNLP 2025 正式版；模型为 Qwen2-7B，另测 LLaMA-3.1-8B

### 21. CacheBlend

- **完整题名**: CacheBlend: Fast Large Language Model Serving for RAG with Cached Knowledge Fusion
- **作者**: Jiayi Yao, Hanchen Li, Yuhan Liu, Siddhant Ray, Yihua Cheng, Qizheng Zhang, Kuntai Du, Shan Lu, Junchen Jiang
- **发表**: EuroSys 2025（第 20 届欧洲计算机系统会议），Rotterdam，pp. 94–109；Best Paper
- **页码 / 文章号**: EuroSys 2025, pp. 94–109；ACM TOCS 2025, DOI 10.1145/3790254
- **DOI / URL**: https://doi.org/10.1145/3689031.3696098
- **arXiv**: arXiv:2405.16444v3；本地 PDF 为 arXiv 版
- **本地 PDF**: `paper_source/CacheBlend_arXiv2405.16444.pdf`
- **解读**: `CacheBlend_解读.html` / `CacheBlend_解读.md`
- **版本边界**: 数字取自 arXiv v3；与 EuroSys 正式版可能存在排版差异；Best Paper 称号来自会议信息

### 22. ContextPilot

- **完整题名**: ContextPilot: Fast Long-Context Inference via Context Reuse
- **作者**: Yinsicheng Jiang, Yeqi Huang, Liang Cheng, Cheng Deng, Xuan Sun, Luo Mai
- **发表**: Proceedings of the 9th MLSys Conference，Bellevue, WA, USA，2026
- **页码 / 文章号**: MLSys 2026；页码未印
- **DOI / URL**: https://proceedings.mlsys.org/paper_files/paper/2026/hash/b0131b6ee02a00b03fc3320176fec8f5-Abstract-Conference.html
- **arXiv**: arXiv:2511.03475v4
- **本地 PDF**: `paper_source/ContextPilot_MLSys2026.pdf`
- **解读**: `ContextPilot_解读.html` / `ContextPilot_解读.md`
- **版本边界**: 数字来自 arXiv v4；MLSys 正式版可能有差异

### 23. FreshCache

- **完整题名**: Risk-Constrained Freshness-Aware Semantic Caching for Open-Web Retrieval-Augmented LLMs
- **作者**: Muhammad Mansoor, Tahir Ahmad, Yeo-Chan Yoon
- **发表**: arXiv 预印本，2026
- **页码 / 文章号**: arXiv 预印本，16 页
- **DOI / URL**: https://arxiv.org/abs/2607.04281
- **arXiv**: arXiv:2607.04281v1
- **本地 PDF**: `paper_source/FreshCache_arXiv2607.04281.pdf`
- **解读**: `FreshCache_解读.html` / `FreshCache_解读.md`
- **版本边界**: 所有数字来自 arXiv v1；未经同行评审的正式版校验

### 24. FinCacheServe

- **完整题名**: FinCacheServe: Dependency-Consistent Answer Reuse for Cost-Efficient RAG Serving over Mutable Enterprise Documents
- **作者**: Lingteng Zeng, Yifan Jin
- **发表**: arXiv 预印本，2026
- **页码 / 文章号**: arXiv 预印本，16 页
- **DOI / URL**: https://arxiv.org/abs/2607.26076
- **arXiv**: arXiv:2607.26076v1
- **本地 PDF**: `paper_source/FinCacheServe_arXiv2607.26076.pdf`
- **解读**: `FinCacheServe_解读.html` / `FinCacheServe_解读.md`
- **版本边界**: 所有数字来自 arXiv v1；单机 vLLM 与归档 trace 回放

### 25. LMCache

- **完整题名**: LMCache: An Efficient KV Cache Layer for Enterprise-Scale LLM Inference
- **作者**: Yuhan Liu\*, Jiayi Yao\*, Yihua Cheng\*, Yuwei An, Xiaokun Chen, Shaoting Feng, Yuyang Huang, Samuel Shen, Rui Zhang, Kuntai Du, Junchen Jiang（\* 同等贡献）
- **发表**: arXiv 2025；任务清单标注 MLSys 2026 invited talk（论文正文未提及该信息）
- **页码 / 文章号**: arXiv 预印本，19 页；MLSys 2026 invited talk（论文正文未提）
- **DOI / URL**: https://arxiv.org/abs/2510.09665
- **arXiv**: arXiv:2510.09665v2
- **本地 PDF**: `paper_source/LMCache_arXiv2510.09665.pdf（19 页）`
- **解读**: `LMCache_解读.html` / `LMCache_解读.md`
- **版本边界**: 实测 LMCACHE v0.3.6；基线为 vLLM v0.10.2 与 v0.11.0；商业 API 只做黑盒对比

### 26. PromptPeek

- **完整题名**: I Know What You Asked: Prompt Leakage via KV-Cache Sharing in Multi-Tenant LLM Serving
- **作者**: Guanlong Wu, Zheng Zhang, Yao Zhang, Weili Wang, Jianyu Niu, Ye Wu, Yinqian Zhang（通讯作者）
- **发表**: Network and Distributed System Security (NDSS) Symposium 2025，2025-02-24/28，San Diego
- **页码 / 文章号**: NDSS 2025；15 页
- **DOI / URL**: https://www.ndss-symposium.org/wp-content/uploads/2025-1772-paper.pdf
- **arXiv**: 未发现 arXiv 版本；本地为 NDSS 正式 PDF
- **本地 PDF**: `paper_source/PromptPeek_NDSS2025.pdf（15 页）`
- **解读**: `PromptPeek_解读.html` / `PromptPeek_解读.md`
- **版本边界**: 实验基于 SGLang，具体版本论文未给出；单张 A100 80G；目标模型 Llama2-13B

### 27. SCBench

- **完整题名**: SCBench: A KV Cache-Centric Analysis of Long-Context Methods
- **作者**: Yucheng Li†, Huiqiang Jiang‡, Qianhui Wu, Xufang Luo, Surin Ahn, Chengruidong Zhang, Amir H. Abdi, Dongsheng Li, Jianfeng Gao, Yuqing Yang, Lili Qiu
- **发表**: International Conference on Learning Representations (ICLR) 2025
- **页码 / 文章号**: ICLR 2025；31 页
- **DOI / URL**: https://proceedings.iclr.cc/paper_files/paper/2025/hash/a540b17fb2295c736d5afd6c507acf66-Abstract-Conference.html
- **arXiv**: 未发现 arXiv 版本；项目页 https://aka.ms/SCBench
- **本地 PDF**: `paper_source/SCBench_ICLR2025.pdf（31 页）`
- **解读**: `SCBench_解读.html` / `SCBench_解读.md`
- **版本边界**: ICLR 2025 camera-ready；评测截至该版本，未覆盖 2025 年后的新方法

### 28. AdaptCache

- **完整题名**: AdaptCache: KV Cache Native Storage Hierarchy for Low-Delay and High-Quality Language Model Serving
- **作者**: Shaoting Feng\*, Hanchen Li\*, Kuntai Du, Zhuohan Gu, Yuhan Liu, Jiayi Yao, Siddhant Ray, Samuel Shen, Yihua Cheng, Ganesh Ananthanarayanan, Junchen Jiang（\* 同等贡献）
- **发表**: SOSP 2025 BigMem Workshop（按任务清单；论文正文未标注会议信息）
- **页码 / 文章号**: SOSP 2025 BigMem Workshop；3 页 preliminary results
- **DOI / URL**: https://arxiv.org/abs/2509.00105
- **arXiv**: arXiv:2509.00105v2
- **本地 PDF**: `paper_source/AdaptCache_arXiv2509.00105.pdf（3 页）`
- **解读**: `AdaptCache_解读.html` / `AdaptCache_解读.md`
- **版本边界**: 3 页 preliminary results；单张 A100（100 GB DRAM、400 GB SSD）；Llama-3.1-8B-Instruct

### 29. KVCacheCostModel

- **完整题名**: Towards More Economical Context-Augmented LLM Generation by Reusing Stored KV Cache
- **作者**: Hanchen Li\*, Yuhan Liu\*, Yihua Cheng, Kuntai Du, Junchen Jiang（\* 同等贡献）
- **发表**: arXiv 2025；会议/期刊正式发表信息论文未给出
- **页码 / 文章号**: arXiv 2025；2 页 poster
- **DOI / URL**: https://arxiv.org/abs/2503.14647
- **arXiv**: arXiv:2503.14647v1
- **本地 PDF**: `paper_source/KVCacheCostModel_arXiv2503.14647.pdf（2 页）`
- **解读**: `KVCacheCostModel_解读.html` / `KVCacheCostModel_解读.md`
- **版本边界**: 解析模型 + 初步仿真；Llama-7B、4×V100；不是完整系统实现

### 30. AWM

- **完整题名**: Agent Workflow Memory
- **作者**: Zora Zhiruo Wang, Jiayuan Mao, Daniel Fried, Graham Neubig
- **发表**: Proceedings of the 42nd International Conference on Machine Learning (ICML), Vancouver, 2025；PMLR 267
- **页码 / 文章号**: ICML 2025, PMLR 267:63897–63911
- **DOI / URL**: https://proceedings.mlr.press/v267/wang25bx.html
- **arXiv**: arXiv:2409.07429
- **本地 PDF**: `paper_source/AWM_ICML2025.pdf（15 页）`
- **解读**: `AWM_解读.html` / `AWM_解读.md`
- **版本边界**: ICML 2025 正式版；实验模型为 GPT-4o / GPT-4 / GPT-3.5-turbo，温度 0

### 31. KVShare

- **完整题名**: KVShare: An LLM Service System with Efficient and Effective Multi-Tenant KV Cache Reuse
- **作者**: Huan Yang, Renji Zhang, Mingzhe Huang, Weijun Wang, Yin Tang, Yuanchun Li, Yunxin Liu, Deyu Zhang
- **发表**: arXiv 2025 预印本；论文标注 “Preprint. Under review.”，正式发表信息论文未给出
- **页码 / 文章号**: arXiv 2025；22 页；论文标注 Preprint. Under review.
- **DOI / URL**: https://arxiv.org/abs/2503.16525
- **arXiv**: arXiv:2503.16525v2
- **本地 PDF**: `paper_source/KVShare_arXiv2503.16525.pdf（22 页）`
- **解读**: `KVShare_解读.html` / `KVShare_解读.md`
- **版本边界**: 基于 vLLM 0.4.1，约 2K 行 Python；单张 NVIDIA L40S；3 个模型
