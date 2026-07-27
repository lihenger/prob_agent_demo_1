"""Analytics Agent — 独立节点：学习数据分析 + 断点续学（不含 summary）"""
from langchain_openai import ChatOpenAI
from config.settings import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from config.prompts import ANALYTICS_AGENT_PROMPT
from workflow.state import AgentState
from tools.db_tool import db_read


TYPE_LABELS = {
    "progress": "学习进度分析",
    "history": "历史记录摘要",
    "bookmark": "断点续学建议",
}


def analytics_node(state: AgentState) -> dict:
    user_input = state.get("user_input", "")
    plan = state.get("plan", {})
    analytics_type = plan.get("analytics_type", "progress")

    llm = ChatOpenAI(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=0.3,
        timeout=60,
    )

    try:
        db_result = db_read(analytics_type)
    except Exception as e:
        db_result = f"[数据库查询异常] {type(e).__name__}: {e}"

    analytics_type_text = TYPE_LABELS.get(analytics_type, f"未知类型({analytics_type})")
    prompt = ANALYTICS_AGENT_PROMPT.format(
        user_input=user_input,
        analytics_type_text=analytics_type_text,
        db_result=db_result,
    )

    try:
        resp = llm.invoke(prompt)
        result = resp.content
    except Exception as e:
        result = f"[Analytics Agent 调用失败] {type(e).__name__}: {e}"

    return {
        "analytics_results": result,
        "current_step": "analytics",
        "message_history": [{"sender": "analytics", "type": "analytics_result", "payload": "..."}],
    }
