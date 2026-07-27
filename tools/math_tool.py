"""数学计算工具 — SymPy 占位实现

[Extension] 大产品升级为真实 SymPy 符号计算：
- 替换实现为：sympy.parse_expr -> solve/diff/integrate/simplify -> latex 渲染
- 保持 math_compute(user_input: str, mode: str) -> str 签名不变
"""


def math_compute(user_input: str, mode: str) -> str:
    """模拟数学计算，返回占位提示
    Args:
        user_input: 用户查询
        mode: 解题模式 ("solve" / "compare" / "grade")
    Returns:
        模拟计算结果的提示前缀
    """
    mode_labels = {"solve": "解题", "compare": "多解对比", "grade": "批改"}
    mode_text = mode_labels.get(mode, mode)
    return (
        f"【模拟数学计算 - {mode_text}模式】\n"
        f"用户输入：{user_input}\n"
        "说明：当前为模拟计算模式。\n"
        "计算过程将由 DeepSeek 基于其内置数学能力生成。\n"
        "---\n"
    )
