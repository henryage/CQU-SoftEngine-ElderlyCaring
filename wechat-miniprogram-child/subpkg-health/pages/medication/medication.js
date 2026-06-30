const app = getApp()

Page({
  data: {
    isBound: false
  },

  onShow() {
    this.setData({
      isBound: !!app.getBoundElderlyId()
    })
  }
})
