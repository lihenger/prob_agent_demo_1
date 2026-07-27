"""项目配置：支持从环境变量或 .env 文件读取"""
import os
from dotenv import load_dotenv

# 自动加载 .env 文件（如果存在）
load_dotenv()

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")  # Flash 模型（默认）

# [Extension] 大产品配置项预占位
# QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
# QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
# POSTGRES_DSN = os.getenv("POSTGRES_DSN", "")
# REDIS_URL = os.getenv("REDIS_URL", "")
# JWT_SECRET = os.getenv("JWT_SECRET", "")
