const { login } = require('../../utils/api')
const app = getApp()

Page({
  data: {
    loading: false,
    error: ''
  },

  async doWxLogin() {
    this.setData({ loading: true, error: '' })

    try {
      // 调用微信登录获取临时 code
      const codeResp = await new Promise((resolve, reject) => {
        wx.login({ success: resolve, fail: reject })
      })

      // 后端用 code 换 openid，查/建 WxAccount + ChildUser，签发 JWT
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
