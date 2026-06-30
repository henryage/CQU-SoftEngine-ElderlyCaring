Page({
  data: { reminders: null },

  onShow() { this.setData({ reminders: null }) },

  goBack() { wx.switchTab({ url: '/pages/index/index' }) },
  goToTrace() { wx.navigateTo({ url: '/subpkg-health/pages/trace/trace' }) }
})
