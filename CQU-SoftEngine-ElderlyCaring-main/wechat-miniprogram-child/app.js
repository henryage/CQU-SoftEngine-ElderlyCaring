const { login, healthCheck } = require('./utils/api')

App({
  onLaunch() {
    this.initGlobalData()
    this.checkLogin()
  },

  initGlobalData() {
    this.globalData = {
      token: '',
      refreshToken: '',
      childId: null,
      nickname: '子女用户',
      userType: 'child',
      currentElderly: null
    }

    this.globalData.token = wx.getStorageSync('token') || ''
    this.globalData.refreshToken = wx.getStorageSync('refresh_token') || ''
    this.globalData.childId = wx.getStorageSync('child_id') || null
    this.globalData.nickname = wx.getStorageSync('nickname') || '子女用户'
  },

  checkLogin() {
    if (!this.globalData.childId) {
      wx.reLaunch({ url: '/pages/login/login' })
      return
    }
    // 后台静默续 token
    this.silentRefreshToken()
  },

  async silentRefreshToken() {
    if (!this.globalData.refreshToken) return
    try {
      const { refreshToken } = require('./utils/api')
      const data = await refreshToken(this.globalData.refreshToken)
      if (data && data.token) {
        this.globalData.token = data.token
        wx.setStorageSync('token', data.token)
      }
    } catch (e) {
      // 刷新失败：尝试重新 wx-login
      try {
        const codeResp = await new Promise((resolve, reject) => {
          wx.login({ success: resolve, fail: reject })
        })
        const data = await login(codeResp.code, 'child')
        if (data && data.token) {
          this.globalData.token = data.token
          this.globalData.refreshToken = data.refresh_token
          wx.setStorageSync('token', data.token)
          wx.setStorageSync('refresh_token', data.refresh_token)
        }
      } catch (e2) { /* 静默失败 */ }
    }
  },

  doLogin(refId, tokenData = {}) {
    this.globalData.childId = refId
    this.globalData.token = tokenData.token || ''
    this.globalData.refreshToken = tokenData.refresh_token || ''
    this.globalData.nickname = tokenData.nickname || ('子女' + refId)

    wx.setStorageSync('child_id', refId)
    wx.setStorageSync('token', tokenData.token || '')
    wx.setStorageSync('refresh_token', tokenData.refresh_token || '')
    wx.setStorageSync('nickname', tokenData.nickname || ('子女' + refId))
  },

  doLogout() {
    this.globalData.token = ''
    this.globalData.refreshToken = ''
    this.globalData.childId = null
    this.globalData.nickname = '子女用户'
    this.globalData.currentElderly = null

    wx.setStorageSync('token', '')
    wx.setStorageSync('refresh_token', '')
    wx.setStorageSync('child_id', '')
    wx.setStorageSync('nickname', '')

    wx.reLaunch({ url: '/pages/login/login' })
  },

  getToken() { return this.globalData.token },
  getChildId() { return this.globalData.childId },
  getNickname() { return this.globalData.nickname },
  getCurrentElderly() { return this.globalData.currentElderly },
  setCurrentElderly(u) { this.globalData.currentElderly = u },

  globalData: {}
})
