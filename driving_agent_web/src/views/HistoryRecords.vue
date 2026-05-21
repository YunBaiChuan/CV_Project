<template>
  <div class="history-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <h3>历史警告记录</h3>
          <div class="header-buttons">
            <el-button 
              type="danger" 
              size="small" 
              @click="clearAllAlarms"
              :disabled="alarmList.length === 0"
              :loading="clearLoading"
            >
              清空全部
            </el-button>
          </div>
        </div>
      </template>

      <el-table 
        :data="alarmList" 
        style="width: 100%" 
        v-loading="loading" 
        border
      >
        <el-table-column prop="id" label="ID" width="80" align="center" />
        
        <el-table-column prop="alarm_type" label="警告类型" width="150">
          <template #default="scope">
            <span>{{ getAlarmTypeText(scope.row.alarm_type) }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="alarm_level" label="等级" width="120" align="center">
          <template #default="scope">
            <el-tag 
              :type="scope.row.alarm_level === 1 ? 'danger' : scope.row.alarm_level === 2 ? 'warning' : 'info'"
              size="small"
            >
              {{ getLevelText(scope.row.alarm_level) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="info" label="详细信息" show-overflow-tooltip />

        <el-table-column prop="vehicle_id" label="关联车辆" width="120" />

        <el-table-column prop="trigger_time" label="触发时间" width="180" />

        <el-table-column label="操作" width="100" fixed="right" align="center">
          <template #default="scope">
            <el-button 
              type="danger" 
              size="small" 
              link 
              @click="deleteAlarm(scope.row.id)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'

const API_BASE = 'http://127.0.0.1:8000'

const alarmList = ref([])
const loading = ref(false)
const clearLoading = ref(false)

const getAlarmTypeText = (type) => {
  switch(type) {
    case 'speeding': return '超速告警'
    case 'collision_risk': return '碰撞告警'
    case 'ai_analysis': return '智能告警'
    default: return type || '未知'
  }
}

const getLevelText = (level) => {
  switch(level) {
    case 1: return '紧急'
    case 2: return '严重'
    default: return '一般'
  }
}

// 获取告警列表（带用户ID过滤）
const fetchData = async () => {
  loading.value = true
  try {
    // 从 localStorage 获取用户ID
    const userId = localStorage.getItem('userId')
    
    if (!userId) {
      ElMessage.warning('请先登录')
      alarmList.value = []
      loading.value = false
      return
    }
    
    const res = await axios.get(`${API_BASE}/api/alarms?user_id=${userId}`)
    
    if (Array.isArray(res.data)) {
      alarmList.value = res.data
    } else {
      console.error('数据格式错误:', res.data)
      ElMessage.error('数据格式异常')
    }
  } catch (error) {
    console.error('获取数据失败:', error)
    ElMessage.error('无法连接到服务器获取警告记录')
  } finally {
    loading.value = false
  }
}

// 删除单条告警
const deleteAlarm = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除这条告警记录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    const res = await axios.delete(`${API_BASE}/api/alarms/${id}`)
    
    if (res.data.success) {
      ElMessage.success('删除成功')
      fetchData()
    } else {
      ElMessage.error(res.data.message || '删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

// 清空所有告警
const clearAllAlarms = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要清空所有告警记录吗？此操作不可恢复！', 
      '警告', 
      {
        confirmButtonText: '确定清空',
        cancelButtonText: '取消',
        type: 'error'
      }
    )
    
    clearLoading.value = true
    const res = await axios.delete(`${API_BASE}/api/alarms/clear`)
    
    if (res.data.success) {
      ElMessage.success('已清空所有告警记录')
      fetchData()
    } else {
      ElMessage.error(res.data.message || '清空失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('清空失败:', error)
      ElMessage.error('清空失败')
    }
  } finally {
    clearLoading.value = false
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.history-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-buttons {
  display: flex;
  gap: 10px;
}

/* 操作按钮样式 */
.el-button--danger.is-link {
  padding: 0;
}
</style>