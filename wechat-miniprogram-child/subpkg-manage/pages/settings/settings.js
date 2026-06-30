const app = getApp()

Page({
  data: {
    isBound: false
  },

  onShow() {
    this.setData({
      isBound: !!app.getBoundElderlyId()
    })
  },

  noop() {
    // 功能暂未实现
  }
})
