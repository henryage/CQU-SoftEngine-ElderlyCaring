const app = getApp()
const { api } = require('../../utils/api')

Page({
  data: {},

  async handleLogin() {
    wx.showLoading({ title: '登录中...' })

    try {
      const loginRes = await new Promise((resolve, reject) => {
        wx.login({
          success: resolve,
          fail: reject
        })
      })

      const data = await api.login(loginRes.code, 'user')

      app.setToken(data.token)
      wx.setStorageSync('refresh_token', data.refresh_token)
      wx.setStorageSync('user_id', data.ref_id)
      wx.setStorageSync('nickname', data.nickname)
      app.setRegistered()

      wx.hideLoading()
      wx.showToast({ title: '登录成功', icon: 'success' })

      setTimeout(() => {
        wx.redirectTo({
          url: '/pages/index/index'
        })
      }, 1500)

    } catch (err) {
      wx.hideLoading()
      console.error('登录失败:', err)
      wx.showModal({
        title: '登录失败',
        content: err.msg || `无法连接后端服务\n请确认：\n1. 手机与后端在同一WiFi\n2. 后端地址可访问`,
        showCancel: false
      })
    }
  },

  async handleSkipLogin() {
    wx.showLoading({ title: '登录中...' })
    
    try {
      await app.skipLogin()
      
      wx.hideLoading()
      wx.showToast({ title: '登录成功', icon: 'success' })
      
      setTimeout(() => {
        wx.redirectTo({
          url: '/pages/index/index'
        })
      }, 1500)
      
    } catch (err) {
      wx.hideLoading()
      console.error('跳过登录失败:', err)
      wx.showModal({
        title: '登录失败',
        content: err.msg || `无法连接后端服务\n请确认：\n1. 手机与后端在同一WiFi\n2. 后端地址可访问`,
        showCancel: false
      })
    }
  },

  handleDebug() {
    wx.showLoading({ title: '测试中...' })
    
    const startTime = Date.now()
    wx.request({
      url: 'http://10.128.229.199:8090/api/v1/auth/heartbeat',
      method: 'POST',
      enableHttp2: false,
      enableQuic: false,
      timeout: 15000,
      header: { 'Content-Type': 'application/json' },
      success: (res) => {
        const elapsed = Date.now() - startTime
        wx.hideLoading()
        wx.showModal({
          title: '网络诊断结果',
          content: `状态码: ${res.statusCode}\n耗时: ${elapsed}ms\n\nwx.request 调用成功，网络连接正常。\n请尝试点击"微信一键登录"。`,
          showCancel: false
        })
      },
      fail: (err) => {
        const elapsed = Date.now() - startTime
        wx.hideLoading()
        const errDetail = JSON.stringify(err)
        wx.showModal({
          title: '网络诊断失败',
          content: `耗时: ${elapsed}ms\n错误: ${err.errMsg || '无详细信息'}\n详情: ${errDetail}`,
          showCancel: false
        })
      }
    })
  }
})