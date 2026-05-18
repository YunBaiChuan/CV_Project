"""测试api能否使用"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("DEEPSEEK_API_KEY")
print(f"API Key: {api_key[:10]}...")  # 只显示前10位确认

# 测试 DeepSeek API
url = "https://api.deepseek.com/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

data = {
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "你好"}],
    "max_tokens": 100
}

try:
    print("正在连接 DeepSeek API...")
    response = requests.post(url, headers=headers, json=data, timeout=10)
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        print("✅ API 连接成功！")
        print(f"响应: {response.json()['choices'][0]['message']['content']}")
    else:
        print(f"❌ API 错误: {response.text}")
except requests.exceptions.Timeout:
    print("❌ 连接超时 - 无法访问 DeepSeek API")
except Exception as e:
    print(f"❌ 错误: {e}")