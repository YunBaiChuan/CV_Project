import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    // 核心修改：添加 server 和 proxy 配置
    proxy: {
      // 这里的 '/api' 必须和你 axios 请求的前缀一致
      '/api': {
        target: 'http://localhost:8000', // ⚠️ 重点：这里填你后端 SpringBoot/Java 服务的真实端口
        changeOrigin: true, // 允许跨域
        rewrite: (path) => path.replace(/^\/api/, '') // 如果后端接口路径不带 /api，需要重写去掉
      }
    }
  }
})