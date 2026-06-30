const { api } = require('./utils/api')

App({
  onLaunch() {
    this.initGlobalData()
    // 跳过登录检查，直接进入首页
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
      nickname: '子女用户',
      userType: 'child',
      sessionId: null,
      boundElderlyId: null,
      boundElderlyName: ''
    }

    const savedToken = wx.getStorageSync('token')
    const savedRefreshToken = wx.getStorageSync('refresh_token')
    const savedUserId = wx.getStorageSync('user_id')
    const savedNickname = wx.getStorageSync('nickname')
    const boundElderlyId = wx.getStorageSync('bound_elderly_id')
    const boundElderlyName = wx.getStorageSync('bound_elderly_name')

    if (savedToken) this.globalData.token = savedToken
    if (savedRefreshToken) this.globalData.refreshToken = savedRefreshToken
    if (savedUserId) this.globalData.userId = savedUserId
    if (savedNickname) this.globalData.nickname = savedNickname
    if (boundElderlyId) this.globalData.boundElderlyId = boundElderlyId
    if (boundElderlyName) this.globalData.boundElderlyName = boundElderlyName
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

  getBoundElderlyId() {
    return this.globalData.boundElderlyId
  },

  setBoundElderlyId(elderlyId) {
    this.globalData.boundElderlyId = elderlyId
    wx.setStorageSync('bound_elderly_id', elderlyId)
  },

  getBoundElderlyName() {
    return this.globalData.boundElderlyName
  },

  setBoundElderlyName(name) {
    this.globalData.boundElderlyName = name
    wx.setStorageSync('bound_elderly_name', name)
  },

  heartbeatTimer: null,

  startHeartbeat() {
    if (this.heartbeatTimer) clearInterval(this.heartbeatTimer)
    const sendHeartbeat = async () => {
      try { await api.heartbeat() } catch (err) { console.error('心跳失败:', err) }
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
