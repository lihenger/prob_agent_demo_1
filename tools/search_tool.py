"""模拟搜索工具

[Extension] 大产品中替换为真实搜索引擎（Tavily / DuckDuckGo / Bing API）：
- 保持 simulate_search(user_input: str) -> str 签名不变
- 替换实现为 requests 调用搜索 API -> 提取摘要文本
"""

def simulate_search(user_input: str) -> str:
    """模拟网络搜索，返回占位提示
    Args:
        user_input: 用户查询
    Returns:
        模拟结果的提示前缀（实际内容由 DeepSeek 在 knowledge.py 中生成）
    """
    return (
        "【模拟搜索结果】\n"
        f"用户查询：{user_input}\n"
        "说明：当前为模拟搜索模式。\n"
        "搜索上下文将由 DeepSeek 基于其内置知识生成。\n"
        "---\n"
    )
