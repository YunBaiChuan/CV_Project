import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import Register from '../views/Register.vue'
import AppLayout from '../views/AppLayout.vue' // 引入后台布局组件

const routes = [
  // 1.处理根路径，自动重定向到登录页
  {
    path: '/',
    redirect: '/login'
  },

  // 原有路由
  { path: '/login', component: Login },
  { path: '/register', component: Register },
  {
    path: '/app',
    component: AppLayout,
    redirect: '/app/track', // 默认跳转到实时追踪
    children: [
      // 注意：子路由 path 不带斜杠，表示是 /app 的相对路径
      { path: 'track', component: () => import('../views/RealTimeTrack.vue') },
      { path: 'chat', component: () => import('../views/AgentChat.vue') },
      { path: 'history', component: () => import('../views/HistoryRecords.vue') },
      { path: 'analysis', component: () => import('../views/AlarmAnalysis.vue') }  // 新增告警分析页面
    ]
  },

  // 2. 404 通配符，必须放在路由数组的最后
  // 如果访问的路径不在上面列表中，强制跳转到登录页（或者你可以做一个专门的 404 页面）
  {
    path: '/:pathMatch(.*)*',
    redirect: '/login'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫：未登录拦截
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  // 如果没有 token 且不是去登录或注册页，则强制去登录
  if (!token && to.path !== '/login' && to.path !== '/register') {
    next('/login')
  } else {
    next()
  }
})

export default router