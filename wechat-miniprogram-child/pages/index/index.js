const app = getApp()

Page({
  data: {
    isBound: false,
    boundElderlyName: ''
  },

  onShow() {
    const elderlyId = app.getBoundElderlyId()
    const elderlyName = app.getBoundElderlyName()
    this.setData({
      isBound: !!elderlyId,
      boundElderlyName: elderlyName
    })
  },

  // 功能页面跳转（功能暂未实现）
  goToBind() {
    wx.navigateTo({ url: '/pages/bind/bind' })
  },
  goToHealth() {
    wx.navigateTo({ url: '/pages/health/health' })
  },
  goToMedication() {
    wx.navigateTo({ url: '/pages/medication/medication' })
  },
  goToTrace() {
    wx.navigateTo({ url: '/pages/trace/trace' })
  },
  goToHistory() {
    wx.navigateTo({ url: '/pages/history/history' })
  },
  goToMessage() {
    wx.navigateTo({ url: '/pages/message/message' })
  },
  goToGreeting() {
    wx.navigateTo({ url: '/pages/greeting/greeting' })
  },
  goToSettings() {
    wx.navigateTo({ url: '/pages/settings/settings' })
  },
  goToKnowledge() {
    wx.navigateTo({ url: '/pages/knowledge/knowledge' })
  }
})
