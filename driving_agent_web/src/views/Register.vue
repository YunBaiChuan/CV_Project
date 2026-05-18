<template>
  <div class="auth-container">
    <el-card class="register-card" shadow="hover">
      <h2>用户注册</h2>

      <el-form
        :model="form"
        :rules="rules"
        ref="registerFormRef"
        label-position="top"
      >
        <el-form-item label="登录账号" prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入登录用户名 (3-16位字符)"
            prefix-icon="User"
            clearable
          />
        </el-form-item>

        <el-form-item label="电子邮箱" prop="email">
          <el-input
            v-model="form.email"
            placeholder="请输入常用邮箱地址"
            prefix-icon="Message"
            clearable
          />
        </el-form-item>

        <el-form-item label="登录密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="设置登录密码 (至少3位)"
            prefix-icon="Lock"
            show-password
          />
        </el-form-item>

        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="form.confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            prefix-icon="Key"
            show-password
          />
        </el-form-item>

        <el-button type="success" @click="submitForm" class="submit-btn" :loading="loading">
          立即注册
        </el-button>
      </el-form>

      <div class="form-footer">
        已有账号？
        <router-link to="/login">返回登录</router-link>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const registerFormRef = ref(null)
const loading = ref(false)

const API_BASE = 'http://127.0.0.1:8000'

const form = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 16, message: '长度在 3 到 16 个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: ['blur', 'change'] }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 3, message: '密码长度至少3位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

const submitForm = () => {
  registerFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      
      try {
        const response = await axios.post(`${API_BASE}/api/register`, {
          username: form.username,
          password: form.password,
          email: form.email
        })
        
        if (response.data.success) {
          ElMessage.success('注册成功！即将跳转登录')
          setTimeout(() => {
            router.push('/login')
          }, 1500)
        } else {
          ElMessage.error(response.data.message || '注册失败')
        }
      } catch (error) {
        console.error('注册错误:', error)
        ElMessage.error('网络错误，请确保后端服务已启动')
      } finally {
        loading.value = false
      }
    } else {
      ElMessage.error('请检查表单填写是否正确')
    }
  })
}
</script>

<style scoped>
.auth-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f0f2f5;
}

.register-card {
  width: 450px;
  padding: 20px;
  border-radius: 8px;
}

.register-card h2 {
  text-align: center;
  margin-bottom: 30px;
  color: #333;
}

.submit-btn {
  width: 100%;
  margin-top: 10px;
}

.form-footer {
  margin-top: 20px;
  text-align: center;
}

.form-footer a {
  color: #409eff;
  text-decoration: none;
  margin-left: 5px;
}
</style>