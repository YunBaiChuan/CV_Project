from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass, field

@dataclass
class Message:
    """单条消息"""
    role: str  # user, assistant, system
    content: str
    timestamp: datetime = field(default_factory=datetime.now)

class ConversationMemory:
    """对话记忆管理"""
    
    def __init__(self, max_history: int = 50):
        self.messages: List[Message] = []
        self.max_history = max_history
    
    def add(self, role: str, content: str):
        """添加消息"""
        self.messages.append(Message(role=role, content=content))
        # 保持不超过最大限制
        if len(self.messages) > self.max_history:
            self.messages.pop(0)
        print(f"[Memory] 添加 {role} 消息，当前共 {len(self.messages)} 条")
    
    def get_context(self, n: Optional[int] = None) -> List[Dict]:
        """获取上下文（用于API调用）"""
        messages = self.messages
        if n:
            messages = messages[-n:]
        return [{"role": m.role, "content": m.content} for m in messages]
    
    def clear(self):
        """清空记忆"""
        self.messages.clear()
        print("[Memory] 记忆已清空")
    
    def get_summary(self) -> str:
        """获取记忆摘要"""
        if not self.messages:
            return "暂无对话历史"
        recent = self.messages[-3:]
        summary = "\n".join([f"{m.role}: {m.content[:50]}..." for m in recent])
        return f"最近3条对话:\n{summary}"
    
    def __len__(self):
        return len(self.messages)