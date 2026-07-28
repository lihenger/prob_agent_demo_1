"""可视化工具 — 引用 prob-dist-viz 脚本生成交互式 HTML
"""

import os
import sys


DIST_NAME_MAP = {
    "chi-squared": "chi_square", "chi_squared": "chi_square",
    "chisquare": "chi_square", "chi2": "chi_square",
    "student": "student_t", "students_t": "student_t",
    "t": "student_t",
    "weibull": "weibull",
    "lognormal": "lognormal",
    "negative_binomial": "negative_binomial",
    "nb": "negative_binomial",
    "binom": "binomial",
    "exp": "exponential",
    "norm": "normal",
    "uniform": "uniform",
    "poisson": "poisson",
    "geometric": "geometric",
    "bernoulli": "bernoulli",
    "beta": "beta",
    "gamma": "gamma",
    "laplace": "laplace",
    "f": "f",
}


def _normalize_dist_type(name: str) -> str:
    """统一分布名变体为 catalog key（chi-square → chi_square）"""
    if not name:
        return name
    key = name.lower().replace("-", "_").replace(" ", "_").strip()
    return DIST_NAME_MAP.get(key, key)


def _find_skill_scripts() -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        os.path.join(base, "参考文档", "skills", "prob-dist-viz", "scripts"),
        os.path.join(base, "..", "skills", "prob-dist-viz", "scripts"),
    ]
    for p in candidates:
        if os.path.isdir(p):
            return p
    return ""


def generate_visualization(distribution_type: str, params: dict, user_input: str = "") -> str:
    distribution_type = _normalize_dist_type(distribution_type)
    if not distribution_type:
        return ""
    skill_dir = _find_skill_scripts()
    if not skill_dir:
        return "[可视化脚本目录未找到]"
    sys.path.insert(0, skill_dir)
    try:
        import distributions_catalog as dc
        import parse_input as pi
        from generate_visualization import build_html
        if distribution_type not in dc.CATALOG:
            return f"[暂不支持的分布类型：{distribution_type}]"
        dist = dc.CATALOG[distribution_type]

        # 优先用 skill 的 parse_input 从用户原始输入提取参数（覆盖 LLM 输出）
        skill_params = {}
        if user_input:
            try:
                parsed = pi.parse(user_input, override_type=distribution_type)
                skill_params = parsed.get("params", {})
            except Exception:
                skill_params = {}

        # 合并：用户输入解析结果 > LLM 传参 > catalog 默认值
        full_params = {}
        for name, spec in dist["params"].items():
            if name in skill_params:
                full_params[name] = float(skill_params[name])
            elif name in params:
                full_params[name] = float(params[name])
            else:
                full_params[name] = float(spec["default"])

        domain = dist["domain_fn"](full_params)
        desc = {
            "distribution_type": distribution_type,
            "display_name": dist["display_name"],
            "is_discrete": dist["is_discrete"],
            "params": full_params,
            "domain": domain, "mode": "catalog",
            "raw_formula": None,
            "source_input": f"{distribution_type}({','.join(f'{k}={v}' for k,v in full_params.items())})",
        }
        html = build_html(desc)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(base_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{distribution_type}_viz.html")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        return output_path
    except Exception as e:
        return f"[可视化生成失败] {type(e).__name__}: {e}"
    finally:
        if skill_dir in sys.path:
            sys.path.remove(skill_dir)
