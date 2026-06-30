Page({
  data: { settings: {}, changes: [], loading: false },

  onShow() {
    this.setData({ settings: {}, changes: [], loading: false })
  },

  onToggle() {
    wx.showToast({ title: '后端尚未实现远程配置接口', icon: 'none', duration: 2000 })
  },

  doSave() {
    wx.showToast({ title: '后端尚未实现远程配置接口', icon: 'none', duration: 2000 })
  },

  goBack() { wx.switchTab({ url: '/pages/index/index' }) },
  goToKnowledge() { wx.navigateTo({ url: '/subpkg-manage/pages/knowledge/knowledge' }) }
})
