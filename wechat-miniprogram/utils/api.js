const app = getApp()

const BASE_URL = 'http://127.0.0.1:8090'

const request = (options) => {
  const { url, method = 'GET', data = {}, header = {}, isUpload = false } = options

  return new Promise((resolve, reject) => {
    const token = app.getToken()
    const defaultHeader = {
      ...(token && { 'Authorization': `Bearer ${token}` }),
      ...header
    }

    if (isUpload) {
      wx.uploadFile({
        url: `${BASE_URL}${url}`,
        filePath: data.filePath,
        name: data.name || 'file',
        formData: data.formData || {},
        header: defaultHeader,
        success: (res) => {
          try {
            const result = JSON.parse(res.data)
            if (result.code === 0) {
              resolve(result.data)
            } else {
              reject(result)
            }
          } catch {
            reject({ code: -1, msg: '解析响应失败' })
          }
        },
        fail: (err) => {
          reject({ code: -1, msg: '网络请求失败', err })
        }
      })
    } else {
      wx.request({
        url: `${BASE_URL}${url}`,
        method,
        data,
        header: {
          'Content-Type': 'application/json',
          ...defaultHeader
        },
        success: (res) => {
          const { statusCode, data: responseData } = res
          if (statusCode === 200) {
            if (responseData.code === 0) {
              resolve(responseData.data)
            } else {
              if (responseData.code === 401) {
                app.setToken('')
                wx.showToast({
                  title: '请重新登录',
                  icon: 'none'
                })
              }
              reject(responseData)
            }
          } else if (responseData.detail) {
            reject({ code: statusCode, msg: responseData.detail })
          } else {
            reject({ code: statusCode, msg: '请求失败' })
          }
        },
        fail: (err) => {
          reject({ code: -1, msg: '网络请求失败', err })
        }
      })
    }
  })
}

const get = (url, data = {}) => request({ url, method: 'GET', data })
const post = (url, data = {}) => request({ url, method: 'POST', data })
const upload = (url, data = {}) => request({ url, method: 'POST', data, isUpload: true })

const api = {
  login: (code, userType = 'user') => {
    return post('/api/v1/auth/wx-login', { code, user_type: userType })
  },

  heartbeat: () => {
    return post('/api/v1/auth/heartbeat')
  },

  uploadImage: (filePath) => {
    return upload('/api/v1/media/upload/image', { filePath })
  },

  uploadVoice: (filePath) => {
    return upload('/api/v1/media/upload/voice', { filePath })
  },

  ask: (inputType, text, mediaUrl = null, sessionId = null) => {
    const data = { input_type: inputType, text }
    if (mediaUrl) data.media_url = mediaUrl
    if (sessionId) data.session_id = sessionId
    return post('/api/v1/qa/ask', data)
  },

  getHistory: (params = {}) => {
    return get('/api/v1/qa/history', params)
  },

  emergencyCall: () => {
    return post('/api/v1/alert/emergency/call')
  },

  sendToChild: (message) => {
    return post('/api/v1/child/send-message', { message })
  },

  getMedicationReminder: () => {
    return get('/api/v1/reminder/medication')
  }
}

module.exports = {
  request,
  get,
  post,
  upload,
  api,
  BASE_URL
}