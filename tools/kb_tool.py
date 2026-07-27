"""知识库查询工具

[Extension] 大产品升级为 Qdrant 向量检索时保持此函数签名不变：
def search_knowledge_base(user_input: str) -> str:
    # 替换实现为：embedding -> Qdrant cosine search -> 拼接 top-k
"""

import os
import re


def search_knowledge_base(user_input: str) -> str:
    """按关键词匹配知识库，返回相关知识点（Markdown 格式）"""
    kb_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "knowledge_base", "prob_knowledge.md",
    )
    if not os.path.exists(kb_path):
        return "[知识库文件未找到]"
    with open(kb_path, "r", encoding="utf-8") as f:
        content = f.read()
    keywords = _extract_keywords(user_input)
    sections = re.split(r"\n## ", content)
    matched = []
    for sec in sections:
        score = sum(1 for kw in keywords if kw.lower() in sec.lower())
        if score > 0:
            matched.append((score, "## " + sec))
    matched.sort(key=lambda x: -x[0])
    if not matched:
        return "知识库未找到相关内容。"
    return "\n\n".join(sec for _, sec in matched[:3])


def _extract_keywords(text: str) -> list:
    """提取搜索关键词

    [Extension] 大产品中替换为：LLM 提取 + 同义词扩展
    """
    dist_names = [
        "正态", "均匀", "指数", "伽马", "贝塔", "卡方", "t分布",
        "F分布", "韦布尔", "拉普拉斯", "对数正态", "伯努利",
        "二项", "泊松", "几何", "负二项",
        "normal", "poisson", "binomial", "exponential", "uniform",
    ]
    concepts = [
        "期望", "方差", "均值", "分布函数", "密度", "特征函数",
        "矩母", "大数定律", "中心极限", "参数估计", "假设检验",
        "置信区间", "协方差", "相关系数", "贝叶斯",
    ]
    keywords = []
    text_lower = text.lower()
    for d in dist_names:
        if d.lower() in text_lower:
            keywords.append(d)
    for c in concepts:
        if c in text:
            keywords.append(c)
    return keywords if keywords else [text[:20]]
