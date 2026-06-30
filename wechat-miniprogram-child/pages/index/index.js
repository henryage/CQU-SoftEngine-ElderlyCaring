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
