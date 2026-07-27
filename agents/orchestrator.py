"""Orchestrator Agent - 中央调度（Supervisor 角色）

[Extension] 大产品中此节点可扩展：
- 调用意图分类精确路由到 5 个 Agent
- 解析会话状态（断点续学时恢复 context）
- 注入用户画像（Analytics Agent 提供的历史数据）
"""

import json
import re
from langchain_openai import ChatOpenAI
from config.settings import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from config.prompts import ORCHESTRATOR_PROMPT
from workflow.state import AgentState


def orchestrator_node(state: AgentState) -> dict:
    """分析用户输入，输出结构化执行计划"""
    user_input = state.get("user_input", "")
    llm = ChatOpenAI(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=0.1,
        timeout=30,
    )
    prompt = ORCHESTRATOR_PROMPT.format(user_input=user_input)

    try:
        response = llm.invoke(prompt)
        plan = _parse_plan(response.content)
    except Exception as e:
        plan = {
            "need_kb": True, "need_search": False, "need_viz": False,
            "query_type": "concept", "response_mode": "standard",
            "target_distribution": None, "params": {},
            "reasoning": f"[Orchestrator 调用失败] {type(e).__name__}: {e}",
        }

    return {
        "plan": plan,
        "current_step": "orchestrator",
        "message_history": [{
            "sender": "orchestrator",
            "type": "plan",
            "payload": plan,
        }],
    }


def _parse_plan(content: str) -> dict:
    """解析 LLM 输出的 JSON 计划，失败时返回默认计划"""
    json_match = re.search(r"\{.*\}", content, re.DOTALL)
    if json_match:
        raw = json_match.group()
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            preview = raw[:200].replace("\n", " ")
            return {
                "need_kb": True, "need_search": False, "need_viz": False,
                "query_type": "concept", "response_mode": "standard",
                "target_distribution": None, "params": {},
                "reasoning": f"[JSON 解析失败] {e}。原始响应：{preview}...",
            }
    preview = content[:200].replace("\n", " ")
    return {
        "need_kb": True, "need_search": False, "need_viz": False,
        "query_type": "concept", "response_mode": "standard",
        "target_distribution": None, "params": {},
        "reasoning": f"[未检测到 JSON] 原始响应：{preview}...",
    }
