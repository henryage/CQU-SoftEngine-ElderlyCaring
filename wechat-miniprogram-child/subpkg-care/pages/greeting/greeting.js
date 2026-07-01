const { getBindedUsers, listGreetings, createGreeting } = require('../../../utils/api')

Page({
  data: {
    bindedUsers: [],
    selectedUserId: null,
    selectedNickname: '',
    greetings: [],
    greetingContent: '',
    cronExpr: '0 8 * * *',
    editGreetingId: null,
    saving: false
  },

  onShow() {
    this.loadBindedUsers()
  },

  async loadBindedUsers() {
    try {
      const users = await getBindedUsers()
      this.setData({
        bindedUsers: users || [],
        selectedUserId: null,
        selectedNickname: '',
        greetings: [],
        greetingContent: '',
        cronExpr: '0 8 * * *',
        editGreetingId: null
      })
    } catch (err) {
      console.error('加载绑定列表失败:', err)
    }
  },

  onElderSelect(e) {
    const idx = e.detail.value
    const user = this.data.bindedUsers[idx]
    if (user) {
      this.setData({
        selectedUserId: user.user_id,
        selectedNickname: user.nickname,
        greetings: [],
        greetingContent: '',
        cronExpr: '0 8 * * *',
        editGreetingId: null
      })
      this.loadGreetings()
    }
  },

  async loadGreetings() {
    if (!this.data.selectedUserId) return
    try {
      const res = await listGreetings(this.data.selectedUserId)
      this.setData({ greetings: res || [] })
    } catch (err) {
      console.error('加载问候列表失败:', err)
    }
  },

  doEditGreeting(e) {
    const { id, content, cron } = e.currentTarget.dataset
    this.setData({
      editGreetingId: id,
      greetingContent: content || '',
      cronExpr: cron || '0 8 * * *'
    })
  },

  cancelEdit() {
    this.setData({
      editGreetingId: null,
      greetingContent: '',
      cronExpr: '0 8 * * *'
    })
  },

  onGreetingInput(e) { this.setData({ greetingContent: e.detail.value }) },
  onCronInput(e) { this.setData({ cronExpr: e.detail.value }) },

  async doSaveGreeting() {
    const { selectedUserId, greetingContent, cronExpr, editGreetingId } = this.data
    if (!greetingContent.trim()) { wx.showToast({ title: '请输入问候语', icon: 'none' }); return }
    if (!cronExpr.trim()) { wx.showToast({ title: '请输入Cron表达式', icon: 'none' }); return }

    this.setData({ saving: true })
    try {
      await createGreeting(selectedUserId, greetingContent.trim(), cronExpr.trim(), editGreetingId)
      wx.showToast({ title: editGreetingId ? '问候已更新' : '问候已创建', icon: 'success' })
      this.setData({
        editGreetingId: null,
        greetingContent: '',
        cronExpr: '0 8 * * *'
      })
      this.loadGreetings()
    } catch (err) {
      wx.showToast({ title: err.msg || err.detail || '保存失败', icon: 'none' })
    } finally {
      this.setData({ saving: false })
    }
  }

})
