Page({
  data: { traces: null },

  onShow() { this.setData({ traces: null }) },

  goBack() { wx.switchTab({ url: '/pages/index/index' }) },
  goToMedication() { wx.navigateTo({ url: '/subpkg-health/pages/medication/medication' }) }
})
