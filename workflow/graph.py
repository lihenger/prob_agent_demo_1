"""LangGraph 图定义 — pause 节点 + 并行路由
"""
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt
from workflow.state import AgentState
from agents import (
    orchestrator_node, knowledge_node, search_node,
    visualization_node, summary_node,
    problem_node, analytics_node,
)


def build_graph(memory):
    builder = StateGraph(AgentState)

    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("pause", _pause_node)
    builder.add_node("execute_kb", knowledge_node)
    builder.add_node("execute_search", search_node)
    builder.add_node("execute_viz", visualization_node)
    builder.add_node("execute_problem", problem_node)
    builder.add_node("execute_analytics", analytics_node)
    builder.add_node("summary", summary_node)

    builder.set_entry_point("orchestrator")
    builder.add_edge("orchestrator", "pause")

    # pause → 条件路由：退回 orchestrator 或 并行分发到执行节点
    builder.add_conditional_edges("pause", _route_after_pause)

    # 所有执行节点执行完后汇聚到 summary
    builder.add_edge("execute_kb", "summary")
    builder.add_edge("execute_search", "summary")
    builder.add_edge("execute_viz", "summary")
    builder.add_edge("execute_problem", "summary")
    builder.add_edge("execute_analytics", "summary")
    builder.add_edge("summary", END)

    return builder.compile(checkpointer=memory)


# ---- 路由函数 ----

def _route_after_pause(state):
    """pause 节点后的路由：
    - approved=False → 退回 orchestrator 重新分析
    - approved=True  → 按 need_* 列表并行分发；全部 False 则走 summary
    """
    plan = state.get("plan", {})
    if not plan.get("approved", False):
        return "orchestrator"

    targets = []
    if plan.get("need_kb"):
        targets.append("execute_kb")
    if plan.get("need_search"):
        targets.append("execute_search")
    if plan.get("need_viz"):
        targets.append("execute_viz")
    if plan.get("need_problem"):
        targets.append("execute_problem")
    if plan.get("need_analytics"):
        targets.append("execute_analytics")

    return targets if targets else "summary"


# ---- HITL 节点 ----

def _pause_node(state: AgentState) -> dict:
    """HITL 暂停节点：展示计划，等待用户决策。
    interrupt 的返回值来自 Command(resume=...)：
      - approved: bool
      - corrected_input（可选）: 用户修正后的问题
    """
    plan = state.get("plan", {})
    response = interrupt({
        "type": "pause",
        "plan": plan,
    })
    approved = response.get("approved", False)
    updates = {"plan": {**plan, "approved": approved}}
    # 用户拒绝时清理旧结果，防止泄漏到下一轮
    if not approved:
        updates["kb_results"] = ""
        updates["search_results"] = ""
        updates["viz_path"] = ""
        updates["final_output"] = ""
        updates["problem_results"] = ""
        updates["analytics_results"] = ""
        if response.get("corrected_input"):
            updates["user_input"] = response["corrected_input"]
    return updates
