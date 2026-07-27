"""Problem Agent — 独立节点：题目讲解 + 多解对比 + 批改（不含 summary）"""
from langchain_openai import ChatOpenAI
from config.settings import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from config.prompts import PROBLEM_AGENT_PROMPT
from workflow.state import AgentState
from tools.math_tool import math_compute


MODE_LABELS = {
    "solve": "解题模式 — 逐步讲解解题过程",
    "compare": "多解模式 — 提供多种解法并对比",
    "grade": "批改模式 — 批改用户答案并评分",
}


def problem_node(state: AgentState) -> dict:
    user_input = state.get("user_input", "")
    plan = state.get("plan", {})
    problem_mode = plan.get("problem_mode", "solve")

    llm = ChatOpenAI(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=0.3,
        timeout=60,
    )

    try:
        math_result = math_compute(user_input, problem_mode)
    except Exception as e:
        math_result = f"[数学计算异常] {type(e).__name__}: {e}"

    mode_text = MODE_LABELS.get(problem_mode, f"未知模式({problem_mode})")
    prompt = PROBLEM_AGENT_PROMPT.format(
        user_input=user_input,
        mode_text=mode_text,
        math_result=math_result,
    )

    try:
        resp = llm.invoke(prompt)
        result = resp.content
    except Exception as e:
        result = f"[Problem Agent 调用失败] {type(e).__name__}: {e}"

    return {
        "problem_results": result,
        "current_step": "problem",
        "message_history": [{"sender": "problem", "type": "problem_result", "payload": "..."}],
    }
