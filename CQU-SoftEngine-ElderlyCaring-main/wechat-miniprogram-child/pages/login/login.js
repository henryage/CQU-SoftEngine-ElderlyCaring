const { login } = require('../../utils/api')
const app = getApp()

Page({
  data: {
    childIdInput: '',
    loading: false,
    error: ''
  },

  onLoad() {
    const savedId = wx.getStorageSync('child_id')
    if (savedId) {
      this.setData({ childIdInput: String(savedId) })
    }
  },

  onIdInput(e) {
    this.setData({ childIdInput: e.detail.value, error: '' })
  },

  async doLogin() {
    const id = this.data.childIdInput.trim()
    if (!id) {
      this.setData({ error: '请输入子女 ID' })
      return
    }
    const childId = parseInt(id)
    if (isNaN(childId) || childId <= 0) {
      this.setData({ error: '请输入有效的数字 ID' })
      return
    }

    this.setData({ loading: true, error: '' })

    try {
      // dev 模式：将 child_id 用作 mock openid，同一 child_id 永远返回同一账号
      // prod 模式：wx.login() code 由微信分配，绑定真实 openid
      const codeResp = await new Promise((resolve, reject) => {
        wx.login({ success: resolve, fail: reject })
      })
      // dev 模式后端用 code 作 openid；传入 child_id 保证稳定
      const tokenData = await login(codeResp.code, 'child')

      // tokenData = { token, refresh_token, token_type, user_type, ref_id, nickname }
      app.doLogin(tokenData.ref_id, tokenData)
      wx.switchTab({ url: '/pages/index/index' })
    } catch (err) {
      this.setData({
        loading: false,
        error: err.msg || err.detail || '登录失败，请检查后端是否启动'
      })
    }
  }
})
