const { getBindedUsers, commText, commHistory } = require('../../../utils/api')

Page({
  data: {
    bindedUsers: [],
    selectedUserId: null,
    selectedNickname: '',
    msgContent: '',
    sending: false,
    sentMsg: '',
    history: [],
    historyLoading: false
  },

  onShow() {
    this.loadBindedUsers()
  },

  async loadBindedUsers() {
    try {
      const users = await getBindedUsers()
      this.setData({ bindedUsers: users || [], selectedUserId: null, selectedNickname: '', msgContent: '', sentMsg: '', history: [] })
    } catch (err) {
      console.error('加载绑定列表失败:', err)
    }
  },

  onElderSelect(e) {
    const idx = e.detail.value
    const user = this.data.bindedUsers[idx]
    if (user) {
      this.setData({ selectedUserId: user.user_id, selectedNickname: user.nickname, sentMsg: '', history: [] })
      this.loadHistory()
    }
  },

  onMsgInput(e) { this.setData({ msgContent: e.detail.value }) },

  async doSend() {
    const { selectedUserId, msgContent } = this.data
    if (!selectedUserId) { wx.showToast({ title: '请先选择老人', icon: 'none' }); return }
    if (!msgContent.trim()) { wx.showToast({ title: '请输入留言内容', icon: 'none' }); return }

    this.setData({ sending: true })
    try {
      await commText(selectedUserId, msgContent.trim())
      wx.showToast({ title: '留言已发送', icon: 'success' })
      this.setData({ sentMsg: msgContent.trim(), msgContent: '' })
      this.loadHistory()
    } catch (err) {
      wx.showToast({ title: err.msg || err.detail || '发送失败', icon: 'none' })
    } finally {
      this.setData({ sending: false })
    }
  },

  async loadHistory() {
    if (!this.data.selectedUserId) return
    this.setData({ historyLoading: true })
    try {
      const res = await commHistory(this.data.selectedUserId, 1, 30)
      this.setData({ history: res.items || [] })
    } catch (err) {
      console.error('加载通信历史失败:', err)
    } finally {
      this.setData({ historyLoading: false })
    }
  }

})
