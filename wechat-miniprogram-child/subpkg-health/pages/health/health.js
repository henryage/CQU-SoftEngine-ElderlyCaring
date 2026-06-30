Page({
  data: { loading: false, dashboard: null },

  onShow() {
    this.setData({ dashboard: null, loading: false })
  },

  goBack() { wx.switchTab({ url: '/pages/index/index' }) },
  goToAlerts() { wx.switchTab({ url: '/pages/alert/alert' }) },
  goToMedication() { wx.navigateTo({ url: '/subpkg-health/pages/medication/medication' }) }
})
