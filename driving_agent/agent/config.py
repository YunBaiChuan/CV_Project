import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # DeepSeek 配置
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "xxxxxxxxxxxxxxxxxxxxxxx")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat")
    
    MAX_HISTORY = 50
