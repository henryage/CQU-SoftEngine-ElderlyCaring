const { api } = require('./utils/api')

App({
  onLaunch() {
    this.initGlobalData()
    this.checkRegistration()
  },

  onShow() {
    if (this.getToken()) {
      this.startHeartbeat()
    }
  },

  onHide() {
    this.stopHeartbeat()
  },

  initGlobalData() {
    this.globalData = {
      token: '',
      refreshToken: '',
      userId: null,
      nickname: '',
      userType: '',
      sessionId: null,
      isRegistered: false
    }

    const savedToken = wx.getStorageSync('token')
    const savedRefreshToken = wx.getStorageSync('refresh_token')
    const savedUserId = wx.getStorageSync('user_id')
    const savedNickname = wx.getStorageSync('nickname')
    const isRegistered = wx.getStorageSync('is_registered')

    if (savedToken) this.globalData.token = savedToken
    if (savedRefreshToken) this.globalData.refreshToken = savedRefreshToken
    if (savedUserId) this.globalData.userId = savedUserId
    if (savedNickname) this.globalData.nickname = savedNickname
    if (isRegistered === 'true') this.globalData.isRegistered = true
  },

  checkRegistration() {
    const isRegistered = wx.getStorageSync('is_registered')
    
    if (isRegistered === 'true') {
      this.autoLogin()
    }
  },

  async autoLogin() {
    try {
      const loginRes = await new Promise((resolve, reject) => {
        wx.login({
          success: resolve,
          fail: reject
        })
      })

      const data = await api.login(loginRes.code, 'user')

      this.globalData.token = data.token
      this.globalData.refreshToken = data.refresh_token
      this.globalData.userId = data.ref_id
      this.globalData.nickname = data.nickname
      this.globalData.userType = data.user_type

      wx.setStorageSync('token', data.token)
      wx.setStorageSync('refresh_token', data.refresh_token)
      wx.setStorageSync('user_id', data.ref_id)
      wx.setStorageSync('nickname', data.nickname)

    } catch (err) {
      console.error('自动登录失败:', err)
    }
  },

  setRegistered() {
    this.globalData.isRegistered = true
    wx.setStorageSync('is_registered', 'true')
  },

  isRegistered() {
    return this.globalData.isRegistered
  },

  getToken() {
    return this.globalData.token
  },

  setToken(token) {
    this.globalData.token = token
    wx.setStorageSync('token', token)
  },

  getUserId() {
    return this.globalData.userId
  },

  getNickname() {
    return this.globalData.nickname
  },

  getSessionId() {
    return this.globalData.sessionId
  },

  setSessionId(sessionId) {
    this.globalData.sessionId = sessionId
  },

  heartbeatTimer: null,

  startHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
    }

    const sendHeartbeat = async () => {
      try {
        await api.heartbeat()
      } catch (err) {
        console.error('心跳失败:', err)
      }
    }

    sendHeartbeat()
    this.heartbeatTimer = setInterval(sendHeartbeat, 30000)
  },

  stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  },

  globalData: {}
})