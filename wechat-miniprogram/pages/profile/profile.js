const app = getApp()

Page({
  data: {
    nickname: '',
    userId: '',
    token: '',
    tokenVisible: false,
    tokenType: ''
  },

  onLoad() {
    this.loadUserInfo()
  },

  loadUserInfo() {
    const nickname = app.getNickname() || '老人'
    const userId = app.getUserId() || ''
    const token = app.getToken() || ''
    const tokenType = token ? 'JWT Token' : '无token'
    this.setData({ nickname, userId, token, tokenType })
  },

  toggleTokenVisibility() {
    this.setData({ tokenVisible: !this.data.tokenVisible })
  },

  copyToken() {
    const token = this.data.token
    if (!token) {
      wx.showToast({ title: '暂无token', icon: 'none' })
      return
    }
    
    wx.setClipboardData({
      data: token,
      success: () => {
        wx.showToast({ title: '复制成功', icon: 'success' })
      },
      fail: () => {
        wx.showToast({ title: '复制失败', icon: 'none' })
      }
    })
  },

  handleLogout() {
    wx.showModal({
      title: '退出登录',
      content: '确定要退出登录吗？退出后需要重新登录才能使用',
      confirmText: '退出',
      cancelText: '取消',
      success: (res) => {
        if (res.confirm) {
          app.setToken('')
          wx.setStorageSync('refresh_token', '')
          wx.setStorageSync('user_id', '')
          wx.setStorageSync('nickname', '')
          wx.setStorageSync('is_registered', '')
          
          wx.showToast({ title: '已退出登录', icon: 'success' })
          
          setTimeout(() => {
            wx.reLaunch({
              url: '/pages/register/register'
            })
          }, 1500)
        }
      }
    })
  },

  goBack() {
    wx.navigateBack()
  }
})