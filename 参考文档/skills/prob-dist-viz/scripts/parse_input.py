#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parse_input.py
==============
将用户多种格式的输入统一解析为「标准分布描述 JSON」。

支持输入形态：
  1. 常见分布名称 + 参数：  "正态分布 N(0,1)" / "泊松分布 λ=3" / "Binomial(10,0.5)"
  2. 概率密度函数：        "f(x)=λe^{-λx}, x≥0"
  3. 分布函数表达式：      "F(x)=1-e^{-λx}"
  4. 口头描述：            "描述独立随机事件发生间隔的分布"
  5. 自定义公式（兜底）：   "f(x)=x*exp(-x/2)"

用法：
  python parse_input.py --input "正态分布 N(0,1)"
  python parse_input.py --input "..." --out dist.json
  python parse_input.py --type poisson --params-json '{"lam":3}'
  echo "..." | python parse_input.py

可选参数：
  --type        直接指定分布类型（跳过自动识别），如 poisson / normal
  --params-json 直接提供参数 JSON，如 '{"lam":2}'
  --out         将标准 JSON 写入该文件（同时仍打印到 stdout）
"""

import argparse
import json
import re
import sys

import distributions_catalog as dc

# 口头描述关键词 → 分布类型（别名匹配失败时的兜底）
KEYWORD_MAP = [
    (["间隔", "到达时间", "等待时间", "寿命", "无记忆", "失效时间", "事件间隔", "泊松过程"], "exponential"),
    (["次数", "发生数", "单位时间", "单位面积", "稀有事件", "来话", "计数", " Kendall"], "poisson"),
    (["成功次数", "n次", "试验成功", "合格率", "n 次"], "binomial"),
    (["首次", "第一次成功"], "geometric"),
    (["第", "次成功", "失败次数"], "negative_binomial"),
    (["比例", "概率p", "百分比", "完成率", "比率"], "beta"),
    (["误差", "测量误差", "钟形", "高斯", "集中"], "normal"),
    (["均匀", "等可能", "区间"], "uniform"),
    (["方差", "拟合优度", "卡方", "独立性检验"], "chi_square"),
    (["小样本", "t检验", "均值推断", "学生"], "student_t"),
    (["可靠性", "失效分析", "风速", "极端值"], "weibull"),
    (["收入", "财富", "股价", "对数", "右偏"], "lognormal"),
    (["一次试验", "0或1", "是非", "0/1"], "bernoulli"),
    (["双指数", "拉普拉斯", "厚尾"], "laplace"),
    (["伽马", "等待第", "erlang"], "gamma"),
    (["F分布", "f分布", "费舍尔", "fisher", "snedecor", "方差比"], "f"),
]

# 参数名 → 识别正则（希腊/拉丁）
PARAM_PATTERNS = {
    "mu":    r"(?:μ|mu|miu)",
    "sigma": r"(?:σ|sigma)",
    "lam":   r"(?:λ|lam|lambda)",
    "alpha": r"(?:α|alpha)",
    "beta":  r"(?:β|beta)",
    "nu":    r"(?:ν|nu)",
    "theta": r"(?:θ|theta)",
    "k":     r"k",
    "p":     r"p",
    "n":     r"n",
    "r":     r"r",
    "a":     r"a",
    "b":     r"b",
    "df":    r"df",
}
GREEK_OF = {"lam": "λ", "mu": "μ", "sigma": "σ", "alpha": "α", "beta": "β", "nu": "ν", "theta": "θ"}

RESERVED_TOKENS = {"Math", "exp", "sqrt", "log", "abs", "sin", "cos", "tan",
                   "gamma", "beta", "pow", "PI", "E", "x"}

# 参数跨名映射：用户常说"卡方 n=5"（n→k）、"t 分布 df=10"（df→nu）等
# key → catalog 参数名，按分布区分
PARAM_REMAP = {
    "chi_square":  {"n": "k", "df": "k"},
    "student_t":   {"n": "nu", "df": "nu"},
    "poisson":     {"lambda": "lam"},
    "exponential": {"lambda": "lam"},
}


def match_type(text):
    """返回分布类型字符串（含别名与关键词兜底）。"""
    t = text.lower()
    # 1) 别名精确匹配（优先最长别名；跳过带 "(" 的记号，避免与数学函数 exp()/gamma() 混淆）
    best, best_len = None, 0
    for dtype, e in dc.CATALOG.items():
        for alias in e["aliases"]:
            if alias.endswith("("):
                continue
            al = alias.lower()
            if al in t and len(al) > best_len:
                best, best_len = dtype, len(al)
    if best:
        return best
    # 2) 关键词兜底
    for keywords, dtype in KEYWORD_MAP:
        if any(kw in text for kw in keywords):
            return dtype
    return None


# 仅用于「括号参数」提取的记号（与别名检测分离，避免误匹配数学函数）
PAREN_NOTATIONS = {
    "normal": ["n", "N"],
    "uniform": ["u", "U"],
    "exponential": ["exp"],
    "gamma": ["gamma", "Gamma"],
    "beta": ["beta", "Beta"],
    "weibull": ["weibull", "Weibull"],
    "laplace": ["laplace", "Laplace"],
    "lognormal": ["lognormal"],
    "bernoulli": ["bernoulli", "Bernoulli"],
    "binomial": ["binomial", "Binomial", "binom"],
    "poisson": ["poisson", "Poisson"],
    "geometric": ["geometric", "Geometric"],
    "negative_binomial": ["negative_binomial", "nb"],
    "f": ["f", "F"],
}


def _parse_numbers(s):
    """从 '0,1' / '0.5, 3' 中解析出浮点数列表。"""
    return [float(x) for x in re.findall(r"-?\d*\.?\d+", s)]


def extract_parenthetical(text, dtype):
    """尝试从输入中提取形如 Name(a,b) 或 (a,b) 的参数。"""
    entry = dc.CATALOG[dtype]
    names = list(entry["params"].keys())
    # 优先：记号后紧跟的括号
    for note in PAREN_NOTATIONS.get(dtype, []):
        m = re.search(re.escape(note) + r"\s*\(([^)]*)\)", text, re.IGNORECASE)
        if m:
            nums = _parse_numbers(m.group(1))
            if nums:
                return dict(zip(names[: len(nums)], nums))
    # 兜底：文本中第一个含数字的括号
    m = re.search(r"\(([^)]*)\)", text)
    if m and re.search(r"\d", m.group(1)):
        nums = _parse_numbers(m.group(1))
        if nums:
            return dict(zip(names[: len(nums)], nums))
    return {}


def extract_params(text, dtype, entry):
    """综合「括号参数 + param=value」提取参数。"""
    params = extract_parenthetical(text, dtype)
    # 应用参数跨名映射：将用户常用名转为 catalog 名
    remap = PARAM_REMAP.get(dtype, {})
    params = {remap.get(k, k): v for k, v in params.items()}
    for key, pat in PARAM_PATTERNS.items():
        if key in params:
            continue
        # 跳过不属于当前分布的参数（除非有跨名映射）
        if key not in entry["params"]:
            mapped = remap.get(key)
            if mapped is None:
                continue
            # 如果映射目标已有值，不覆盖
            if mapped in params:
                continue
            m = re.search(r"(?<![A-Za-z])" + pat + r"(?:\s*=\s*)(-?\d*\.?\d+)", text)
            if m:
                params[mapped] = float(m.group(1))
            continue
        m = re.search(r"(?<![A-Za-z])" + pat + r"(?:\s*=\s*)(-?\d*\.?\d+)", text)
        if m:
            params[key] = float(m.group(1))
    # 补全默认值
    for key, spec in entry["params"].items():
        params.setdefault(key, spec["default"])
    return params


# ---------------------------------------------------------------------------
# 公式模式（自定义公式兜底）
# ---------------------------------------------------------------------------
def _to_js_expr(rhs):
    s = rhs.strip()
    # 注意顺序：先处理 exp(...) 再处理 e^{...}，避免 Math.exp( 被二次替换
    s = re.sub(r"exp\s*\(", "Math.exp(", s)
    # e^{...} / e^(...) / e^x
    s = re.sub(r"e\^\{([^}]*)\}", r"Math.exp(\1)", s)
    s = re.sub(r"e\^\(([^)]*)\)", r"Math.exp(\1)", s)
    s = re.sub(r"e\^([A-Za-z0-9_.+\-]+)", r"Math.exp(\1)", s)
    # 希腊字母 → 拉丁，并补上隐式乘法（尾随 *，由后续清理处理）
    s = s.replace("λ", "lam*").replace("α", "alpha*").replace("β", "beta*") \
         .replace("μ", "mu*").replace("σ", "sigma*").replace("ν", "nu*") \
         .replace("θ", "theta*").replace("π", "PI")
    # 其余函数名
    for a, b in [("sqrt", "Math.sqrt"), ("ln", "Math.log"), ("log", "Math.log"),
                 ("abs", "Math.abs"), ("sin", "Math.sin"), ("cos", "Math.cos"),
                 ("tan", "Math.tan"), ("Γ", "_gamma"), ("B(", "_beta(")]:
        s = s.replace(a, b)
    # 剩余 caret → 幂
    s = s.replace("^", "**")
    # JS 中一元负号不能直接位于 ** 前（如 -x**2 非法），需加括号
    s = re.sub(r"-\s*([A-Za-z0-9_.]+)\s*\*\*\s*([A-Za-z0-9_.]+)", r"-(\1**\2)", s)
    # 隐式乘法：数字后紧跟字母/括号
    s = re.sub(r"(\d)([A-Za-z(])", r"\1*\2", s)
    # 清理多余/错误的 *
    s = re.sub(r"\*([)\]])", r"\1", s)
    s = re.sub(r"([(])\*", r"\1", s)
    s = s.strip("*")
    return s


def _detect_params(text, expr):
    tokens = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", expr))
    params = {}
    warnings = []
    for tok in tokens:
        if tok in RESERVED_TOKENS:
            continue
        val = None
        # 尝试拉丁名
        m = re.search(r"(?<![A-Za-z])" + re.escape(tok) + r"(?:\s*=\s*)(-?\d*\.?\d+)", text)
        if m:
            val = float(m.group(1))
        # 尝试对应希腊字符
        greek = GREEK_OF.get(tok)
        if val is None and greek:
            m2 = re.search(re.escape(greek) + r"(?:\s*=\s*)(-?\d*\.?\d+)", text)
            if m2:
                val = float(m2.group(1))
        if val is None:
            val = 1.0
            warnings.append(f"公式中的参数 '{tok}' 未在输入中给出取值，已默认设为 1，请核实。")
        params[tok] = val
    return params, warnings


def parse_formula(text):
    """从 'f(x)=...' / 'F(x)=...' 等提取公式并构造 formula 模式 JSON。"""
    warnings = []
    m = re.search(r"[fFpP]\s*\([xXkK]\)\s*=\s*([^\n,，]+)", text)
    if not m:
        # 退而求其次：取第一个等号后的表达式
        m = re.search(r"=\s*([^\n,，]+)", text)
    if not m:
        raise ValueError("未能从输入中识别公式，请使用 f(x)=... 形式。")
    rhs = m.group(1).strip()
    expr = _to_js_expr(rhs)
    params, pw = _detect_params(text, expr)
    warnings += pw
    # 定义域推断
    lo, hi = -5.0, 5.0
    if re.search(r"x\s*>\s*=\s*0|x\s*>=\s*0|x≥0", text):
        lo = 0.0
        if "lam" in params and params["lam"] > 0:
            hi = 5.0 / params["lam"]
    mm = re.search(r"x\s*∈\s*\[?\s*(-?\d*\.?\d+)\s*,\s*(-?\d*\.?\d+)\s*\]?", text)
    if mm:
        lo, hi = float(mm.group(1)), float(mm.group(2))
    return {
        "distribution_type": "custom",
        "display_name": "自定义公式分布",
        "is_discrete": False,
        "params": params,
        "domain": [lo, hi],
        "mode": "formula",
        "raw_formula": expr,
        "display_formula": rhs,
        "source_input": text,
        "warnings": warnings,
    }


def match_cdf_type(text):
    """若输入为分布函数 F(x)=... 形式且能识别为已知分布，返回类型；否则 None。"""
    if not re.search(r"F\s*\(|分布函数", text):
        return None
    # 指数分布 CDF：1 - e^{-...x} 形式
    if re.search(r"1\s*-\s*(?:e\^\{|e\^\(|exp\()", text) and re.search(r"[λx]", text):
        return "exponential"
    # 均匀分布 CDF：(x-a)/(b-a)
    if "(x-a)" in text.lower() or "(x − a)" in text.lower():
        return "uniform"
    return None


def parse(text, override_type=None, override_params=None):
    dtype = override_type or match_type(text) or match_cdf_type(text)
    if not dtype or dtype not in dc.CATALOG:
        if dtype == "custom":
            return parse_formula(text)
        # 尝试公式模式
        try:
            return parse_formula(text)
        except Exception:
            pass
        raise ValueError(f"无法识别分布类型，输入：{text!r}。可改用 f(x)=... 形式，或显式指定 --type。")
    entry = dc.CATALOG[dtype]
    if override_params:
        params = {k: float(v) for k, v in override_params.items()}
        for key, spec in entry["params"].items():
            params.setdefault(key, spec["default"])
    else:
        params = extract_params(text, dtype, entry)
        # 指数分布 CDF 形如 F(x)=1-e^{-kx} / 1-e^{-x/θ}：从指数系数反推 λ
        if dtype == "exponential":
            low = text.lower()
            if "λ" not in text and "lam" not in low and "lambda" not in low:
                mc = re.search(r"e\^\{-?\s*([0-9]*\.?[0-9]+)\s*\*?\s*x", text)
                if mc:
                    params["lam"] = float(mc.group(1))
                else:
                    mc2 = re.search(r"e\^\{-?\s*x\s*/\s*([0-9.]+)", text)
                    if mc2:
                        params["lam"] = 1.0 / float(mc2.group(1))
    domain = dc.compute_domain(dtype, params)
    return {
        "distribution_type": dtype,
        "display_name": entry["display_name"],
        "is_discrete": entry["is_discrete"],
        "params": params,
        "domain": domain,
        "mode": "catalog",
        "raw_formula": None,
        "source_input": text,
        "warnings": [],
    }


def main():
    ap = argparse.ArgumentParser(description="将概率分布输入解析为标准 JSON")
    ap.add_argument("--input", help="用户输入文本（省略则从 stdin 读取）")
    ap.add_argument("--type", help="直接指定分布类型，跳过自动识别")
    ap.add_argument("--params-json", help="直接提供参数 JSON，如 '{\"lam\":3}'")
    ap.add_argument("--out", help="将标准 JSON 写入该文件")
    args = ap.parse_args()

    text = args.input if args.input is not None else sys.stdin.read()
    override_params = json.loads(args.params_json) if args.params_json else None

    result = parse(text, override_type=args.type, override_params=override_params)
    out = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"[ok] 已写入 {args.out}", file=sys.stderr)
    print(out)


if __name__ == "__main__":
    main()
