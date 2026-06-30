// ============================
// 子女端 API 封装
// 依据：backend/app/api/v1/ 实际路由
// ============================

const BASE_URL = 'http://10.128.229.199:8090'

// ---- Token ----
function getToken() {
  return wx.getStorageSync('token') || ''
}
function getRefreshToken() {
  return wx.getStorageSync('refresh_token') || ''
}

// ---- 通用请求 ----
let refreshQueue = []
let isRefreshing = false

function request(options) {
  const { url, method = 'GET', data, _retry = false } = options

  return new Promise((resolve, reject) => {
    const token = getToken()
    wx.request({
      url: `${BASE_URL}${url}`,
      method,
      data,
      timeout: 15000,
      header: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      },
      success: async (res) => {
        const body = res.data || {}
        const code = body.code !== undefined ? body.code : res.statusCode

        if (res.statusCode === 200 && code === 0) {
          resolve(body.data)
          return
        }

        // 401 → refresh token
        if ((res.statusCode === 401 || code === 401) && !_retry) {
          if (isRefreshing) {
            return new Promise(r => refreshQueue.push(r))
              .then(() => resolve(request({ ...options, _retry: true })))
              .catch(reject)
          }
          isRefreshing = true
          try {
            const rt = getRefreshToken()
            if (!rt) throw new Error('no refresh token')
            const d = await post('/api/v1/auth/refresh', { refresh_token: rt })
            wx.setStorageSync('token', d.token)
            isRefreshing = false
            refreshQueue.forEach(r => r())
            refreshQueue = []
            return resolve(request({ ...options, _retry: true }))
          } catch (e) {
            isRefreshing = false
            refreshQueue.forEach(r => r())
            refreshQueue = []
            wx.setStorageSync('token', '')
            wx.setStorageSync('refresh_token', '')
            wx.showToast({ title: '登录过期', icon: 'none' })
            setTimeout(() => wx.reLaunch({ url: '/pages/login/login' }), 1000)
            reject({ code: 401, msg: '登录过期' })
            return
          }
        }

        reject(body || { code: res.statusCode, msg: body?.detail || '请求失败' })
      },
      fail: (err) => reject({ code: -1, msg: '网络连接失败', err })
    })
  })
}

function get(url, params = {}) {
  const keys = Object.keys(params).filter(k => params[k] !== undefined && params[k] !== null && params[k] !== '')
  if (keys.length) {
    url += '?' + keys.map(k => `${encodeURIComponent(k)}=${encodeURIComponent(params[k])}`).join('&')
  }
  return request({ url, method: 'GET' })
}

function post(url, data = {}) {
  return request({ url, method: 'POST', data })
}

function put(url, data = {}) {
  return request({ url, method: 'PUT', data })
}

function del(url) {
  return request({ url, method: 'DELETE' })
}

function patch(url, data = {}) {
  return request({ url, method: 'PATCH', data })
}

// ============ 认证 auth.py ============
// POST /api/v1/auth/wx-login       老人/子女共用
// POST /api/v1/auth/refresh        token 刷新
// POST /api/v1/auth/logout         登出
// POST /api/v1/auth/bind-phone     子女绑定手机号
// POST /api/v1/auth/heartbeat      老人端心跳（子女不可用）
// POST /api/v1/auth/subscribe/grant 订阅授权上报
// POST /api/v1/auth/admin/login    管理员登录
// GET  /api/v1/auth/dev/create-admin 开发创建管理员

function login(code, userType = 'child') {
  return post('/api/v1/auth/wx-login', { code, user_type: userType })
}

function refreshToken(rt) {
  return post('/api/v1/auth/refresh', { refresh_token: rt })
}

function logout() {
  return post('/api/v1/auth/logout')
}

function bindPhone(phone, name, relation) {
  return post('/api/v1/auth/bind-phone', { phone, name, relation })
}

// ============ 记忆 memory.py ============
// GET    /api/v1/memory                       列表（分页/筛选）
// POST   /api/v1/memory                       新增（需 user_id）
// GET    /api/v1/memory/{memory_id}            详情
// PUT    /api/v1/memory/{memory_id}            编辑
// DELETE /api/v1/memory/{memory_id}            删除（软删）
// PATCH  /api/v1/memory/{memory_id}/importance 调整重要度
// POST   /api/v1/memory/search                语义检索

function listMemory(params = {}) {
  return get('/api/v1/memory', params)
}

function createMemory(data) {
  return post('/api/v1/memory', data)
}

function getMemory(memoryId) {
  return get(`/api/v1/memory/${memoryId}`)
}

function updateMemory(memoryId, data) {
  return put(`/api/v1/memory/${memoryId}`, data)
}

function deleteMemory(memoryId) {
  return del(`/api/v1/memory/${memoryId}`)
}

function setImportance(memoryId, importance) {
  return patch(`/api/v1/memory/${memoryId}/importance`, { importance })
}

function searchMemory(data) {
  return post('/api/v1/memory/search', data)
}

// ============ 问答 qa.py ============
// GET /api/v1/qa/history          历史问答（子女需传 user_id，且需已绑定）
// GET /api/v1/qa/history/{msg_id} 单条详情

function qaHistory(params = {}) {
  return get('/api/v1/qa/history', params)
}

function qaDetail(msgId) {
  return get(`/api/v1/qa/history/${msgId}`)
}

// ============ 系统 ============
function healthCheck() {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${BASE_URL}/api/v1/health`,
      method: 'GET',
      timeout: 5000,
      success: (res) => {
        if (res.statusCode === 200 && res.data && res.data.code === 0) {
          resolve(res.data.data)
        } else {
          reject(res.data)
        }
      },
      fail: (err) => reject(err)
    })
  })
}

module.exports = {
  BASE_URL,
  request, get, post, put, del, patch,
  // auth
  login, refreshToken, logout, bindPhone,
  // memory
  listMemory, createMemory, getMemory, updateMemory, deleteMemory, setImportance, searchMemory,
  // qa
  qaHistory, qaDetail,
  // system
  healthCheck
}
