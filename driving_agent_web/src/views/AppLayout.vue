<template>
  <el-container style="height: 100vh;">
    <!-- 左侧侧边栏 -->
    <el-aside width="220px" class="sidebar-container">
      
      <!-- 菜单区域：使用 flex: 1 自动撑满剩余高度 -->
      <el-menu
        :default-active="$route.path"
        class="sidebar-menu"
        background-color="#001529"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
        router
      >
        <el-menu-item index="/app/track">
          <el-icon><VideoCamera /></el-icon>
          <span>实时追踪</span>
        </el-menu-item>
        
        <el-menu-item index="/app/chat">
          <el-icon><ChatDotRound /></el-icon>
          <span>智能驾驶</span>
        </el-menu-item>
        
        <el-menu-item index="/app/history">
          <el-icon><Document /></el-icon>
          <span>历史告警</span>
        </el-menu-item>

        <el-menu-item index="/app/analysis">
          <el-icon><DataAnalysis /></el-icon>
          <span>告警分析</span>
        </el-menu-item>
      </el-menu>

      <!-- 退出登录按钮：保持在 DOM 结构底部 -->
      <div class="logout-btn" @click="handleLogout">
        <el-icon><SwitchButton /></el-icon>
        <span>退出登录</span>
      </div>
    </el-aside>

    <el-container>
      <el-header style="background: #fff; box-shadow: 0 1px 4px rgba(0,21,41,.08);">
        <!-- 这里可以放顶栏内容 -->
      </el-header>
      
      <el-main style="background: #f0f2f5;">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import { SwitchButton, DataAnalysis } from '@element-plus/icons-vue'

const router = useRouter()

const handleLogout = () => {
  ElMessageBox.confirm('确定要退出登录吗？', '退出系统', {
    confirmButtonText: '确认退出',
    cancelButtonText: '再想想',
    type: 'warning',
    center: true,
  }).then(() => {
    localStorage.removeItem('token')
    router.replace('/login')
    ElMessage.success('已安全退出')
  }).catch(() => {})
}
</script>

<style scoped>
/* 侧边栏容器：启用 Flex 布局 */
.sidebar-container {
  background-color: #002649;
  display: flex;
  flex-direction: column; /* 垂直排列子元素 */
  height: 100%;
}

/* 菜单区域：占据所有剩余空间 */
.sidebar-menu {
  flex: 1;
  border-right: none; /* 去除 Element Plus 默认右边框 */
  overflow-y: auto; /* 如果菜单太长，允许滚动 */
}

/* 退出按钮样式 */
.logout-btn {
  /* 移除 position: absolute */
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #bfcbd9;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.05); /* 增加顶部分割线 */
  background-color: #001529;
}

.logout-btn:hover {
  color: #fff;
  background-color: rgba(255, 255, 255, 0.08);
}

.logout-btn .el-icon {
  margin-right: 8px;
}
</style>