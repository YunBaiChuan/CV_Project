from typing import Optional, Dict, List, Any
import requests
import json
import time
import os
from .memory import ConversationMemory
from .config import Config
from .functions import track_vehicle

class DrivingAgent:
    """驾驶监控Agent - 支持DeepSeek API + Function Calling"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Config.DEEPSEEK_API_KEY
        if not self.api_key:
            raise ValueError("请设置DEEPSEEK_API_KEY")
        
        self.base_url = Config.DEEPSEEK_BASE_URL
        self.model = Config.MODEL_NAME
        self.memory = ConversationMemory(max_history=Config.MAX_HISTORY)
        
        self.functions = {}
        self.request_timeout = 180
        
        self.system_prompt = """你是一个专业的车辆驾驶监控助手。你可以通过调用以下工具来帮助用户：

## 可用工具：
1. **track_vehicle** - 分析视频文件，追踪所有车辆的行驶轨迹

## 重要规则：
- 当用户要求分析视频时，你必须调用 track_vehicle 函数
- 不要直接回答，必须通过函数调用获取结果

## 示例：
用户: "分析 test_video.mp4"
你: 调用 track_vehicle(video_path="test_video.mp4")
"""
        
        self._register_functions()
        
        print(f"[Agent] 初始化完成，使用模型: {self.model}")
        print(f"[Agent] 已注册 {len(self.functions)} 个函数: {list(self.functions.keys())}")
    
    def _register_functions(self):
        self.register_function(
            name="track_vehicle",
            func=track_vehicle,
            description="分析视频文件，追踪所有车辆的轨迹。传入视频文件路径，返回车辆数量和轨迹数据。",
            parameters={
                "type": "object",
                "properties": {
                    "video_path": {
                        "type": "string",
                        "description": "视频文件的完整路径"
                    }
                },
                "required": ["video_path"]
            }
        )
    
    def register_function(self, name: str, func: callable, description: str, parameters: dict):
        self.functions[name] = {
            "function": func,
            "description": description,
            "parameters": parameters
        }
        print(f"[Agent] 注册函数: {name}")
    
    def _build_messages(self, user_input: str) -> List[Dict]:
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self.memory.get_context())
        messages.append({"role": "user", "content": user_input})
        return messages
    
    def _execute_function_call(self, function_name: str, arguments: dict) -> Dict:
        if function_name not in self.functions:
            return {"status": "error", "message": f"未找到函数 {function_name}"}
        
        try:
            func = self.functions[function_name]["function"]
            print(f"[Agent] 开始执行函数 {function_name}...")
            result = func(**arguments)
            
            if isinstance(result, dict):
                return result
            return {"status": "success", "data": str(result)}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}
    
    def chat(self, user_input: str) -> str:
        print(f"[Agent] 收到用户消息: {user_input[:50]}...")
        
        self.memory.add("user", user_input)
        messages = self._build_messages(user_input)
        
        # 准备 tools 列表
        tools = []
        for name, info in self.functions.items():
            tools.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": info["description"],
                    "parameters": info["parameters"]
                }
            })
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000,
            "stream": False
        }
        
        if tools:
            data["tools"] = tools
            data["tool_choice"] = "auto"
        
        try:
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=self.request_timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                message = result['choices'][0]['message']
                
                # 检查是否有 tool_calls
                if 'tool_calls' in message and message['tool_calls']:
                    print(f"[Agent] 检测到函数调用")
                    
                    for tool_call in message['tool_calls']:
                        function_name = tool_call['function']['name']
                        arguments = json.loads(tool_call['function']['arguments'])
                        
                        print(f"[Agent] 调用函数: {function_name}({arguments})")
                        
                        # 执行函数并直接返回结果
                        function_result = self._execute_function_call(function_name, arguments)
                        
                        # 格式化返回结果
                        return self._format_function_result(function_result)
                else:
                    assistant_message = message.get('content', '')
                    if assistant_message:
                        self.memory.add("assistant", assistant_message)
                        return assistant_message
                    else:
                        return "模型没有返回内容，请重试。"
            else:
                print(f"[Agent] API错误: {response.status_code} - {response.text[:200]}")
                return f"抱歉，请求出错: {response.status_code}"
                
        except requests.exceptions.Timeout:
            return "抱歉，请求超时，请稍后重试。"
        except Exception as e:
            print(f"[Agent] 请求失败: {str(e)}")
            return f"抱歉，{str(e)}"
    
    def _format_function_result(self, result: Dict) -> str:
        """格式化函数执行结果"""
        if result.get("status") == "success":
            data = result.get("data", {})
            vehicles = data.get("vehicles", [])
            vehicles_count = data.get("vehicles_count", 0)
            duration = data.get("duration", 0)
            
            summary = f"✅ 追踪完成！\n\n"
            summary += f"📊 统计信息：\n"
            summary += f"   - 视频时长：{duration:.1f} 秒\n"
            summary += f"   - 检测到车辆：{vehicles_count} 辆\n\n"
            
            if vehicles:
                summary += f"📝 车辆详情：\n"
                for v in vehicles[:10]:
                    summary += f"   - {v['vehicle_id']}: {v['trajectory_length']} 个轨迹点, 平均速度 {v['avg_speed']:.1f}\n"
            
            if len(vehicles) > 10:
                summary += f"   ... 还有 {len(vehicles) - 10} 辆车\n"
            
            self.memory.add("assistant", summary)
            return summary
        else:
            error_msg = f"❌ 追踪失败: {result.get('message', '未知错误')}"
            self.memory.add("assistant", error_msg)
            return error_msg
    
    def clear_memory(self):
        self.memory.clear()
    
    def get_memory_info(self) -> Dict:
        return {
            "total_messages": len(self.memory),
            "recent_summary": self.memory.get_summary()
        }