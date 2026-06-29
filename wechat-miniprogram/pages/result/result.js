const { api } = require('../../utils/api')

Page({
  data: {
    historyList: [],
    keyword: '',
    page: 1,
    pageSize: 20,
    total: 0
  },

  onLoad() {
    this.loadHistory()
  },

  onShow() {
    this.loadHistory()
  },

  async loadHistory() {
    wx.showLoading({ title: '加载中...' })
    
    try {
      const data = await api.getHistory({
        page: this.data.page,
        page_size: this.data.pageSize,
        keyword: this.data.keyword
      })
      
      this.setData({
        historyList: data.items,
        total: data.total,
        page: data.page
      })
    } catch (err) {
      console.error('加载历史记录失败:', err)
      wx.showToast({ title: err.msg || '加载失败', icon: 'none' })
    } finally {
      wx.hideLoading()
    }
  },

  onKeywordInput(e) {
    this.setData({ keyword: e.detail.value })
  },

  searchHistory() {
    this.setData({ page: 1 })
    this.loadHistory()
  },

  formatTime(dateStr) {
    if (!dateStr) return ''
    try {
      const date = new Date(dateStr)
      const month = (date.getMonth() + 1).toString().padStart(2, '0')
      const day = date.getDate().toString().padStart(2, '0')
      const hour = date.getHours().toString().padStart(2, '0')
      const minute = date.getMinutes().toString().padStart(2, '0')
      return `${month}-${day} ${hour}:${minute}`
    } catch {
      return dateStr
    }
  },

  goBack() {
    wx.navigateBack({ delta: 1 })
  }
})