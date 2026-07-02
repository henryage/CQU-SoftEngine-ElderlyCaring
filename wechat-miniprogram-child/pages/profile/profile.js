const { getMyInfo, bindPhone } = require('../../utils/api')
const app = getApp()

Page({
  data: {
    nickname: '',
    childId: '',
    phone: '',
    bindName: '',
    bindRelation: '子女',
    loading: false
  },

  onShow() {
    this.setData({
      nickname: app.getNickname(),
      childId: app.getChildId()
    })
    this.loadMyInfo()
  },

  async loadMyInfo() {
    try {
      const info = await getMyInfo()
      // getMyInfo 不返回 phone，本地占位
      this.setData({ phone: info.phone || '' })
    } catch (err) {
      console.error('获取个人信息失败:', err)
    }
  },

  onPhoneInput(e) { this.setData({ phone: e.detail.value }) },
  onNameInput(e) { this.setData({ bindName: e.detail.value }) },
  onRelationInput(e) { this.setData({ bindRelation: e.detail.value || '子女' }) },

  async doBindPhone() {
    const phone = this.data.phone.trim()
    if (!phone || phone.length !== 11) {
      wx.showToast({ title: '请输入11位手机号', icon: 'none' })
      return
    }
    this.setData({ loading: true })
    try {
      await bindPhone(phone, this.data.bindName.trim(), this.data.bindRelation.trim())
      wx.showToast({ title: '手机号已绑定', icon: 'success' })
    } catch (err) {
      wx.showToast({ title: err.msg || err.detail || '绑定失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  goToAlerts() {
    wx.switchTab({ url: '/pages/alert/alert' })
  },

  goToBind() {
    wx.navigateTo({ url: '/subpkg-manage/pages/bind/bind' })
  },

  doSwitchAccount() {
    wx.showModal({
      title: '切换账号',
      content: '切换后将清除当前登录信息，需要重新输入子女 ID',
      success: (res) => {
        if (res.confirm) {
          app.doLogout()
        }
      }
    })
  }
})
