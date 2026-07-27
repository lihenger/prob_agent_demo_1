# 概率论与数理统计 Agent Demo — 接口文档

## 1. Agent 节点函数

所有 Agent 节点函数遵循 LangGraph 节点签名：`(state: AgentState) -> dict`

### 1.1 orchestrator_node

| 项目 | 说明 |
|------|------|
| **路径** | `agents/orchestrator.py` |
| **输入** | `state.user_input` |
| **输出** | `state.plan`, `state.current_step`, `state.message_history` |
| **模型** | DeepSeek `deepseek-chat`，temperature=0.1，timeout=30 |
| **Prompt** | `config/prompts.py` → `ORCHESTRATOR_PROMPT` |

**plan 结构：**
```python
{
    "need_kb": bool,              # 是否需要查知识库
    "need_search": bool,          # 是否需要网络搜索
    "need_viz": bool,             # 是否需要可视化
    "query_type": str,            # concept/distribution/formula/comparison/application/greeting/other
    "response_mode": str,         # "standard"（专业回答）或 "simple"（简单回应）
    "target_distribution": str,   # 分布英文名（normal/binomial/poisson/chi_square/student_t/exponential…）
    "params": dict,               # 分布参数，如 {"mu": 0, "sigma": 1}
    "reasoning": str,             # 分析理由
}
```

### 1.2 knowledge_node（execute_kb 节点）

| 项目 | 说明 |
|------|------|
| **路径** | `agents/knowledge.py` |
| **流程** | `kb_tool.search_knowledge_base()` 检索 → DeepSeek `KB_AGENT_PROMPT` 提取知识点 |
| **输出** | `state.kb_results` |
| **模型** | DeepSeek `deepseek-chat`，temperature=0.3，timeout=60 |
| **注意** | 不含 summary 逻辑，summary 由独立节点负责 |

### 1.3 search_node（execute_search 节点）

| 项目 | 说明 |
|------|------|
| **路径** | `agents/search_agent.py` |
| **流程** | `search_tool.simulate_search()` + DeepSeek `SEARCH_AGENT_PROMPT` 生成模拟结果 |
| **输出** | `state.search_results` |
| **触发条件** | `need_search=true` 且（`need_kb=false` 或知识库未命中） |

### 1.4 visualization_node（execute_viz 节点）

| 项目 | 说明 |
|------|------|
| **路径** | `agents/visualization.py` |
| **流程** | 从 `plan.params` 提取参数 → `viz_tool.generate_visualization()` |
| **输出** | `state.viz_path`（HTML 文件路径） |
| **生成** | `output/{dist_type}_viz.html` |

### 1.5 summary_node

| 项目 | 说明 |
|------|------|
| **路径** | `agents/summary.py` |
| **流程** | 读取 `state.kb_results` + `state.search_results` + `state.viz_path` → LLM 优化输出 → 写入 md 文件 |
| **输出** | `state.final_output` + `output/summary_{timestamp}.md` |
| **模型** | DeepSeek `deepseek-chat`，temperature=0.3，timeout=60 |
| **分支** | `response_mode="simple"` 时走 `SIMPLE_RESPONSE_PROMPT` |

---

## 2. LangGraph 图配置

### 2.1 build_graph

| 项目 | 说明 |
|------|------|
| **路径** | `workflow/graph.py` |
| **入口** | orchestrator |
| **节点** | orchestrator, pause, execute_kb, execute_search, execute_viz, summary |
| **Checkpointer** | MemorySaver（thread_id 维度） |
| **HITL** | 1 个 `interrupt()`：pause（暂停展示计划） |
| **并行** | pause 后按 need_* 列表 fan-out 并行执行 kb/search/viz |
| **回退** | 拒绝时 pause 退回 orchestrator 重新分析 |

### 2.2 路由函数

```python
# pause:
#   approved=False → orchestrator（回退重新分析）
#   approved=True → [need_kb → execute_kb, need_search → execute_search, need_viz → execute_viz] 并行
#   approved=True & 全 false → summary
# execute_kb → summary（固定边）
# execute_search → summary（固定边）
# execute_viz → summary（固定边）
# summary → END
```

---

## 3. 工具函数

### 3.1 kb_tool.search_knowledge_base

```python
def search_knowledge_base(user_input: str) -> str:
    """按关键词匹配知识库，返回 Markdown 相关章节"""
```

- 输入：用户查询文本
- 输出：知识库中匹配的章节内容（Markdown）
- 未命中：`"知识库未找到相关内容。"`
- 扩展：大产品替换为 Qdrant 向量检索，签名不变

### 3.2 search_tool.simulate_search

```python
def simulate_search(user_input: str) -> str:
    """返回模拟搜索占位文本"""
```

- 扩展：大产品替换为 DuckDuckGo / Tavily / Bing API

### 3.3 viz_tool.generate_visualization

```python
def generate_visualization(distribution_type: str, params: dict) -> str:
    """生成交互式 HTML 可视化，返回文件路径"""
```

- 输入：分布英文名（`"normal"` 等）+ 参数字典
- 输出：HTML 文件路径或错误提示字符串
- 特性：`DIST_NAME_MAP` 归一化（chi-square → chi_square）+ 缺失参数以 catalog 默认值填充
- 依赖：`参考文档/skills/prob-dist-viz/scripts/`（引用不拷贝）
- 扩展：大产品替换为 SymPy + Matplotlib

---

## 4. AgentState 定义

```python
class AgentState(TypedDict):
    user_input: str          # 用户原始问题
    messages: list           # 对话历史
    plan: dict               # Orchestrator 输出的执行计划
    kb_results: str          # execute_kb 的检索结果
    search_results: str      # execute_search 的搜索结果
    viz_path: str            # execute_viz 的可视化 HTML 路径
    final_output: str        # summary 优化后的最终回答
    current_step: str        # 当前执行步骤
    errors: list             # operator.add 归约，记录各步异常
    message_history: list    # operator.add 归约，记录 {sender, type, payload}
```

**扩展预留：** `problem_results`, `analytics_data`, `message_queue`, `user_id`, `session_id`

---

## 5. HITL 接口

### 5.1 方案审批（HITL #1，graph 内）

```python
interrupt({
    "type": "pause",
    "plan": plan,           # dict
})
# 批准：Command(resume={"approved": True})
# 拒绝：Command(resume={"approved": False, "corrected_input": "修正后的问题"})
```

### 5.2 方案修正（main 循环，非 graph interrupt）

```
用户输入 n → 提示「请补充或修正你的问题」
用户输入补充内容 → 合并原问题 → Command(resume={"approved": False, "corrected_input": merged})
→ pause 节点清理旧结果 → _route_after_pause 返回 orchestrator → 原 thread 内重新分析
修正内容逐轮累积（user_input 随每次修正更新），不丢失上下文
```

---

## 6. CLI 入口

| 项目 | 说明 |
|------|------|
| **路径** | `main.py` |
| **启动** | `python main.py`（需 `.env` 中配置 DEEPSEEK_API_KEY） |
| **命令** | `exit` 退出，`clear` 重置会话 |
| **流式输出** | `graph.stream(stream_mode="updates")` 阶段提示 + `stream_print()` 逐字打字效果 |

### 6.1 执行流程（standard 模式）

```
1. 用户输入 → graph.stream() → orchestrator 完成 → pause 暂停
2. 展示 plan → 用户 y/n
3. y → Command(resume={"approved": True}) → 按 need_* 列表并行分发到 kb/search/viz
4. 各执行节点完成后走固定边汇聚到 summary
5. 每个节点完成后打印阶段提示（间隔 0.5s）
6. summary 完成 → 读取 state → 打字效果输出回答
7. 显示可视化路径（如有）→ 回到 >>> 提示
3n. n → 输入修正内容 → Command(resume={"approved": False, "corrected_input": merged})
     → pause 清理旧结果 → 退回 orchestrator 重新分析 → 展示新 plan
     （可多次拒绝修正，每次在上次修正基础上追加）
```

### 6.2 执行流程（simple 模式）

```
1. 用户输入 → orchestrator 完成 → pause 暂停
2. 检测到 response_mode="simple" → 自动 resume
3. Command(resume={"approved": True}) → need_* 全 false → summary（simple 分支）→ 直接输出回答
4. 回到 >>> 提示
```

---

## 7. 知识库结构

| 项目 | 说明 |
|------|------|
| **路径** | `knowledge_base/prob_knowledge.md` |
| **内容** | 概率论 9 章（ch01-ch09）+ 15 种常见分布详解 |
| **检索方式** | 关键词匹配章节标题（`_extract_keywords`） |
| **扩展** | 大产品替换为 Qdrant 向量库 + BM25 混合检索 |

### 章节覆盖

| 编号 | 章节 | 核心知识点 |
|------|------|-----------|
| ch01 | 随机事件与概率 | 概率公理、条件概率、全概率、贝叶斯 |
| ch02 | 随机变量与分布 | 分布函数、常见分布 |
| ch03 | 多维随机变量 | 联合分布、协方差、相关系数 |
| ch04 | 数字特征 | 期望、方差、矩、条件期望 |
| ch05 | 大数定律与中心极限定理 | 切比雪夫、CLT |
| ch06 | 统计量及其分布 | 抽样分布、三大分布 |
| ch07 | 参数估计 | 点估计、MLE、置信区间 |
| ch08 | 假设检验 | t 检验、χ² 检验、p 值 |
| ch09 | 方差分析与回归 | ANOVA、线性回归 |

### 分布覆盖（15 种）

连续：正态、均匀、指数、伽马、贝塔、χ²、t、韦布尔、拉普拉斯、对数正态、F
离散：伯努利、二项、泊松、几何、负二项

---

## 8. 扩展预留接口清单

| 当前文件 | 函数/类 | 签名 | 大产品替换方案 |
|----------|---------|------|---------------|
| `tools/kb_tool.py` | `search_knowledge_base` | `(str) -> str` | Qdrant 向量检索 |
| `tools/search_tool.py` | `simulate_search` | `(str) -> str` | Tavily / DuckDuckGo API |
| `tools/viz_tool.py` | `generate_visualization` | `(str, dict) -> str` | SymPy + Matplotlib |
| `workflow/state.py` | `AgentState` | TypedDict | 追加 message_queue 等字段 |
| `workflow/graph.py` | `build_graph` | `(MemorySaver) -> StateGraph` | 追加 Problem/Analytics 节点 |
| `main.py` | `main` | CLI 入口 | FastAPI + SSE |
| `agents/knowledge.py` | `knowledge_node` | `(state) -> dict` | 升级为 RAG + Qdrant 检索 |
| `agents/summary.py` | `summary_node` | `(state) -> dict` | 可拆分独立 Summary Agent |

## 9. prompt 模板总览

| 模板 | 用途 | 关键特性 |
|------|------|----------|
| `ORCHESTRATOR_PROMPT` | 意图分析 + plan 生成 | 输出 JSON，含 response_mode 字段 |
| `KB_AGENT_PROMPT` | 知识库知识点提取 | 含 Extension 占位（RAG 上下文） |
| `SEARCH_AGENT_PROMPT` | 模拟网络搜索 | 以「【模拟搜索结果】」开头 |
| `SUMMARY_AGENT_PROMPT` | 整合输出优化 | 含 viz_results 占位 + 仅可视化精简规则 + 可视化引用放末尾 |
| `SIMPLE_RESPONSE_PROMPT` | 问候/闲聊回应 | 不自我介绍、不强行联系概率论 |
