const app = getApp()

Page({
  data: {
    nickname: '子女用户',
    isBound: false,
    boundElderlyName: ''
  },

  onShow() {
    this.loadProfile()
  },

  loadProfile() {
    const nickname = app.getNickname() || '子女用户'
    const elderlyId = app.getBoundElderlyId()
    const elderlyName = app.getBoundElderlyName() || ''
    this.setData({
      nickname: nickname,
      isBound: !!elderlyId,
      boundElderlyName: elderlyName
    })
  },

  goToBind() {
    wx.navigateTo({ url: '/pages/bind/bind' })
  },

  noop() {
    // 功能暂未实现
  },

  logout() {
    wx.showModal({
      title: '退出登录',
      content: '确定要退出登录吗？',
      success: (res) => {
        if (res.confirm) {
          wx.clearStorageSync()
          app.globalData = {}
          wx.reLaunch({ url: '/pages/index/index' })
        }
      }
    })
  }
})
