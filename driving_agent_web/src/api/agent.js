import axios from 'axios'

// Agent 后端地址
const AGENT_API = 'http://127.0.0.1:8000'

// 创建 axios 实例
const agentAxios = axios.create({
  baseURL: AGENT_API,
  timeout: 300000, // 5分钟超时
  headers: {
    'Content-Type': 'application/json'
  }
})

// Agent 对话（发送文本消息）
export async function chat(message) {
  try {
    const response = await agentAxios.post('/chat', { message })
    return {
      success: true,
      data: response.data
    }
  } catch (error) {
    console.error('Agent 请求失败:', error)
    return {
      success: false,
      error: error.message,
      response: '抱歉，服务暂时不可用，请确保后端服务已启动（python api/server.py）'
    }
  }
}

// 清空记忆
export async function clearMemory() {
  try {
    const response = await agentAxios.post('/clear_memory')
    return response.data
  } catch (error) {
    return { status: 'error' }
  }
}

// 健康检查
export async function healthCheck() {
  try {
    const response = await agentAxios.get('/health')
    return response.data
  } catch (error) {
    return { status: 'unhealthy' }
  }
}