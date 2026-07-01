const app = getApp()

Page({
  data: {
    nickname: '',
    childId: ''
  },

  onShow() {
    this.setData({
      nickname: app.getNickname(),
      childId: app.getChildId()
    })
  },

  goToAlerts() {
    wx.switchTab({ url: '/pages/alert/alert' })
  },

  goToBind() {
    app.requireLogin(() => wx.navigateTo({ url: '/subpkg-manage/pages/bind/bind' }))
  },

  doSwitchAccount() {
    wx.showModal({
      title: '切换账号',
      content: '切换后将清除当前登录信息，需要重新输入子女 ID',
      success: (res) => {
        if (res.confirm) {
          app.doLogout()
        }
      }
    })
  }
})
