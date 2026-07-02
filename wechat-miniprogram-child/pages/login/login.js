const { login } = require('../../utils/api')
const app = getApp()

Page({
  data: {
    childId: '',
    loading: false,
    error: ''
  },

  onIdInput(e) {
    this.setData({ childId: e.detail.value })
  },

  async doLogin() {
    const id = this.data.childId.trim()
    if (!id) {
      wx.showToast({ title: '请输入子女ID', icon: 'none' })
      return
    }
    this.setData({ loading: true, error: '' })

    try {
      // dev模式下code即openid，用childId作为code登录
      const tokenData = await login(id, 'child')
      app.doLogin(tokenData.ref_id, tokenData)
      wx.setStorageSync('login_id', id)
      wx.switchTab({ url: '/pages/index/index' })
    } catch (err) {
      this.setData({
        loading: false,
        error: err.msg || err.detail || '登录失败，请检查后端是否启动'
      })
    }
  }
})
