const express = require('express')
const mysql = require('mysql2')
const cors = require('cors')

const app = express()
app.use(cors()) // 解决跨域问题
app.use(express.json()) // 解析前端发来的 JSON 数据

// 1. 连接 MySQL 数据库
const db = mysql.createConnection({
  host: 'localhost',
  user: 'root',        // 你的 MySQL 用户名
  password: '123456', // 你的 MySQL 密码
  database: 'car_monitor_db' // 数据库名
})

db.connect(err => {
  if (err) {
    console.error(' MySQL 数据库连接失败:', err)
    return
  }
  console.log(' 成功连接到本地 MySQL 数据库！')
})

// ================= 接口区域 =================

// 2. 注册接口 (真实写入数据库)
app.post('/api/register', (req, res) => {
  const { username, password } = req.body
  const sql = 'INSERT INTO users (username, password) VALUES (?, ?)'
  db.query(sql, [username, password], (err, result) => {
    if (err) {
      res.status(500).json({ message: '注册失败，用户名可能已存在' })
      return
    }
    res.json({ success: true, message: '注册成功' })
  })
})

// 3. 登录接口 (真实查询数据库)
app.post('/api/login', (req, res) => {
  const { username, password } = req.body
  const sql = 'SELECT * FROM users WHERE username = ? AND password = ?'
  db.query(sql, [username, password], (err, results) => {
    if (err) {
      console.error('数据库查询出错:', err)
      // 显式返回 500 错误
      return res.status(500).json({ success: false, message: '服务器内部错误' })
    }
    if (results.length === 0) {
      // 显式返回 401 错误
      return res.status(401).json({ success: false, message: '用户名或密码错误' })
    }

    // 登录成功：显式返回 200 状态码
    const user = results[0]
    res.status(200).json({
      success: true,
      message: '登录成功', // 加上 message 方便调试
      token: 'fake-jwt-token-' + Date.now(),
      user: { id: user.id, username: user.username }
    })
  })
})

// 4. 获取历史告警记录接口
app.get('/api/alarms', (req, res) => {
  const sql = 'SELECT * FROM alarm_records ORDER BY id DESC'
  db.query(sql, (err, results) => {
    if (err) {
      res.status(500).json({ error: err.message })
      return
    }
    res.json(results)
  })
})

// ================= 启动服务 =================
const PORT = 8000
app.listen(PORT, () => {
  console.log(` 后端服务已启动，监听端口: http://localhost:${PORT}`)
})