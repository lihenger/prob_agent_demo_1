"""数据库查询工具 — PostgreSQL 占位实现

[Extension] 大产品升级为真实 SQLAlchemy 查询：
- 替换实现为：session.query(UserProgress).filter(...) -> dict
- 保持 db_read(analytics_type: str) -> str 签名不变
- 新增 db_write(data_type: str, data: dict) -> None
"""


def db_read(analytics_type: str) -> str:
    """模拟数据库查询，返回占位数据
    Args:
        analytics_type: 分析类型 ("progress" / "history" / "bookmark")
    Returns:
        模拟查询结果的提示
    """
    mock_data = {
        "progress": (
            "【模拟数据 - 学习进度】\n"
            "- 正态分布：已完成（掌握度 85%）\n"
            "- 二项分布：已完成（掌握度 72%）\n"
            "- 泊松分布：学习中（掌握度 45%）\n"
            "- 假设检验：未开始\n"
            "- 总进度：3/9 章节\n"
        ),
        "history": (
            "【模拟数据 - 历史记录】\n"
            "- 2026-01-15: 正态分布的定义和性质\n"
            "- 2026-01-16: 正态分布的参数估计\n"
            "- 2026-01-18: 二项分布与泊松分布的关系\n"
            "- 2026-01-20: 中心极限定理的应用\n"
        ),
        "bookmark": (
            "【模拟数据 - 断点信息】\n"
            "- 上次学习时间：2024-01-20 14:30\n"
            "- 上次学习内容：中心极限定理\n"
            "- 上次停留位置：第 5 章第 3 节\n"
            "- 建议从此处继续学习\n"
        ),
    }
    return mock_data.get(
        analytics_type,
        f"【模拟数据】未知分析类型：{analytics_type}\n当前为模拟数据库模式。\n",
    )
