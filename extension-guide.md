# 扩展规划指南

## 1. 概述

本文档说明如何将当前 Agent Demo（3 Agent、CLI、文件检索）平滑扩展到
「our-system/backend/」大产品（5 Agent、FastAPI、Qdrant 向量检索、PostgreSQL 持久化）。

## 2. 目录结构迁移

### 当前 demo（demo_1/）

`
demo_1/
├── agents/          # 3 Agent 节点函数
├── tools/           # 工具函数
├── workflow/        # LangGraph 图 + State
├── config/          # API 配置 + Prompt 模板
├── knowledge_base/  # 本地文件知识库
├── output/          # 可视化 HTML 输出
├── main.py          # CLI 入口
├── data.md          # 修改日志
├── .env.example     # 环境变量模板
└── extension-guide.md  # 本文档
`

### 大产品目标（our-system/backend/）

`
our-system/backend/
├── agents/           # 5 Agent
├── tools/            # 升级版工具
├── workflow/         # LangGraph 图 + State
├── config/           # 配置
├── db/               # SQLAlchemy 模型
├── api/              # FastAPI 路由
├── knowledge_base/   # 教材 + ingest.py
├── main.py           # FastAPI 入口
├── tests/
└── deployment/       # Docker + Compose
`

## 3. Agent 扩展

### 当前（3 Agent）

| Agent | 职责 | 实现方式 |
|-------|------|----------|
| Orchestrator | 意图分析 + 路由 | LLM 分析 -> 结构化 plan -> 代码条件路由 |
| Knowledge | 知识查询 + 内容优化 | 文件检索 -> DeepSeek 提取 -> 优化输出 |
| Visualization | 分布可视化 | 调 prob-dist-viz 脚本生成 HTML |

### 大产品（5 Agent）

| Agent | 新增能力 | 涉及改动 |
|-------|----------|----------|
| Knowledge | RAG 向量检索 | tools/kb_tool.py -> Qdrant vector_search |
| **Problem** (新增) | 题目讲解 + 多解对比 + 批改 | 新建 agents/problem.py + tools/math_tool.py |
| **Analytics** (新增) | 学习数据分析 + 断点续学 | 新建 agents/analytics.py + tools/db_tool.py |
| Visualization | SymPy 符号计算 + Matplotlib 出图 | tools/viz_tool.py -> SymPy plot + PNG URL |
| Orchestrator | 路由 5 Agent | 条件边从 3 路扩到 5 路 |

## 4. 通信模式升级

### 当前：共享 State 直接写入
`
def knowledge_node(state):
    return {"kb_results": result, "final_output": optimized}
`

### 大产品：拉取式消息队列
`
def knowledge_node(state):
    messages = get_messages_for_agent("knowledge")  # 拉取
    add_message("knowledge", "RESPONSE", payload)    # 投递
    clear_message_queue("knowledge")                 # 清空
`

**State 新增字段：**
- message_queue: list — 待处理信件 {sender, recipient, type, payload}
- message_history: list — 只追加存档（operator.add）
- agent_outputs 字段保留，但仅由 Orchestrator 写入

## 5. 检索升级

| 维度 | 当前（demo） | 大产品 |
|------|-------------|--------|
| 引擎 | 关键词匹配文件 | Qdrant 向量库 |
| 嵌入 | 无 | BGE-M3 / Qwen-Embedding |
| 检索 | 按关键词匹配章节 | 向量 cosine + BM25 混合 |
| 函数签名 | search_knowledge_base(str) -> str | 保持相同签名 |

## 6. 可视化升级

| 维度 | 当前（demo） | 大产品 |
|------|-------------|--------|
| 引擎 | prob-dist-viz HTML | SymPy + Matplotlib |
| 输出 | 交互式 HTML 文件 | PNG 图片 URL |
| 计算 | 预置目录 | SymPy 符号推导 |
| 接口 | generate_visualization(type, params) -> str | 保持相同签名 |

## 7. HITL 升级

| 维度 | 当前（CLI） | 大产品（FastAPI） |
|------|------------|-------------------|
| 交互 | input() 标准输入 | POST /api/knowledge/confirm |
| 展示 | print() | 前端黄色卡片 + 确认/修正/补充按钮 |
| 恢复 | Command(resume=...) | Command(resume={"action": "confirm"}) |
| 流式 | time.sleep 打字效果 | SSE event stream |

## 8. 配置升级

| 当前 | 大产品追加 |
|------|-----------|
| DEEPSEEK_API_KEY | QDRANT_HOST:PORT |
| DEEPSEEK_BASE_URL | POSTGRES_DSN |
| DEEPSEEK_MODEL | REDIS_URL |
| | JWT_SECRET |
| | LANGCHAIN_API_KEY |

## 9. 新增模块

| 模块 | 技术选型 | 说明 |
|------|----------|------|
| API 层 | FastAPI + Pydantic | 5 模块路由 + JWT + SSE |
| 关系库 | PostgreSQL + SQLAlchemy | 用户/记录/断点/反馈 |
| 缓存 | Redis | 会话状态 |
| 鉴权 | JWT | access_token |
| 部署 | Docker + Compose + Nginx | R5 维护 |
| 测试 | pytest + RAGAS | 单元 + E2E + RAG 质量 |

## 10. 预留接口清单

以下函数/类的签名已锁定，大产品只替换实现不替换签名：

| 当前文件 | 函数 | 签名 |
|----------|------|------|
| tools/kb_tool.py | search_knowledge_base | (user_input: str) -> str |
| tools/search_tool.py | simulate_search | (user_input: str) -> str |
| tools/viz_tool.py | generate_visualization | (type: str, params: dict) -> str |
| agents/*.py | *node | (state: AgentState) -> dict |
| config/settings.py | DEEPSEEK_API_KEY | os.getenv pattern |
| workflow/state.py | AgentState | TypedDict 扩展 |
