import requests
import time

BASE_URL = "http://127.0.0.1:8000"

def test():
    print("开始测试...")
    start = time.time()
    
    response = requests.post(
        f"{BASE_URL}/chat",
        json={"message": "分析 test_video.mp4 中的车辆"},
        timeout=300
    )
    
    elapsed = time.time() - start
    print(f"耗时: {elapsed:.1f}秒")
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n回复:\n{data['response']}")
    else:
        print(f"错误: {response.text}")

if __name__ == "__main__":
    test()