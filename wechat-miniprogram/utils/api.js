const USE_MOCK = false
const BASE_URL = 'http://10.242.5.159:8090'

let isRefreshing = false
let refreshQueue = []

const mockDelay = (data, ms = 300) => new Promise(resolve => setTimeout(() => resolve(data), ms))

const mockData = {
  login: () => ({
    token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidHlwZSI6InVzZXIiLCJleHAiOjk5OTk5OTk5OTl9.mock',
    refresh_token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh_mock',
    token_type: 'Bearer',
    user_type: 'user',
    ref_id: 1,
    nickname: '老人1'
  }),
  heartbeat: () => ({ heartbeat_at: new Date().toISOString(), online_status: 'online' }),
  uploadImage: () => ({ media_id: 'img_mock', url: '/files/img_mock.jpg', enhanced_url: '/files/img_mock_enhanced.jpg', filename: 'photo.jpg', size: 102400, width: 1920, height: 1080, operations: ['gamma_1.3'], uploaded_at: new Date().toISOString() }),
  uploadVoice: () => ({ media_id: 'voice_mock', url: '/files/voice_mock.wav', filename: 'recording.wav', size: 204800, asr_text: '我今天头疼该吃什么药', uploaded_at: new Date().toISOString() }),
  ask: () => ({ msg_id: 1, session_id: 'sess_mock', answer: '这是模拟回答，实际使用时需要连接后端服务。', intercepted: false, risk_tags: [], latency_ms: 500, cat_action: 'speak', alert_signal: null }),
  getHistory: () => ({ total: 0, page: 1, page_size: 20, items: [] }),
  emergencyCall: () => ({ alert_id: 1, alert_time: new Date().toISOString() }),
  getMedicationReminder: () => []
}

const api = {
  login: (code, userType = 'user') => {
    if (USE_MOCK) return mockDelay(mockData.login())
    return post('/api/v1/auth/wx-login', { code, user_type: userType })
  },
  heartbeat: () => {
    if (USE_MOCK) return mockDelay(mockData.heartbeat())
    return post('/api/v1/auth/heartbeat')
  },
  uploadImage: (filePath) => {
    if (USE_MOCK) return mockDelay(mockData.uploadImage())
    return upload('/api/v1/media/upload/image', { filePath })
  },
  uploadVoice: (filePath) => {
    if (USE_MOCK) return mockDelay(mockData.uploadVoice())
    return upload('/api/v1/media/upload/voice', { filePath })
  },
  ask: (inputType, text, mediaUrl = null, sessionId = null) => {
    if (USE_MOCK) return mockDelay(mockData.ask())
    const data = { input_type: inputType, text }
    if (mediaUrl) data.media_url = mediaUrl
    if (sessionId) data.session_id = sessionId
    return post('/api/v1/qa/ask', data)
  },
  getHistory: (params = {}) => {
    if (USE_MOCK) return mockDelay(mockData.getHistory())
    return get('/api/v1/qa/history', params)
  },
  emergencyCall: () => {
    if (USE_MOCK) return mockDelay(mockData.emergencyCall())
    return post('/api/v1/alert/emergency/call')
  },
  getMedicationReminder: () => {
    if (USE_MOCK) return mockDelay(mockData.getMedicationReminder())
    return get('/api/v1/reminder/medication')
  }
}

const refreshToken = async () => {
  if (USE_MOCK) return mockData.login().token
  const refreshToken = wx.getStorageSync('refresh_token')
  if (!refreshToken) return null
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${BASE_URL}/api/v1/auth/refresh`,
      method: 'POST',
      data: { refresh_token: refreshToken },
      header: { 'Content-Type': 'application/json' },
      success: (res) => {
        if (res.statusCode === 200 && res.data.code === 0) {
          wx.setStorageSync('token', res.data.data.token)
          if (res.data.data.refresh_token) wx.setStorageSync('refresh_token', res.data.data.refresh_token)
          resolve(res.data.data.token)
        } else { reject(res.data) }
      },
      fail: reject
    })
  })
}

const request = (options) => {
  const { url, method = 'GET', data = {}, header = {}, isUpload = false, _retry = false } = options
  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('token')
    const defaultHeader = { ...(token && { 'Authorization': `Bearer ${token}` }), ...header }
    const handleResponse = (res) => {
      const { statusCode, data: responseData } = res
      if (statusCode === 200) {
        if (responseData.code === 0) { resolve(responseData.data) }
        else if (responseData.code === 401 && !_retry) {
          if (!isRefreshing) {
            isRefreshing = true
            refreshToken().then(newToken => {
              isRefreshing = false; refreshQueue.forEach(cb => cb(newToken)); refreshQueue = []
              if (newToken) { options._retry = true; resolve(request(options)) }
              else { wx.setStorageSync('token', ''); wx.showToast({ title: '请重新登录', icon: 'none' }); reject(responseData) }
            }).catch(() => {
              isRefreshing = false; refreshQueue.forEach(cb => cb(null)); refreshQueue = []
              wx.setStorageSync('token', ''); wx.showToast({ title: '请重新登录', icon: 'none' }); reject(responseData)
            })
          } else { refreshQueue.push(newToken => { if (newToken) { options._retry = true; resolve(request(options)) } else { reject(responseData) } }) }
        } else { reject(responseData) }
      } else { reject({ code: statusCode, msg: responseData.detail || '请求失败' }) }
    }

    if (isUpload) {
      wx.uploadFile({
        url: `${BASE_URL}${url}`, filePath: data.filePath, name: data.name || 'file', formData: data.formData || {}, header: defaultHeader,
        success: (res) => {
          try {
            const result = JSON.parse(res.data)
            if (result.code === 0) resolve(result.data)
            else reject(result)
          } catch { reject({ code: -1, msg: '解析响应失败' }) }
        },
        fail: (err) => reject({ code: -1, msg: '网络请求失败', err })
      })
    } else {
      wx.request({
        url: `${BASE_URL}${url}`, method, data, timeout: 15000,
        header: { 'Content-Type': 'application/json', ...defaultHeader },
        success: handleResponse,
        fail: (err) => reject({ code: -1, msg: '网络请求失败', err })
      })
    }
  })
}

const get = (url, data = {}) => request({ url, method: 'GET', data })
const post = (url, data = {}) => request({ url, method: 'POST', data })
const upload = (url, data = {}) => request({ url, method: 'POST', data, isUpload: true })

module.exports = { request, get, post, upload, api, BASE_URL }