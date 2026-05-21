<template>
  <div class="analysis-container">
    <!-- 统计卡片 -->
    <div class="stats-cards">
      <el-card class="stat-card" shadow="hover">
        <div class="stat-icon warning">⚠️</div>
        <div class="stat-info">
          <div class="stat-value">{{ totalAlarms }}</div>
          <div class="stat-label">总告警数</div>
        </div>
      </el-card>
      
      <el-card class="stat-card" shadow="hover">
        <div class="stat-icon danger">🚨</div>
        <div class="stat-info">
          <div class="stat-value">{{ dangerCount }}</div>
          <div class="stat-label">紧急告警</div>
        </div>
      </el-card>
      
      <el-card class="stat-card" shadow="hover">
        <div class="stat-icon warning">⚠️</div>
        <div class="stat-info">
          <div class="stat-value">{{ warningCount }}</div>
          <div class="stat-label">严重告警</div>
        </div>
      </el-card>
      
      <el-card class="stat-card" shadow="hover">
        <div class="stat-icon info">💡</div>
        <div class="stat-info">
          <div class="stat-value">{{ infoCount }}</div>
          <div class="stat-label">一般告警</div>
        </div>
      </el-card>
    </div>

    <!-- 图表区域 -->
    <div class="charts-row">
      <el-card class="chart-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>📊 告警类型分布</span>
          </div>
        </template>
        <div ref="typeChartRef" style="height: 350px"></div>
      </el-card>

      <el-card class="chart-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>📈 告警趋势（最近7天）</span>
          </div>
        </template>
        <div ref="trendChartRef" style="height: 350px"></div>
      </el-card>
    </div>

    <div class="charts-row">
      <el-card class="chart-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>🚗 高频告警车辆 Top 10</span>
          </div>
        </template>
        <div ref="vehicleChartRef" style="height: 350px"></div>
      </el-card>

      <el-card class="chart-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>⏰ 告警时段分布</span>
          </div>
        </template>
        <div ref="hourChartRef" style="height: 350px"></div>
      </el-card>
    </div>

    <!-- 告警类型占比表格 -->
    <el-card class="table-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>📋 告警类型详情</span>
        </div>
      </template>
      <el-table :data="typeStats" style="width: 100%" border>
        <el-table-column prop="type_name" label="告警类型" width="150" />
        <el-table-column prop="count" label="数量" width="120" align="center" />
        <el-table-column prop="percentage" label="占比" align="center">
          <template #default="scope">
            <el-progress :percentage="scope.row.percentage" :stroke-width="10" />
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'

const API_BASE = 'http://127.0.0.1:8000'

// 统计数据
const totalAlarms = ref(0)
const dangerCount = ref(0)
const warningCount = ref(0)
const infoCount = ref(0)

// 图表数据
const typeStats = ref([])
const trendData = ref([])
const vehicleStats = ref([])
const hourStats = ref([])

// 图表实例
const typeChartRef = ref(null)
const trendChartRef = ref(null)
const vehicleChartRef = ref(null)
const hourChartRef = ref(null)

let typeChart = null
let trendChart = null
let vehicleChart = null
let hourChart = null

// 获取告警数据
const fetchAlarmData = async () => {
  try {
    const userId = localStorage.getItem('userId')
    if (!userId) {
      ElMessage.warning('请先登录')
      return
    }
    
    const res = await axios.get(`${API_BASE}/api/alarms?user_id=${userId}`)
    const alarms = res.data
    
    if (!Array.isArray(alarms)) return
    
    // 统计总数和等级分布
    totalAlarms.value = alarms.length
    dangerCount.value = alarms.filter(a => a.alarm_level === 1).length
    warningCount.value = alarms.filter(a => a.alarm_level === 2).length
    infoCount.value = alarms.filter(a => a.alarm_level === 3 || !a.alarm_level).length
    
    // ========== 统计告警类型分布（包含碰撞风险） ==========
    const typeMap = new Map()
    alarms.forEach(alarm => {
      let typeName = ''
      if (alarm.alarm_type === 'ai_analysis') {
        typeName = '智能告警'
      } else if (alarm.alarm_type === 'speeding') {
        typeName = '速度告警'
      } else if (alarm.alarm_type === 'collision_risk') {
        typeName = '碰撞告警'
      } else {
        typeName = alarm.alarm_type || '未知'
      }
      typeMap.set(typeName, (typeMap.get(typeName) || 0) + 1)
    })
    typeStats.value = Array.from(typeMap.entries()).map(([type_name, count]) => ({
      type_name,
      count,
      percentage: Math.round(count / totalAlarms.value * 100)
    }))
    
    // 统计7天趋势
    const trendMap = new Map()
    const now = new Date()
    for (let i = 6; i >= 0; i--) {
      const date = new Date(now)
      date.setDate(date.getDate() - i)
      const dateStr = `${date.getMonth()+1}/${date.getDate()}`
      trendMap.set(dateStr, 0)
    }
    alarms.forEach(alarm => {
      const date = new Date(alarm.trigger_time)
      const dateStr = `${date.getMonth()+1}/${date.getDate()}`
      if (trendMap.has(dateStr)) {
        trendMap.set(dateStr, trendMap.get(dateStr) + 1)
      }
    })
    trendData.value = Array.from(trendMap.entries()).map(([date, count]) => ({ date, count }))
    
    // 统计高频告警车辆（提取车辆ID）
    const vehicleMap = new Map()
    alarms.forEach(alarm => {
      if (alarm.vehicle_id && alarm.vehicle_id !== 'None') {
        vehicleMap.set(alarm.vehicle_id, (vehicleMap.get(alarm.vehicle_id) || 0) + 1)
      }
    })
    vehicleStats.value = Array.from(vehicleMap.entries())
      .map(([vehicle_id, count]) => ({ vehicle_id, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10)
    
    // 统计时段分布
    const hourMap = new Map()
    for (let i = 0; i < 24; i++) {
      hourMap.set(i, 0)
    }
    alarms.forEach(alarm => {
      const hour = new Date(alarm.trigger_time).getHours()
      hourMap.set(hour, hourMap.get(hour) + 1)
    })
    hourStats.value = Array.from(hourMap.entries()).map(([hour, count]) => ({ hour, count }))
    
    // 渲染图表
    renderCharts()
    
  } catch (error) {
    console.error('获取数据失败:', error)
    ElMessage.error('获取告警数据失败')
  }
}

// 渲染图表
const renderCharts = () => {
  // 告警类型分布饼图
  if (typeChartRef.value) {
    if (typeChart) typeChart.dispose()
    typeChart = echarts.init(typeChartRef.value)
    typeChart.setOption({
      tooltip: { trigger: 'item' },
      legend: { top: '5%', left: 'center' },
      series: [{
        name: '告警类型',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: { show: true, formatter: '{b}: {d}%' },
        data: typeStats.value.map(item => ({ name: item.type_name, value: item.count }))
      }],
      color: ['#f56c6c', '#e6a23c', '#67c23a', '#409eff', '#909399']
    })
  }
  
  // 告警趋势折线图
  if (trendChartRef.value) {
    if (trendChart) trendChart.dispose()
    trendChart = echarts.init(trendChartRef.value)
    trendChart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: trendData.value.map(d => d.date) },
      yAxis: { type: 'value', name: '告警数量' },
      series: [{
        data: trendData.value.map(d => d.count),
        type: 'line',
        smooth: true,
        lineStyle: { color: '#409eff', width: 3 },
        areaStyle: { opacity: 0.3, color: '#409eff' },
        symbol: 'circle',
        symbolSize: 8,
        itemStyle: { color: '#409eff' }
      }]
    })
  }
  
  // 高频告警车辆条形图
  if (vehicleChartRef.value) {
    if (vehicleChart) vehicleChart.dispose()
    vehicleChart = echarts.init(vehicleChartRef.value)
    vehicleChart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'value', name: '告警次数' },
      yAxis: { type: 'category', data: vehicleStats.value.map(v => `车辆${v.vehicle_id}`), name: '车辆ID' },
      series: [{
        data: vehicleStats.value.map(v => v.count),
        type: 'bar',
        itemStyle: { borderRadius: [0, 4, 4, 0], color: '#e6a23c' }
      }]
    })
  }
  
  // 时段分布柱状图
  if (hourChartRef.value) {
    if (hourChart) hourChart.dispose()
    hourChart = echarts.init(hourChartRef.value)
    hourChart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      xAxis: { type: 'category', data: hourStats.value.map(h => `${h.hour}:00`), axisLabel: { rotate: 45 } },
      yAxis: { type: 'value', name: '告警数量' },
      series: [{
        data: hourStats.value.map(h => h.count),
        type: 'bar',
        itemStyle: { borderRadius: [4, 4, 0, 0], color: '#67c23a' }
      }]
    })
  }
}

// 窗口大小变化时重新调整图表
const handleResize = () => {
  [typeChart, trendChart, vehicleChart, hourChart].forEach(chart => {
    if (chart) chart.resize()
  })
}

onMounted(() => {
  fetchAlarmData()
  window.addEventListener('resize', handleResize)
})

// 监听数据变化重新渲染
watch([typeStats, trendData, vehicleStats, hourStats], () => {
  renderCharts()
})
</script>

<style scoped>
.analysis-container {
  padding: 20px;
  background: #f5f7fa;
  min-height: 100vh;
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 20px;
  border-radius: 12px;
}

.stat-icon {
  font-size: 48px;
  width: 70px;
  text-align: center;
}

.stat-info {
  flex: 1;
  text-align: center;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #333;
}

.stat-label {
  font-size: 14px;
  color: #999;
  margin-top: 8px;
}

.charts-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}

.chart-card {
  border-radius: 12px;
}

.table-card {
  border-radius: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  color: #333;
}

@media (max-width: 1200px) {
  .stats-cards {
    grid-template-columns: repeat(2, 1fr);
  }
  .charts-row {
    grid-template-columns: 1fr;
  }
}
</style>