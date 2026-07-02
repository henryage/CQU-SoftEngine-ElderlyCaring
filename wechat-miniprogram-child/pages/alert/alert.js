const { getBindedUsers } = require('../../utils/api')
const app = getApp()

Page({
  data: {
    loading: false,
    bindedUsers: []
  },

  onShow() {
    this.loadAlerts()
  },

  async loadAlerts() {
    this.setData({ loading: true })
    try {
      const users = await getBindedUsers()
      this.setData({ bindedUsers: users || [] })
    } catch (err) {
      console.error('加载预警信息失败:', err)
    } finally {
      this.setData({ loading: false })
    }
  },

  doHandle(e) {
    const userId = e.currentTarget.dataset.uid
    const alertCount = e.currentTarget.dataset.count
    wx.showToast({
      title: `老人${userId}有${alertCount}条待处理预警`,
      icon: 'none',
      duration: 2000
    })
  },

  goToIndex() { wx.switchTab({ url: '/pages/index/index' }) },
  goToProfile() { wx.switchTab({ url: '/pages/profile/profile' }) }
})
