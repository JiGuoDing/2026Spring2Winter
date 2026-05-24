# Ray面试题

## prompt

你是 Ray 及分布式计算系统方面的专家。我正在为应聘分布式系统、机器学习基础设施、实时/离线计算平台、后端开发等相关岗位做面试准备。接下来我会向你提问一些与 Ray、分布式任务调度、分布式训练、分布式推理、资源管理、容错机制以及后端系统设计相关的问题。

请你在回答时注意以下要求：

1. **准确严谨**
   - 确保回答在技术上正确、严谨，避免含糊或不确定的表述。
   - 如果涉及 Ray 的内部机制，请尽量从架构、调度、执行、容错、资源管理等角度解释清楚。

2. **结构清晰**
   - 使用 Markdown 格式回答，方便我记录和复盘。
   - 回答要有清晰的层次结构，例如：概念定义、核心原理、执行流程、优缺点、典型场景、面试回答总结等。

3. **深入但不冗长**
   - 不要只停留在表面概念，要适当深入到底层原理和设计动机。
   - 但也要避免过度发散，重点围绕面试中可能被追问的内容展开。

4. **结合例子说明**
   - 如果有必要，请结合具体例子帮助理解。
   - 如果适合使用代码，请给出简洁的 Python/Ray 示例，并添加必要注释。

5. **便于面试表达**
   - 在回答最后，请给出一段完整、连贯、适合在面试中直接表达的总结性回答。
   - 这段回答要自然、有逻辑，避免像背诵定义。

6. **知识扩展**
   - 在最后补充与当前问题相关的知识点，例如 Ray Core、Ray Serve、Ray Tune、Ray Train、Actor 模型、任务调度、对象存储、容错机制、Kubernetes 部署等。
   - 扩展部分不需要过细，只需说明它们和当前问题的关联。

另外，如果回答中出现括号，请使用英文括号 ()，不要使用中文括号。

## 1. 资源管理与调度

### 1.1 Ray 的扩缩容机制是怎样的？其底层原理是怎样的？请深入浅出地说明一下。

Ray 的扩缩容 (Autoscaling) 机制是指集群能够根据当前任务和 Actor 的资源需求，自动增加或减少节点 (Node)，从而在保证任务及时调度的同时控制资源成本。这是 Ray 区别于静态集群的重要特性之一。

#### 一、为什么需要自动扩缩容？

在分布式计算中，资源需求往往是动态变化的：

- 训练任务启动时需要大量 GPU 节点，训练结束后资源应该释放
- 推理服务在高峰期需要扩容，在低谷期应该缩容
- 一个 Ray 集群上可能同时运行多个 Job，每个 Job 的资源需求不同

如果手动管理节点数量，要么过度分配 (浪费成本)，要么分配不足 (任务排队等待)。Ray 的 Autoscaler 就是为了解决这个问题：**让集群大小跟着工作负载自动伸缩。**

#### 二、Ray 集群架构概览

要理解扩缩容，首先需要理解 Ray 集群的核心组件：

```text
┌─────────────────────────────────────────────────┐
│                  Ray Cluster                    │
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │            Head Node                      │  │
│  │  ┌─────────────┐  ┌──────────────────┐   │  │
│  │  │     GCS      │  │   Autoscaler     │   │  │
│  │  │ (Global      │  │   (自动扩缩容     │   │  │
│  │  │  Control     │  │    决策引擎)      │   │  │
│  │  │  Store)      │  └──────────────────┘   │  │
│  │  └─────────────┘                          │  │
│  │  ┌─────────────┐  ┌──────────────────┐   │  │
│  │  │   Driver     │  │    Raylet        │   │  │
│  │  │  (用户程序)  │  │  (本地调度器)     │   │  │
│  │  └─────────────┘  └──────────────────┘   │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  ┌──────────────────┐  ┌──────────────────┐    │
│  │   Worker Node 1   │  │   Worker Node 2   │   │
│  │  ┌─────────────┐  │  │  ┌─────────────┐  │  │
│  │  │   Raylet    │  │  │  │   Raylet    │  │  │
│  │  └─────────────┘  │  │  └─────────────┘  │  │
│  │  ┌─────┐ ┌─────┐  │  │  ┌─────┐ ┌─────┐  │  │
│  │  │Task │ │Actor│  │  │  │Task │ │Task │  │  │
│  │  └─────┘ └─────┘  │  │  └─────┘ └─────┘  │  │
│  └──────────────────┘  └──────────────────┘    │
└─────────────────────────────────────────────────┘
```

核心组件说明：

- **GCS (Global Control Store)**：全局控制存储，保存集群的元数据 (节点信息、Actor 注册表、资源使用情况等)。运行在 Head Node 上。
- **Raylet**：每个节点上的本地调度器，负责本节点的资源管理和任务调度。Raylet 之间通过 GCS 协调。
- **Autoscaler**：自动扩缩容的决策引擎，运行在 Head Node 上，监控集群资源状态并做出扩缩容决策。
- **Node Provider**：Autoscaler 的"执行器"，负责实际创建和销毁节点。不同环境有不同的 Provider (AWS、GCP、Kubernetes 等)。

#### 三、Autoscaler 的工作原理

##### 1. 核心概念：资源需求 vs 资源容量

Autoscaler 的决策基于两个关键指标：

- **Pending Demands (待满足的资源需求)**：当前集群中有多少任务/Actor 在排队等待资源，它们各自需要多少 CPU、GPU、内存等
- **Cluster Capacity (集群容量)**：当前所有节点提供的总资源量

当 Pending Demands > 0 时，说明集群资源不足，需要扩容；当某些节点空闲且没有活跃任务时，可以缩容。

##### 2. Autoscaling Loop (扩缩容决策循环)

Autoscaler 以一个固定频率的循环运行，每个循环包含以下步骤：

```text
┌─────────────────────────────────────────────────┐
│              Autoscaler Loop (~每 5 秒)          │
│                                                  │
│  Step 1: 收集状态                                 │
│    - 从 GCS 获取所有节点的资源使用情况             │
│    - 从 Raylet 获取 Pending 任务的资源需求         │
│    - 获取当前正在启动中的节点                      │
│                                                  │
│  Step 2: 计算需求                                 │
│    - 统计所有 Pending 任务的资源需求总和           │
│    - 减去当前集群可用资源                          │
│    - 得到"资源缺口"                               │
│                                                  │
│  Step 3: 决策                                     │
│    - 如果资源缺口 > 0 → 扩容 (launch new nodes)   │
│    - 如果有节点空闲超过阈值 → 缩容 (terminate)    │
│    - 考虑启动中节点、延迟等因素                    │
│                                                  │
│  Step 4: 执行                                     │
│    - 调用 Node Provider 创建/销毁节点              │
│    - 更新集群状态                                  │
└─────────────────────────────────────────────────┘
```

##### 3. 扩容逻辑详解

当有任务提交但集群资源不足时，Autoscaler 的扩容逻辑如下：

```python
# 简化的 Autoscaler 扩容决策伪代码
def autoscale(pending_tasks, cluster_resources, launching_nodes):
    # 1. 统计待满足的资源需求
    pending_demands = aggregate_demands(pending_tasks)
    # 例如: {"CPU": 16, "GPU": 4}

    # 2. 计算当前可用资源 (包括正在启动中的节点)
    available = cluster_resources.available + launching_nodes.expected_resources

    # 3. 计算缺口
    deficit = {}
    for resource, demand in pending_demands.items():
        gap = demand - available.get(resource, 0)
        if gap > 0:
            deficit[resource] = gap

    # 4. 选择节点类型来填补缺口
    if deficit:
        nodes_to_launch = node_type_selector(deficit)
        # 例如: 需要 4 GPU → 启动 1 个 4-GPU 节点
        #       或者启动 2 个 2-GPU 节点 (取决于可用的节点类型配置)

        # 5. 发起节点创建请求
        for node_type, count in nodes_to_launch.items():
            node_provider.create_node(node_type, count)
```

关键点：Autoscaler 不是简单地"一有需求就启动节点"，它会考虑：

- **正在启动中的节点**：已经发起了创建请求但尚未就绪的节点，避免重复创建
- **节点类型选择**：根据资源缺口选择最合适的节点类型 (如 GPU 型号、CPU 核数)
- **批量创建**：一次性创建多个节点，而不是逐个创建，减少启动延迟
- **最大节点数限制**：通过 `max_workers` 配置限制集群最大规模，防止成本失控

##### 4. 缩容逻辑详解

```python
def autoscaler_loop():
    while True:
        # 1. 获取当前集群状态
        cluster_state = get_cluster_state()

        # 2. 获取当前未满足的资源需求
        resource_demands = get_resource_demands(cluster_state)

        # 3. 根据资源需求决定是否扩容
        nodes_to_launch = decide_scale_up(
            cluster_state=cluster_state,
            resource_demands=resource_demands,
        )

        # 4. 启动新节点
        if nodes_to_launch:
            launch_nodes(nodes_to_launch)

        # 5. 根据空闲节点状态决定是否缩容
        nodes_to_terminate = decide_scale_down(
            cluster_state=cluster_state,
        )

        # 6. 删除空闲节点
        if nodes_to_terminate:
            terminate_nodes(nodes_to_terminate)

        # 7. 等待下一轮检查
        sleep(AUTOSCALER_UPDATE_INTERVAL)
```

当某些节点空闲时，Autoscaler 的缩容逻辑如下：

```python
# 简化的 Autoscaler 缩容决策伪代码
def downscale(cluster_resources, idle_threshold=5*60):
    # 1. 找出空闲节点 (资源使用率为 0 且没有任何活跃任务)
    idle_nodes = []
    for node in cluster_resources.nodes:
        if node.cpu_usage == 0 and node.gpu_usage == 0:
            idle_duration = time.now() - node.last_task_end_time
            if idle_duration > idle_threshold:
                idle_nodes.append(node)

    # 2. 按空闲时间排序，优先缩容空闲最久的节点
    idle_nodes.sort(key=lambda n: n.last_task_end_time)

    # 3. 但要保留至少 min_workers 个节点
    nodes_to_keep = max(config.min_workers, len(cluster_resources.nodes) - len(idle_nodes))
    nodes_to_terminate = idle_nodes[:len(cluster_resources.nodes) - nodes_to_keep]

    # 4. 执行缩容
    for node in nodes_to_terminate:
        # 确保节点上没有正在运行的任务和 Actor
        if node.is_drained():
            node_provider.terminate_node(node)
```

关键点：

- **空闲阈值 (Idle Timeout)**：默认 5 分钟，节点空闲超过这个时间才会被缩容，避免频繁扩缩容 (thrashing)
- **Drain 机制**：缩容前会先将节点标记为 Drain，等待其上的任务完成，不会直接杀掉正在运行的任务
- **最小节点数 (min_workers)**：即使所有节点都空闲，也会保留 `min_workers` 个节点，避免完全缩到 0

#### 四、Ray 的资源配置

Autoscaler 的行为由集群配置文件 (通常是一个 YAML 文件) 决定：

```yaml
# cluster_config.yaml - Ray 集群自动扩缩容配置示例
cluster_name: my-ray-cluster

# 最大/最小 Worker 节点数
max_workers: 10          # 集群最多 10 个 Worker 节点
min_workers: 1           # 至少保留 1 个 Worker 节点 (即使空闲)

# 空闲超时时间 (秒)，超过此时间的空闲节点会被缩容
idle_timeout_minutes: 5

# Head 节点配置
head_node_type: head_node
available_node_types:
  head_node:
    resources:
      CPU: 4
      memory: 16G
    node_config:
      InstanceType: m5.xlarge

  # GPU Worker 节点
  gpu_worker:
    min_workers: 0        # 可以完全缩容到 0
    max_workers: 4
    resources:
      CPU: 8
      GPU: 2              # 每个节点 2 张 GPU
      memory: 32G
    node_config:
      InstanceType: g4dn.2xlarge

  # CPU Worker 节点
  cpu_worker:
    min_workers: 1        # 至少保留 1 个
    max_workers: 6
    resources:
      CPU: 16
      memory: 64G
    node_config:
      InstanceType: m5.4xlarge
```

用户在提交任务时通过 `num_cpus`、`num_gpus` 等参数声明资源需求：

```python
import ray

# 声明任务需要 1 个 CPU 和 0.5 个 GPU
@ray.remote(num_cpus=1, num_gpus=0.5)
def train_model(data):
    # 训练逻辑
    return model

# 声明 Actor 需要 4 个 CPU 和 1 个 GPU
@ray.remote(num_cpus=4, num_gpus=1)
class TrainerActor:
    def train(self, batch):
        return self.model.train(batch)

# 提交任务后，如果集群资源不足，Autoscaler 会自动扩容
futures = [train_model.remote(data) for data in dataset]
results = ray.get(futures)
```

#### 五、Kubernetes 环境下的扩缩容 (KubeRay)

在 Kubernetes 环境中，Ray 的扩缩容通过 **KubeRay Operator** 实现，它将 Ray 的 Autoscaler 逻辑与 Kubernetes 的资源管理能力结合起来：

```text
┌───────────────────────────────────────────────────┐
│                Kubernetes Cluster                 │
│                                                   │
│  ┌─────────────────────────────────────────────┐  │
│  │           KubeRay Operator                  │  │
│  │  ┌───────────────┐  ┌────────────────────┐  │  │
│  │  │ RayCluster    │  │ Ray Autoscaler     │  │  │
│  │  │ Controller    │  │ (运行在 Head Pod)   │  │  │
│  │  └───────────────┘  └────────────────────┘  │  │
│  └─────────────────────────────────────────────┘  │
│                                                   │
│  ┌──────────────┐  ┌──────────────┐              │
│  │   Head Pod    │  │  Worker Pod  │              │
│  │  (GCS +       │  │  (Raylet +   │              │
│  │   Autoscaler) │  │   Tasks)     │              │
│  └──────────────┘  └──────────────┘              │
│                                                   │
│  Autoscaler 通过 K8s API 创建/销毁 Worker Pod     │
│  可以配合 K8s Cluster Autoscaler 扩缩 Node        │
└───────────────────────────────────────────────────┘
```

KubeRay 的扩缩容流程：

1. Ray Autoscaler 检测到资源不足
2. Autoscaler 通过 KubeRay Operator 请求创建新的 Worker Pod
3. KubeRay Operator 调用 Kubernetes API 创建 Pod
4. 如果 K8s 集群节点资源不足，K8s Cluster Autoscaler 会自动扩容 K8s Node
5. 新 Pod 启动后加入 Ray 集群，任务被调度到新节点

```yaml
# RayCluster CRD 示例 (KubeRay)
apiVersion: ray.io/v1
kind: RayCluster
metadata:
  name: my-ray-cluster
spec:
  enableInTreeAutoscaling: true   # 启用 Ray Autoscaler
  autoscalerOptions:
    upscalingMode: Default         # 扩容模式: Default (按需) / Aggressive (激进)
    idleTimeoutSeconds: 300        # 空闲超时 5 分钟

  headGroupSpec:
    rayStartParams:
      num-cpus: "0"               # Head 节点不运行计算任务
    template:
      spec:
        containers:
        - name: ray-head
          image: rayproject/ray:latest
          resources:
            requests:
              cpu: "2"
              memory: "4Gi"

  workerGroupSpecs:
  - groupName: gpu-worker
    replicas: 0                    # 初始 0 个 Worker
    minReplicas: 0                 # 最少 0 个
    maxReplicas: 4                 # 最多 4 个
    rayStartParams:
      num-gpus: "1"
    template:
      spec:
        containers:
        - name: ray-worker
          image: rayproject/ray:latest
          resources:
            requests:
              cpu: "4"
              memory: "8Gi"
              nvidia.com/gpu: "1"
```

#### 六、扩缩容的高级机制

##### 1. 节点类型选择 (Node Type Selection)

当集群中有多种节点类型时 (如 GPU 节点和 CPU 节点)，Autoscaler 需要决定启动哪种类型的节点。选择策略基于：

- **资源匹配度**：优先选择能满足需求的最小节点类型 (避免浪费)
- **GPU 亲和性**：GPU 任务优先分配到 GPU 节点，CPU 任务优先分配到 CPU 节点
- **成本考虑**：在云环境中，不同实例类型的价格不同，Autoscaler 会考虑性价比

##### 2. 防抖机制 (Anti-Thrashing)

为避免频繁扩缩容导致的"抖动"，Ray 引入了多个防抖机制：

- **Idle Timeout**：节点必须空闲超过一定时间才会被缩容 (默认 5 分钟)
- **启动中节点计入容量**：已经发起创建请求但尚未就绪的节点会被计入"预期容量"，避免重复创建
- **缩容保护期**：节点刚启动后的一段时间内不会被缩容

```text
防抖机制示意:
时间线: ──────────────────────────────────────────→

任务提交 ──→ 资源不足 ──→ Autoscaler 请求扩容
                              │
                    等待节点启动 (30~120 秒)
                              │
                    节点就绪 ──→ 任务开始执行
                              │
                    任务完成 ──→ 节点空闲
                              │
                    等待 idle_timeout (5 分钟)
                              │
                    仍然空闲 ──→ Autoscaler 请求缩容
```

##### 3. 资源预留 (Resource Reservation)

Autoscaler 支持为特定场景预留资源，避免所有资源被即时任务占满：

- **min_workers**：保留的最小节点数
- **Head Node 资源隔离**：Head Node 默认不运行计算任务 (通过设置 `num-cpus: 0`)
- **节点标签**：可以为特定节点打标签，确保某些任务只在特定节点上运行

#### 七、扩缩容的常见问题与优化

##### 问题一：扩容延迟过高

从 Autoscaler 检测到资源不足到新节点可用，通常需要 30~120 秒。这个延迟包括：

- 云 API 调用延迟 (1~5 秒)
- 实例启动时间 (30~90 秒)
- Ray 节点注册时间 (5~10 秒)

**优化方案**：

- 设置 `min_workers > 0`，保留基础容量
- 使用 `upscalingMode: Aggressive` 激进扩容模式，提前创建节点
- 使用预热节点池 (如 K8s 的 Node Pool 预热)

##### 问题二：缩容过于保守

Autoscaler 的缩容策略偏保守 (默认 5 分钟空闲才缩容)，在波动较大的场景中可能导致资源浪费。

**优化方案**：

- 降低 `idle_timeout_minutes` (但不宜过低，避免频繁扩缩)
- 对于明确的批处理任务，使用 `ray.get()` 后手动关闭不需要的节点

##### 问题三：多节点类型的资源碎片化

当集群中有多种节点类型时，可能出现"资源碎片"——每个节点都有一些剩余资源，但都不够启动新任务。

**优化方案**：

- 合理配置节点类型的资源比例 (如 GPU 节点的 CPU 数量与 GPU 数量匹配)
- 使用 Placement Group 确保相关任务在同一节点上
- 在任务提交时精确声明资源需求

#### 八、面试时可以这样回答

Ray 的扩缩容机制由 Autoscaler 组件实现，它运行在 Head Node 上，以固定频率 (约 5 秒一次) 监控集群状态。核心逻辑是：当有任务排队等待资源时 (Pending Demands > 0)，Autoscaler 根据资源缺口的大小和类型，选择合适的节点类型发起扩容；当某些节点空闲超过阈值 (默认 5 分钟) 且没有活跃任务时，Autoscaler 会执行缩容。扩容时，Autoscaler 会考虑正在启动中的节点，避免重复创建；缩容时，会先 Drain 节点上的任务再终止，并保留 `min_workers` 个最小节点。在 Kubernetes 环境中，Ray 通过 KubeRay Operator 将 Autoscaler 的决策转化为 Pod 的创建和销毁，进一步可以配合 K8s Cluster Autoscaler 实现节点级别的弹性伸缩。扩缩容的核心挑战是启动延迟和防抖——Ray 通过 Idle Timeout、启动中节点计入容量等机制来平衡响应速度和稳定性。

#### 知识扩展

- **Ray Cluster 配置**：扩缩容行为完全由集群配置决定，理解 `available_node_types`、`max_workers`、`min_workers` 等参数是调优的基础。
- **KubeRay Operator**：Kubernetes 上部署 Ray 的标准方式，理解 RayCluster CRD 和 Operator 模式有助于理解云原生场景下的扩缩容。
- **Ray GCS (Global Control Store)**：Autoscaler 依赖 GCS 获取集群状态，GCS 的可用性直接影响扩缩容决策的准确性。
- **Raylet 调度器**：每个节点上的 Raylet 负责本地资源管理，Autoscaler 通过 Raylet 获取 Pending 任务的资源需求。
- **Placement Group**：在扩缩容场景中，Placement Group 可以确保相关任务被调度到同一组节点上，避免跨节点通信开销。
- **Ray Serve Autoscaler**：Ray Serve 有自己独立的 Autoscaler，基于请求队列长度和延迟指标来扩缩 Replica，与集群级 Autoscaler 是两个层次的弹性机制。
- **云厂商节点池**：在 AWS/GCP/Azure 中，不同实例类型的启动时间和价格差异很大，选择合适的节点类型是扩缩容优化的关键。

### 1.2 Ray 的 GCS 的作用是什么？其架构是什么？其底层逻辑是如何实现的？请深入浅出地说明。

GCS (Global Control Store / Global Control Service) 是 Ray 集群的全局控制存储，可以理解为整个 Ray 集群的"大脑"或"中央元数据库"。它负责存储集群级别的元数据、协调节点间的状态同步，并为调度器、Autoscaler 等组件提供全局状态视图。

#### 一、为什么需要 GCS？

分布式系统的核心挑战之一是**状态一致性**——不同节点看到的集群状态必须一致。举个例子：

- Worker Node A 上有一个 Actor，Worker Node B 需要调用这个 Actor，B 如何知道 Actor 在哪？
- 一个 Task 执行完成后产生了 Object，其他 Task 依赖这个 Object，去哪里找？
- Autoscaler 需要知道当前有多少节点、各节点资源使用情况，这些信息从哪获取？

如果每个节点各自维护一份状态，很快就会产生不一致。所以需要一个**中心化的元数据服务**来统一管理这些信息——这就是 GCS。

```text
为什么需要 GCS：
                         ┌─────────────┐
                         │    GCS       │
                         │ (全局元数据)  │
                         └──┬──┬──┬────┘
                            │  │  │
              ┌─────────────┘  │  └─────────────┐
              ▼                ▼                ▼
        ┌──────────┐    ┌──────────┐    ┌──────────┐
        │  Node A  │    │  Node B  │    │  Node C  │
        │ "Actor X │    │ "我要调用 │    │ "Object Y│
        │  在我这"  │    │  Actor X"│    │  在我这"  │
        └──────────┘    └──────────┘    └──────────┘

各节点将自身状态上报到 GCS，查询其它节点的状态也通过 GCS。
GCS 是集群中唯一的"全局真相源 (Source of Truth)"。
```

#### 二、GCS 的架构概览

在 Ray 2.0 之前，GCS 依赖外部 Redis 存储。自 Ray 2.0 起，社区用 C++ 重写了原生 GCS (In-Memory Key-Value Store)，移除了 Redis 依赖。

```text
┌─────────────────────────────────────────────────────────────┐
│                        Head Node                            │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                     GCS Server                        │  │
│  │                                                       │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  │  │
│  │  │ In-Memory   │  │   Pub/Sub    │  │   Raft      │  │  │
│  │  │   KV Store  │  │   Manager    │  │  Consensus  │  │  │
│  │  │ (内存存储)  │  │  (发布订阅)  │  │ (高可用)    │  │  │
│  │  └─────────────┘  └──────────────┘  └─────────────┘  │  │
│  │                                                       │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │              Table Storage (表存储)             │  │  │
│  │  │  ┌──────────┐ ┌──────────┐ ┌────────────────┐  │  │
│  │  │  │Node Table│ │Actor Tab.│ │Placement Group │  │  │
│  │  │  │          │ │          │ │    Table       │  │  │
│  │  │  └──────────┘ └──────────┘ └────────────────┘  │  │
│  │  │  ┌──────────┐ ┌──────────┐ ┌────────────────┐  │  │
│  │  │  │Job Table │ │Object T. │ │Worker Table    │  │  │
│  │  │  │          │ │          │ │                │  │  │
│  │  │  └──────────┘ └──────────┘ └────────────────┘  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Raylet     │  │  Autoscaler  │  │    Driver        │  │
│  │ (GCS Client) │  │ (GCS Client) │  │  (GCS Client)    │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│                              │                              │
└──────────────────────────────┼──────────────────────────────┘
                               │ gRPC
        ┌──────────────────────┼──────────────────────────┐
        ▼                      ▼                          ▼
  ┌──────────┐          ┌──────────┐              ┌──────────┐
  │ Worker   │          │ Worker   │              │ Worker   │
  │ Raylet   │          │ Raylet   │              │ Raylet   │
  │(GCS Cli) │          │(GCS Cli) │              │(GCS Cli) │
  └──────────┘          └──────────┘              └──────────┘
```

架构要点：

- **GCS Server**：运行在 Head Node 上，是整个集群的元数据中枢。所有状态变更都经过它。
- **GCS Client**：嵌入在每个 Raylet、Driver 和 Autoscaler 中，通过 gRPC 与 GCS Server 通信。
- **In-Memory KV Store**：数据全量存在内存中，保证极低延迟的读写。
- **Pub/Sub**：支持基于表的发布-订阅机制，当表中数据变化时通知订阅者。
- **Raft Consensus**：多副本场景下保证 GCS 的高可用和数据一致性。

#### 三、GCS 存储了哪些数据？(核心表详解)

GCS 的数据按"表 (Table)"来组织，每种实体类型对应一张逻辑表：

##### 1. Node Table (节点表)

存储集群中所有节点的信息：

```text
NodeTable:
┌──────────┬──────────────┬───────────────────────────┬──────────┐
│ Node ID  │  Node IP     │  Resources (Total/Avail)  │  Status  │
├──────────┼──────────────┼───────────────────────────┼──────────┤
│ node-001 │ 10.0.0.1     │ CPU:8/6, GPU:2/2, Mem:32G │  ALIVE   │
│ node-002 │ 10.0.0.2     │ CPU:16/10, GPU:0, Mem:64G │  ALIVE   │
│ node-003 │ 10.0.0.3     │ CPU:8/0,  GPU:4/0, Mem:32G│  DEAD    │
└──────────┴──────────────┴───────────────────────────┴──────────┘
```

每个 Node 对应的 Raylet 定期向 GCS 发送**心跳 (Heartbeat)**，上报资源使用情况。如果心跳超时，GCS 将该节点标记为 DEAD。

##### 2. Actor Table (Actor 表)

存储所有 Actor 的注册信息和位置：

```text
ActorTable:
┌───────────────┬──────────────┬──────────────┬──────────┬──────────┐
│   Actor ID    │   Class      │   Node ID    │  State   │  Owner   │
├───────────────┼──────────────┼──────────────┼──────────┼──────────┤
│ actor-001     │ TrainerActor │  node-001    │  ALIVE   │  job-A   │
│ actor-002     │ InferActor   │  node-002    │  PENDING │  job-B   │
│ actor-003     │ CacheActor   │  node-001    │  ALIVE   │  job-A   │
└───────────────┴──────────────┴──────────────┴──────────┴──────────┘
```

当 Driver 创建 Actor 时，先从 GCS 注册并获取全局唯一的 Actor ID，然后 GCS 将 Actor 的创建请求转发给目标节点的 Raylet。

##### 3. Object Table (对象表)

Ray 的 Object Store 是分布式的 (每个节点有自己的 Plasma Store)，但"哪个 Object 存在哪个节点"这个索引信息存在 GCS 中：

```text
ObjectTable:
┌──────────────────────┬──────────────┬──────────────┬──────────┐
│     Object ID        │   Node ID    │    Size      │  Pinned  │
├──────────────────────┼──────────────┼──────────────┼──────────┤
│ obj-abc123           │  node-001    │   128 MB     │  true    │
│ obj-def456           │  node-003    │   64 MB      │  false   │
│ obj-ghi789           │  node-002    │   256 MB     │  true    │
└──────────────────────┴──────────────┴──────────────┴──────────┘
```

当 Task B 需要读取 Task A 的输出 Object 时，Task B 的调度节点通过 GCS 查询 Object 的所在位置，从而决定是从本地读取还是拉取远程数据。

##### 4. Job Table (作业表)

记录每个提交到集群的 Job 的状态和元数据：

```text
JobTable:
┌──────────────┬──────────────┬──────────────┬──────────────────┐
│   Job ID     │   Driver PID │ Submit Time  │     Status       │
├──────────────┼──────────────┼──────────────┼──────────────────┤
│ job-001      │   12345      │ 12:00:00     │   RUNNING        │
│ job-002      │   12346      │ 12:05:00     │   SUCCEEDED      │
│ job-003      │   12347      │ 12:10:00     │   FAILED         │
└──────────────┴──────────────┴──────────────┴──────────────────┘
```

##### 5. Worker Table (Worker 表)

管理 Worker 进程的分配和生命周期：

```text
WorkerTable:
┌──────────────┬──────────────┬──────────────┬──────────────────┐
│  Worker ID   │   Node ID    │   Worker PID │     Type         │
├──────────────┼──────────────┼──────────────┼──────────────────┤
│ worker-001   │  node-001    │   20001      │   WORKER (CPU)   │
│ worker-002   │  node-001    │   20002      │   WORKER (GPU)   │
│ worker-003   │  node-002    │   20003      │   ACTOR          │
└──────────────┴──────────────┴──────────────┴──────────────────┘
```

每一个 Task 或 Actor 的执行都需要一个 Worker 进程。Raylet 向 GCS 请求分配 Worker，GCS 记录 Worker 的分配情况。

##### 6. Placement Group Table

存储 Placement Group 的预留资源和调度策略。

##### 7. Error Table

记录集群中出现过的错误信息。

#### 四、GCS 的底层实现原理

##### 1. 数据模型：基于内存的 KV 存储

GCS 的核心是一个**带索引的内存 KV 存储**。每个 Table 本质上是一个 Key-Value 集合：

- Key：实体 ID (如 Node ID、Actor ID、Object ID)
- Value：实体的完整属性 (Protobuf 序列化)
- Index：对常用查询字段建立内存索引 (如按 Node ID 查所有 Actor)

```cpp
// GCS 内部存储的简化模型 (C++ 实现)
class GcsTableStorage {
    // 每个 Table 是一个 map
    std::unordered_map<std::string, std::string> table_data_;

    // 对常用查询字段建立索引
    // 例如：按 NodeID 快速查到该节点上的所有 Actor
    std::unordered_map<std::string, std::vector<std::string>> indexes_;

public:
    // 写入操作
    Status Put(const std::string& key, const std::string& value);

    // 读取操作
    Status Get(const std::string& key, std::string* value);

    // 按索引查询 (例如：查某节点上的所有 Actor)
    std::vector<std::string> GetByIndex(
        const std::string& index_name,
        const std::string& index_value
    );

    // 删除操作
    Status Delete(const std::string& key);
};
```

选择内存存储的原因：GCS 处于调度关键路径上，每次 Actor 创建、Object 查询都要访问 GCS。如果使用磁盘存储，毫秒级的延迟会被放大到整个分布式调度链路中。

##### 2. 通信协议：gRPC

GCS Server 与 GCS Client 之间通过 **gRPC** 通信。GCS 对外暴露的 RPC 接口大致如下：

```protobuf
service GcsService {
    // 节点注册与心跳
    rpc RegisterNode(RegisterNodeRequest) returns (RegisterNodeReply);
    rpc ReportHeartbeat(HeartbeatRequest) returns (HeartbeatReply);

    // Actor 管理
    rpc RegisterActor(RegisterActorRequest) returns (RegisterActorReply);
    rpc GetActorInfo(GetActorInfoRequest) returns (GetActorInfoReply);

    // Object 位置查询
    rpc AddObjectLocation(AddObjectLocationRequest) returns (Status);
    rpc GetObjectLocations(GetObjectLocationsRequest) returns (GetObjectLocationsReply);

    // Worker 分配
    rpc LeaseWorker(LeaseWorkerRequest) returns (LeaseWorkerReply);
    rpc ReturnWorker(ReturnWorkerRequest) returns (Status);

    // 订阅通知
    rpc Subscribe(SubscribeRequest) returns (stream Notification);
}
```

##### 3. 心跳机制 (Heartbeat)

心跳是 GCS 感知集群状态的核心机制：

```text
心跳流程：

  Worker Node              GCS Server               集群状态变化
      │                       │                        │
      │── Heartbeat ─────────→│                        │
      │  (包含: Node ID,      │                        │
      │   资源使用情况,        │                        │
      │   运行的 Task/Actor)   │                        │
      │                       │── 更新 Node Table ──→  │
      │                       │── 更新 Resource View──→│
      │                       │                        │
      │  ←─ Heartbeat Ack ────│                        │
      │                       │                        │
      │  ... (下一次心跳)      │                        │
      │                       │                        │
      │     (如果超时未收到心跳) │                        │
      │                       │── 标记 Node DEAD ───→  │
      │                       │── 清理该节点 Actor ──→  │
      │                       │── 通知 Autoscaler ──→  │
```

心跳包含的信息非常丰富，不只是"我还活着"：

- 节点的可用资源量 (CPU、GPU、Memory、自定义资源)
- 节点上正在运行的 Task 列表
- 节点上存在的 Actor 列表
- 节点上缓存的 Object 列表

GCS 收到心跳后，更新内存中的 Node Table 和对局资源视图。如果某个节点超过一定时间 (默认约 30 秒) 没有发心跳，GCS 就会将其标记为 DEAD，触发该节点上所有 Actor 和 Task 的重建。

##### 4. 发布-订阅机制 (Pub/Sub)

GCS 实现了高效的**基于表的发布-订阅**，避免各个组件频繁轮询：

```text
Pub/Sub 机制示意：

   ┌─────────┐          ┌─────────┐          ┌─────────┐
   │ Raylet A│          │GCS Server│          │ Raylet B│
   └────┬────┘          └────┬─────┘          └────┬────┘
        │                    │                     │
        │ Subscribe(Actor   │                     │
        │  Table Changes)   │                     │
        │──────────────────→│                     │
        │                    │                     │
        │                    │  ←── Actor X        │
        │                    │     registered      │
        │                    │     on Node B       │
        │                    │                     │
        │ Notification:      │                     │
        │  Actor X is ALIVE  │                     │
        │  on Node B         │                     │
        │←───────────────────│                     │
        │                    │                     │
        │ 现在 Raylet A 知道 Actor X 在 Node B 上  │
```

典型订阅场景：

| 订阅者 | 订阅内容 | 用途 |
|--------|---------|------|
| Autoscaler | Node Table | 监控节点数量和使用率 |
| Raylet | Actor Table | 感知 Actor 的位置变化 |
| Driver | Job Table / Error Table | 追踪作业状态和错误 |
| Scheduler | Resource View | 获取集群资源全局视图 |

##### 5. GCS 内部的调度职责

GCS 不仅是被动的元数据存储，还直接参与部分调度决策：

```text
Actor 创建流程中 GCS 的角色：

Driver                    GCS                     Raylet(Node B)
  │                        │                          │
  │── CreateActor(X) ────→│                          │
  │                        │                          │
  │                        │── 1. 分配全局唯一 ID     │
  │                        │── 2. 查询集群资源        │
  │                        │── 3. 选择目标节点        │
  │                        │── 4. 写入 Actor Table    │
  │                        │   (State: PENDING)       │
  │                        │                          │
  │                        │── ScheduleActor ────────→│
  │                        │                          │
  │                        │                          │── 创建 Actor
  │                        │                          │   进程
  │                        │                          │
  │                        │←── Actor Ready ─────────│
  │                        │                          │
  │                        │── 更新 Actor Table      │
  │                        │   (State: ALIVE)        │
  │                        │── Notify Subscribers    │
  │                        │                          │
  │←── Actor Handle ──────│                          │
```

GCS 在 Actor 创建时扮演了**协调者**的角色：分配 ID、选择节点、注册元数据、通知订阅者。这使得其他组件 (如调用方) 只需要向 GCS 查询即可获取 Actor 的最新位置。

#### 五、GCS 的容错与高可用

##### 1. 为什么 GCS 挂了是大问题？

GCS 是集群状态的唯一真相源。如果 GCS 宕机：

- 新任务无法调度 (不知道各节点剩余资源)
- 新 Actor 无法创建 (无法注册)
- Object 位置无法查询 (跨节点数据读取失败)
- Autoscaler 无法工作 (失去集群视图)

但**已经在运行的任务和 Actor 不会立即失败**，因为它们已经在 Worker 进程中执行，不依赖 GCS 的实时参与。

GCS 宕机影响：

```text
GCS 故障影响范围：
  ✅ 已运行中的 Task/Actor ──→ 继续执行 (不受影响)
  ❌ 新 Task 提交 ──→ 调度失败 (无法查询资源)
  ❌ 新 Actor 创建 ──→ 创建失败 (无法注册)
  ❌ 跨节点 Object 读取 ──→ 查询位置失败
  ❌ Autoscaler ──→ 停止决策
  ❌ Worker 心跳 ──→ 累积超时，已运行任务可能被误判
```

##### 2. Redis 时代的容错 (Ray 1.x)

早期 Ray 使用 Redis 作为 GCS 后端。容错方案依赖 Redis 自身的主从复制和哨兵模式：

```text
Ray 1.x GCS (Redis-based):

   Head Node                              Standby Node(s)
  ┌──────────────┐                    ┌──────────────────┐
  │ Redis Master │ ←── replication ── │ Redis Slave      │
  │ (GCS Backend)│                    │ (GCS Backend)    │
  └──────────────┘                    └──────────────────┘
         │                                     │
         ▼                                     ▼
   ┌──────────┐                          ┌──────────┐
   │  Raylet  │                          │  Raylet  │
   └──────────┘                          └──────────┘
```

**问题**：Redis 是外部依赖，增加了部署复杂度；Redis Master 切换期间有短暂不可用窗口；Redis 的内存模型与 Ray 的元数据访问模式不完全匹配。

##### 3. 原生 GCS 的容错机制 (Ray 2.x)

Ray 2.0 引入了原生实现的 GCS，使用 **Raft 共识协议**实现高可用：

```text
Ray 2.x GCS HA (Raft-based):

               ┌────────────────────────────────────┐
               │           Raft Group               │
               │                                    │
               │  ┌──────────┐   ┌──────────┐      │
               │  │  GCS     │   │  GCS     │      │
               │  │ Leader   │   │Follower 1│      │
               │  │ (Head)   │   │          │      │
               │  └────┬─────┘   └──────────┘      │
               │       │                            │
               │       │ Raft Log Replication       │
               │       │                            │
               │       ├─────────────→ ┌──────────┐ │
               │       │               │  GCS     │ │
               │       └─────────────→ │Follower 2│ │
               │                       │          │ │
               │                       └──────────┘ │
               └────────────────────────────────────┘

   - Leader 处理所有写请求，Followers 被动复制日志
   - Leader 故障时，Raft 自动选举新 Leader
   - 写操作在多数节点确认后才返回成功 (Quorum)
```

GCS 数据持久化策略：

- **内存 + Raft Log**：所有写操作先写入 Raft Log (持久化到磁盘)，然后应用到内存状态。即使所有节点重启，也可以从 Raft Log 恢复状态。
- **快照 (Snapshot)**：定期生成状态快照，避免 Raft Log 无限增长。
- **读写分离**：读操作直接访问 Leader 内存，不需要走 Raft 共识，延迟极低。

```text
GCS 写操作的完整路径：

  Client (Raylet)              GCS Leader              GCS Followers
       │                           │                       │
       │── RegisterActor ─────────→│                       │
       │                           │── Append Raft Log ───→│
       │                           │                      │── 写磁盘
       │                           │                      │── Ack
       │                           │←── Quorum Ack ──────│
       │                           │                       │
       │                           │── Apply to In-Memory │
       │                           │   KV Store           │
       │                           │                       │
       │←── Success ──────────────│                       │
```

#### 六、从 Redis 到原生 GCS 的演进动机

| 对比维度 | Redis GCS (Ray 1.x) | 原生 GCS (Ray 2.x) |
|---------|---------------------|-------------------|
| 依赖 | 需要独立部署 Redis | 零外部依赖，内嵌在 Ray 中 |
| 性能 | Redis 网络跳转增加延迟 | 进程内访问，延迟更低 |
| 表模型支持 | 基于 Redis Hash，不直观 | 原生 Table 模型 + 索引，语义清晰 |
| Pub/Sub | 基于 Redis Pub/Sub，功能受限 | 原生表级 Pub/Sub，支持增量推送 |
| 高可用 | 依赖 Redis Sentinel，运维复杂 | 内置 Raft，配置简单 |
| 启动时间 | 需要等 Redis 启动 | 随 Ray 进程一起启动 |
| 数据模型 | Key-Value 扁平结构 | 结构化 Protobuf + 多级索引 |

核心演进动机归纳为三点：

1. **减少外部依赖**：删除 Redis 降低了部署和运维的复杂度。
2. **性能优化**：免去 Redis 网络往返，Actor 注册、Object 查询等关键路径延迟显著降低。
3. **语义匹配**：Ray 的元数据管理天然是"表 + 索引"模式，用 Redis KV 模拟这种模式很别扭。原生 GCS 可以直接使用 Protobuf 定义表结构，读写更高效。

#### 七、GCS 在调度链路中的位置

汇总 GCS 在整个任务调度链路中扮演的角色：

```text
一个 Remote Task 从提交到执行的完整链路：

Driver                GCS                  Raylet A           Raylet B
  │                    │                      │                  │
  │── f.remote() ──→  │                      │                  │
  │                    │                      │                  │
  │                    │←─ 心跳上报资源 ───────│                  │
  │                    │←─────────────────────│                  │
  │                    │                      │                  │
  │── 查询 Object     │                      │                  │
  │   位置 ──────────→│                      │                  │
  │←── Object 在      │                      │                  │
  │   Node B ────────│                      │                  │
  │                    │                      │                  │
  │── 请求调度 Task ─→│                      │                  │
  │                    │── 查询资源视图      │                  │
  │                    │   (自己维护)        │                  │
  │                    │                      │                  │
  │                    │── 选择 Node B ───────────────────────→│
  │                    │   (因为 Object 在 B 上)               │
  │                    │                      │                  │
  │                    │                      │     ←── 执行 Task
  │                    │                      │                  │
  │                    │←─ Task 完成通知 ──────────────────────│
  │                    │                      │                  │
  │                    │── 更新 Object Table │                  │
  │                    │   (新 Object 在 B)   │                  │
  │                    │                      │                  │
  │←── Result ────────│                      │                  │
```

GCS 在这个链路中提供了三个关键能力：
1. **Object 位置索引**：决定将 Task 调度到离数据最近的节点 (Data Locality)。
2. **全局资源视图**：基于各 Raylet 的心跳汇总，调度器据此做出放置决策。
3. **结果注册**：Task 完成后，其输出 Object 的位置被注册到 GCS，供下游 Task 查询。

#### 八、面试时可以这样回答

GCS 是 Ray 集群的全局控制存储，可以理解为整个集群的"大脑"。它运行在 Head Node 上，负责存储和管理集群级别的所有元数据，包括节点信息、Actor 注册表、Object 位置索引、Job 状态、Worker 分配记录等。从实现角度看，Ray 2.0 开始用 C++ 重写了原生 GCS，采用内存 KV 存储 + Protobuf 序列化 + gRPC 通信的架构，底层用 Raft 共识协议实现高可用。各节点的 Raylet 通过 gRPC 与 GCS 通信——每个节点定期发送心跳上报资源使用情况和本地 Objects，GCS 汇总后形成集群全局资源视图；同时 GCS 支持基于表的发布-订阅，组件可以订阅关心的表变更事件而无需轮询。GCS 在调度链路中的关键作用是提供 Object 位置查询和资源视图，使调度器能做出"数据本地性感知"的调度决策。如果 GCS 宕机，已经在运行的任务不受影响，但新任务调度、Actor 创建、跨节点 Object 读取都会失败。因此生产环境通常会部署多副本 GCS + Raft 共识来保证高可用。从 Redis 到原生 GCS 的演进主要解决了外部依赖、性能开销和数据模型不匹配三个问题。

#### 知识扩展

- **Raylet**：每个节点上的本地调度器，通过 GCS Client 与 GCS 通信。Raylet 上报心跳、请求 Worker 分配、查询 Object 位置都依赖 GCS。
- **GCS Pub/Sub 与调度效率**：通过订阅 Actor Table 或 Node Table 的变更事件，Raylet 可以在 Actor 就绪或节点加入的第一时间感知到，避免轮询造成的延迟和资源浪费。
- **Object Store (Plasma)**：GCS 存储的是 Object 的"位置索引"，真正的 Object 数据存在各节点的 Plasma Store 中。两者的关系类似"图书馆索引卡片"和"书架上的书"。
- **Raft 共识协议**：GCS 的 HA 基于 Raft。理解 Raft 的 Leader 选举、Log Replication 和 Quorum 机制有助于理解 GCS 在故障时的行为。
- **KubeRay**：在 K8s 环境中，GCS 运行在 Head Pod 内。Head Pod 挂掉时，KubeRay Operator 负责重建 Head Pod 并恢复 GCS 状态。
- **Autoscaler 与 GCS**：Autoscaler 是 GCS 的重度使用者——它订阅 Node Table 和资源视图，根据集群状态变化做出扩缩容决策。
- **Placement Group**：Placement Group 的创建和生命周期管理完全通过 GCS 协调，GCS 中的 Placement Group Table 记录每个 PG 的预留资源和成员节点。
- **Ray Serve 独立控制面**：Ray Serve 有自己的控制面 (Serve Controller)，但它依赖 GCS 获取底层 Actor 的运行状态和节点信息。