"""Search Agent — 独立节点：模拟网络搜索（触发条件见 plan）"""
from langchain_openai import ChatOpenAI
from config.settings import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from config.prompts import SEARCH_AGENT_PROMPT
from workflow.state import AgentState
from tools.search_tool import simulate_search


def search_node(state: AgentState) -> dict:
    user_input = state.get("user_input", "")
    llm = ChatOpenAI(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=0.3,
        timeout=60,
    )
    search_msg = simulate_search(user_input)
    search_prompt = SEARCH_AGENT_PROMPT.format(user_input=user_input)
    try:
        resp = llm.invoke(search_prompt)
        result = resp.content
    except Exception as e:
        result = f"[Search 调用失败] {type(e).__name__}: {e}"
    return {
        "search_results": result,
        "current_step": "search",
        "message_history": [{"sender": "search", "type": "search_result", "payload": "..."}],
    }
