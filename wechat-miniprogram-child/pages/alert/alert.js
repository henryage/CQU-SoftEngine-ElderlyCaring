Page({
  data: { loading: false, alerts: [] },

  onShow() {
    this.setData({ alerts: [], loading: false })
  },

  doHandle() {
    wx.showToast({ title: '后端尚未实现预警列表/处置接口', icon: 'none', duration: 2000 })
  },

  goToIndex() { wx.switchTab({ url: '/pages/index/index' }) },
  goToProfile() { wx.switchTab({ url: '/pages/profile/profile' }) }
})
