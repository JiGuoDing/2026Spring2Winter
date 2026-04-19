# Agent 项目运行与开发指导

## 1. 文档目标

这份文档用于帮助你在回看本项目时，能够快速回答三个问题：

1. Agent 是如何从用户输入走到最终输出的。
2. 每个关键功能由哪个文件实现。
3. 运行时的数据、提示词、日志、向量库分别放在哪里。

本文基于目录 AI-Agent-Project/Agent-Project 当前内容整理，按照实际执行逻辑组织，而不是按文件名罗列。

---

## 2. 一句话架构

本项目是一个基于 LangChain Agent + 工具调用 + RAG 检索总结 + 动态提示词切换的智能体示例。

主路径是：
用户问题 -> ReAct Agent -> 工具调用（天气/用户信息/外部记录/RAG）-> 中间件监控与上下文标记 -> 按场景切换 Prompt -> 模型输出（流式）。

---

## 3. 运行主链路（按执行顺序）

### 3.1 入口与 Agent 组装

- agent/ReAct_agent.py
  - 定义 ReActAgent 类。
  - 在 __init__ 中通过 create_agent 组装：
    - 模型：model/factory.py 的 chat_model
    - 系统提示词：utils/prompt_loader.py 的 load_system_prompts
    - 工具集合：agent/tools/agent_tools.py
    - 中间件集合：agent/tools/middleware.py
  - execute_stream(query) 使用 stream_mode=values 流式返回结果文本。

说明：这个文件是当前项目最接近“真实可运行主入口”的实现。

### 3.2 配置加载与路径解析

- utils/config_handler.py
  - 统一加载 config/rag.yaml、config/prompt.yaml、config/chroma.yaml、config/agent.yaml。
  - 在模块级创建 rag_config、prompt_config、chroma_config、agent_config 全局配置对象。

- utils/path_tool.py
  - get_project_root() 计算项目根目录。
  - get_abs_path(relative_path) 将相对路径转换为绝对路径。

说明：后续模型初始化、向量库、提示词加载、外部数据读取都依赖这两处。

### 3.3 模型与向量化组件创建

- model/factory.py
  - ChatModelFactory -> ChatTongyi（聊天模型）。
  - EmbeddingsFactory -> DashScopeEmbeddings（向量模型）。
  - 暴露 chat_model 与 embedding_model 单例供全项目复用。

说明：模型名称来自 config/rag.yaml。

### 3.4 RAG 向量库与检索

- rag/vector_store.py
  - VectorStoreService 初始化 Chroma 持久化向量库。
  - load_document() 负责把 data 目录知识文件切片后入库。
  - 使用 md5.text 去重，避免重复导入同一文档。
  - get_retriever() 返回检索器。

- rag/rag_service.py
  - RagSummarizeService 组合检索器、提示词模板、模型、输出解析器。
  - rag_summarize(query) 执行检索并拼装 context，再让模型生成总结。

说明：RAG 的作用是给 Agent 提供知识库增强能力，不仅靠模型记忆回答。

### 3.5 工具层（Agent 的外部能力）

- agent/tools/agent_tools.py
  - rag_summarize(query): 调用 RAG 总结服务。
  - get_weather(city): 返回天气文本（示例实现）。
  - get_user_location(): 返回随机城市。
  - get_user_id(): 返回随机用户 ID。
  - get_current_month(): 返回随机月份。
  - fetch_external_data(user_id, month): 从 data/external/records.csv 查询用户月度记录。
  - fill_context_for_report(): 触发报告场景标记（配合中间件）。

说明：records.csv 当前已整理为 6 列结构（用户ID、特征、清洁效率、耗材、对比、时间），和工具解析逻辑对齐。

### 3.6 中间件层（监控、切换、上下文控制）

- agent/tools/middleware.py
  - monitor_tool（wrap_tool_call）
    - 记录工具调用日志。
    - 当调用 fill_context_for_report 时，把 runtime.context["report"] 标记为 True。
  - log_before_model（before_model）
    - 模型调用前打印消息数量与最新消息内容。
  - report_prompt_switch（dynamic_prompt）
    - 根据 report 标记，动态切换：
      - 普通场景 -> prompts/main_prompt.txt
      - 报告场景 -> prompts/report_prompt.txt

说明：这部分是项目最关键的“流程控制点”，负责把工具调用与提示词切换串起来。

### 3.7 提示词装载

- utils/prompt_loader.py
  - load_system_prompts() -> main_prompt
  - load_rag_prompts() -> rag_summarize_prompt
  - load_report_prompts() -> report_prompt

- config/prompt.yaml
  - 配置三类 prompt 文件路径。

---

## 4. 一次典型请求如何执行

以请求“为我生成我的使用报告”为例：

1. ReActAgent.execute_stream 收到用户 query（agent/ReAct_agent.py）。
2. Agent 进入推理，模型先决定需要哪些工具。
3. 可能先调用 get_user_id 与 get_current_month 获取查询维度（agent/tools/agent_tools.py）。
4. 调用 fetch_external_data 读取 records.csv 中对应用户与月份记录。
5. 调用 fill_context_for_report 触发报告场景标记。
6. 中间件 report_prompt_switch 检测 report=True，自动改用 report_prompt。
7. 模型基于当前对话上下文与工具结果生成报告内容，流式输出。
8. 全链路日志写入 logs/agent_时间戳.log（utils/logger_handler.py）。

---

## 5. 文件级功能地图（全目录视角）

### 5.1 根目录脚本

- agent/ReAct_agent.py：当前主链路 Agent 实现（推荐入口）。
- main.py：PyCharm 默认模板，不属于当前 Agent 主流程。
- introduction_to_agent.py：最小 Agent 教学样例（工具 + invoke）。
- agent_ReAct.py：ReAct 教学样例（BMI 工具调用）。
- agent_stream_output.py：流式输出教学样例。
- agent_middleware.py：中间件教学样例。
- check_kb.py：知识库文件规范校验脚本（含路径与格式断言）。

### 5.2 Agent 核心目录

- agent/tools/agent_tools.py：工具实现与外部数据读取。
- agent/tools/middleware.py：工具监控、模型前日志、动态提示词切换。
- agent/chroma_db/chroma.sqlite3：agent 目录下的本地 Chroma 数据库文件。

### 5.3 RAG 目录

- rag/vector_store.py：知识文件切片、向量入库、检索器创建。
- rag/rag_service.py：检索后总结链路。
- rag/chroma_db/chroma.sqlite3 + bin 文件：RAG 向量索引持久化产物。

### 5.4 配置目录

- config/rag.yaml：聊天模型和向量模型配置。
- config/chroma.yaml：向量库集合名、持久化路径、切片参数等。
- config/prompt.yaml：三类 prompt 路径。
- config/agent.yaml：Agent 业务配置（当前为 external_data_path）。

### 5.5 Prompt 目录

- prompts/main_prompt.txt：普通对话系统提示词。
- prompts/rag_summarize_prompt.txt：RAG 总结专用提示词。
- prompts/report_prompt.txt：报告场景专用提示词。

### 5.6 数据目录

- data/故障排除.txt
- data/扫地机器人100问.txt
- data/扫拖一体机器人100问.txt
- data/维护保养.txt
- data/选购指南.txt
  - 以上为知识库语料，均为结构化长文本，末行含“更新日期”。

- data/external/records.csv
  - 外部业务数据源。
  - 当前结构：用户ID、特征、清洁效率、耗材、对比、时间。

### 5.7 公共工具目录

- utils/config_handler.py：配置加载。
- utils/path_tool.py：路径转换。
- utils/file_handler.py：文件加载器、文件后缀过滤、MD5 计算。
- utils/logger_handler.py：日志器初始化与输出格式。
- utils/prompt_loader.py：提示词读取。

### 5.8 运行与工程辅助文件

- md5.text：已入库知识文件的 MD5 列表。
- logs/*.log：运行日志。
- .gitignore：忽略 pycache、日志、虚拟环境、IDE 文件等。

- .idea/*：PyCharm 本地工程配置（解释器、运行配置、变更状态等）。
  - 属于开发环境元数据，不参与 Agent 运行逻辑。

- __pycache__/*.pyc、*.sqlite3、*.bin：解释器缓存与向量数据库二进制数据。

---

## 6. 开发与排查建议（基于当前代码现状）

1. 优先以 agent/ReAct_agent.py 作为启动与联调入口。
2. 若 RAG 检索效果异常，先检查：
   - rag/vector_store.py 是否已成功 load_document()
   - md5.text 是否导致“误判已入库”
   - rag/chroma_db 是否存在历史脏数据
3. 若报告场景未触发，重点看：
   - 是否调用 fill_context_for_report
   - middleware.py 中 report 标记是否写入 runtime.context
4. 若外部记录查询为空，检查：
   - config/agent.yaml 的 external_data_path
   - records.csv 是否与 6 列解析规则一致

---

## 7. 当前可见风险与注意事项

1. agent/tools/agent_tools.py 中 user_ids 列表目前是 001-008，不包含 009；而 records.csv 中包含 009。
2. get_user_location 工具 description 为空，可能影响模型选工具质量。
3. check_kb.py 使用了固定 Windows 路径，并且要求 data 目录文件集合严格等于 5 个文件；在当前目录含 data/external 子目录时可能校验失败。
4. .idea/workspace.xml 含本地运行环境变量示例（含密钥字符串），该文件不应进入版本控制。

---

## 8. 推荐回看路径（最快理解项目）

按下面顺序阅读，理解成本最低：

1. agent/ReAct_agent.py
2. agent/tools/agent_tools.py
3. agent/tools/middleware.py
4. utils/prompt_loader.py + prompts/*.txt
5. rag/rag_service.py
6. rag/vector_store.py
7. config/*.yaml
8. data/external/records.csv 与 data/*.txt

完成以上顺序后，你可以完整复盘：
- Agent 怎么决策
- 工具怎么调用
- RAG 怎么增强
- 提示词怎么切换
- 日志怎么追踪

这也是本项目的实际工作闭环。

---

## 9. 全文件索引（逐项定位）

下面按“你在目录中能看到的文件”给出定位说明，便于回看时直接按文件名查找。

### 9.1 业务与示例代码

- main.py：PyCharm 初始模板脚本，不参与项目主链路。
- introduction_to_agent.py：最小 Agent 教学示例（单工具 + invoke）。
- agent_ReAct.py：ReAct 教学示例（展示思考-行动-观察过程）。
- agent_stream_output.py：流式输出教学示例。
- agent_middleware.py：中间件钩子教学示例。
- check_kb.py：知识库文件结构与更新时间校验脚本。
- agent/ReAct_agent.py：主 Agent 组装与流式执行。
- agent/tools/agent_tools.py：工具实现与 records.csv 查询逻辑。
- agent/tools/middleware.py：工具监控、模型前日志、动态 prompt 切换。
- model/factory.py：聊天模型与向量模型工厂。
- rag/rag_service.py：RAG 检索后总结服务。
- rag/vector_store.py：知识库入库与检索器封装。
- utils/config_handler.py：配置读取。
- utils/file_handler.py：文件加载、后缀过滤、MD5 工具。
- utils/logger_handler.py：日志器初始化。
- utils/path_tool.py：工程根路径与绝对路径转换。
- utils/prompt_loader.py：三类提示词加载。

### 9.2 配置与提示词

- config/agent.yaml：业务侧配置（当前为 external_data_path）。
- config/chroma.yaml：向量库参数、切片参数、数据路径。
- config/prompt.yaml：系统/RAG/报告提示词路径。
- config/rag.yaml：聊天模型名与向量模型名。
- prompts/main_prompt.txt：通用助手提示词。
- prompts/rag_summarize_prompt.txt：RAG 总结提示词。
- prompts/report_prompt.txt：报告生成提示词。

### 9.3 数据与运行产物

- data/故障排除.txt：故障排查知识语料。
- data/扫地机器人100问.txt：扫地机器人 FAQ 知识语料。
- data/扫拖一体机器人100问.txt：扫拖一体 FAQ 知识语料。
- data/维护保养.txt：维护保养知识语料。
- data/选购指南.txt：选购知识语料。
- data/external/records.csv：外部业务记录（工具 fetch_external_data 读取）。
- md5.text：已入库语料的 MD5 记录，用于去重。
- logs/agent_*.log：运行日志，记录模型调用与工具调用链路。

### 9.4 向量库与缓存二进制

- agent/chroma_db/chroma.sqlite3：Agent 目录下的 Chroma 持久化文件。
- rag/chroma_db/chroma.sqlite3：RAG 向量库元数据。
- rag/chroma_db/2e389695-b0b7-4911-997a-0206c49fb4db/*.bin：向量索引二进制分段文件。
- agent/tools/__pycache__/*.pyc、model/__pycache__/*.pyc、rag/__pycache__/*.pyc、utils/__pycache__/*.pyc：Python 运行缓存。

### 9.5 工程与 IDE 元数据

- .gitignore：Git 忽略规则。
- .idea/.gitignore：IDE 局部忽略规则。
- .idea/Agent-Project.iml：PyCharm 模块配置。
- .idea/misc.xml：项目解释器与 Black 配置。
- .idea/modules.xml：模块声明。
- .idea/vcs.xml：VCS 映射。
- .idea/inspectionProfiles/profiles_settings.xml：代码检查配置。
- .idea/workspace.xml：本地工作区状态、运行配置、临时记录（非业务逻辑）。
