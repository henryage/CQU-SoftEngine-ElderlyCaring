Page({
  data: { dashboard: null },

  onShow() { this.setData({ dashboard: null }) },

  goBack() { wx.switchTab({ url: '/pages/index/index' }) },
  goToMessage() { wx.navigateTo({ url: '/subpkg-care/pages/message/message' }) }
})
