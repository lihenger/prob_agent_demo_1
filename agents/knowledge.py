"""Knowledge Agent — 独立节点：知识库检索 + LLM 提取（不含 summary）"""
from langchain_openai import ChatOpenAI
from config.settings import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from config.prompts import KB_AGENT_PROMPT
from workflow.state import AgentState
from tools.kb_tool import search_knowledge_base


def knowledge_node(state: AgentState) -> dict:
    user_input = state.get("user_input", "")
    llm = ChatOpenAI(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=0.3,
        timeout=60,
    )

    try:
        kb_content = search_knowledge_base(user_input)
    except Exception as e:
        kb_content = f"[知识库检索异常] {type(e).__name__}: {e}"

    kb_prompt = KB_AGENT_PROMPT.format(user_input=user_input, knowledge_base=kb_content)
    try:
        resp = llm.invoke(kb_prompt)
        kb_result = resp.content
    except Exception as e:
        kb_result = f"[Knowledge 提取失败] {type(e).__name__}: {e}"

    return {
        "kb_results": kb_result,
        "current_step": "knowledge",
        "message_history": [{"sender": "knowledge", "type": "kb_result", "payload": "..."}],
    }
