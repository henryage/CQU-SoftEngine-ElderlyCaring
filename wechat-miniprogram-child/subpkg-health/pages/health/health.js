const { getBindedUsers, getDashboard } = require('../../../utils/api')
const app = getApp()

Page({
  data: {
    bindedUsers: [],
    selectedUserId: null,
    selectedNickname: '',
    dashboard: null,
    loading: false
  },

  onShow() {
    this.loadBindedUsers()
  },

  async loadBindedUsers() {
    try {
      const users = await getBindedUsers()
      this.setData({
        bindedUsers: users || [],
        dashboard: null,
        selectedUserId: null,
        selectedNickname: ''
      })
    } catch (err) {
      console.error('加载绑定列表失败:', err)
    }
  },

  onElderSelect(e) {
    const idx = e.detail.value
    const user = this.data.bindedUsers[idx]
    if (user) {
      this.setData({ selectedUserId: user.user_id, selectedNickname: user.nickname })
      this.loadDashboard(user.user_id)
    }
  },

  async loadDashboard(userId) {
    this.setData({ loading: true, dashboard: null })
    try {
      const d = await getDashboard(userId)
      this.setData({ dashboard: d })
    } catch (err) {
      console.error('加载看板失败:', err)
      wx.showToast({ title: err.msg || err.detail || '加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

})
