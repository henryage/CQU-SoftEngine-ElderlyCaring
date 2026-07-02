const { getBindedUsers, qaHistory, getChildMessages } = require('../../../utils/api')
const app = getApp()

Page({
  data: {
    bindedUsers: [],
    selectedUserId: null,
    selectedNickname: '',
    records: [],
    loading: false,
    keyword: '',
    page: 1,
    pageSize: 20,
    total: 0,
    hasMore: false
  },

  onShow() {
    this.loadBindedUsers()
  },

  async loadBindedUsers() {
    try {
      const users = await getBindedUsers()
      this.setData({
        bindedUsers: users || [],
        records: [],
        selectedUserId: null,
        selectedNickname: '',
        page: 1
      })
    } catch (err) {
      console.error('加载绑定列表失败:', err)
    }
  },

  onElderSelect(e) {
    const idx = e.detail.value
    const user = this.data.bindedUsers[idx]
    if (user) {
      this.setData({ selectedUserId: user.user_id, selectedNickname: user.nickname, records: [], page: 1 })
      this.loadRecords()
    }
  },

  onKeywordInput(e) { this.setData({ keyword: e.detail.value }) },

  async loadRecords() {
    if (!this.data.selectedUserId) return
    this.setData({ loading: true })
    try {
      const params = {
        user_id: this.data.selectedUserId,
        page: this.data.page,
        page_size: this.data.pageSize
      }
      if (this.data.keyword) params.keyword = this.data.keyword

      // 使用 child/messages 接口，数据更完整
      const res = await getChildMessages(this.data.selectedUserId, params)
      const items = res.items || res || []
      const total = res.total || items.length
      this.setData({
        records: this.data.page === 1 ? items : [...this.data.records, ...items],
        total: total,
        hasMore: this.data.page * this.data.pageSize < total
      })
    } catch (err) {
      console.error('加载问答记录失败:', err)
    } finally {
      this.setData({ loading: false })
    }
  },

  onSearch() {
    this.setData({ page: 1, records: [] })
    this.loadRecords()
  },

  loadMore() {
    if (!this.data.hasMore || this.data.loading) return
    this.setData({ page: this.data.page + 1 })
    this.loadRecords()
  },

})
