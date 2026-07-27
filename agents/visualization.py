"""Visualization Agent - 概率分布可视化

[Extension] 大产品中此节点可扩展：
- SymPy 符号计算（期望/方差/MGF 自动推导）
- Matplotlib 服务端出图（返回图片 URL）
- 多分布对比图
"""

from workflow.state import AgentState
from tools.viz_tool import generate_visualization


def visualization_node(state: AgentState) -> dict:
    """根据用户问题生成概率分布可视化 HTML"""
    plan = state.get("plan", {})
    dist_type = plan.get("target_distribution", "")
    params = plan.get("params", {})
    viz_path = generate_visualization(dist_type, params) if dist_type else ""
    return {
        "viz_path": viz_path,
        "current_step": "visualization",
        "message_history": [{
            "sender": "visualization",
            "type": "viz_result",
            "payload": {"path": viz_path, "distribution": dist_type},
        }],
    }
