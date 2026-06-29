const app = getApp()
const { api } = require('../../utils/api')

Page({
  data: {
    currentStep: 1,
    userName: '',
    phone: '',
    password: '',
    confirmPassword: '',
    childName: '',
    childPhone: '',
    relation: '子女'
  },

  onUserNameInput(e) {
    this.setData({ userName: e.detail.value })
  },

  onPhoneInput(e) {
    this.setData({ phone: e.detail.value })
  },

  onPasswordInput(e) {
    this.setData({ password: e.detail.value })
  },

  onConfirmPasswordInput(e) {
    this.setData({ confirmPassword: e.detail.value })
  },

  onChildNameInput(e) {
    this.setData({ childName: e.detail.value })
  },

  onChildPhoneInput(e) {
    this.setData({ childPhone: e.detail.value })
  },

  selectRelation(e) {
    this.setData({ relation: e.currentTarget.dataset.value })
  },

  nextStep() {
    const { userName, phone, password, confirmPassword } = this.data

    if (!userName) {
      wx.showToast({ title: '请输入老人姓名', icon: 'none' })
      return
    }
    if (!phone || phone.length !== 11) {
      wx.showToast({ title: '请输入正确的手机号', icon: 'none' })
      return
    }
    if (!password || password.length < 6) {
      wx.showToast({ title: '密码至少6位', icon: 'none' })
      return
    }
    if (password !== confirmPassword) {
      wx.showToast({ title: '两次密码不一致', icon: 'none' })
      return
    }

    this.setData({ currentStep: 2 })
  },

  prevStep() {
    this.setData({ currentStep: 1 })
  },

  async submitRegister() {
    const { childName, childPhone, relation } = this.data

    if (!childName) {
      wx.showToast({ title: '请输入子女姓名', icon: 'none' })
      return
    }
    if (!childPhone || childPhone.length !== 11) {
      wx.showToast({ title: '请输入正确的子女手机号', icon: 'none' })
      return
    }

    wx.showLoading({ title: '注册中...' })

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
      wx.showToast({ title: '注册成功', icon: 'success' })

      setTimeout(() => {
        wx.switchTab({
          url: '/pages/index/index'
        })
      }, 1500)

    } catch (err) {
      wx.hideLoading()
      console.error('注册失败:', err)
      wx.showToast({ title: err.msg || '注册失败', icon: 'none' })
    }
  }
})