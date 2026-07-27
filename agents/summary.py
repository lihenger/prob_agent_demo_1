"""Summary Agent — 独立节点：整合所有结果，最终优化输出 + 写入 md 文件"""
import os
import time
from langchain_openai import ChatOpenAI
from config.settings import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from config.prompts import SUMMARY_AGENT_PROMPT, SIMPLE_RESPONSE_PROMPT
from workflow.state import AgentState


def summary_node(state: AgentState) -> dict:
    user_input = state.get("user_input", "")
    plan = state.get("plan", {})
    response_mode = plan.get("response_mode", "standard")
    kb_results = state.get("kb_results", "")
    search_results = state.get("search_results", "")
    viz_path = state.get("viz_path", "")

    llm = ChatOpenAI(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=0.3,
        timeout=60,
    )

    # ---- simple 分支：非数学问题直接回应 ----
    if response_mode == "simple":
        simple_prompt = SIMPLE_RESPONSE_PROMPT.format(user_input=user_input)
        try:
            resp = llm.invoke(simple_prompt)
            result = resp.content
        except Exception as e:
            result = f"[Simple 回应失败] {type(e).__name__}: {e}"
        return {"final_output": result, "current_step": "summary"}

    # ---- standard 分支：整合 kb + search + viz ----
    # 注意：此时所有前置节点已执行完毕，state 中的字段都是完整的
    viz_hint = ""
    if viz_path and not viz_path.startswith("["):
        viz_hint = f"\n\n[图表] 可视化已生成：{viz_path}"
    elif viz_path:
        viz_hint = f"\n\n[可视化] {viz_path}"

    summary_prompt = SUMMARY_AGENT_PROMPT.format(
        user_input=user_input,
        kb_results=kb_results or "（无相关知识库内容）",
        search_results=search_results or "",
        viz_results=viz_hint,
    )

    try:
        resp = llm.invoke(summary_prompt)
        result = resp.content
    except Exception as e:
        result = f"[Summary 调用失败] {type(e).__name__}: {e}"

    # ---- 写入 md 文件 ----
    try:
        ts = str(int(time.time()))
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "output",
        )
        os.makedirs(output_dir, exist_ok=True)
        md_path = os.path.join(output_dir, f"summary_{ts}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# 概率论 Agent 回答\n\n")
            f.write(f"**问题**：{user_input}\n\n")
            f.write(result)
    except Exception as e:
        pass  # md 文件写入失败不影响主流程

    return {"final_output": result, "current_step": "summary"}
