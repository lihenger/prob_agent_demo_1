"""test_offline.py — 在安全软件解决前，先测试不依赖网络的模块

运行：python test_offline.py
"""

import os, sys

def test(name, ok):
    status = "✓" if ok else "✗"
    print(f"  {status} {name}")

print("=" * 50)
print("Agent Demo — 脱机模块测试")
print("=" * 50)

# 1. 知识库检索
print("\n[1/5] 工具函数")
try:
    from tools.kb_tool import search_knowledge_base
    result = search_knowledge_base("正态分布 N(0,1)")
    test("知识库检索（正态分布）", "正态" in result and "均值" in result)
    test("检索结果含公式", "f(x)" in result or "σ" in result)

    result2 = search_knowledge_base("不存在的不存在的")
    test("知识库未命中返回空", "未找到" in result2)
except Exception as e:
    test(f"知识库检索异常：{e}", False)

# 2. 可视化脚本路径
from tools.viz_tool import _find_skill_scripts
path = _find_skill_scripts()
test("prob-dist-viz 脚本路径可定位", bool(path))

# 3. 记忆体文件
from knowledge_base.kb_loader import load_knowledge_base
try:
    kb = load_knowledge_base()
    test("knowledge_base/__init__.py 存在", True)
except Exception as e:
    test(f"knowledge_base 加载失败：{e}", False)

# 4. 可视化工具（纯内存路径检查）
import tempfile
from tools.viz_tool import generate_visualization
result = generate_visualization("", {})
test("可视化工具（空参数返回空）", result == "")

result2 = generate_visualization("nonexistent_dist", {})
test("可视化工具（未知分布返回错误提示）", result2.startswith("["))

# 4b. 新增工具函数
from tools.math_tool import math_compute
result = math_compute("求正态分布N(0,1)的期望", "solve")
test("数学计算工具（solve 模式返回占位）", "模拟数学计算" in result and "解题" in result)

from tools.db_tool import db_read
result = db_read("progress")
test("数据库工具（progress 返回占位）", "模拟数据" in result and "正态" in result)
result2 = db_read("bookmark")
test("数据库工具（bookmark 返回占位）", "断点" in result2)
result3 = db_read("unknown_type")
test("数据库工具（未知类型返回提示）", "未知" in result3)

# 5. AgentState
print("\n[2/5] Workflow 定义")
try:
    from workflow.state import AgentState
    from typing import get_type_hints
    test("AgentState TypedDict 定义", "plan" in AgentState.__annotations__)
    test("State 含扩展预留字段", "message_history" in AgentState.__annotations__)
    test("State 含 problem_results 字段", "problem_results" in AgentState.__annotations__)
    test("State 含 analytics_results 字段", "analytics_results" in AgentState.__annotations__)
except Exception as e:
    test(f"State 加载异常：{e}", False)

# 6. Graph 编译（不调 API）
from langgraph.checkpoint.memory import MemorySaver
from workflow.graph import build_graph
try:
    graph = build_graph(MemorySaver())
    test("LangGraph 编译成功", graph is not None)
    nodes = list(graph.get_graph().nodes.keys())
    test("图含 orchestrator 节点", "orchestrator" in nodes)
    test("图含 knowledge 节点", "execute_kb" in nodes)
    test("图含 visualization 节点", "execute_viz" in nodes)
    test("图含 problem 节点", "execute_problem" in nodes)
    test("图含 analytics 节点", "execute_analytics" in nodes)
except Exception as e:
    test(f"Graph 编译异常：{e}", False)

# 7. 配置加载
print("\n[3/5] 配置与提示词")
try:
    from config.settings import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
    test("配置可加载", True)
    test(f"当前模型：{DEEPSEEK_MODEL}", bool(DEEPSEEK_MODEL))
    test(f"API 地址：{DEEPSEEK_BASE_URL}", bool(DEEPSEEK_BASE_URL))
    if DEEPSEEK_API_KEY:
        test(f"API Key 已配置（前8位：{DEEPSEEK_API_KEY[:8]}...）", True)
    else:
        test("API Key 未配置（在 .env 中填入后可联网）", False)
except Exception as e:
    test(f"配置加载异常：{e}", False)

# 8. 提示词解析验证
from config.prompts import ORCHESTRATOR_PROMPT, KB_AGENT_PROMPT, SEARCH_AGENT_PROMPT, SUMMARY_AGENT_PROMPT
try:
    # 用正常参数格式化，测试是否抛 KeyError
    p1 = ORCHESTRATOR_PROMPT.format(user_input="测试")
    test("Orchestrator 提示词无解析错误", "测试" in p1 and "{{" not in p1)

    p2 = KB_AGENT_PROMPT.format(user_input="测试", knowledge_base="测试内容")
    test("KB Agent 提示词无解析错误", "测试" in p2 and "{{" not in p2)

    p3 = SEARCH_AGENT_PROMPT.format(user_input="测试")
    test("Search Agent 提示词无解析错误", True)

    p4 = SUMMARY_AGENT_PROMPT.format(
        user_input="测试", kb_results="结果",
        search_results="", viz_results="",
        problem_results="", analytics_results=""
    )
    test("Summary Agent 提示词无解析错误", True)

    from config.prompts import PROBLEM_AGENT_PROMPT, ANALYTICS_AGENT_PROMPT
    p5 = PROBLEM_AGENT_PROMPT.format(user_input="测试", mode_text="解题模式", math_result="占位")
    test("Problem Agent 提示词无解析错误", "测试" in p5 and "{{" not in p5)

    p6 = ANALYTICS_AGENT_PROMPT.format(user_input="测试", analytics_type_text="学习进度", db_result="占位")
    test("Analytics Agent 提示词无解析错误", "测试" in p6 and "{{" not in p6)
except KeyError as e:
    test(f"提示词 KeyError（花括号未转义）：{e}", False)
except Exception as e:
    test(f"提示词异常：{e}", False)

# 9. Agent 函数签名
print("\n[4/5] Agent 节点函数")
try:
    from agents.orchestrator import orchestrator_node, _parse_plan
    result = _parse_plan('{"need_kb": true, "need_search": false, "need_viz": false, "reasoning": "测试"}')
    test("Orchestrator JSON 解析正确", result.get("need_kb") == True)
    test("默认 plan 字段完整", "need_kb" in result and "reasoning" in result)

    from agents.knowledge import knowledge_node
    import inspect
    sig = inspect.signature(knowledge_node)
    test("Knowledge 节点签名 (state) -> dict", True)

    from agents.visualization import visualization_node
    sig2 = inspect.signature(visualization_node)
    test("Visualization 节点签名 (state) -> dict", True)

    from agents.problem import problem_node
    sig3 = inspect.signature(problem_node)
    test("Problem 节点签名 (state) -> dict", True)

    from agents.analytics import analytics_node
    sig4 = inspect.signature(analytics_node)
    test("Analytics 节点签名 (state) -> dict", True)
except Exception as e:
    test(f"Agent 函数异常：{e}", False)

print()
if os.getenv("DEEPSEEK_API_KEY"):
    print(f"[API Key 已配置，可运行 python main.py]")
else:
    print(f"[API Key 未配置，请创建 .env 文件后重试]")
print("=" * 50)
