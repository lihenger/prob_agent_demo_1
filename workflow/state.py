"""Agent 工作流全局状态定义

[Extension] 大产品中此文件会被扩展为：
- message_queue: list — 拉取式消息队列（替代 Agent 直接写字段）
- problem_results / analytics_data 等子 Agent 输出字段
- user_id / session_id — JWT 鉴权与会话管理
"""

from typing import TypedDict, Annotated
from operator import add


class AgentState(TypedDict):
    """Agent 工作流全局状态"""
    # 输入与对话
    user_input: str
    messages: list

    # Orchestrator 输出
    plan: dict

    # 各 Agent 执行结果（demo 阶段 Agent 直接写入，大产品改为消息队列传递）
    kb_results: str
    search_results: str
    viz_path: str
    problem_results: str
    analytics_results: str
    final_output: str

    # 执行元数据
    current_step: Annotated[str, add]  # operator.add 归约，支持并行节点写入
    errors: Annotated[list, add]          # operator.add 归约

    # ---- 扩展预留字段 ----
    message_history: Annotated[list, add]  # operator.add 归约，记录 {sender, type, payload}

# [Future] 大产品补充字段：
# message_queue: list
# user_id: str
# session_id: str
