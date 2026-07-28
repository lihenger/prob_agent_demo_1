#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
distributions_catalog.py
========================
概率分布目录：单一数据源，供 `parse_input.py`（解析/校验）与
`generate_visualization.py`（生成 HTML 动画）复用。

每个条目包含：
  - display_name : 中文显示名
  - is_discrete  : 是否离散分布
  - aliases      : 名称/别名（中英文、简写），用于解析时匹配
  - params       : 参数规格 {name: {default, min, max, step, label}}
  - morph_param  : 参数敏感性面板自动演示时优先变化的参数名
  - domain_fn    : lambda(p)->[lo, hi]，按参数计算绘图定义域
  - pdf_js       : JS 版密度/质量函数字符串 "function(x,p){...}"
  - pdf_py       : Python 版密度/质量函数（用于数值校验/采样）
  - formula      : 显示用公式文本
  - mean/variance/std/char_func/mgf : 结构化知识（字符串）
  - applications : 典型应用场景（列表）

JS 端还会注入 JS_HELPERS（gamma / lgamma / beta / comb 等）。
CDF 由可视化生成器对 pdf 做数值积分得到，无需逐分布提供 cdf。
"""

import math

# ---------------------------------------------------------------------------
# JS 辅助函数（注入到生成的 HTML 中，供 pdf_js 调用）
# ---------------------------------------------------------------------------
JS_HELPERS = r"""
var PI = Math.PI;
function _lgamma(z){
  var g=7;
  var c=[0.99999999999980993,676.5203681218851,-1259.1392167224028,
         771.32342877765313,-176.61502916214059,12.507343278686905,
         -0.13857109526572012,9.9843695780195716e-6,1.5056327351493116e-7];
  if(z<0.5){ return Math.log(PI/Math.sin(PI*z)) - _lgamma(1-z); }
  z-=1;
  var x=c[0];
  for(var i=1;i<g+2;i++){ x+=c[i]/(z+i); }
  var t=z+g+0.5;
  return 0.5*Math.log(2*PI) + (z+0.5)*Math.log(t) - t + Math.log(x);
}
function _gamma(z){ return Math.exp(_lgamma(z)); }
function _beta(a,b){ return _gamma(a)*_gamma(b)/_gamma(a+b); }
function _comb(n,k){
  n=Math.round(n); k=Math.round(k);
  if(k<0||k>n) return 0;
  return Math.exp(_lgamma(n+1)-_lgamma(k+1)-_lgamma(n-k+1));
}
"""

# ---------------------------------------------------------------------------
# 辅助：F 分布定义域（按自由度自适应右界，容纳重尾）
# ---------------------------------------------------------------------------
def _f_domain(p):
    d1, d2 = p["d1"], p["d2"]
    if d2 > 4:
        m = d2 / (d2 - 2)
        var = 2 * d2 * d2 * (d1 + d2 - 2) / (d1 * (d2 - 2) ** 2 * (d2 - 4))
        s = math.sqrt(var) if var > 0 else 1.0
        hi = m + 5 * s
    elif d2 > 2:
        m = d2 / (d2 - 2)
        hi = m * 3 + 4
    else:
        hi = max(12.0, 5.0 * d1)
    return [0.0, float(max(hi, 8.0))]


# ---------------------------------------------------------------------------
# 分布目录
# ---------------------------------------------------------------------------
CATALOG = {
    # ===================== 连续分布 =====================
    "normal": {
        "display_name": "正态分布",
        "is_discrete": False,
        "aliases": ["normal", "gaussian", "正态", "高斯", "gauss"],
        "params": {
            "mu":    {"default": 0.0, "min": -5.0, "max": 5.0, "step": 0.1, "label": "μ"},
            "sigma": {"default": 1.0, "min": 0.2, "max": 3.0, "step": 0.1, "label": "σ"},
        },
        "morph_param": "sigma",
        "domain_fn": lambda p: [p["mu"] - 4 * p["sigma"], p["mu"] + 4 * p["sigma"]],
        "pdf_js": "function(x,p){var s=p.sigma;return Math.exp(-((x-p.mu)*(x-p.mu))/(2*s*s))/(s*Math.sqrt(2*PI));}",
        "pdf_py": lambda x, p: math.exp(-((x - p["mu"]) ** 2) / (2 * p["sigma"] ** 2)) / (p["sigma"] * math.sqrt(2 * math.pi)),
        "formula": "f(x) = 1/(σ√2π) · e^( -(x-μ)²/(2σ²) )",
        "mean": "μ", "variance": "σ²", "std": "σ",
        "char_func": "φ(t) = exp(iμt − σ²t²/2)",
        "mgf": "M(t) = exp(μt + σ²t²/2),  t∈ℝ",
        "applications": ["测量误差建模", "身高/体重等生物度量", "中心极限定理", "金融收益率近似"],
    },
    "uniform": {
        "display_name": "均匀分布",
        "is_discrete": False,
        "aliases": ["uniform", "均匀", "均匀分布"],
        "params": {
            "a": {"default": 0.0, "min": -5.0, "max": 5.0, "step": 0.1, "label": "a"},
            "b": {"default": 1.0, "min": -4.0, "max": 6.0, "step": 0.1, "label": "b"},
        },
        "morph_param": "b",
        "domain_fn": lambda p: [p["a"] - 0.15 * (p["b"] - p["a"]), p["b"] + 0.15 * (p["b"] - p["a"])],
        "pdf_js": "function(x,p){ if(x<p.a||x>p.b) return 0; return 1/(p.b-p.a); }",
        "pdf_py": lambda x, p: 1 / (p["b"] - p["a"]) if p["a"] <= x <= p["b"] else 0,
        "formula": "f(x) = 1/(b−a),  x∈[a,b]",
        "mean": "(a+b)/2", "variance": "(b−a)²/12", "std": "(b−a)/√12",
        "char_func": "φ(t) = (e^(itb) − e^(ita))/(it(b−a))",
        "mgf": "M(t) = (e^(tb) − e^(ta))/(t(b−a))",
        "applications": ["舍入误差", "随机数生成", "等可能区间建模"],
    },
    "exponential": {
        "display_name": "指数分布",
        "is_discrete": False,
        "aliases": ["exponential", "指数", "指数分布"],
        "params": {
            "lam": {"default": 1.0, "min": 0.2, "max": 4.0, "step": 0.1, "label": "λ"},
        },
        "morph_param": "lam",
        "domain_fn": lambda p: [0.0, 5.0 / p["lam"]],
        "pdf_js": "function(x,p){ if(x<0) return 0; return p.lam*Math.exp(-p.lam*x); }",
        "pdf_py": lambda x, p: p["lam"] * math.exp(-p["lam"] * x) if x >= 0 else 0,
        "formula": "f(x) = λe^(−λx),  x≥0",
        "mean": "1/λ", "variance": "1/λ²", "std": "1/λ",
        "char_func": "φ(t) = λ/(λ − it)",
        "mgf": "M(t) = λ/(λ − t),  t<λ",
        "applications": ["独立事件时间间隔（泊松过程）", "设备寿命", "排队等待时间"],
    },
    "gamma": {
        "display_name": "伽马分布",
        "is_discrete": False,
        "aliases": ["gamma", "伽马", "伽玛"],
        "params": {
            "alpha": {"default": 2.0, "min": 0.3, "max": 8.0, "step": 0.1, "label": "α"},
            "beta":  {"default": 1.0, "min": 0.2, "max": 4.0, "step": 0.1, "label": "β"},
        },
        "morph_param": "alpha",
        "domain_fn": lambda p: [0.0, (p["alpha"] + 4 * math.sqrt(p["alpha"])) / p["beta"]],
        "pdf_js": "function(x,p){ if(x<=0) return 0; var a=p.alpha,b=p.beta; return Math.pow(b,a)*Math.pow(x,a-1)*Math.exp(-b*x)/_gamma(a); }",
        "pdf_py": lambda x, p: (p["beta"] ** p["alpha"]) * (x ** (p["alpha"] - 1)) * math.exp(-p["beta"] * x) / math.gamma(p["alpha"]) if x > 0 else 0,
        "formula": "f(x) = β^α x^(α−1) e^(−βx) / Γ(α),  x>0  (β为速率)",
        "mean": "α/β", "variance": "α/β²", "std": "√α/β",
        "char_func": "φ(t) = (β/(β − it))^α",
        "mgf": "M(t) = (β/(β − t))^α,  t<β",
        "applications": ["等待第k个事件发生的时间", "降雨量的聚合模型", "贝叶斯共轭先验"],
    },
    "beta": {
        "display_name": "贝塔分布",
        "is_discrete": False,
        "aliases": ["beta", "贝塔"],
        "params": {
            "alpha": {"default": 2.0, "min": 0.3, "max": 8.0, "step": 0.1, "label": "α"},
            "beta":  {"default": 2.0, "min": 0.3, "max": 8.0, "step": 0.1, "label": "β"},
        },
        "morph_param": "alpha",
        "domain_fn": lambda p: [0.0, 1.0],
        "pdf_js": "function(x,p){ if(x<=0||x>=1) return 0; var a=p.alpha,b=p.beta; return Math.pow(x,a-1)*Math.pow(1-x,b-1)/_beta(a,b); }",
        "pdf_py": lambda x, p: (x ** (p["alpha"] - 1)) * ((1 - x) ** (p["beta"] - 1)) / (math.gamma(p["alpha"]) * math.gamma(p["beta"]) / math.gamma(p["alpha"] + p["beta"])) if 0 < x < 1 else 0,
        "formula": "f(x) = x^(α−1)(1−x)^(β−1) / B(α,β),  x∈(0,1)",
        "mean": "α/(α+β)", "variance": "αβ/((α+β)²(α+β+1))", "std": "√(αβ/((α+β)²(α+β+1)))",
        "char_func": "无简单闭式（用合流超几何函数表示）",
        "mgf": "M(t) = ₁F₁(α; α+β; t)",
        "applications": ["比例/概率建模", "贝叶斯伯努利试验的共轭先验", "订单完成率估计"],
    },
    "chi_square": {
        "display_name": "卡方分布",
        "is_discrete": False,
        "aliases": ["chi_square", "chi-square", "chisq", "卡方", "卡方分布"],
        "params": {
            "k": {"default": 3.0, "min": 1.0, "max": 15.0, "step": 1.0, "label": "k"},
        },
        "morph_param": "k",
        "domain_fn": lambda p: [0.0, p["k"] + 4 * math.sqrt(2 * p["k"])],
        "pdf_js": "function(x,p){ if(x<=0) return 0; var k=p.k; return Math.pow(x,k/2-1)*Math.exp(-x/2)/(Math.pow(2,k/2)*_gamma(k/2)); }",
        "pdf_py": lambda x, p: (x ** (p["k"] / 2 - 1)) * math.exp(-x / 2) / ((2 ** (p["k"] / 2)) * math.gamma(p["k"] / 2)) if x > 0 else 0,
        "formula": "f(x) = x^(k/2−1) e^(−x/2) / (2^(k/2) Γ(k/2)),  x>0",
        "mean": "k", "variance": "2k", "std": "√(2k)",
        "char_func": "φ(t) = (1 − 2it)^(−k/2)",
        "mgf": "M(t) = (1 − 2t)^(−k/2),  t<1/2",
        "applications": ["方差的推断", "拟合优度检验", "独立性检验", "伽马分布 k/2 特例"],
        "construction": {"latex": r"\chi^2=\sum_{i=1}^{k} Z_i^{\,2},\quad Z_i\overset{iid}{\sim}N(0,1)", "text": "χ² = Σᵢ Zᵢ²，Zᵢ 独立同分布 ~ N(0,1)"},
    },
    "student_t": {
        "display_name": "学生 t 分布",
        "is_discrete": False,
        "aliases": ["student_t", "student-t", "student", "t分布", "t 分布", "学生t", "学生 t"],
        "params": {
            "nu": {"default": 5.0, "min": 1.0, "max": 30.0, "step": 1.0, "label": "ν"},
        },
        "morph_param": "nu",
        "domain_fn": lambda p: [-(max(6, 4 * math.sqrt(p["nu"]))), max(6, 4 * math.sqrt(p["nu"]))],
        "pdf_js": "function(x,p){ var nu=p.nu; var c=_gamma((nu+1)/2)/(_gamma(nu/2)*Math.sqrt(nu*PI)); return c*Math.pow(1+x*x/nu, -(nu+1)/2); }",
        "pdf_py": lambda x, p: (math.gamma((p["nu"] + 1) / 2) / (math.gamma(p["nu"] / 2) * math.sqrt(p["nu"] * math.pi))) * ((1 + x * x / p["nu"]) ** (-(p["nu"] + 1) / 2)),
        "formula": "f(x) = Γ((ν+1)/2) / (√(νπ) Γ(ν/2)) · (1 + x²/ν)^(−(ν+1)/2)",
        "mean": "0 (ν>1); 不存在 (ν=1)", "variance": "ν/(ν−2) (ν>2); ∞ (1<ν≤2)",
        "std": "√(ν/(ν−2))",
        "char_func": "无简单闭式",
        "mgf": "不存在",
        "applications": ["小样本均值推断", "回归系数显著性检验", "正态总体方差未知时的 t 检验"],
        "construction": {"latex": r"t=\dfrac{Z}{\sqrt{V/\nu}},\quad Z\sim N(0,1),\ V\sim\chi^2(\nu)\ \text{indep.}", "text": "t = Z/√(V/ν)，Z~N(0,1)、V~χ²(ν) 相互独立"},
    },
    "weibull": {
        "display_name": "韦布尔分布",
        "is_discrete": False,
        "aliases": ["weibull", "韦布尔", "威布尔", "weibull("],
        "params": {
            "lam": {"default": 1.0, "min": 0.2, "max": 4.0, "step": 0.1, "label": "λ"},
            "k":   {"default": 1.5, "min": 0.3, "max": 6.0, "step": 0.1, "label": "k"},
        },
        "morph_param": "k",
        "domain_fn": lambda p: [0.0, p["lam"] * ((4.6) ** (1.0 / p["k"]))],
        "pdf_js": "function(x,p){ if(x<0) return 0; var lam=p.lam,k=p.k; return (k/lam)*Math.pow(x/lam,k-1)*Math.exp(-Math.pow(x/lam,k)); }",
        "pdf_py": lambda x, p: (p["k"] / p["lam"]) * (x / p["lam"]) ** (p["k"] - 1) * math.exp(-(x / p["lam"]) ** p["k"]) if x >= 0 else 0,
        "formula": "f(x) = (k/λ)(x/λ)^(k−1) e^(−(x/λ)^k),  x≥0",
        "mean": "λ·Γ(1+1/k)", "variance": "λ²[Γ(1+2/k) − Γ²(1+1/k)]", "std": "λ·√[Γ(1+2/k) − Γ²(1+1/k)]",
        "char_func": "无简单闭式",
        "mgf": "不存在",
        "applications": ["可靠性工程/失效分析", "风速建模", "极端值分析"],
    },
    "laplace": {
        "display_name": "拉普拉斯分布",
        "is_discrete": False,
        "aliases": ["laplace", "拉普拉斯", "双指数", "laplace("],
        "params": {
            "mu": {"default": 0.0, "min": -5.0, "max": 5.0, "step": 0.1, "label": "μ"},
            "b":  {"default": 1.0, "min": 0.2, "max": 4.0, "step": 0.1, "label": "b"},
        },
        "morph_param": "b",
        "domain_fn": lambda p: [p["mu"] - 6 * p["b"], p["mu"] + 6 * p["b"]],
        "pdf_js": "function(x,p){ return Math.exp(-Math.abs(x-p.mu)/p.b)/(2*p.b); }",
        "pdf_py": lambda x, p: math.exp(-abs(x - p["mu"]) / p["b"]) / (2 * p["b"]),
        "formula": "f(x) = 1/(2b) · e^(−|x−μ|/b)",
        "mean": "μ", "variance": "2b²", "std": "b√2",
        "char_func": "φ(t) = e^(iμt) / (1 + b²t²)",
        "mgf": "M(t) = e^(μt) / (1 − b²t²),  |t|<1/b",
        "applications": ["金融收益率尾部", "差分信号建模", "鲁棒回归的误差项"],
    },
    "lognormal": {
        "display_name": "对数正态分布",
        "is_discrete": False,
        "aliases": ["lognormal", "log-normal", "对数正态", "lognormal("],
        "params": {
            "mu":    {"default": 0.0, "min": -1.0, "max": 2.0, "step": 0.1, "label": "μ"},
            "sigma": {"default": 0.5, "min": 0.1, "max": 1.5, "step": 0.1, "label": "σ"},
        },
        "morph_param": "sigma",
        "domain_fn": lambda p: [0.0, math.exp(p["mu"] + 3 * p["sigma"])],
        "pdf_js": "function(x,p){ if(x<=0) return 0; var m=p.mu,s=p.sigma; return Math.exp(-Math.pow(Math.log(x)-m,2)/(2*s*s))/(x*s*Math.sqrt(2*PI)); }",
        "pdf_py": lambda x, p: math.exp(-((math.log(x) - p["mu"]) ** 2) / (2 * p["sigma"] ** 2)) / (x * p["sigma"] * math.sqrt(2 * math.pi)) if x > 0 else 0,
        "formula": "f(x) = 1/(xσ√2π) · e^( −(ln x−μ)²/(2σ²) ),  x>0",
        "mean": "e^(μ+σ²/2)", "variance": "(e^(σ²)−1)e^(2μ+σ²)", "std": "√( (e^(σ²)−1)e^(2μ+σ²) )",
        "char_func": "无简单闭式",
        "mgf": "不存在",
        "applications": ["收入/财富分布", "股价建模", "保险理赔金额"],
    },
    "f": {
        "display_name": "F 分布",
        "is_discrete": False,
        "aliases": ["f分布", "F分布", "费舍尔", "fisher", "snedecor", "f-distribution"],
        "params": {
            "d1": {"default": 5.0, "min": 1.0, "max": 30.0, "step": 1.0, "label": "d₁"},
            "d2": {"default": 10.0, "min": 1.0, "max": 30.0, "step": 1.0, "label": "d₂"},
        },
        "morph_param": "d1",
        "domain_fn": _f_domain,
        "pdf_js": "function(x,p){ if(x<=0) return 0; var d1=p.d1,d2=p.d2; var c=_gamma((d1+d2)/2)/(_gamma(d1/2)*_gamma(d2/2)); var t=d1/d2; return c*Math.pow(t,d1/2)*Math.pow(x,d1/2-1)*Math.pow(1+t*x,-(d1+d2)/2); }",
        "pdf_py": lambda x, p: (math.gamma((p["d1"]+p["d2"])/2)/(math.gamma(p["d1"]/2)*math.gamma(p["d2"]/2))) * (p["d1"]/p["d2"])**(p["d1"]/2) * x**(p["d1"]/2-1) * (1+(p["d1"]/p["d2"])*x)**(-(p["d1"]+p["d2"])/2) if x > 0 else 0,
        "formula": "f(x) = [Γ((d₁+d₂)/2)/(Γ(d₁/2)Γ(d₂/2))]·(d₁/d₂)^(d₁/2)·x^(d₁/2−1)·(1+d₁x/d₂)^(−(d₁+d₂)/2),  x>0",
        "mean": "d₂/(d₂−2),  d₂>2", "variance": "2d₂²(d₁+d₂−2)/[d₁(d₂−2)²(d₂−4)],  d₂>4", "std": "—",
        "char_func": "无简单闭式",
        "mgf": "不存在",
        "applications": ["两独立卡方之比的方差分析", "回归方程整体显著性检验（F 检验）", "两正态总体方差比检验"],
        "construction": {"latex": r"F=\dfrac{U/d_1}{V/d_2},\quad U\sim\chi^2(d_1),\ V\sim\chi^2(d_2)\ \text{indep.}", "text": "F = (U/d₁)/(V/d₂)，U~χ²(d₁)、V~χ²(d₂) 相互独立"},
    },

    # ===================== 离散分布 =====================
    "bernoulli": {
        "display_name": "伯努利分布",
        "is_discrete": True,
        "aliases": ["bernoulli", "伯努利", "bernoulli("],
        "params": {
            "p": {"default": 0.5, "min": 0.01, "max": 0.99, "step": 0.01, "label": "p"},
        },
        "morph_param": "p",
        "domain_fn": lambda p: [0, 1],
        "pdf_js": "function(x,p){ if(x===0) return 1-p.p; if(x===1) return p.p; return 0; }",
        "pdf_py": lambda x, p: (1 - p["p"]) if x == 0 else (p["p"] if x == 1 else 0),
        "formula": "P(X=1)=p,  P(X=0)=1−p",
        "mean": "p", "variance": "p(1−p)", "std": "√(p(1−p))",
        "char_func": "φ(t) = 1−p + p e^(it)",
        "mgf": "M(t) = 1−p + p e^t",
        "applications": ["一次成败试验", "二项分布的基本单元", "点击/转化建模"],
    },
    "binomial": {
        "display_name": "二项分布",
        "is_discrete": True,
        "aliases": ["binomial", "二项", "二项分布", "binom", "binomial("],
        "params": {
            "n": {"default": 10.0, "min": 1.0, "max": 50.0, "step": 1.0, "label": "n"},
            "p": {"default": 0.5, "min": 0.01, "max": 0.99, "step": 0.01, "label": "p"},
        },
        "morph_param": "p",
        "domain_fn": lambda p: [0, int(p["n"])],
        "pdf_js": "function(x,p){ if(x<0||x>p.n) return 0; return _comb(p.n,x)*Math.pow(p.p,x)*Math.pow(1-p.p,p.n-x); }",
        "pdf_py": lambda x, p: math.comb(int(p["n"]), int(x)) * (p["p"] ** x) * ((1 - p["p"]) ** (p["n"] - x)) if 0 <= x <= p["n"] else 0,
        "formula": "P(X=k) = C(n,k) p^k (1−p)^(n−k),  k=0,1,…,n",
        "mean": "np", "variance": "np(1−p)", "std": "√(np(1−p))",
        "char_func": "φ(t) = (1−p + p e^(it))^n",
        "mgf": "M(t) = (1−p + p e^t)^n",
        "applications": ["n次独立成败试验成功次数", "质量控制合格率", "A/B 测试转化数"],
    },
    "poisson": {
        "display_name": "泊松分布",
        "is_discrete": True,
        "aliases": ["poisson", "泊松", "泊松分布", "poisson("],
        "params": {
            "lam": {"default": 3.0, "min": 0.2, "max": 15.0, "step": 0.1, "label": "λ"},
        },
        "morph_param": "lam",
        "domain_fn": lambda p: [0, int(p["lam"] + 4 * math.sqrt(p["lam"]) + 1)],
        "pdf_js": "function(x,p){ if(x<0) return 0; var l=p.lam; return Math.exp(-l)*Math.pow(l,x)/_gamma(x+1); }",
        "pdf_py": lambda x, p: math.exp(-p["lam"]) * (p["lam"] ** x) / math.factorial(int(x)) if x >= 0 else 0,
        "formula": "P(X=k) = λ^k e^(−λ) / k!,  k=0,1,2,…",
        "mean": "λ", "variance": "λ", "std": "√λ",
        "char_func": "φ(t) = exp(λ(e^(it)−1))",
        "mgf": "M(t) = exp(λ(e^t−1))",
        "applications": ["单位时间/区域内稀有事件发生数", "呼叫中心来话量", "放射性衰变计数"],
    },
    "geometric": {
        "display_name": "几何分布",
        "is_discrete": True,
        "aliases": ["geometric", "几何", "几何分布", "geometric("],
        "params": {
            "p": {"default": 0.3, "min": 0.01, "max": 0.99, "step": 0.01, "label": "p"},
        },
        "morph_param": "p",
        "domain_fn": lambda p: [1, int(1.0 / p["p"] + 4 * (1 - p["p"]) / p["p"] + 1)],
        "pdf_js": "function(x,p){ if(x<1) return 0; return Math.pow(1-p.p,x-1)*p.p; }",
        "pdf_py": lambda x, p: ((1 - p["p"]) ** (x - 1)) * p["p"] if x >= 1 else 0,
        "formula": "P(X=k) = (1−p)^(k−1) p,  k=1,2,3,…  (首次成功所需试验次数)",
        "mean": "1/p", "variance": "(1−p)/p²", "std": "√((1−p)/p²)",
        "char_func": "φ(t) = p e^(it) / (1 − (1−p)e^(it))",
        "mgf": "M(t) = p e^t / (1 − (1−p)e^t)",
        "applications": ["首次成功所需试验次数", "可靠性首次失效", "无记忆性（与指数分布对应）"],
    },
    "negative_binomial": {
        "display_name": "负二项分布",
        "is_discrete": True,
        "aliases": ["negative_binomial", "负二项", "负二项分布", "nb", "negative_binomial("],
        "params": {
            "r": {"default": 3.0, "min": 1.0, "max": 20.0, "step": 1.0, "label": "r"},
            "p": {"default": 0.4, "min": 0.01, "max": 0.99, "step": 0.01, "label": "p"},
        },
        "morph_param": "r",
        "domain_fn": lambda p: [0, int(p["r"] * (1 - p["p"]) / p["p"] + 4 * math.sqrt(p["r"] * (1 - p["p"])) / p["p"] + 1)],
        "pdf_js": "function(x,p){ if(x<0) return 0; return _comb(x+p.r-1,p.r-1)*Math.pow(p.p,p.r)*Math.pow(1-p.p,x); }",
        "pdf_py": lambda x, p: math.comb(int(x) + int(p["r"]) - 1, int(p["r"] - 1)) * (p["p"] ** p["r"]) * ((1 - p["p"]) ** x) if x >= 0 else 0,
        "formula": "P(X=k) = C(k+r−1, r−1) p^r (1−p)^k,  k=0,1,…  (第r次成功前的失败次数)",
        "mean": "r(1−p)/p", "variance": "r(1−p)/p²", "std": "√(r(1−p)/p²)",
        "char_func": "φ(t) = (p e^(it)/(1−(1−p)e^(it)))^r",
        "mgf": "M(t) = (p e^t/(1−(1−p)e^t))^r",
        "applications": ["第r次成功前的失败次数", " contagion/聚类事件建模", "过度离散计数（泊松的推广）"],
    },
}


# ---------------------------------------------------------------------------
# LaTeX 公式（供 HTML 内 KaTeX 渲染：概率密度/质量函数 + 分布函数 + 核心量）
# 仅在值为纯数学时使用；含中文（如「无简单闭式」「不存在」）的字段留空，
# 由渲染层回退为纯文本显示，避免 KaTeX 无法渲染中文而报错。
# ---------------------------------------------------------------------------
LATEX = {
    "normal": {
        "pdf": r"f(x)=\frac{1}{\sigma\sqrt{2\pi}}\,e^{-\frac{(x-\mu)^2}{2\sigma^2}}",
        "cdf": r"F(x)=\frac{1}{2}\left[1+\operatorname{erf}\!\left(\frac{x-\mu}{\sigma\sqrt{2}}\right)\right]",
        "mean": r"\mu",
        "variance": r"\sigma^2",
        "char_func": r"\varphi(t)=\exp\!\left(i\mu t-\frac{\sigma^2 t^2}{2}\right)",
        "mgf": r"M(t)=\exp\!\left(\mu t+\frac{\sigma^2 t^2}{2}\right),\quad t\in\mathbb{R}",
    },
    "uniform": {
        "pdf": r"f(x)=\frac{1}{b-a},\quad x\in[a,b]",
        "cdf": r"F(x)=\begin{cases}0,&x<a\\[2pt]\dfrac{x-a}{b-a},&a\le x\le b\\[2pt]1,&x>b\end{cases}",
        "mean": r"\dfrac{a+b}{2}",
        "variance": r"\dfrac{(b-a)^2}{12}",
        "char_func": r"\varphi(t)=\dfrac{e^{itb}-e^{ita}}{it(b-a)}",
        "mgf": r"M(t)=\dfrac{e^{tb}-e^{ta}}{t(b-a)}",
    },
    "exponential": {
        "pdf": r"f(x)=\lambda e^{-\lambda x},\quad x\ge 0",
        "cdf": r"F(x)=1-e^{-\lambda x},\quad x\ge 0",
        "mean": r"\dfrac{1}{\lambda}",
        "variance": r"\dfrac{1}{\lambda^2}",
        "char_func": r"\varphi(t)=\dfrac{\lambda}{\lambda-it}",
        "mgf": r"M(t)=\dfrac{\lambda}{\lambda-t},\quad t<\lambda",
    },
    "gamma": {
        "pdf": r"f(x)=\dfrac{\beta^\alpha x^{\alpha-1}e^{-\beta x}}{\Gamma(\alpha)},\quad x>0",
        "cdf": r"F(x)=\dfrac{\gamma(\alpha,\beta x)}{\Gamma(\alpha)}",
        "mean": r"\dfrac{\alpha}{\beta}",
        "variance": r"\dfrac{\alpha}{\beta^2}",
        "char_func": r"\varphi(t)=\left(\dfrac{\beta}{\beta-it}\right)^{\alpha}",
        "mgf": r"M(t)=\left(\dfrac{\beta}{\beta-t}\right)^{\alpha},\quad t<\beta",
    },
    "beta": {
        "pdf": r"f(x)=\dfrac{x^{\alpha-1}(1-x)^{\beta-1}}{\mathrm{B}(\alpha,\beta)},\quad x\in(0,1)",
        "cdf": r"F(x)=I_x(\alpha,\beta)=\dfrac{\mathrm{B}(x;\alpha,\beta)}{\mathrm{B}(\alpha,\beta)}",
        "mean": r"\dfrac{\alpha}{\alpha+\beta}",
        "variance": r"\dfrac{\alpha\beta}{(\alpha+\beta)^2(\alpha+\beta+1)}",
    },
    "chi_square": {
        "pdf": r"f(x)=\dfrac{x^{k/2-1}e^{-x/2}}{2^{k/2}\Gamma(k/2)},\quad x>0",
        "cdf": r"F(x)=\dfrac{\gamma(k/2,\,x/2)}{\Gamma(k/2)}",
        "mean": r"k",
        "variance": r"2k",
        "char_func": r"\varphi(t)=(1-2it)^{-k/2}",
        "mgf": r"M(t)=(1-2t)^{-k/2},\quad t<\frac{1}{2}",
    },
    "student_t": {
        "pdf": r"f(x)=\frac{\Gamma\!\big(\frac{\nu+1}{2}\big)}{\sqrt{\nu\pi}\,\Gamma\!\big(\frac{\nu}{2}\big)}\left(1+\frac{x^2}{\nu}\right)^{-\frac{\nu+1}{2}}",
        "cdf": r"F(x)=\begin{cases}\frac{1}{2} I_{\frac{\nu}{\nu+x^2}}\!\big(\frac{\nu}{2},\frac{1}{2}\big),&x\le 0\\[4pt]1-\frac{1}{2} I_{\frac{\nu}{\nu+x^2}}\!\big(\frac{\nu}{2},\frac{1}{2}\big),&x>0\end{cases}",
    },
    "weibull": {
        "pdf": r"f(x)=\frac{k}{\lambda}\left(\frac{x}{\lambda}\right)^{k-1}e^{-(x/\lambda)^k},\quad x\ge 0",
        "cdf": r"F(x)=1-e^{-(x/\lambda)^k},\quad x\ge 0",
        "mean": r"\lambda\,\Gamma\!\left(1+\frac{1}{k}\right)",
        "variance": r"\lambda^2\!\left[\Gamma\!\left(1+\frac{2}{k}\right)-\Gamma^2\!\left(1+\frac{1}{k}\right)\right]",
    },
    "laplace": {
        "pdf": r"f(x)=\frac{1}{2b}\,e^{-\frac{|x-\mu|}{b}}",
        "cdf": r"F(x)=\begin{cases}\frac{1}{2} e^{\frac{x-\mu}{b}},&x<\mu\\[4pt]1-\frac{1}{2} e^{-\frac{x-\mu}{b}},&x\ge\mu\end{cases}",
        "mean": r"\mu",
        "variance": r"2b^2",
        "char_func": r"\varphi(t)=\dfrac{e^{i\mu t}}{1+b^2 t^2}",
        "mgf": r"M(t)=\dfrac{e^{\mu t}}{1-b^2 t^2},\quad |t|<\frac{1}{b}",
    },
    "lognormal": {
        "pdf": r"f(x)=\frac{1}{x\sigma\sqrt{2\pi}}\,e^{-\frac{(\ln x-\mu)^2}{2\sigma^2}},\quad x>0",
        "cdf": r"F(x)=\frac{1}{2}+\frac{1}{2}\operatorname{erf}\!\left(\frac{\ln x-\mu}{\sigma\sqrt{2}}\right),\quad x>0",
        "mean": r"e^{\mu+\frac{\sigma^2}{2}}",
        "variance": r"(e^{\sigma^2}-1)\,e^{2\mu+\sigma^2}",
    },
    "bernoulli": {
        "pdf": r"P(X=x)=p^x(1-p)^{1-x},\quad x\in\{0,1\}",
        "cdf": r"F(k)=\begin{cases}0,&k<0\\[4pt]1-p,&0\le k<1\\[4pt]1,&k\ge 1\end{cases}",
        "mean": r"p",
        "variance": r"p(1-p)",
        "char_func": r"\varphi(t)=1-p+p e^{it}",
        "mgf": r"M(t)=1-p+p e^{t}",
    },
    "binomial": {
        "pdf": r"P(X=k)=\binom{n}{k}p^k(1-p)^{n-k},\quad k=0,1,\dots,n",
        "cdf": r"F(k)=\sum_{i=0}^{\lfloor k\rfloor}\binom{n}{i}p^i(1-p)^{n-i}",
        "mean": r"np",
        "variance": r"np(1-p)",
        "char_func": r"\varphi(t)=(1-p+p e^{it})^n",
        "mgf": r"M(t)=(1-p+p e^t)^n",
    },
    "poisson": {
        "pdf": r"P(X=k)=\dfrac{\lambda^k e^{-\lambda}}{k!},\quad k=0,1,2,\dots",
        "cdf": r"F(k)=\sum_{i=0}^{\lfloor k\rfloor}\dfrac{\lambda^i e^{-\lambda}}{i!}",
        "mean": r"\lambda",
        "variance": r"\lambda",
        "char_func": r"\varphi(t)=\exp\!\big(\lambda(e^{it}-1)\big)",
        "mgf": r"M(t)=\exp\!\big(\lambda(e^t-1)\big)",
    },
    "geometric": {
        "pdf": r"P(X=k)=(1-p)^{k-1}p,\quad k=1,2,3,\dots",
        "cdf": r"F(k)=1-(1-p)^k,\quad k=1,2,3,\dots",
        "mean": r"\dfrac{1}{p}",
        "variance": r"\dfrac{1-p}{p^2}",
        "char_func": r"\varphi(t)=\dfrac{p e^{it}}{1-(1-p)e^{it}}",
        "mgf": r"M(t)=\dfrac{p e^{t}}{1-(1-p)e^{t}}",
    },
    "negative_binomial": {
        "pdf": r"P(X=k)=\binom{k+r-1}{r-1}p^r(1-p)^k,\quad k=0,1,\dots",
        "cdf": r"F(k)=\sum_{i=0}^{\lfloor k\rfloor}\binom{i+r-1}{r-1}p^r(1-p)^i",
        "mean": r"\dfrac{r(1-p)}{p}",
        "variance": r"\dfrac{r(1-p)}{p^2}",
        "char_func": r"\varphi(t)=\left(\dfrac{p e^{it}}{1-(1-p)e^{it}}\right)^r",
        "mgf": r"M(t)=\left(\dfrac{p e^{t}}{1-(1-p)e^{t}}\right)^r",
    },
    "f": {
        "pdf": r"f(x)=\frac{\Gamma\!\big(\frac{d_1+d_2}{2}\big)}{\Gamma\!\big(\frac{d_1}{2}\big)\Gamma\!\big(\frac{d_2}{2}\big)}\left(\frac{d_1}{d_2}\right)^{\!d_1/2}x^{d_1/2-1}\left(1+\frac{d_1}{d_2}x\right)^{\!-(d_1+d_2)/2},\quad x>0",
        "cdf": r"F(x)=I_{\frac{d_1 x}{d_1 x+d_2}}\!\left(\frac{d_1}{2},\frac{d_2}{2}\right)",
        "mean": r"\dfrac{d_2}{d_2-2},\quad d_2>2",
        "variance": r"\dfrac{2d_2^2(d_1+d_2-2)}{d_1(d_2-2)^2(d_2-4)},\quad d_2>4",
    },
}


# ---------------------------------------------------------------------------
# 辅助接口
# ---------------------------------------------------------------------------
def get_entry(dist_type):
    """返回某分布的目录条目；不存在返回 None。"""
    return CATALOG.get(dist_type)


def default_params(dist_type):
    """返回某分布默认参数字典。"""
    e = CATALOG.get(dist_type)
    if not e:
        return {}
    return {name: spec["default"] for name, spec in e["params"].items()}


def compute_domain(dist_type, params):
    """按参数计算绘图定义域 [lo, hi]。"""
    e = CATALOG.get(dist_type)
    if not e:
        return [-5.0, 5.0]
    lo, hi = e["domain_fn"](params)
    return [float(lo), float(hi)]


def match_type(text):
    """根据输入文本匹配分布类型（返回 type 字符串或 None）。"""
    t = text.lower()
    best = None
    best_len = 0
    for dtype, e in CATALOG.items():
        for alias in e["aliases"]:
            al = alias.lower()
            if al in t:
                # 偏好更长的别名匹配（更精确）
                if len(al) > best_len:
                    best = dtype
                    best_len = len(al)
    return best


if __name__ == "__main__":
    # 自检：打印目录概况
    print("Catalog distributions:", len(CATALOG))
    for k, v in CATALOG.items():
        print(f"  - {k:18s} {v['display_name']:10s} discrete={v['is_discrete']}")
