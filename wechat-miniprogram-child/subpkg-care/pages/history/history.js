Page({
  data: { records: [], loading: false, keyword: '', page: 1 },

  onShow() {
    this.setData({ records: [], loading: false, page: 1 })
  },

  onSearch() {
    wx.showToast({ title: '后端尚未实现问答记录接口', icon: 'none', duration: 2000 })
  },

  goBack() { wx.switchTab({ url: '/pages/index/index' }) },
  goToMessage() { wx.navigateTo({ url: '/subpkg-care/pages/message/message' }) }
})
