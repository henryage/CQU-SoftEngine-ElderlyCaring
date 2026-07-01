const app = getApp()

Page({
  data: {
    loading: false,
    childId: ''
  },

  onShow() {
    this.setData({ childId: app.getChildId() || '' })
  },

  // 导航到各功能页（需登录）
  goToBind()       { app.requireLogin(() => wx.navigateTo({ url: '/subpkg-manage/pages/bind/bind' })) },
  goToHealth()     { app.requireLogin(() => wx.navigateTo({ url: '/subpkg-health/pages/health/health' })) },
  goToMedication() { app.requireLogin(() => wx.navigateTo({ url: '/subpkg-health/pages/medication/medication' })) },
  goToTrace()      { app.requireLogin(() => wx.navigateTo({ url: '/subpkg-health/pages/trace/trace' })) },
  goToHistory()    { app.requireLogin(() => wx.navigateTo({ url: '/subpkg-care/pages/history/history' })) },
  goToMessage()    { app.requireLogin(() => wx.navigateTo({ url: '/subpkg-care/pages/message/message' })) },
  goToGreeting()   { app.requireLogin(() => wx.navigateTo({ url: '/subpkg-care/pages/greeting/greeting' })) },
  goToSettings()   { app.requireLogin(() => wx.navigateTo({ url: '/subpkg-manage/pages/settings/settings' })) },
  goToKnowledge()  { app.requireLogin(() => wx.navigateTo({ url: '/subpkg-manage/pages/knowledge/knowledge' })) }
})
