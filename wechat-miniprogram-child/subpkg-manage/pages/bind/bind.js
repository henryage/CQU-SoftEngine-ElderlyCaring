const app = getApp()

Page({
  data: {
    bindCode: ''
  },

  onLoad() {
    const elderlyId = app.getBoundElderlyId()
    if (elderlyId) {
      // 已绑定状态
    }
  }
})
