const app = getApp()

Page({
  data: {
    isBound: false,
    alerts: []
  },

  onShow() {
    this.setData({
      isBound: !!app.getBoundElderlyId()
    })
  },

  // 预警功能暂未实现
  onPullDownRefresh() {
    wx.stopPullDownRefresh()
  }
})
