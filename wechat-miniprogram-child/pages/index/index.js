const app = getApp()

Page({
  data: {
    loading: false,
    childId: ''
  },

  onShow() {
    this.setData({ childId: app.getChildId() || '' })
  },

  // 导航到各功能页
  goToBind()       { wx.navigateTo({ url: '/subpkg-manage/pages/bind/bind' }) },
  goToHealth()     { wx.navigateTo({ url: '/subpkg-health/pages/health/health' }) },
  goToMedication() { wx.navigateTo({ url: '/subpkg-health/pages/medication/medication' }) },
  goToTrace()      { wx.navigateTo({ url: '/subpkg-health/pages/trace/trace' }) },
  goToHistory()    { wx.navigateTo({ url: '/subpkg-care/pages/history/history' }) },
  goToMessage()    { wx.navigateTo({ url: '/subpkg-care/pages/message/message' }) },
  goToGreeting()   { wx.navigateTo({ url: '/subpkg-care/pages/greeting/greeting' }) },
  goToSettings()   { wx.navigateTo({ url: '/subpkg-manage/pages/settings/settings' }) },
  goToKnowledge()  { wx.navigateTo({ url: '/subpkg-manage/pages/knowledge/knowledge' }) }
})
