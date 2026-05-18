"""测试Agent基本功能"""
import requests
import json

# API地址
BASE_URL = "http://localhost:8000"

def test_chat():
    """测试对话功能"""
    print("=" * 50)
    print("测试Agent对话功能")
    print("=" * 50)
    
    # 测试对话
    conversations = [
        "你好，能介绍一下你自己吗？",
        "我有一辆车在高速上行驶，需要注意什么？",
        "刚才我急刹车了一下，这危险吗？"
    ]
    
    for msg in conversations:
        print(f"\n用户: {msg}")
        response = requests.post(
            f"{BASE_URL}/chat",
            json={"message": msg}
        )
        if response.status_code == 200:
            data = response.json()
            print(f"Agent: {data['response']}")
            print(f"记忆信息: {data['memory_info']['total_messages']}条对话")
        else:
            print(f"错误: {response.status_code}")
    
    # 查看记忆信息
    print("\n" + "=" * 50)
    response = requests.get(f"{BASE_URL}/memory_info")
    if response.status_code == 200:
        print("当前记忆状态:")
        print(response.json()['recent_summary'])

def test_clear_memory():
    """测试清空记忆"""
    print("\n" + "=" * 50)
    print("测试清空记忆")
    print("=" * 50)
    
    response = requests.post(f"{BASE_URL}/clear_memory")
    if response.status_code == 200:
        print("✓ 记忆已清空")
        
        # 验证
        info = requests.get(f"{BASE_URL}/memory_info").json()
        print(f"当前对话数: {info['total_messages']}")

if __name__ == "__main__":
    # 先检查服务是否运行
    try:
        requests.get(f"{BASE_URL}/health")
    except:
        print("错误: Agent服务未启动")
        print("请先运行: cd api && python server.py")
        exit(1)
    
    # 运行测试
    test_chat()
    test_clear_memory()