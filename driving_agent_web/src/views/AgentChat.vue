<template>
  <div class="agent-chat-container">
    <!-- 左右分栏布局 -->
    <div class="split-layout">
      
      <!-- 左侧：视频追踪区域 -->
      <div class="video-panel">
        <div class="panel-header">
          <h3>🚗 智能辅助驾驶</h3>
          <div class="video-controls">
            <el-button size="small" type="primary" @click="selectVideo" :disabled="isTracking">
              <el-icon><VideoCamera /></el-icon> 选择视频
            </el-button>
            <el-button 
              size="small" 
              type="success" 
              @click="startTracking" 
              :disabled="!selectedFile || isTracking"
              :loading="isTracking"
            >
              {{ isTracking ? '追踪中...' : '开始追踪' }}
            </el-button>
            <el-button 
              size="small" 
              type="danger" 
              @click="stopTracking" 
              :disabled="!isTracking"
            >
              停止
            </el-button>
          </div>
        </div>

        <!-- 视频画面 -->
        <div class="video-container">
          <canvas ref="canvasRef" style="width: 100%; height: 100%; background: #f5f5f5;"></canvas>
          <div v-if="!isTracking && !hasVideoSelected" class="video-placeholder">
            <el-icon><VideoCamera /></el-icon>
            <p>请选择视频文件</p>
          </div>
          <div v-if="isTracking && !hasFrame" class="tracking-status">
            <el-icon class="is-loading"><Loading /></el-icon>
            <p>正在启动追踪...</p>
          </div>
        </div>

        <!-- 追踪进度条 -->
        <div class="tracking-stats">
          <div class="stat-item">
            <span class="stat-label">分析进度</span>
            <el-progress :percentage="progress" :stroke-width="8" />
          </div>
          <div class="stat-item">
            <span class="stat-label">状态</span>
            <el-tag :type="isTracking ? 'warning' : 'info'" size="small">
              {{ isTracking ? '实时监控中' : '待机' }}
            </el-tag>
          </div>
        </div>
      </div>

      <!-- 右侧：Agent 区域（预警 + 对话） -->
      <div class="chat-panel">
        <div class="panel-header">
          <div class="header-tabs">
            <span 
              :class="['tab', { active: activeTab === 'alert' }]" 
              @click="activeTab = 'alert'"
            >
              ⚠️ 实时预警
            </span>
            <span 
              :class="['tab', { active: activeTab === 'chat' }]" 
              @click="activeTab = 'chat'"
            >
              💬 智能对话
            </span>
          </div>
          <span :class="['status-badge', backendStatus ? 'online' : 'offline']">
            {{ backendStatus ? '● 在线' : '● 离线' }}
          </span>
        </div>

        <!-- 预警列表 -->
        <div v-show="activeTab === 'alert'" class="alert-list" ref="alertContainer">
          <div v-if="alerts.length === 0 && !isTracking" class="empty-state">
            <el-icon><Bell /></el-icon>
            <p>暂无预警信息</p>
            <p class="hint">选择视频并开始追踪后，预警会显示在这里</p>
          </div>
          <div v-if="isTracking && alerts.length === 0 && !hasFrame" class="empty-state">
            <el-icon class="is-loading"><Loading /></el-icon>
            <p>正在分析视频流...</p>
          </div>
          <div
            v-for="(alert, index) in alerts"
            :key="index"
            :class="['alert-item', alert.severity]"
          >
            <div class="alert-icon">
              <span v-if="alert.severity === 'danger'">🚨</span>
              <span v-else-if="alert.severity === 'warning'">⚠️</span>
              <span v-else>💡</span>
            </div>
            <div class="alert-content">
              <div class="alert-message">{{ alert.message }}</div>
              <div class="alert-time">{{ alert.time }}</div>
            </div>
          </div>
        </div>

        <!-- 对话区域 -->
        <div v-show="activeTab === 'chat'" class="messages-list" ref="messagesContainer">
          <div
            v-for="(msg, index) in messages"
            :key="index"
            :class="['message-item', msg.role]"
          >
            <div class="message-avatar">
              {{ msg.role === 'user' ? '👤' : '🤖' }}
            </div>
            <div class="message-bubble">
              <div class="message-content" v-html="renderMarkdown(msg.content)"></div>
              <div class="message-time">{{ msg.time || formatTime(msg.timestamp) }}</div>
            </div>
          </div>
          
          <!-- 加载状态 -->
          <div v-if="loading" class="message-item agent">
            <div class="message-avatar">🤖</div>
            <div class="message-bubble loading-bubble">
              <div class="loading-dots">
                <span></span><span></span><span></span>
              </div>
              <div class="loading-text">{{ loadingText }}</div>
            </div>
          </div>
        </div>

        <!-- 输入区域 -->
        <div class="input-area">
          <el-input
            v-model="textMessage"
            type="textarea"
            :rows="2"
            :placeholder="activeTab === 'chat' ? '输入问题... (Enter 发送)' : '切换到「智能对话」与我交流'"
            @keydown.enter.prevent="activeTab === 'chat' && sendTextMessage()"
            :disabled="loading || activeTab !== 'chat'"
          />
          <el-button 
            type="primary" 
            @click="sendTextMessage" 
            :loading="loading"
            :disabled="activeTab !== 'chat'"
          >
            发送
          </el-button>
        </div>
      </div>
      
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoCamera, Loading, Bell } from '@element-plus/icons-vue'
import axios from 'axios'
import { marked } from 'marked'

const WS_URL = 'ws://127.0.0.1:8000/ws/track2'
const API_BASE = 'http://127.0.0.1:8000'

// 配置 marked
marked.setOptions({
  breaks: true,
  gfm: true
})

// 渲染 Markdown
function renderMarkdown(content: string): string {
  return marked.parse(content, { async: false }) as string
}

// Tab 切换
const activeTab = ref<'alert' | 'chat'>('alert')

// 视频相关
const selectedFile = ref<File | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const isTracking = ref<boolean>(false)
const hasFrame = ref<boolean>(false)
const hasVideoSelected = ref<boolean>(false)
const progress = ref<number>(0)
let ws: WebSocket | null = null
let previewVideo: HTMLVideoElement | null = null
let animationId: number | null = null

// 帧缓冲优化变量
let frameBuffer: string | null = null
let isProcessing = false
let lastFrameTime = 0
const FRAME_INTERVAL = 100  // 限制 10 fps

// 预警相关
const backendStatus = ref(false)
const alerts = ref<{message: string, time: string, severity: 'danger' | 'warning' | 'info'}[]>([])
const alertContainer = ref<HTMLElement | null>(null)

// 对话相关
const textMessage = ref('')
const loading = ref(false)
const loadingText = ref('正在思考...')
const messages = ref<{role: 'user' | 'agent', content: string, timestamp: Date, time?: string}[]>([
  { 
    role: 'agent', 
    content: '你好！我是智能驾驶监控助手 🚗\n\n我可以：\n- 实时分析视频中的车辆行为\n- 检测超速、碰撞风险并预警\n- 回答驾驶相关问题\n\n点击「选择视频」开始监控，或直接向我提问。',
    timestamp: new Date(),
    time: formatTime(new Date())
  }
])
const messagesContainer = ref<HTMLElement | null>(null)

// 格式化时间
function formatTime(date: Date): string {
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  const seconds = date.getSeconds().toString().padStart(2, '0')
  return `${hours}:${minutes}:${seconds}`
}

// 添加预警消息
function addAlert(message: string, severity: 'danger' | 'warning' | 'info' = 'warning') {
  const now = new Date()
  alerts.value.unshift({
    message,
    time: formatTime(now),
    severity
  })
  if (alerts.value.length > 50) {
    alerts.value.pop()
  }
}

// 添加对话消息
function addMessage(role: 'user' | 'agent', content: string) {
  const now = new Date()
  messages.value.push({
    role,
    content,
    timestamp: now,
    time: formatTime(now)
  })
  scrollToBottom()
}

// 滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// 帧缓冲渲染函数
function processFrameBuffer() {
  if (isProcessing || !frameBuffer) return
  
  const now = Date.now()
  if (now - lastFrameTime < FRAME_INTERVAL) {
    setTimeout(() => processFrameBuffer(), FRAME_INTERVAL - (now - lastFrameTime))
    return
  }
  
  isProcessing = true
  lastFrameTime = now
  
  requestAnimationFrame(() => {
    if (canvasRef.value && frameBuffer) {
      const img = new Image()
      img.onload = () => {
        const ctx = canvasRef.value?.getContext('2d')
        if (ctx && canvasRef.value) {
          canvasRef.value.width = img.width
          canvasRef.value.height = img.height
          ctx.drawImage(img, 0, 0)
        }
        isProcessing = false
        if (frameBuffer) processFrameBuffer()
      }
      img.src = `data:image/jpeg;base64,${frameBuffer}`
      frameBuffer = null
    } else {
      isProcessing = false
    }
  })
}

// 选择视频并预览
const selectVideo = () => {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'video/mp4,video/avi,video/mov,video/mkv'
  input.onchange = (e: Event) => {
    const target = e.target as HTMLInputElement
    const file = target.files?.[0]
    if (file) {
      selectedFile.value = file
      hasVideoSelected.value = true
      
      const url = URL.createObjectURL(file)
      if (!previewVideo) {
        previewVideo = document.createElement('video')
        previewVideo.autoplay = true
        previewVideo.muted = true
        previewVideo.loop = false
        previewVideo.playsInline = true
      }
      previewVideo.src = url
      previewVideo.onloadeddata = () => {
        previewVideo?.play()
        drawPreviewToCanvas()
      }
      
      ElMessage.success(`已选择：${file.name}`)
    }
  }
  input.click()
}

// 预览视频绘制到 canvas
const drawPreviewToCanvas = () => {
  if (!previewVideo || !canvasRef.value) return
  
  const ctx = canvasRef.value.getContext('2d')
  if (!ctx) return
  
  const draw = () => {
    if (previewVideo && canvasRef.value && !isTracking.value) {
      const canvas = canvasRef.value
      if (previewVideo.videoWidth && previewVideo.videoHeight) {
        canvas.width = previewVideo.videoWidth
        canvas.height = previewVideo.videoHeight
      }
      ctx.drawImage(previewVideo, 0, 0, canvas.width, canvas.height)
      animationId = requestAnimationFrame(draw)
    }
  }
  draw()
}

const stopPreviewDraw = () => {
  if (animationId) {
    cancelAnimationFrame(animationId)
    animationId = null
  }
}

// 开始追踪
const startTracking = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择视频')
    return
  }
  
  // 获取当前播放时间
  const currentPlayTime = previewVideo ? previewVideo.currentTime : 0
  console.log(`从 ${currentPlayTime.toFixed(1)} 秒开始追踪`)
  
  stopPreviewDraw()
  if (previewVideo) {
    previewVideo.pause()
  }
  
  isTracking.value = true
  hasFrame.value = false
  progress.value = 0
  alerts.value = []
  
  const formData = new FormData()
  formData.append('video', selectedFile.value)
  
  try {
    const uploadRes = await axios.post(`${API_BASE}/track/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000
    })
    
    if (uploadRes.data.status === 'success') {
      const taskId = uploadRes.data.task_id
      const videoFileName = selectedFile.value.name
      const userId = localStorage.getItem('userId')
      
      ws = new WebSocket(WS_URL)
      
      if (ws) {
        ws.onopen = () => {
          console.log('WebSocket 已连接')
          if (ws) {
            ws.send(JSON.stringify({ 
              task_id: taskId, 
              start_time: currentPlayTime,
              user_id: userId ? parseInt(userId) : null,
              video_path: videoFileName
            }))
          }
        }
        
        ws.onmessage = (event) => {
          const data = JSON.parse(event.data)
          
          switch (data.type) {
            case 'start':
              addAlert(`开始视频分析，从 ${data.start_time?.toFixed(1) || 0} 秒开始监控`, 'info')
              break
              
            case 'frame':
              frameBuffer = data.image
              processFrameBuffer()
              progress.value = data.progress
              hasFrame.value = true
              break
              
            case 'warning':
              let severity: 'danger' | 'warning' | 'info' = 'warning'
              if (data.message.includes('严重') || data.message.includes('碰撞')) {
                severity = 'danger'
              } else if (data.message.includes('注意')) {
                severity = 'warning'
              } else {
                severity = 'info'
              }
              addAlert(data.message, severity)
              break
              
            case 'agent_warning':
              addAlert(data.message, data.severity === 'danger' ? 'danger' : 'warning')
              break
              
            case 'complete':
              addAlert(`✅ 分析完成！共监控到 ${data.vehicles} 辆次车辆`, 'info')
              isTracking.value = false
              if (ws) ws.close()
              break
              
            case 'stopped':
              addAlert(`⏹️ 追踪已停止`, 'info')
              isTracking.value = false
              if (ws) ws.close()
              break
              
            case 'error':
              addAlert(`❌ 分析出错：${data.message}`, 'danger')
              isTracking.value = false
              if (ws) ws.close()
              break
          }
        }
        
        ws.onerror = () => {
          ElMessage.error('WebSocket 连接失败')
          isTracking.value = false
        }
        
        ws.onclose = () => {
          console.log('WebSocket 已断开')
          if (isTracking.value) {
            addAlert('⚠️ 连接已断开', 'warning')
            isTracking.value = false
          }
        }
      }
    } else {
      throw new Error(uploadRes.data.message || '上传失败')
    }
  } catch (error: any) {
    console.error('追踪失败:', error)
    addAlert(`追踪失败：${error.message}`, 'danger')
    isTracking.value = false
  }
}

// 停止追踪 - 发送停止信号给后端
const stopTracking = () => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send('stop')
    addAlert('正在停止追踪...', 'info')
  } else {
    isTracking.value = false
    ElMessage.info('已停止追踪')
  }
}

// 发送文本消息
const sendTextMessage = async () => {
  const message = textMessage.value.trim()
  if (!message) return
  
  addMessage('user', message)
  textMessage.value = ''
  
  // 创建一个临时消息用于流式显示
  const tempMsgIndex = messages.value.length
  messages.value.push({
    role: 'agent',
    content: '',
    timestamp: new Date(),
    time: formatTime(new Date())
  })
  scrollToBottom()
  
  // 创建流式对话 WebSocket
  const chatWs = new WebSocket('ws://127.0.0.1:8000/ws/chat')
  
  chatWs.onopen = () => {
    chatWs.send(JSON.stringify({ message }))
  }
  
  chatWs.onmessage = (event) => {
    const data = JSON.parse(event.data)
    
    if (data.type === 'chunk') {
      // 逐字追加到消息
      messages.value[tempMsgIndex].content += data.content
      scrollToBottom()
    } else if (data.type === 'end') {
      // 完整内容已接收，关闭连接
      chatWs.close()
    }
  }
  
  chatWs.onerror = () => {
    messages.value[tempMsgIndex].content = '❌ 连接失败，请稍后重试'
    chatWs.close()
  }
}

// 检查后端状态
const checkBackend = async () => {
  try {
    const response = await axios.get(`${API_BASE}/health`, { timeout: 5000 })
    backendStatus.value = response.data.status === 'healthy'
  } catch (error) {
    backendStatus.value = false
  }
}

onMounted(() => {
  checkBackend()
  setInterval(checkBackend, 30000)
})

onUnmounted(() => {
  if (ws) {
    if (ws.readyState === WebSocket.OPEN) {
      ws.close()
    }
    ws = null
  }
  if (previewVideo) {
    previewVideo.pause()
    previewVideo.src = ''
  }
  stopPreviewDraw()
})
</script>

<style scoped>
.agent-chat-container {
  height: 100vh;
  background: #f0f2f5;
}

.split-layout {
  display: flex;
  height: 100%;
  gap: 16px;
  padding: 20px;
}

/* 左侧视频面板 */
.video-panel {
  flex: 1;
  background: white;
  border-radius: 16px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
}

.panel-header {
  padding: 16px 20px;
  background: #fafafa;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-tabs {
  display: flex;
  gap: 20px;
}

.tab {
  font-size: 15px;
  color: #666;
  cursor: pointer;
  padding: 4px 0;
  transition: all 0.2s;
}

.tab:hover {
  color: #409eff;
}

.tab.active {
  color: #409eff;
  border-bottom: 2px solid #409eff;
}

.video-controls {
  display: flex;
  gap: 10px;
}

.video-container {
  flex: 1;
  background: #f5f5f5;
  position: relative;
  min-height: 400px;
}

.video-container canvas {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.video-placeholder,
.tracking-status {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #999;
  gap: 16px;
  background: #fafafa;
}

.tracking-status .el-icon {
  font-size: 48px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.tracking-stats {
  display: flex;
  gap: 20px;
  padding: 12px 20px;
  background: #fafafa;
  border-top: 1px solid #e8e8e8;
}

.stat-item {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
}

.stat-label {
  color: #666;
  font-size: 12px;
  min-width: 60px;
}

/* 右侧面板 */
.chat-panel {
  width: 400px;
  background: white;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
}

.status-badge {
  font-size: 12px;
  padding: 4px 12px;
  border-radius: 20px;
}

.status-badge.online {
  color: #67c23a;
  background: rgba(103,194,58,0.1);
}

.status-badge.offline {
  color: #f56c6c;
  background: rgba(245,108,108,0.1);
}

/* 预警列表 */
.alert-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: #fafafa;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #999;
  gap: 12px;
  text-align: center;
}

.empty-state .el-icon {
  font-size: 48px;
}

.empty-state .hint {
  font-size: 12px;
  color: #bbb;
}

.alert-item {
  display: flex;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 12px;
  background: white;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.alert-item.danger {
  border-left: 4px solid #f56c6c;
  background: #fef0f0;
}

.alert-item.warning {
  border-left: 4px solid #e6a23c;
  background: #fdf6ec;
}

.alert-item.info {
  border-left: 4px solid #409eff;
  background: #ecf5f9;
}

.alert-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.alert-content {
  flex: 1;
}

.alert-message {
  font-size: 13px;
  line-height: 1.5;
  color: #333;
}

.alert-time {
  font-size: 10px;
  color: #999;
  margin-top: 4px;
}

/* 对话区域 */
.messages-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: #fafafa;
}

.message-item {
  display: flex;
  gap: 10px;
}

.message-item.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #e8e8e8;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}

.message-item.user .message-avatar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.message-bubble {
  max-width: 70%;
  background: white;
  border-radius: 12px;
  padding: 10px 14px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.message-item.user .message-bubble {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.message-content {
  font-size: 13px;
  line-height: 1.5;
  color: #333;
  white-space: pre-wrap;
  word-wrap: break-word;
}

/* Markdown 内容样式 */
.message-content h1,
.message-content h2,
.message-content h3 {
  margin: 8px 0;
  font-weight: 600;
}

.message-content h1 { font-size: 18px; }
.message-content h2 { font-size: 16px; }
.message-content h3 { font-size: 14px; }

.message-content p {
  margin: 6px 0;
}

.message-content ul,
.message-content ol {
  margin: 6px 0;
  padding-left: 20px;
}

.message-content li {
  margin: 2px 0;
}

.message-content code {
  background: rgba(0,0,0,0.08);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
}

.message-content pre {
  background: #f4f4f4;
  padding: 10px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
}

.message-content blockquote {
  border-left: 3px solid #ddd;
  margin: 8px 0;
  padding-left: 12px;
  color: #666;
}

.message-content a {
  color: #409eff;
  text-decoration: none;
}

.message-content a:hover {
  text-decoration: underline;
}

.message-content table {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
}

.message-content th,
.message-content td {
  border: 1px solid #ddd;
  padding: 6px 10px;
  text-align: left;
}

.message-content th {
  background: #f5f5f5;
}

.message-item.user .message-content {
  color: white;
}

.message-time {
  font-size: 10px;
  color: #999;
  margin-top: 4px;
}

.message-item.user .message-time {
  color: rgba(255,255,255,0.7);
}

.loading-bubble {
  background: #e8e8e8;
}

.loading-dots {
  display: flex;
  gap: 4px;
}

.loading-dots span {
  width: 6px;
  height: 6px;
  background: #888;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.loading-dots span:nth-child(1) { animation-delay: -0.32s; }
.loading-dots span:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.loading-text {
  font-size: 11px;
  color: #888;
  margin-top: 4px;
}

/* 输入区域 */
.input-area {
  padding: 16px;
  border-top: 1px solid #e8e8e8;
  background: white;
  display: flex;
  gap: 10px;
}

.input-area .el-input {
  flex: 1;
}

/* 滚动条 */
.alert-list::-webkit-scrollbar,
.messages-list::-webkit-scrollbar {
  width: 4px;
}

.alert-list::-webkit-scrollbar-track,
.messages-list::-webkit-scrollbar-track {
  background: #e8e8e8;
  border-radius: 2px;
}

.alert-list::-webkit-scrollbar-thumb,
.messages-list::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 2px;
}

/* 响应式 */
@media (max-width: 900px) {
  .split-layout {
    flex-direction: column;
  }
  
  .chat-panel {
    width: 100%;
    height: 450px;
  }
}
</style>