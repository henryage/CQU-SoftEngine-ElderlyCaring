Page({
  data: { childId: '' },

  onShow() {
    this.setData({ childId: getApp().getChildId() || '' })
  },

  doBind() {
    wx.showToast({ title: '后端尚未实现绑定接口\n(child.py 路由待开发)', icon: 'none', duration: 3000 })
  },

  goBack() { wx.switchTab({ url: '/pages/index/index' }) },
  goToSettings() { wx.navigateTo({ url: '/subpkg-manage/pages/settings/settings' }) }
})
