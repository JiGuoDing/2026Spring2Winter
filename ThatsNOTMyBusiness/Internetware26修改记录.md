# Internetware '26 投稿 —— 初版修改记录

## 1. Introduction

- 将原本 Introduction 中的 Organization Structure of This Paper 子章节删去
- 将原本 Introduction 中的剩余 4 个子章节融合为一个完整的章节
- 对融合后的完整的章节进行了内容精简，主要是对与 related work 有关的部分进行了内容提炼 (原来对每个 related work 都进行了详细描述，篇幅过长)；后续考虑单独列为一章 related work

## 2. Background Knowledge

- 精简了子章节 2.1 和 2.2 的表述
- 对容器、虚拟机等技术背景进行简化阐述，不再以类似科普的方式对这些云原生技术进行深入剖析，而是把重心放在容器化与虚拟机的对比上，说明云原生环境的优越性
- 精简对 MPI 的出现背景的讲解，并且对 MPI 涉及的具体操作的描述进行了简化

## 3. Memory Bandwidth-Aware Elastic Scaling Mechanism for MPI Jobs in Cloud-Native Environments

- 将本章序言以及 3.1 子章节进行缩减，把 3.1 章节中的问题背景和问题分析以及动机实验拆解到 3.2, 3.3 子章节中
- 删除了冗余的背景铺垫和重复性解释文字

## 4. Experimental Evaluation and Analysis

- 将原本第三章中的实验部分单独拎出来作为独立的一章
- 将最后的 Chapter Summary 章节删去
- 重新绘制部分图片

## 5. Conclusion and Future Work

- 将原本 Conclusion 和 Future Work 两个子章节合并
- 删去了关于云原生技术发展方向等冗余铺垫内容
- 保留对两种模式（性能最优/成本最优）的核心描述，删去重复性解释内容
- 保留 Future Work 对两个研究方向的核心内容 (multi-dimensional performance bottleneck awareness, real-time monitoring mechanism)，删去了详细展开的说明

## 6. 其他修改内容

- 修改了文中的文献引用格式
- 对一些孤行寡字进行补全
