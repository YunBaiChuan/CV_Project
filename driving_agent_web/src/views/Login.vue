<template>
  <div class="login-container">
    <!-- 左侧品牌区域 -->
    <div class="login-aside">
      <div class="aside-content">
        <div class="project-logo">
          <!-- <div class="logo-icon">🚗</div> -->
          <h1>道路车辆多目标<br>实时跟踪系统</h1>
        </div>
        <p class="project-desc">基于 YOLOv8 + DeepSeek 的智能驾驶监控系统</p>
      </div>
    </div>

    <!-- 右侧表单区域 -->
    <div class="login-form-wrapper">
      <div class="form-container">
        <div class="form-header">
          <h2>账号登录</h2>
          <p>请输入您的账号信息以继续</p>
        </div>

        <el-form :model="form" :rules="rules" ref="loginFormRef">
          <el-form-item prop="username">
            <el-input
              v-model="form.username"
              placeholder="请输入用户名"
              size="large"
              prefix-icon="User"
            />
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入密码"
              size="large"
              prefix-icon="Lock"
              show-password
            />
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              size="large"
              style="width: 100%; font-weight: 500; letter-spacing: 2px;"
              @click="handleLogin"
              :loading="loading"
            >
              立即登录
            </el-button>
          </el-form-item>
        </el-form>

        <div class="form-footer">
          <span>还没有账号？</span>
          <router-link to="/register">去注册</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const router = useRouter()
const loading = ref(false)
const loginFormRef = ref(null)

const API_BASE = 'http://127.0.0.1:8000'

const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const handleLogin = async () => {
  if (!form.username || !form.password) {
    ElMessage.warning('请填写用户名和密码')
    return
  }
  
  loading.value = true
  
  try {
    const response = await axios.post(`${API_BASE}/api/login`, {
      username: form.username,
      password: form.password
    })
    
    if (response.data.success) {
      // 保存登录信息
      localStorage.setItem('token', response.data.token)
      localStorage.setItem('user', JSON.stringify(response.data.user))
      localStorage.setItem('userId', response.data.user.id)  // 保存用户ID
      ElMessage.success(response.data.message || '登录成功')
      router.push('/app/track')
    } else {
      ElMessage.error(response.data.message || '登录失败')
    }
  } catch (error) {
    console.error('登录错误:', error)
    ElMessage.error('网络错误，请确保后端服务已启动')
  } finally {
    loading.value = false
  }
}

const handleKeyPress = (e) => {
  if (e.key === 'Enter') {
    handleLogin()
  }
}

onMounted(() => {
  window.addEventListener('keypress', handleKeyPress)
})

onUnmounted(() => {
  window.removeEventListener('keypress', handleKeyPress)
})
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  width: 100%;
  background-color: #ffffff;
  overflow: hidden;
}

.login-aside {
  flex: 1;
  background: linear-gradient(135deg, #409eff 0%, #2b76e5 100%);
  display: flex;
  justify-content: center;
  align-items: center;
  color: white;
  text-align: center;
}

.aside-content {
  max-width: 400px;
  padding: 40px;
}

.project-logo {
  margin-bottom: 30px;
}

.logo-icon {
  font-size: 64px;
  margin-bottom: 20px;
}

.aside-content h1 {
  font-size: 32px;
  font-weight: 700;
  margin: 0;
  line-height: 1.3;
  color: white;
}

.project-desc {
  font-size: 14px;
  opacity: 0.85;
  margin-top: 20px;
  line-height: 1.6;
}

.login-form-wrapper {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f9f9f9;
}

.form-container {
  width: 400px;
  padding: 48px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.05);
}

.form-header {
  margin-bottom: 32px;
  text-align: left;
}

.form-header h2 {
  font-size: 28px;
  color: #333;
  margin: 0;
  font-weight: 700;
}

.form-header p {
  color: #999;
  margin-top: 8px;
  font-size: 14px;
}

.form-footer {
  margin-top: 24px;
  text-align: center;
  font-size: 14px;
  color: #666;
}

.form-footer a {
  color: #409eff;
  text-decoration: none;
  margin-left: 5px;
}

.form-footer a:hover {
  text-decoration: underline;
}

/* 表单项样式优化 */
:deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
  transition: all 0.3s;
}

:deep(.el-input__wrapper:hover) {
  box-shadow: 0 2px 8px rgba(64,158,255,0.2);
}

:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #409eff inset;
}

:deep(.el-button) {
  border-radius: 8px;
  height: 44px;
  font-size: 16px;
}

@media (max-width: 768px) {
  .login-aside {
    display: none;
  }
  .login-form-wrapper {
    width: 100%;
  }
  .form-container {
    width: 90%;
    padding: 32px 24px;
  }
}
</style>