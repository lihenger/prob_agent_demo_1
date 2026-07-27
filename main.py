"""概率论与数理统计 Agent Demo — CLI 入口（清理后版本）
"""
import os
import time
from workflow.graph import build_graph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command


def stream_print(text: str, delay: float = 0.02):
    for char in text:
        print(char, end="", flush=True)
        time.sleep(delay)
    print()


def print_header():
    print("=" * 60)
    print("  概率论与数理统计 Agent Demo")
    print("  Powered by LangGraph + DeepSeek")
    print("=" * 60)
    print()


STAGE_LABELS = {
    "execute_kb": "知识库检索",
    "execute_search": "网络搜索",
    "execute_viz": "可视化生成",
    "summary": "内容优化",
}


def _run_simple_mode(graph, config):
    """simple 模式：自动批准，stream 到结束，直接输出回答。"""
    for event in graph.stream(
        Command(resume={"approved": True}), config, stream_mode="updates"
    ):
        pass
    state = graph.get_state(config)
    out = state.values.get("final_output", "")
    if out:
        print("\n===== 回答 =====\n")
        stream_print(out)


def _display_plan(plan):
    kb_s = "\u662f" if plan.get("need_kb") else "\u5426"
    sr_s = "\u662f" if plan.get("need_search") else "\u5426"
    vz_s = "\u662f" if plan.get("need_viz") else "\u5426"
    print(f"  知识库={kb_s}  搜索={sr_s}  可视化={vz_s}")
    if plan.get("target_distribution"):
        print(f"  涉及分布：{plan['target_distribution']}")
    print(f"  理由：{plan.get('reasoning', '')}\n")


def _show_results(state):
    final_output = state.values.get("final_output", "")
    viz_path = state.values.get("viz_path", "")
    if final_output:
        print("\n===== 回答 =====\n")
        stream_print(final_output)
    if viz_path and not viz_path.startswith("["):
        print(f"\n[图表] 可视化文件：{os.path.abspath(viz_path)}")


def main():
    from config.settings import DEEPSEEK_API_KEY

    if not DEEPSEEK_API_KEY:
        print("[!] 未找到 DeepSeek API Key")
        print("    在项目根目录创建 .env 文件：echo DEEPSEEK_API_KEY=sk-your-key > .env")
        return

    memory = MemorySaver()
    graph = build_graph(memory)

    print_header()
    print("输入 exit 退出，输入 clear 重置会话\n")

    while True:
        try:
            user_input = input("\n>>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("再见！")
            break
        if user_input.lower() == "clear":
            print("[会话已重置]")
            continue

        thread_id = f"thread_{int(time.time())}"
        config = {"configurable": {"thread_id": thread_id}}

        # ---- Phase 1: 初始分析 ----
        print("\n===== 分析中 =====\n")
        for event in graph.stream({
            "user_input": user_input, "messages": [],
            "errors": [], "message_history": [],
        }, config, stream_mode="updates"):
            if "__interrupt__" in event:
                break

        state = graph.get_state(config)
        plan = state.values.get("plan", {})

        # ---- 计划审查循环（内层） ----
        while True:
            # simple 模式：问候/闲聊自动批准，直接输出
            if plan.get("response_mode") == "simple":
                _run_simple_mode(graph, config)
                break

            if not plan.get("reasoning"):
                print("[跳过] 未生成有效计划\n")
                break

            print("===== 执行计划 =====\n")
            _display_plan(plan)
            choice = input("执行此计划？(y/n): ").strip().lower()

            if choice in ("y", "yes"):
                print("\n===== 执行阶段 =====\n")
                step = 0
                for event in graph.stream(
                    Command(resume={"approved": True}), config, stream_mode="updates"
                ):
                    node_name = next(iter(event))
                    if node_name in STAGE_LABELS:
                        step += 1
                        print(f"===== ({step}) {STAGE_LABELS[node_name]} =====\n")
                        time.sleep(0.5)
                state = graph.get_state(config)
                _show_results(state)
                break

            if choice in ("n", "no"):
                correction = input("\n请补充或修正你的问题：").strip()
                if not correction or len(correction) < 2:
                    print("[已取消]\n")
                    break

                # 拒绝 + 合并修正 → 退回 orchestrator 重新分析
                merged = user_input + " " + correction
                user_input = merged    # 累积修正，下一轮在此之上继续追加
                print("\n===== 重新分析中 =====\n")
                for event in graph.stream(
                    Command(resume={"approved": False, "corrected_input": merged}),
                    config, stream_mode="updates"
                ):
                    if "__interrupt__" in event:
                        break
                state = graph.get_state(config)
                plan = state.values.get("plan", {})
                continue

            # 其他输入视为取消
            print("[已取消]\n")
            break


if __name__ == "__main__":
    main()
