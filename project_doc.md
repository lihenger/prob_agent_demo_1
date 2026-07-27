# 概率论与数理统计 Agent Demo — 项目文档

## 1. 项目概述

基于 LangGraph + DeepSeek 的概率论与数理统计问答 Agent。用户可提问知识点、请求可视化、求解题目、查看学习分析，系统通过 7 个 Agent 节点协作完成：
Orchestrator 分析意图 → pause 暂停等待确认 → 按 plan 并行分发到最多 5 个执行节点 → Summary 整合输出。
体现多 Agent 协作、HITL 人机交互、并行 fan-out、流式输出、Prompt 编排五个核心技术点。

### 当前可实现的全部功能

| 功能 | 触发关键词 | 对应 Agent | 输出 |
|------|-----------|-----------|------|
| 知识库查询 | 概念/定理/公式类问题（如"什么是正态分布"） | execute_kb | 从本地知识库提取知识点 |
| 网络搜索模拟 | 知识库未命中的冷门概念 | execute_search | 模拟搜索结果 |
| 可视化生成 | "画一下/绘制 XX 分布" | execute_viz | 交互式 HTML 图表 |
| 题目讲解 | "帮我解这道题"/"比较两种解法" | execute_problem | 解题/多解对比/批改 |
| 学习分析 | "我的学习进度如何" | execute_analytics | 进度/历史/断点分析 |
| 闲聊/问候 | "你好"/"谢谢" | orchestrator→summary(simple) | 简短问候回应（跳过 HITL） |
| HITL 审批 | 每次执行前（simple 模式除外） | pause | 展示 plan → 用户确认/拒绝/修正 |

## 2. 技术栈

| 维度 | 选型 |
|------|------|
| 编排框架 | LangGraph 1.2.9（StateGraph + Supervisor + HITL + 并行 fan-out） |
| 大模型 | DeepSeek API（`deepseek-v4-flash`，兼容 OpenAI SDK） |
| LLM SDK | langchain-openai |
| 可视化 | prob-dist-viz（引用参考文档技能脚本，不拷贝） |
| 知识库 | 本地 Markdown 文件（关键词检索） |
| 数学计算 | math_tool（占位，待替换为 SymPy） |
| 学习数据 | db_tool（占位，待替换为 PostgreSQL） |
| API Key 加载 | `.env` 文件（通过 python-dotenv 自动加载） |
| 入口 | CLI（Python，`graph.stream` 流式模式） |
| 测试 | 脱机测试套件（40 项，不依赖网络） |

## 3. 架构图

```
用户输入 (CLI)
    │
    ▼
┌───────────────────────────────┐
│  orchestrator                 │
│  LLM 分析意图 → plan JSON    │
│  (含 need_kb/search/viz/     │
│   problem/analytics 共 5 项)  │
└──────────────┬────────────────┘
               │
               ▼
         ┌──────────┐
         │   pause  │  ← interrupt() HITL
         └────┬─────┘
              │
        ┌─────┴─────┐
        │ approved?  │
        └─┬───────┬──┘
     No   │       │ Yes
     ┌────┘       │
     │            ▼
     │     按 need_* 列表并行分发
     │   ┌────┬────┬────┬────┬────┐
     │   │    │    │    │    │    │
     │   ▼    ▼    ▼    ▼    ▼    │
     │  kb  search viz problem analytics
     │   │    │    │    │    │    │
     │   └────┴────┴────┴────┴────┘
     │               │
     │               ▼
     │        ┌──────────────┐
     │        │  summary     │
     │        │  整合 5 路结果│
     │        └──────┬───────┘
     │               │
     │               ▼
     │              END
     │
     └────→ orchestrator（修正后重新分析）
```

## 4. 目录结构

```
demo_1/
├── main.py                       # CLI 入口（流式 + 阶段提示 + HITL）
├── agents/
│   ├── __init__.py               # 导出 7 个节点函数
│   ├── orchestrator.py           # 调度 Agent：LLM 分析意图 → plan
│   ├── knowledge.py              # 知识库检索 + LLM 提取
│   ├── search_agent.py           # 模拟搜索节点（按 plan 触发）
│   ├── visualization.py          # 可视化节点（生成交互式 HTML）
│   ├── problem.py                # 题目讲解节点（解题/多解对比/批改）
│   ├── analytics.py              # 学习分析节点（进度/历史/断点）
│   └── summary.py                # 总结节点：整合全部 5 路结果 + 写 md 文件
├── workflow/
│   ├── state.py                  # AgentState（11 个字段）
│   └── graph.py                  # LangGraph 图（8 节点 + 条件路由 + 并行）
├── tools/
│   ├── kb_tool.py                # 知识库关键词检索
│   ├── search_tool.py            # 模拟搜索
│   ├── viz_tool.py               # 可视化（分布名称归一化 + 默认参数）
│   ├── math_tool.py              # 数学计算占位（待替换为 SymPy）
│   └── db_tool.py                # 学习数据占位（待替换为 PostgreSQL）
├── config/
│   ├── settings.py               # DeepSeek API 配置（.env 自动加载）
│   └── prompts.py                # Prompt 模板集中管理（7 个模板）
├── knowledge_base/
│   ├── kb_loader.py              # 知识库加载工具
│   └── prob_knowledge.md         # 硬编码知识库（9 章 + 15 种分布）
├── output/                       # 可视化 HTML + summary md 输出
├── .env.example                  # 环境变量模板
├── project_doc.md                # 项目文档（本文档）
├── api_doc.md                    # 接口文档
├── data.md                       # 修改日志
├── extension-guide.md            # 扩展规划指南
├── CLAUDE.md                     # Claude Code 项目指令
└── test_offline.py               # 脱机测试（40 项）
```

## 5. 运行方式

```bash
# 方式一：创建 .env 文件（推荐）
echo DEEPSEEK_API_KEY=sk-your-key > .env
python main.py

# 方式二：设置环境变量
$env:DEEPSEEK_API_KEY = "sk-your-key"
python main.py
```

### 示例对话

```
>>> 正态分布 N(0,1)                       # 知识库命中 → 知识点输出
>>> 画一下指数分布 lambda=2                # 知识库 + 可视化 → HTML
>>> 比较二项分布和泊松分布                  # 知识库比较
>>> 帮我解这道题：P(X>3) X~N(0,1)           # 题目讲解 → 解题模式
>>> 比较解法和贝叶斯方法                   # 题目讲解 → 多解对比模式
>>> 我的学习进度如何                        # 学习分析 → 进度查询
>>> 什么是柯西分布                         # 知识库未命中 → 模拟搜索
>>> 你好                                   # 问候 → response_mode=simple → 直接回应
```

## 6. Graph 节点与路由

| 节点 | 功能 | 触发条件 |
|------|------|----------|
| orchestrator | LLM 分析 → 输出 plan（含 need_kb/search/viz/problem/analytics） | 入口 |
| pause | `interrupt()` 暂停展示计划，等待用户决策 | 无条件 |
| execute_kb | 关键词检索 + LLM 提取知识点 | `need_kb=true` |
| execute_search | 调用 `search_tool` 模拟搜索 | `need_search=true` |
| execute_viz | 调 prob-dist-viz 生成交互式 HTML | `need_viz=true` |
| execute_problem | 调用 math_tool + LLM 生成题目讲解 | `need_problem=true` |
| execute_analytics | 调用 db_tool + LLM 生成学习分析 | `need_analytics=true` |
| summary | 整合全部结果 → LLM 优化输出 → 写 md 文件 | 无条件（最后执行，汇聚节点） |

**路由规则（纯代码，不调 LLM）：**

```
pause → approved=False → orchestrator（回退重新分析）
pause → approved=True  → [need_kb? → execute_kb, need_search? → execute_search, 
                            need_viz? → execute_viz, need_problem? → execute_problem,
                            need_analytics? → execute_analytics] 并行
pause → approved=True  → 全 false → summary
执行节点（kb/search/viz/problem/analytics）→ 各自走固定边 → summary → END
```

## 7. 流式输出与阶段提示

```
===== 分析中 =====
===== 执行计划 =====
  知识库=是  搜索=否  可视化=是  题目=否  分析=否
  涉及分布：normal
  理由：用户询问正态分布

执行此计划？(y/n): y

===== 执行阶段 =====
===== (1) 知识库检索 =====     ← 每阶段间隔 0.5s
===== (2) 可视化生成 =====
===== (3) 内容优化 =====

===== 回答 =====
（逐字打字效果输出...）

[图表] 可视化文件：C:\...\output\normal_viz.html
```

- simple 模式（问候/闲聊）：自动批准 + 自动确认，用户看不到任何 HITL 提示
- 执行阶段提示与 `plan` 实际内容匹配（不存在的节点不展示）
- 题目讲解和分析节点在列表中按需展示

## 8. HITL 设计

| 中断点 | 位置 | 交互 | 用途 |
|--------|------|------|------|
| 暂停点 | pause 节点 | 展示计划 → 用户输入 y/n | 方案审批 |
| 拒绝修正 | main 循环 → pause 返回 orchestrator | 用户补充 → 合并原输入 → 原 thread 内退回 reorchestrator | 方案修正 |

**补充流程**：用户点 n 后，输入修正内容，与原问题合并后通过 `Command(resume={"approved": False, "corrected_input": merged})` 在原 thread 退回 orchestrator 重新分析。修正内容会逐轮累积，不会丢失上下文。

**simple 模式**：`plan.response_mode="simple"` 时自动批准 + 自动确认，不需要用户确认。

## 9. 核心技术点映射

| 要求 | 体现位置 |
|------|----------|
| 多 Agent 架构 | 7 个独立 Agent 节点，Supervisor 模式调度 |
| HITL | `interrupt()` 方案审批 + 补充修正流程 |
| 并行执行 | pause 后按 need_* 列表 fan-out，最多 5 节点并行执行 |
| 流式输出 | `graph.stream(stream_mode="updates")` + 逐字打字效果 |
| Prompt 编排 | `config/prompts.py` 集中管理 7 个模板，按 response_mode 分流 |
| 工具调用 | kb_tool / search_tool / viz_tool / math_tool / db_tool |
| 扩展预留 | `[Extension]` 注释标记 + 函数签名锁定 + 字段占位 |
