# 扩展规划指南

## 1. 概述

本文档说明如何将当前 Agent Demo（**5 Agent**、CLI、文件检索）平滑扩展到
「our-system/backend/」大产品（7 Agent、FastAPI、Qdrant 向量检索、PostgreSQL 持久化）。

### 当前已实现

| 阶段 | Agent | 状态 |
|------|-------|------|
| 核心 3 Agent | Orchestrator + Knowledge + Visualization | ✅ 已完成 |
| 搜索扩展 | Search Agent | ✅ 已完成 |
| 题目讲解 | Problem Agent（解题/多解对比/批改） | ✅ 已完成 |
| 学习分析 | Analytics Agent（进度/历史/断点） | ✅ 已完成 |
| 工具占位 | math_tool + db_tool（mock 数据） | ✅ 已完成 |

### 待实现

| 模块 | 状态 |
|------|------|
| 工具真实实现（SymPy / PostgreSQL） | ⏳ 待替换 |
| 通信模式升级（消息队列） | ❌ 已决策不做 |
| FastAPI + SSE 前端 | ⏳ 待开发 |
| Qdrant 向量检索 | ⏳ 待开发 |
| 部署（Docker + Compose） | ⏳ 待开发 |

---

## 2. 目录结构迁移

### 当前 demo（demo_1/）

```
demo_1/
├── agents/          # 7 Agent 节点函数
├── tools/           # 5 个工具函数
├── workflow/        # LangGraph 图 + State
├── config/          # API 配置 + Prompt 模板
├── knowledge_base/  # 本地文件知识库
├── output/          # 可视化 HTML + summary md 输出
├── main.py          # CLI 入口
├── data.md          # 修改日志
├── project_doc.md   # 项目文档
├── api_doc.md       # 接口文档
├── CLAUDE.md        # Claude Code 项目指令
├── test_offline.py  # 脱机测试（40 项）
├── .env.example     # 环境变量模板
└── extension-guide.md  # 本文档
```

### 大产品目标（our-system/backend/）

```
our-system/backend/
├── agents/           # 7 Agent（新增 Chat 和 Feedback Agent）
├── tools/            # 升级为真实实现（SymPy / PostgreSQL / Tavily）
├── workflow/         # LangGraph 图 + State（保持不变）
├── config/           # 配置（新增数据库等配置项）
├── db/               # SQLAlchemy 模型
├── api/              # FastAPI 路由 + SSE
├── knowledge_base/   # 教材 + ingest.py（Qdrant 索引）
├── main.py           # FastAPI 入口
├── tests/            # pytest + RAGAS
└── deployment/       # Docker + Compose + Nginx
```

---

## 3. Agent 扩展

### 当前（5 Agent，已实现）

| Agent | 职责 | 实现方式 |
|-------|------|----------|
| Orchestrator | 意图分析 + 路由 | LLM 分析 → 结构化 plan → 代码条件路由（5 路） |
| Knowledge | 知识查询 | 文件检索 → DeepSeek 提取知识点 |
| Search | 模拟网络搜索 | search_tool 占位 → DeepSeek 生成模拟结果 |
| Visualization | 分布可视化 | 调 prob-dist-viz 脚本生成交互式 HTML |
| **Problem** | 题目讲解 + 多解对比 + 批改 | math_tool 占位 → DeepSeek 生成讲解 |
| **Analytics** | 学习数据分析 + 断点续学 | db_tool 占位 → DeepSeek 生成分析 |
| Summary | 整合全部结果 + 写 md 文件 | 读取 5 路结果 → DeepSeek 优化输出 |

### 大产品（7 Agent，待实现）

| Agent | 新增能力 | 涉及改动 |
|-------|----------|----------|
| Knowledge | RAG 向量检索 | tools/kb_tool.py → Qdrant vector_search |
| Search | 真实网络搜索 | tools/search_tool.py → Tavily / DuckDuckGo API |
| **Problem** | SymPy 符号计算 | tools/math_tool.py → SymPy solve/diff/integrate |
| **Analytics** | PostgreSQL 持久化 | tools/db_tool.py → SQLAlchemy 真实查询 |
| Visualization | SymPy + Matplotlib 出图 | tools/viz_tool.py → SymPy plot + PNG URL |
| **Chat** (新增) | 多轮对话上下文管理 | 新建 agents/chat.py + 对话历史管理 |
| **Feedback** (新增) | 答案反馈收集 | 新建 agents/feedback.py + db 写入 |

---

## 4. 通信模式

### 当前（已决策沿用）：共享 State 直接写入

```
def knowledge_node(state):
    return {"kb_results": result}
```

- 简单可靠，适合 5~7 Agent 规模
- 所有 Agent 节点函数签名统一为 `(state: AgentState) -> dict`
- 缺点是 Agent 间无法互相通信，但当前架构不需要

### 消息队列方案（已决策不做）

```
def knowledge_node(state):
    messages = get_messages_for_agent("knowledge")
    add_message("knowledge", "RESPONSE", payload)
    clear_message_queue("knowledge")
```

**决策理由**：消息队列增加了复杂度（Queue 管理、消息格式约定、死信处理），在当前 5 Agent 规模下没有实际收益。如果未来 Agent 数超过 15 个或需要 Agent 间互相调用，可重新评估。

---

## 5. 检索升级

| 维度 | 当前（demo） | 大产品 |
|------|-------------|--------|
| 引擎 | 关键词匹配文件 | Qdrant 向量库 |
| 嵌入 | 无 | BGE-M3 / Qwen-Embedding |
| 检索 | 按关键词匹配章节 | 向量 cosine + BM25 混合 |
| 函数签名 | `search_knowledge_base(str) -> str` | 保持相同签名 |

---

## 6. 可视化升级

| 维度 | 当前（demo） | 大产品 |
|------|-------------|--------|
| 引擎 | prob-dist-viz HTML | SymPy + Matplotlib |
| 输出 | 交互式 HTML 文件 | PNG 图片 URL |
| 计算 | 预置目录 | SymPy 符号推导 |
| 接口 | `generate_visualization(type, params) -> str` | 保持相同签名 |

---

## 7. 数学工具升级

| 维度 | 当前（占位） | 大产品（真实） |
|------|-------------|---------------|
| 引擎 | 返回 `【模拟数学计算】` 占位文本 | SymPy 符号计算 |
| 能力 | 无真实计算 | `sympy.solve` / `diff` / `integrate` / `simplify` |
| 输出 | 纯文本 | LaTeX 渲染 + 数值结果 |
| 接口 | `math_compute(str, str) -> str` | 保持相同签名 |

---

## 8. 学习数据升级

| 维度 | 当前（占位） | 大产品（真实） |
|------|-------------|---------------|
| 引擎 | 返回 mock JSON | PostgreSQL + SQLAlchemy |
| 数据 | 硬编码模拟数据 | 用户真实学习记录 |
| 表结构 | 无 | UserProgress / StudyHistory / Bookmark / Feedback |
| 接口 | `db_read(str) -> str` | 保持相同签名 + 新增 `db_write(str, dict) -> None` |

---

## 9. HITL 升级

| 维度 | 当前（CLI） | 大产品（FastAPI） |
|------|------------|-------------------|
| 交互 | `input()` 标准输入 | POST `/api/knowledge/confirm` |
| 展示 | `print()` | 前端黄色卡片 + 确认/修正/补充按钮 |
| 恢复 | `Command(resume=...)` | `Command(resume={"action": "confirm"})` |
| 流式 | `time.sleep` 打字效果 | SSE event stream |

---

## 10. 配置升级

| 当前 | 大产品追加 |
|------|-----------|
| DEEPSEEK_API_KEY | QDRANT_HOST:PORT |
| DEEPSEEK_BASE_URL | POSTGRES_DSN |
| DEEPSEEK_MODEL | REDIS_URL |
| | JWT_SECRET |
| | LANGCHAIN_API_KEY |

---

## 11. 新增模块

| 模块 | 技术选型 | 说明 |
|------|----------|------|
| API 层 | FastAPI + Pydantic | 5 模块路由 + JWT + SSE |
| 关系库 | PostgreSQL + SQLAlchemy | 用户/记录/断点/反馈 |
| 缓存 | Redis | 会话状态 |
| 鉴权 | JWT | access_token |
| 部署 | Docker + Compose + Nginx | R5 维护 |
| 测试 | pytest + RAGAS | 单元 + E2E + RAG 质量 |

---

## 12. 预留接口清单

以下函数/类的签名已锁定，大产品只替换实现不替换签名：

| 当前文件 | 函数 | 签名 |
|----------|------|------|
| `tools/kb_tool.py` | `search_knowledge_base` | `(user_input: str) -> str` |
| `tools/search_tool.py` | `simulate_search` | `(user_input: str) -> str` |
| `tools/viz_tool.py` | `generate_visualization` | `(type: str, params: dict) -> str` |
| `tools/math_tool.py` | `math_compute` | `(user_input: str, mode: str) -> str` |
| `tools/db_tool.py` | `db_read` | `(analytics_type: str) -> str` |
| `agents/*.py` | `*_node` | `(state: AgentState) -> dict` |
| `config/settings.py` | DEEPSEEK_API_KEY | `os.getenv` pattern |
| `workflow/state.py` | `AgentState` | TypedDict 扩展 |
