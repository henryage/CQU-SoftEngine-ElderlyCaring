Page({
  data: { dashboard: null },

  onShow() { this.setData({ dashboard: null }) },

  goBack() { wx.switchTab({ url: '/pages/index/index' }) },
  goToGreeting() { wx.navigateTo({ url: '/subpkg-care/pages/greeting/greeting' }) }
})
