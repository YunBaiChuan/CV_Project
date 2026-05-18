<template>
  <div class="tracking-container">
    <div class="tracking-header">
      <h2>🚗 实时车辆追踪</h2>
      <div class="controls">
        <el-button type="primary" @click="selectVideo" :disabled="isTracking">
          <el-icon><VideoCamera /></el-icon> 选择视频
        </el-button>
        <el-button 
          type="success" 
          @click="startTracking" 
          :disabled="!videoPath || isTracking"
          :loading="isTracking"
        >
          {{ isTracking ? '追踪中...' : '开始追踪' }}
        </el-button>
        <el-button 
          type="danger" 
          @click="stopTracking" 
          :disabled="!isTracking"
        >
          停止追踪
        </el-button>
      </div>
    </div>

    <!-- 实时视频画面 -->
    <div class="video-container">
      <canvas ref="canvasRef" style="width: 100%; height: 100%; background: #000;"></canvas>
      <div v-if="!isTracking && !hasVideoSelected" class="video-placeholder">
        <el-icon><VideoCamera /></el-icon>
        <p>请选择视频文件</p>
      </div>
      <div v-if="isTracking && !hasFrame" class="tracking-status">
        <el-icon class="is-loading"><Loading /></el-icon>
        <p>等待视频流...</p>
      </div>
    </div>

    <!-- 追踪信息 -->
    <el-card class="info-card">
      <div class="info-grid">
        <div class="info-item">
          <span class="label">状态：</span>
          <el-tag :type="isTracking ? 'warning' : 'info'">
            {{ isTracking ? '实时追踪中' : '就绪' }}
          </el-tag>
        </div>
        <div class="info-item">
          <span class="label">检测到车辆：</span>
          <span class="value">{{ vehicleCount }}</span>
        </div>
        <div class="info-item">
          <span class="label">进度：</span>
          <el-progress :percentage="progress" :stroke-width="8" />
        </div>
        <div class="info-item" v-if="currentTime > 0">
          <span class="label">当前时间：</span>
          <span class="value">{{ formatTime(currentTime) }}</span>
        </div>
      </div>
    </el-card>

    <!-- 车辆列表 -->
    <el-card class="vehicle-list-card" v-if="vehicles.length > 0">
      <template #header>
        <span>📋 实时检测到的车辆（共 {{ vehicles.length }} 辆）</span>
      </template>
      <div class="vehicle-list">
        <div v-for="v in vehicles.slice(0, 15)" :key="v.id" class="vehicle-item">
          <span class="vehicle-id">ID: {{ v.id }}</span>
          <span class="vehicle-time">{{ v.time }}</span>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoCamera, Loading } from '@element-plus/icons-vue'

const WS_URL = 'ws://127.0.0.1:8000/ws/track1'

const videoPath = ref<string>('')
const canvasRef = ref<HTMLCanvasElement | null>(null)
const isTracking = ref<boolean>(false)
const hasFrame = ref<boolean>(false)
const hasVideoSelected = ref<boolean>(false)
const vehicleCount = ref<number>(0)
const progress = ref<number>(0)
const vehicles = ref<{id: number, time: string}[]>([])
const currentTime = ref<number>(0)  // 记录当前播放时间
const totalDuration = ref<number>(0)  // 视频总时长
let ws: WebSocket | null = null
let previewVideo: HTMLVideoElement | null = null
let animationId: number | null = null

// 格式化时间显示
const formatTime = (seconds: number): string => {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

// 选择视频文件
const selectVideo = () => {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'video/mp4,video/avi,video/mov,video/mkv'
  input.onchange = (e: Event) => {
    const target = e.target as HTMLInputElement
    const file = target.files?.[0]
    if (file) {
      const url = URL.createObjectURL(file)
      
      if (!previewVideo) {
        previewVideo = document.createElement('video')
        previewVideo.autoplay = true
        previewVideo.muted = true
        previewVideo.loop = false
        previewVideo.playsInline = true
        
        // 监听时间更新，记录当前播放位置
        previewVideo.ontimeupdate = () => {
          if (previewVideo) {
            currentTime.value = previewVideo.currentTime
          }
        }
        
        // 获取视频总时长
        previewVideo.onloadedmetadata = () => {
          if (previewVideo) {
            totalDuration.value = previewVideo.duration
          }
        }
      }
      
      previewVideo.src = url
      previewVideo.onloadeddata = () => {
        if (previewVideo) {
          previewVideo.play()
        }
        hasVideoSelected.value = true
        drawPreviewToCanvas()
      }
      
      videoPath.value = file.name
      hasFrame.value = true
      ElMessage.success(`已选择：${file.name}`)
    }
  }
  input.click()
}

// 将预览视频绘制到 canvas
const drawPreviewToCanvas = () => {
  if (!previewVideo || !canvasRef.value) return
  
  const ctx = canvasRef.value.getContext('2d')
  if (!ctx) return
  
  const draw = () => {
    if (previewVideo && canvasRef.value && !isTracking.value) {
      const video = previewVideo
      const canvas = canvasRef.value
      
      if (video.videoWidth && video.videoHeight) {
        canvas.width = video.videoWidth
        canvas.height = video.videoHeight
      }
      
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
      animationId = requestAnimationFrame(draw)
    }
  }
  
  draw()
}

// 停止预览绘制
const stopPreviewDraw = () => {
  if (animationId) {
    cancelAnimationFrame(animationId)
    animationId = null
  }
}

// 开始追踪（从当前位置开始）
const startTracking = () => {
  if (!videoPath.value) {
    ElMessage.warning('请先选择视频')
    return
  }
  
  // 暂停预览视频，记录当前时间
  if (previewVideo) {
    previewVideo.pause()
    currentTime.value = previewVideo.currentTime
  }
  
  stopPreviewDraw()
  
  isTracking.value = true
  hasFrame.value = false // 是否有黑屏
  vehicles.value = []
  vehicleCount.value = 0
  progress.value = 0
  
  ws = new WebSocket(WS_URL)
  
  ws.onopen = () => {
    console.log('WebSocket 已连接')
    // 发送视频路径和开始时间
    ws?.send(JSON.stringify({ 
      video_path: videoPath.value,
      start_time: currentTime.value
    }))
  }
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    
    switch (data.type) {
      case 'start':
        console.log('开始接收视频流，从', data.start_time, '秒开始')
        ElMessage.info(`从 ${formatTime(data.start_time)} 开始追踪`)
        break
        
      case 'frame':
        // 显示实时追踪画面
        if (canvasRef.value) {
          const img = new Image()
          img.onload = () => {
            const ctx = canvasRef.value?.getContext('2d')
            if (ctx && canvasRef.value) {
              canvasRef.value.width = img.width
              canvasRef.value.height = img.height
              ctx.drawImage(img, 0, 0)
            }
          }
          img.src = `data:image/jpeg;base64,${data.image}`
          hasFrame.value = true
        }
        progress.value = data.progress
        vehicleCount.value = data.vehicles
        break
        
      case 'new_vehicle':
        vehicles.value.push({
          id: data.vehicle_id,
          time: new Date().toLocaleTimeString()
        })
        vehicleCount.value = data.count
        break
        
      case 'complete':
        ElMessage.success(`追踪完成！共检测到 ${data.vehicles} 辆车`)
        isTracking.value = false
        if (ws) ws.close()
        break
        
      case 'error':
        ElMessage.error(`追踪出错：${data.message}`)
        isTracking.value = false
        if (ws) ws.close()
        break
    }
  }
  
  ws.onerror = () => {
    ElMessage.error('WebSocket 连接失败，请确保后端已启动')
    isTracking.value = false
  }
  
  ws.onclose = () => {
    console.log('WebSocket 已断开')
    if (isTracking.value) {
      isTracking.value = false
    }
  }
}

// 停止追踪
const stopTracking = () => {
  if (ws) {
    ws.close()
  }
  isTracking.value = false
  ElMessage.info('已停止追踪')
}

// 组件卸载时清理资源
onUnmounted(() => {
  if (ws) {
    ws.close()
  }
  if (previewVideo) {
    previewVideo.pause()
    previewVideo.src = ''
  }
  stopPreviewDraw()
})
</script>

<style scoped>
.tracking-container {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.tracking-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 16px;
}

.tracking-header h2 {
  margin: 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.controls {
  display: flex;
  gap: 12px;
}

.video-container {
  background: #000;
  width: 100%;
  height: 500px;
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 20px;
  position: relative;
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
  color: #666;
  gap: 16px;
  background: #000;
}

.tracking-status .el-icon {
  font-size: 48px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.video-placeholder .el-icon {
  font-size: 64px;
}

.info-card {
  margin-bottom: 20px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.info-item .label {
  color: #666;
  font-weight: 500;
}

.info-item .value {
  color: #333;
  font-weight: 600;
}

.vehicle-list-card {
  margin-top: 20px;
}

.vehicle-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 250px;
  overflow-y: auto;
}

.vehicle-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 8px;
  transition: all 0.2s;
}

.vehicle-item:hover {
  background: #e9ecef;
  transform: translateX(4px);
}

.vehicle-id {
  font-weight: 600;
  color: #409eff;
}

.vehicle-time {
  font-size: 12px;
  color: #999;
}

/* 滚动条 */
.vehicle-list::-webkit-scrollbar {
  width: 6px;
}

.vehicle-list::-webkit-scrollbar-track {
  background: #f0f2f5;
  border-radius: 3px;
}

.vehicle-list::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.vehicle-list::-webkit-scrollbar-thumb:hover {
  background: #a1a1a1;
}
</style>