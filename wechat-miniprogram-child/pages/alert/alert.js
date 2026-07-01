Page({
  data: { loading: false, alerts: [] },

  onShow() {
    this.setData({ alerts: [], loading: false })
  },

  doHandle() {
    const app = getApp()
    if (!app.isLoggedIn()) {
      wx.showToast({ title: '请先登录', icon: 'none', duration: 1500 })
      setTimeout(() => wx.navigateTo({ url: '/pages/login/login' }), 1500)
      return
    }
    wx.showToast({ title: '后端尚未实现预警列表/处置接口', icon: 'none', duration: 2000 })
  },

  goToIndex() { wx.switchTab({ url: '/pages/index/index' }) },
  goToProfile() { wx.switchTab({ url: '/pages/profile/profile' }) }
})
