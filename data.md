# 修改日志

## 2026-07-14 — 项目初始化
- **修改位置**：所有文件
- **修改原因**：Project Starter
- **修改内容**：创建 Agent Demo 项目骨架，基于 LangGraph + DeepSeek

### 目录结构
| 路径 | 说明 |
|------|------|
| main.py | CLI 入口，含流式输出与 HITL 交互循环 |
| agents/orchestrator.py | 中央调度 Agent（Supervisor） |
| agents/knowledge.py | 知识库查询 + 内容优化（合并 Summary 职能） |
| agents/visualization.py | 概率分布可视化 Agent |
| workflow/graph.py | LangGraph 图构建（含 HITL 中断点） |
| workflow/state.py | AgentState 定义（含扩展预留字段） |
| tools/kb_tool.py | 知识库关键词检索工具 |
| tools/search_tool.py | 模拟搜索工具 |
| tools/viz_tool.py | 可视化工具（引用 prob-dist-viz 脚本） |
| config/settings.py | DeepSeek API 配置 |
| config/prompts.py | Prompt 模板集中管理 |
| knowledge_base/prob_knowledge.md | 硬编码知识库（9 章 + 15 种分布） |
| output/ | 可视化 HTML 输出目录 |
| extension-guide.md | 扩展规划指南 |

### 扩展预留
- State 中预留 message_history、problem_results、analytics_data 等字段
- tools/ 工具函数签名保持不变，大产品只替换实现
- agents/__init__.py 预留导入点和注释

## 2026-07-14 — 功能迭代与 Bug 修复

### 第 1 轮：错误处理与配置
- **修改位置**：config/settings.py, main.py, agents/orchestrator.py, agents/knowledge.py
- **修改原因**：API 调用失败时异常被吞掉，用户看不到错误
- **修改内容**：
  - settings.py 增加 `load_dotenv()` 自动读取 `.env` 文件
  - main.py 所有 try/except 增加具体错误打印
  - orchestrator.py LLM 和 JSON 解析拆分 try/except，失败时保留原始响应到 reasoning
  - knowledge.py 新增 `_call_llm()` 包装函数，每个 LLM 调用有独立错误捕获

### 第 2 轮：Graph 重构与独立节点
- **修改位置**：workflow/graph.py, agents/knowledge.py, agents/search_agent.py（新建）, agents/summary.py（新建）, agents/__init__.py, main.py
- **修改原因**：
  - knowledge 节点内嵌 summary, visualization 在 knowledge 之后执行，summary 拿不到 viz 信息
  - 知识库检索不管 need_kb 真假都会执行
  - Summary 输出混乱（需 vize 时输出 matplotlib 代码、无法生成图像等）
- **修改内容**：
  - 拆分 5 个独立节点：execute_kb / execute_search / execute_viz / summary / plan_approval
  - summary 永远在最后执行，能看到 kb/search/viz 全部结果
  - 路由函数检查 need_kb/need_search 决定是否执行对应节点
  - knowledge.py 只做检索，不包含 summary
  - main.py 改用 `graph.stream(stream_mode="updates")` 按节点粒度展示执行阶段

### 第 3 轮：HITL 与阶段提示优化
- **修改位置**：main.py, agents/summary.py, config/prompts.py
- **修改原因**：
  - 问候语也走完整 HITL 流程（不合理）
  - 计划拒绝后直接退出，用户无法补充
  - HITL #2 确认输出无实际作用
- **修改内容**：
  - 新增 `response_mode: standard/simple` 字段，simple 模式自动批准+自动确认
  - 计划拒绝时提示用户补充，合并原问题后重置 thread 重新分析
  - 移除 final_approval 节点（HITL #2），summary → END
  - 阶段提示改为 `===== (n) XXX =====` 格式，每阶段间隔 0.5s
  - summary 节点输出 `output/summary_{timestamp}.md` 文件
  - main.py 恢复后自动继续（不卡图）

### 第 4 轮：可视化修复
- **修改位置**：tools/viz_tool.py, config/prompts.py, workflow/graph.py, main.py
- **修改原因**：
  - `chi-square`（连字符）vs `chi_square`（下划线）不匹配导致图不生成
  - 参数为空时 catalog domain_fn 报 KeyError
  - Summary 模板缺失 `{viz_results}`，LLM 看不到图表信息
  - HITL #2 卡死后 summary 无法正常结束
- **修改内容**：
  - viz_tool.py 新增 `DIST_NAME_MAP` 归一化所有分布名变体 + 缺失参数用 catalog 默认值填充
  - prompts.py Summary 模板加回 `{viz_results}` + 仅可视化时简洁输出规则 + 可视化引用放末尾规则
  - Orchestrator prompt 补充分布 key 示例（chi_square、student_t 等）
  - graph.py 移除 final_approval, 清理 _auto_run


### 修正：user_input 不随修正累积
- **修改位置**：main.py
- **修改原因**：拒绝修正后，merged = user_input + correction 每次都从原始输入拼接，第一次修正的上下文丢失
- **修改内容**：在拒绝分支中 merged = user_input + correction 后增加 user_input = merged，使后续修正能在已累积的上下文上追加

### 新增文件
- `agents/search_agent.py` — 独立搜索节点
- `agents/summary.py` — 独立总结节点（写入 md 文件）
- `project_doc.md` — 项目文档
- `api_doc.md` — 接口文档
- `.env.example` — 环境变量模板
- `test_offline.py` — 脱机测试套件（28 项）

### 当前目录结构
```
demo_1/
├── main.py                # CLI 入口（流式 + 阶段提示）
├── agents/
│   ├── __init__.py        # 导出 5 节点
│   ├── orchestrator.py    # 调度 Agent
│   ├── knowledge.py       # 知识库检索（不含 summary）
│   ├── search_agent.py    # 模拟搜索节点
│   ├── visualization.py   # 可视化节点
│   └── summary.py         # 总结节点 + 写 md
├── workflow/
│   ├── state.py           # AgentState
│   └── graph.py           # LangGraph 图
├── tools/
│   ├── kb_tool.py         # 知识库检索
│   ├── search_tool.py     # 模拟搜索
│   └── viz_tool.py        # 可视化（参数归一化）
├── config/
│   ├── settings.py        # API 配置（.env 自动加载）
│   └── prompts.py         # 5 个 Prompt 模板
├── knowledge_base/
│   ├── kb_loader.py       # 知识库加载
│   └── prob_knowledge.md  # 9 章 + 15 分布
├── output/                # HTML + md 输出
├── project_doc.md         # 项目文档
├── api_doc.md             # 接口文档
├── data.md                # 修改日志
├── extension-guide.md     # 扩展规划指南
├── test_offline.py        # 28 项脱机测试
├── .env.example           # 环境变量模板
└── 参考文档/              # prob-dist-viz 脚本（引用不拷贝）
```


## 2026-07-15 — Graph 流程清理：并行路由 + 拒绝回退
- **修改位置**：workflow/graph.py, main.py
- **修改原因**：
  - plan_approval 的 interrupt 与实际 CLI 决策重复，形成伪 HITL
  - execute_kb → execute_search 的未找到相关内容字符串启发式路由不可靠（need_search=True 不保证执行搜索）
  - execute_kb / execute_search / execute_viz 串行执行，无法并行
  - main.py 中 next_input 变量绕圈 hack、_stream_phase / _auto_run 函数职责模糊
- **修改内容**：
  - **graph.py**
    - plan_approval → pause，职责缩窄为纯暂停展示计划，不做决策
    - _route_after_pause 支持列表 fan-out：approved=True 时按 need_* 并行分发到执行节点；approved=False 时退回 orchestrator
    - 移除 _route_after_kb、_route_after_search、_route_after_plan
    - 移除 Command 导入（不再需要）
    - 取消 pause 节点中的 content 格式化输出（交给 main.py 展示）
    - pause 拒绝时自动清理 kb_results / search_results / viz_path / final_output，防止旧结果泄漏到重新分析后的 summary
    - 执行节点统一走固定边收敛到 summary（kb→summary、search→summary、iz→summary）
  - **main.py**
    - 移除 _auto_run → 替换为 _run_simple_mode（使用 dict 格式 resume）
    - 移除 _stream_phase → 逻辑内联到批准分支
    - 移除 
ext_input 全局变量绕圈 hack
    - 新增 _display_plan / _show_results 辅助函数
    - 拒绝流：用户输入修正后，通过 Command(resume={approved: False, corrected_input: merged}) 在原 thread 内退回 orchestrator 重新分析（不再创建新 thread）
    - 批准流：Command(resume={approved: True})，stream 中打印所有并行节点标签
    - inner while 循环统一处理 simple 模式检查、计划展示、审批、拒绝回退


### 修正：user_input 不随修正累积
- **修改位置**：main.py
- **修改原因**：拒绝修正后 merged = user_input + correction 每次都从原始输入拼接，第一次修正的上下文丢失
- **修改内容**：在拒绝分支中 merged = user_input + correction 后增加 user_input = merged，使后续修正能在已累积的上下文上追加

### 文档同步更新
- **修改位置**：project_doc.md, api_doc.md
- **修改原因**：graph 流程重构后，文档中的 node 名、路由规则、HITL 交互流程全部过时
- **修改内容**：
  - plan_approval → pause（架构图、节点表、路由规则、HITL 描述）
  - 串行路由 → 并行 fan-out（架构图、路由规则、执行流程）
  - 拒绝后重置 thread → 原 thread 内退回 orchestrator（HITL 接口、执行流程）
  - simple 模式自动 resume 描述同步更新
  - project_doc 新增并行执行核心技术点映射

### ORCHESTRATOR_PROMPT 优先级规则优化
- **修改位置**：config/prompts.py
- **修改原因**：修正拼接输入时 LLM 按结尾语义误判为 simple 模式、丢失专业知识上下文
- **修改内容**：
  - 规则从平铺改为严格优先级排序：专业知识关键词匹配优先于闲聊/问候判定
  - 新增显式关键词列表（假设检验、分布、正态、泊松等约 20 个）
  - 新增 6 个边界示例覆盖混合输入场景
  - 显式说明 response_mode=simple 时 need_* 全为 false
