// ============================
// 子女端 API 封装
// 对齐 backend/app/api/v1/ 所有已实现接口
// ============================

const BASE_URL = 'http://10.178.3.199:8090'

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

        // 支持 200/201 等成功状态码
        if (res.statusCode >= 200 && res.statusCode < 300 && code === 0) {
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

function postQs(url, params = {}) {
  const keys = Object.keys(params).filter(k => params[k] !== undefined && params[k] !== null && params[k] !== '')
  if (keys.length) {
    url += '?' + keys.map(k => `${encodeURIComponent(k)}=${encodeURIComponent(params[k])}`).join('&')
  }
  return request({ url, method: 'POST' })
}

function put(url, data = {}) {
  return request({ url, method: 'PUT', data })
}

function putQs(url, params = {}) {
  const keys = Object.keys(params).filter(k => params[k] !== undefined && params[k] !== null && params[k] !== '')
  if (keys.length) {
    url += '?' + keys.map(k => `${encodeURIComponent(k)}=${encodeURIComponent(params[k])}`).join('&')
  }
  return request({ url, method: 'PUT' })
}

function del(url) {
  return request({ url, method: 'DELETE' })
}

function patch(url, data = {}) {
  return request({ url, method: 'PATCH', data })
}

// ============ 认证 auth.py ============
// POST /api/v1/auth/wx-login
function login(code, userType = 'child') {
  return post('/api/v1/auth/wx-login', { code, user_type: userType })
}

// POST /api/v1/auth/refresh
function refreshToken(rt) {
  return post('/api/v1/auth/refresh', { refresh_token: rt })
}

// POST /api/v1/auth/logout
function logout() {
  return post('/api/v1/auth/logout')
}

// POST /api/v1/auth/bind-phone
function bindPhone(phone, name, relation) {
  return post('/api/v1/auth/bind-phone', { phone, name, relation })
}

// GET /api/v1/auth/me
function getMyInfo() {
  return get('/api/v1/auth/me')
}

// POST /api/v1/auth/subscribe/grant
function grantSubscribe(templateId, grantStatus) {
  return post('/api/v1/auth/subscribe/grant', { template_id: templateId, grant_status: grantStatus })
}

// ============ 媒体 media.py ============
// POST /api/v1/media/upload/image   （需要用 wx.uploadFile，这里提供 URL 供参考）
function uploadImageUrl() {
  return '/api/v1/media/upload/image'
}

// POST /api/v1/media/image/enhance
function enhanceImage(url, brightness = 1.3) {
  return post('/api/v1/media/image/enhance', { url, brightness })
}

// POST /api/v1/media/upload/voice
function uploadVoiceUrl() {
  return '/api/v1/media/upload/voice'
}

// ============ 记忆 memory.py ============
// GET    /api/v1/memory
// POST   /api/v1/memory
// GET    /api/v1/memory/{memory_id}
// PUT    /api/v1/memory/{memory_id}
// DELETE /api/v1/memory/{memory_id}
// PATCH  /api/v1/memory/{memory_id}/importance
// POST   /api/v1/memory/search

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
// GET /api/v1/qa/history
// GET /api/v1/qa/history/{msg_id}

function qaHistory(params = {}) {
  return get('/api/v1/qa/history', params)
}

function qaDetail(msgId) {
  return get(`/api/v1/qa/history/${msgId}`)
}

// ============ 用药提醒 reminder.py ============
// GET    /api/v1/reminder/medication/list  子女端查看老人用药列表
// POST   /api/v1/reminder/medication       新增（Query参数）
// PUT    /api/v1/reminder/medication/{id}  修改（Query参数）
// DELETE /api/v1/reminder/medication/{id}  删除

function listMedications(userId) {
  return get('/api/v1/reminder/medication/list', { user_id: userId })
}

function createMedication(drugName, remindTime, userId, dosage) {
  return postQs('/api/v1/reminder/medication', {
    drug_name: drugName,
    remind_time: remindTime,
    user_id: userId,
    dosage: dosage
  })
}

function updateMedication(reminderId, params = {}) {
  return putQs(`/api/v1/reminder/medication/${reminderId}`, params)
}

function deleteMedication(reminderId) {
  return del(`/api/v1/reminder/medication/${reminderId}`)
}

// ============ 子女端 child.py ============
// POST   /api/v1/child/bind
// DELETE /api/v1/child/unbind/{user_id}
// GET    /api/v1/child/binded-users
// GET    /api/v1/child/dashboard/{user_id}
// GET    /api/v1/child/messages/{user_id}
// GET    /api/v1/child/settings/{user_id}
// PUT    /api/v1/child/settings/{user_id}
// GET    /api/v1/child/settings/{user_id}/changes

function bindElderly(code, relation = '子女') {
  return post('/api/v1/child/bind', { code, relation })
}

function unbindElderly(userId) {
  return del(`/api/v1/child/unbind/${userId}`)
}

function getBindedUsers() {
  return get('/api/v1/child/binded-users')
}

function getDashboard(userId) {
  return get(`/api/v1/child/dashboard/${userId}`)
}

function getChildMessages(userId, params = {}) {
  return get(`/api/v1/child/messages/${userId}`, params)
}

function getChildSettings(userId) {
  return get(`/api/v1/child/settings/${userId}`)
}

function updateChildSettings(userId, data) {
  return put(`/api/v1/child/settings/${userId}`, data)
}

function getSettingsChanges(userId) {
  return get(`/api/v1/child/settings/${userId}/changes`)
}

// ============ 通信 comm.py ============
// POST   /api/v1/comm/text
// POST   /api/v1/comm/voice
// GET    /api/v1/comm/history
// POST   /api/v1/comm/greeting/schedule
// GET    /api/v1/comm/greeting/schedule

function commText(userId, content) {
  return postQs('/api/v1/comm/text', { user_id: userId, content })
}

function commVoice(userId, durationSec, content) {
  return postQs('/api/v1/comm/voice', { user_id: userId, duration_sec: durationSec, content })
}

function commHistory(userId, page = 1, pageSize = 20) {
  return get('/api/v1/comm/history', { user_id: userId, page, page_size: pageSize })
}

function createGreeting(userId, content, cronExpr, greetingId) {
  return postQs('/api/v1/comm/greeting/schedule', { user_id: userId, content, cron_expr: cronExpr, greeting_id: greetingId })
}

function listGreetings(userId) {
  return get('/api/v1/comm/greeting/schedule', { user_id: userId })
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
  login, refreshToken, logout, bindPhone, getMyInfo, grantSubscribe,
  // media
  uploadImageUrl, enhanceImage, uploadVoiceUrl,
  // memory
  listMemory, createMemory, getMemory, updateMemory, deleteMemory, setImportance, searchMemory,
  // qa
  qaHistory, qaDetail,
  // reminder
  listMedications, createMedication, updateMedication, deleteMedication,
  // child
  bindElderly, unbindElderly, getBindedUsers, getDashboard, getChildMessages,
  getChildSettings, updateChildSettings, getSettingsChanges,
  // comm
  commText, commVoice, commHistory, createGreeting, listGreetings,
  // system
  healthCheck
}
