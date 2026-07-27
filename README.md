# 概率论与数理统计 Agent Demo — 项目文档

## 1. 项目概述

基于 LangGraph + DeepSeek 的概率论与数理统计问答 Agent。用户可提问知识点，系统通过 5 个独立节点协作完成：
Orchestrator 分析意图 → 按 plan 路由到不同执行节点 → Summary 整合输出。
体现多 Agent 协作、HITL 人机交互、流式输出、Prompt 编排四个核心技术点。

## 2. 技术栈

| 维度 | 选型 |
|------|------|
| 编排框架 | LangGraph 1.2.9（StateGraph + Supervisor + HITL） |
| 大模型 | DeepSeek API（`deepseek-chat`，兼容 OpenAI SDK） |
| LLM SDK | langchain-openai |
| 可视化 | prob-dist-viz（引用参考文档技能脚本，不拷贝） |
| 知识库 | 本地 Markdown 文件（关键词检索） |
| API Key 加载 | `.env` 文件（通过 python-dotenv 自动加载） |
| 入口 | CLI（Python，`graph.stream` 流式模式） |

## 3. 架构图

```
用户输入 (CLI)
    │
    ▼
┌───────────────────────────────┐
│  orchestrator                 │
│  LLM 分析意图 → plan JSON    │
└──────────────┬────────────────┘
               │
               ▼
         ┌──────────┐
         │   pause  │  ← interrupt() HITL #1
         └────┬─────┘
              │
        ┌─────┴─────┐
        │ approved?  │
        └─┬───────┬──┘
     No   │       │ Yes
     ┌────┘       │
     │            ▼
     │     按 need_* 列表并行分发
     │    ┌──────┬──────┬──────┐
     │    │      │      │      │
     │    ▼      ▼      ▼      │
     │  execute_kb execute_  execute_viz
     │  (知识库)  search   (HTML 图)
     │            (搜索)
     │    │      │      │      │
     │    └──────┴──────┴──────┘
     │               │
     │               ▼
     │        ┌──────────────┐
     │        │  summary     │
     │        │  整合结果     │
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
│   ├── __init__.py               # 导出 5 个节点函数
│   ├── orchestrator.py           # 调度 Agent：LLM 分析意图 → plan
│   ├── knowledge.py              # 知识库检索 + LLM 提取（不含 summary）
│   ├── search_agent.py           # 模拟搜索节点（按 plan 触发）
│   ├── visualization.py          # 可视化节点（调 prob-dist-viz 生成 HTML）
│   └── summary.py                # 总结节点：整合 kb+search+viz + 写 md 文件
├── workflow/
│   ├── state.py                  # AgentState（含扩展预留字段）
│   └── graph.py                  # LangGraph 图（6 节点 + 条件路由）
├── tools/
│   ├── kb_tool.py                # 知识库关键词检索
│   ├── search_tool.py            # 模拟搜索
│   └── viz_tool.py               # 可视化（分布名称归一化 + 默认参数）
├── config/
│   ├── settings.py               # DeepSeek API 配置（.env 自动加载 + 大产品配置占位）
│   └── prompts.py                # Prompt 模板集中管理（5 个模板）
├── knowledge_base/
│   ├── kb_loader.py              # 知识库加载工具
│   └── prob_knowledge.md         # 硬编码知识库（9 章 + 15 种分布）
├── output/                       # 可视化 HTML + summary md 输出
├── .env.example                  # 环境变量模板
├── project_doc.md                # 项目文档（本文档）
├── api_doc.md                    # 接口文档
├── data.md                       # 修改日志
├── extension-guide.md            # 扩展规划指南
└── test_offline.py               # 脱机测试（28 项）
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
>>> 什么是柯西分布                         # 知识库未命中 → 模拟搜索
>>> 你好                                   # 问候 → response_mode=simple → 直接回应
```

## 6. Graph 节点与路由

| 节点 | 功能 | 触发条件 |
|------|------|----------|
| orchestrator | LLM 分析 → 输出 plan（need_kb/need_search/need_viz/response_mode） | 入口 |
| pause | `interrupt()` 暂展示计划，等待用户决策 | 无条件 |
| execute_kb | 关键词检索 + LLM 提取知识点 | `need_kb=true` |
| execute_search | 调用 `search_tool` 模拟搜索 | `need_search=true` |
| execute_viz | 调 prob-dist-viz 生成交互式 HTML | `need_viz=true` |
| summary | 整合 kb+search+viz 结果 → LLM 优化输出 → 写 md 文件 | 无条件（最后执行，汇聚节点） |

**路由规则（纯代码，不调 LLM）：**

```
pause → approved=False → orchestrator（回退重新分析）
pause → approved=True  → [need_kb? → execute_kb, need_search? → execute_search, need_viz? → execute_viz] 并行
pause → approved=True  → 全 false → summary
执行节点（kb/search/viz）→ 各自走固定边 → summary → END
```

## 7. 流式输出与阶段提示

```
===== 分析中 =====
===== 执行计划 =====
  知识库=是  搜索=否  可视化=是
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
| 多 Agent 架构 | 5 个独立图节点，Supervisor 模式调度 |
| HITL | `interrupt()` 方案审批 + 补充修正流程 |
| 并行执行 | pause 后按 need_* 列表 fan-out，kb/search/viz 并行运行 |
| 流式输出 | `graph.stream(stream_mode="updates")` + 逐字打字效果 |
| Prompt 编排 | `config/prompts.py` 集中管理 5 个模板，按 response_mode 分流 |
| 工具调用 | kb_tool / search_tool / viz_tool（引用 prob-dist-viz） |
| 扩展预留 | `[Extension]` 注释标记 + 函数签名锁定 + 字段占位 |
