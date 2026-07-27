"""知识库加载工具"""
import os

def load_knowledge_base() -> str:
    kb_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prob_knowledge.md")
    with open(kb_path, "r", encoding="utf-8") as f:
        return f.read()
