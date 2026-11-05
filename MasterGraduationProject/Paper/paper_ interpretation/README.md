# 论文原文与解读索引

本目录保存 `MasterGraduationProject/Paper/paper_source/` 中 31 篇论文的中文解读。每篇解读有 HTML 与 Markdown 两个版本。

## 目录约定

- 原文：`../paper_source/<file>.pdf`
- 解读 HTML：`<短名>_解读.html`
- 解读 Markdown：`<短名>_解读.md`

## 论文清单

| 短名 | 完整题名 | 作者 | 出处 | 类型 | DOI / arXiv | 原文 | 解读 |
|:--|:--|:--|:--|:--|:--|:--|:--|
| vCache | vCache: Verified Semantic Prompt Caching | Luis Gaspar Schroeder、Aditya Desai、Alejandro Cuadron、Kyle Chu、Shu Liu、Mark Zhao、Stephan Krusche、Alfons Kemper、Matei Zaharia、Joseph E. Gonzalez | ICLR 2026（International Conference on Learning Representations） | resp | arXiv:2502.03771v5（2026-02-21）；论文未印 DOI | `paper_source/vCache.pdf` | `vCache_解读.html` |
| Cortex | Cortex: Achieving Low-Latency, Cost-Efficient Remote Data Access For LLM via Semantic-Aware Knowledge Caching | Chaoyi Ruan、Chao Bi、Kaiwen Zheng、Ziji Shi、Xinyi Wan、Jialin Li | 23rd USENIX Symposium on Networked Systems Design and Implementation（NSDI 2026），2026-05-04 至 05-06，Renton, WA | resp / rag | arXiv:2509.17360v2（2026-02-03）；USENIX 正式版未印会议 DOI | `paper_source/Cortex.pdf` | `Cortex_解读.html` |
| Krites | Asynchronous Verified Semantic Caching for Tiered LLM Architectures | Asmit Kumar Singh、Haozhe Wang、Santosh Attaluri、Tak Chiam、Weihua Zhu | arXiv 预印本，2026；本地 PDF 无正式会议/期刊信息 | resp | arXiv:2602.13165v2 [cs.IR]（2026-03-12）；论文未印 DOI | `paper_source/Krites_arXiv2602.13165.pdf` | `Krites_解读.html` |
| SISO | Rethinking Caching for LLM Serving Systems: Beyond Traditional Heuristics | Jungwoo Kim、Minsang Kim、Jaeheon Lee、Chanwoo Moon、Heejin Kim、Taeho Hwang、Woosuk Chung、Yeseong Kim、Sungjin Lee | arXiv 预印本，2025 | resp | arXiv:2508.18736v1 [cs.DB]（2025-08-26）；论文未印 DOI | `paper_source/SISO_arXiv2508.18736.pdf` | `SISO_解读.html` |
| GenCache | Generative Caching for Structurally Similar Prompts and Responses | Sarthak Chakraborty、Suman Nath、Xuchao Zhang、Chetan Bansal、Indranil Gupta | 39th Conference on Neural Information Processing Systems（NeurIPS 2025） | resp | arXiv:2511.17565v1（2025-11-14）；DOI 10.52202/085713-0162 | `paper_source/GenCache_NeurIPS2025.pdf` | `GenCache_解读.html` |
| IC-Cache | IC-Cache: Efficient Large Language Model Serving via In-context Caching | Yifan Yu、Yu Gan、Nikhil Sarda、Lillian Tsai、Jiaming Shen、Yanqi Zhou、Arvind Krishnamurthy、Fan Lai、Henry M. Levy、David E. Culler | ACM SIGOPS 31st Symposium on Operating Systems Principles（SOSP 2025），2025-10-13 至 10-16，Seoul | resp | arXiv:2501.12689v3（2025-09-04）；DOI 10.1145/3731569.3764829 | `paper_source/IC-Cache_arXiv2501.12689.pdf` | `IC-Cache_解读.html` |
| AgenticPlanCaching | Agentic Plan Caching: Test-Time Memory for Fast and Cost-Efficient LLM Agents | Qizheng Zhang、Michael Wornow、Kunle Olukotun（NeurIPS 2025 版）；arXiv v2 增加 Gerry Wan | 39th Conference on Neural Information Processing Systems（NeurIPS 2025） | plan / resp | arXiv:2506.14852v2（2026-01-26）；论文未印 DOI | `paper_source/AgenticPlanCaching_NeurIPS2025.pdf` | `AgenticPlanCaching_解读.html` |
| MeanCache | MeanCache: User-Centric Semantic Caching for LLM Web Services | Waris Gill、Mohamed Elidrisi、Pallavi Kalapatapu、Ammar Ahmed、Ali Anwar、Muhammad Ali Gulzar | 2025 IEEE 39th International Parallel and Distributed Processing Symposium（IPDPS 2025），2025-06-03 至 06-07，Milan | resp | arXiv:2403.02694v4（2025-03-07）；DOI 10.1109/IPDPS64566.2025.00117 | `paper_source/MeanCache_arXiv2403.02694.pdf` | `MeanCache_解读.html` |
| CachedAttention | Cost-Efficient Large Language Model Serving for Multi-turn Conversations with CachedAttention | Bin Gao, Zhuomin He, Puru Sharma, Qingxuan Kang, Djordje Jevdjic, Junbo Deng, Xingkun Yang, Zhou Yu, Pengfei Zuo | 2024 USENIX Annual Technical Conference（USENIX ATC '24），pp. 111–126 | ctx | arXiv:2403.19708v3 [cs.CL]，2024-06-30；DOI 论文未给出 | `paper_source/CachedAttention_ATC2024.pdf` | `CachedAttention_解读.html` |
| Pensieve | Stateful Large Language Model Serving with Pensieve | Lingfan Yu, Jinkun Lin, Jinyang Li | Twentieth European Conference on Computer Systems（EuroSys '25），2025-03-30 至 04-03，Rotterdam；pp. 144–158 | ctx | arXiv:2312.05516v3 [cs.LG]，2024-10-07；DOI 10.1145/3689031.3696086 | `paper_source/Pensieve_arXiv2312.05516.pdf` | `Pensieve_解读.html` |
| Mooncake | Mooncake: Trading More Storage for Less Computation — A KVCache-centric Architecture for Serving LLM Chatbot | Ruoyu Qin, Zheming Li, Weiran He, Jialei Cui, Feng Ren, Mingxing Zhang, Yongwei Wu, Weimin Zheng, Xinran Xu | 23rd USENIX Conference on File and Storage Technologies（FAST '25），2025-02-25 至 02-27，Santa Clara；pp. 155–170；Best Paper | ctx | 论文未给出 arXiv 编号；DOI 论文未给出；ISBN 978-1-939133-45-8 | `paper_source/Mooncake_FAST2025.pdf` | `Mooncake_解读.html` |
| Pie | Pie: A Programmable Serving System for Emerging LLM Applications | In Gim, Zhiyao Ma, Seung-seob Lee, Lin Zhong | ACM SIGOPS 31st Symposium on Operating Systems Principles（SOSP '25），2025-10-13 至 10-16，Seoul；pp. 415–430，16 页 | ctx | arXiv:2510.24051v1 [cs.CL]，2025-10-28；DOI 10.1145/3731569.3764814 | `paper_source/Pie_arXiv2510.24051.pdf` | `Pie_解读.html` |
| KVFlow | KVFlow: Efficient Prefix Caching for Accelerating LLM-Based Multi-Agent Workflows | Zaifeng Pan, Ajjkumar Patel, Yipeng Shen, Zhengding Hu, Yue Guan, Wan-Lu Li, Lianhui Qin, Yida Wang, Yufei Ding | 39th Conference on Neural Information Processing Systems（NeurIPS 2025） | ctx | 论文未给出 arXiv 编号；DOI 论文未给出 | `paper_source/KVFlow_NeurIPS2025.pdf` | `KVFlow_解读.html` |
| SmartCache | SmartCache: Context-aware Semantic Cache for Efficient Multi-turn LLM Inference | Chengye Yu, Tianyu Wang, Zili Shao, Song Jiang | 39th Conference on Neural Information Processing Systems（NeurIPS 2025） | ctx / resp | 论文未给出 arXiv 编号；DOI 论文未给出 | `paper_source/SmartCache_NeurIPS2025.pdf` | `SmartCache_解读.html` |
| Continuum | Continuum: Efficient and Robust Multi-Turn LLM Agent Scheduling with KV Cache Time-to-Live（正文标题栏拼作 “Continnum”） | Hanchen Li, Runyuan He, Qiuyang Mang, Qizheng Zhang, Huanzhi Mao, Xiaokun Chen, Hangrui Zhou, Huanchen Zhang, Alvin Cheung, Joseph Gonzalez, Ion Stoica | arXiv 2025；论文标注 PVLDB 20(1): XXX–XXX, 2027 | ctx | arXiv:2511.02230v7 [cs.OS]；DOI 论文写作 XX.XX/XXX.XX，未给出 | `paper_source/Continuum_arXiv2511.02230.pdf` | `Continuum_解读.html` |
| Marconi | Marconi: Prefix Caching for the Era of Hybrid LLMs | Rui Pan, Zhuang Wang, Zhen Jia, Can Karakus, Luca Zancato, Tri Dao, Yida Wang, Ravi Netravali | 8th Conference on Machine Learning and Systems（MLSys 2025），Santa Clara | ctx | 论文未给出 arXiv 编号；DOI 论文未给出 | `paper_source/Marconi_MLSys2025.pdf` | `Marconi_解读.html` |
| MemoryOS | Memory OS of AI Agent | Jiazheng Kang, Mingming Ji, Zhe Zhao, Ting Bai | 2025 Conference on Empirical Methods in Natural Language Processing（EMNLP 2025），pp. 25961–25970 | ctx | 论文未给出 arXiv 编号；DOI 论文未给出 | `paper_source/MemoryOS_EMNLP2025.pdf` | `MemoryOS_解读.html` |
| RAGCache | RAGCache: Efficient Knowledge Caching for Retrieval-Augmented Generation | Chao Jin, Zili Zhang, Xuanlin Jiang, Fangyue Liu, Xin Liu, Xuanzhe Liu, Xin Jin | ACM Transactions on Computer Systems（TOCS），2025，Vol. 44，No. 1，Article 2 | rag | arXiv:2404.12457v2 [cs.DC]，25 Apr 2024；DOI 论文未给出 | `paper_source/RAGCache_arXiv2404.12457.pdf` | `RAGCache_解读.html` |
| Cache-Craft | Cache-Craft: Managing Chunk-Caches for Efficient Retrieval-Augmented Generation | Shubham Agarwal, Sai Sundaresan, Subrata Mitra, Debabrata Mahapatra, Archit Gupta, Rounak Sharma, Nirmal Joshua Kapu, Tong Yu, Shiv Saini | ACM SIGMOD 2025 | rag | arXiv:2502.15734v1 [cs.DC]，5 Feb 2025；DOI 论文未给出 | `paper_source/CacheCraft_arXiv2502.15734.pdf` | `Cache-Craft_解读.html` |
| TurboRAG | TurboRAG: Accelerating Retrieval-Augmented Generation with Precomputed KV Caches for Chunked Text | Songshuo Lu, Hua Wang, Yutian Rong, Zhi Chen, Yaohua Tang | EMNLP 2025，pp. 6588–6601 | rag | 论文未给出 arXiv 编号；DOI 论文未给出 | `paper_source/TurboRAG_EMNLP2025.pdf` | `TurboRAG_解读.html` |
| CacheBlend | CacheBlend: Fast Large Language Model Serving for RAG with Cached Knowledge Fusion | Jiayi Yao, Hanchen Li, Yuhan Liu, Siddhant Ray, Yihua Cheng, Qizheng Zhang, Kuntai Du, Shan Lu, Junchen Jiang | EuroSys 2025（第 20 届欧洲计算机系统会议），Rotterdam，pp. 94–109；Best Paper | rag | arXiv:2405.16444v3 [cs.LG]，3 Apr 2025；DOI 10.1145/3689031.3696098 | `paper_source/CacheBlend_arXiv2405.16444.pdf` | `CacheBlend_解读.html` |
| ContextPilot | ContextPilot: Fast Long-Context Inference via Context Reuse | Yinsicheng Jiang, Yeqi Huang, Liang Cheng, Cheng Deng, Xuan Sun, Luo Mai | Proceedings of the 9th MLSys Conference，Bellevue, WA, USA，2026 | rag | arXiv:2511.03475v4 [cs.LG]，6 May 2026；DOI 论文未给出 | `paper_source/ContextPilot_MLSys2026.pdf` | `ContextPilot_解读.html` |
| FreshCache | Risk-Constrained Freshness-Aware Semantic Caching for Open-Web Retrieval-Augmented LLMs | Muhammad Mansoor, Tahir Ahmad, Yeo-Chan Yoon | arXiv 预印本，2026 | rag | arXiv:2607.04281v1 [cs.CL]，5 Jul 2026；DOI 论文未给出 | `paper_source/FreshCache_arXiv2607.04281.pdf` | `FreshCache_解读.html` |
| FinCacheServe | FinCacheServe: Dependency-Consistent Answer Reuse for Cost-Efficient RAG Serving over Mutable Enterprise Documents | Lingteng Zeng, Yifan Jin | arXiv 预印本，2026 | rag / resp | arXiv:2607.26076v1 [cs.IR]，14 Jul 2026；DOI 论文未给出 | `paper_source/FinCacheServe_arXiv2607.26076.pdf` | `FinCacheServe_解读.html` |
| LMCache | LMCache: An Efficient KV Cache Layer for Enterprise-Scale LLM Inference | Yuhan Liu\*, Jiayi Yao\*, Yihua Cheng\*, Yuwei An, Xiaokun Chen, Shaoting Feng, Yuyang Huang, Samuel Shen, Rui Zhang, Kuntai Du, Junchen Jiang（\* 同等贡献） | arXiv 2025；任务清单标注 MLSys 2026 invited talk（论文正文未提及该信息） | ctx | arXiv:2510.09665v2 [cs.LG]；DOI 论文未给出 | `paper_source/LMCache_arXiv2510.09665.pdf` | `LMCache_解读.html` |
| PromptPeek | I Know What You Asked: Prompt Leakage via KV-Cache Sharing in Multi-Tenant LLM Serving | Guanlong Wu, Zheng Zhang, Yao Zhang, Weili Wang, Jianyu Niu, Ye Wu, Yinqian Zhang（通讯作者） | Network and Distributed System Security (NDSS) Symposium 2025，2025-02-24/28，San Diego | ctx / 安全 | DOI 10.14722/ndss.2025.241772；arXiv 编号论文未给出 | `paper_source/PromptPeek_NDSS2025.pdf` | `PromptPeek_解读.html` |
| SCBench | SCBench: A KV Cache-Centric Analysis of Long-Context Methods | Yucheng Li†, Huiqiang Jiang‡, Qianhui Wu, Xufang Luo, Surin Ahn, Chengruidong Zhang, Amir H. Abdi, Dongsheng Li, Jianfeng Gao, Yuqing Yang, Lili Qiu | International Conference on Learning Representations (ICLR) 2025 | ctx / 评测 | DOI 论文未给出；arXiv 编号论文未给出；项目页 https://aka.ms/SCBench | `paper_source/SCBench_ICLR2025.pdf` | `SCBench_解读.html` |
| AdaptCache | AdaptCache: KV Cache Native Storage Hierarchy for Low-Delay and High-Quality Language Model Serving | Shaoting Feng\*, Hanchen Li\*, Kuntai Du, Zhuohan Gu, Yuhan Liu, Jiayi Yao, Siddhant Ray, Samuel Shen, Yihua Cheng, Ganesh Ananthanarayanan, Junchen Jiang（\* 同等贡献） | SOSP 2025 BigMem Workshop（按任务清单；论文正文未标注会议信息） | ctx | arXiv:2509.00105v2 [cs.OS]；DOI 论文未给出 | `paper_source/AdaptCache_arXiv2509.00105.pdf` | `AdaptCache_解读.html` |
| KVCacheCostModel | Towards More Economical Context-Augmented LLM Generation by Reusing Stored KV Cache | Hanchen Li\*, Yuhan Liu\*, Yihua Cheng, Kuntai Du, Junchen Jiang（\* 同等贡献） | arXiv 2025；会议/期刊正式发表信息论文未给出 | 价值模型 | arXiv:2503.14647v1 [cs.NI]；DOI 论文未给出 | `paper_source/KVCacheCostModel_arXiv2503.14647.pdf` | `KVCacheCostModel_解读.html` |
| AWM | Agent Workflow Memory | Zora Zhiruo Wang, Jiayuan Mao, Daniel Fried, Graham Neubig | Proceedings of the 42nd International Conference on Machine Learning (ICML), Vancouver, 2025；PMLR 267 | plan / memory | DOI 论文未给出；arXiv 编号论文未给出 | `paper_source/AWM_ICML2025.pdf` | `AWM_解读.html` |
| KVShare | KVShare: An LLM Service System with Efficient and Effective Multi-Tenant KV Cache Reuse | Huan Yang, Renji Zhang, Mingzhe Huang, Weijun Wang, Yin Tang, Yuanchun Li, Yunxin Liu, Deyu Zhang | arXiv 2025 预印本；论文标注 “Preprint. Under review.”，正式发表信息论文未给出 | ctx / 多租户 | arXiv:2503.16525v2 [cs.CL]；DOI 论文未给出 | `paper_source/KVShare_arXiv2503.16525.pdf` | `KVShare_解读.html` |

## 使用说明

- 引用论文时，以解读页 A 面板的“发表 / 正式版本 / arXiv / DOI”字段为准。
- 预印本标注 `arXiv`；workshop 标注 `Workshop`；正式会议/期刊标注具体会议或期刊。
- 论文的 headline 数字有负载条件。写进论文前，先读解读页 D 面板的实验设置与 F 面板的证据边界。
- 若正式版与 arXiv 版数字不一致，以正式版为准，并在引用中注明版本。

## 重新渲染

单篇：

```bash
node "C:/Users/48520/.config/opencode/skills/answer-me-with-html/scripts/am.mjs" render "<短名>_解读.md" --no-open -o "<短名>_解读.html"
```

总览：

```bash
node "C:/Users/48520/.config/opencode/skills/answer-me-with-html/scripts/am.mjs" render "00_文献解读总览.md" --no-open -o "00_文献解读总览.html"
```
