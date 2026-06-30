const { listMemory, createMemory, deleteMemory } = require('../../../utils/api')
const app = getApp()

Page({
  data: {
    memories: [],
    loading: false,
    showAdd: false,
    elderlyUserId: '',
    newContent: '',
    newMemoryType: '',
    newImportance: 3
  },

  onShow() {
    this.loadMemories()
  },

  async loadMemories() {
    this.setData({ loading: true })
    try {
      const res = await listMemory({ page_size: 100 })
      const raw = res.items || res || []
      this.setData({
        memories: raw.map(m => ({
          ...m,
          importanceStars: m.importance ? '★'.repeat(m.importance) : ''
        }))
      })
    } catch (err) {
      console.error('加载记忆失败:', err)
    } finally {
      this.setData({ loading: false })
    }
  },

  showAdd() { this.setData({ showAdd: true }) },
  hideAdd() {
    this.setData({ showAdd: false, elderlyUserId: '', newContent: '', newMemoryType: '', newImportance: 3 })
  },

  onElderlyInput(e)    { this.setData({ elderlyUserId: e.detail.value }) },
  onContentInput(e)    { this.setData({ newContent: e.detail.value }) },
  onTypeInput(e)       { this.setData({ newMemoryType: e.detail.value }) },
  onImportanceInput(e) { this.setData({ newImportance: parseInt(e.detail.value) || 3 }) },

  async doCreate() {
    const { elderlyUserId, newContent, newMemoryType, newImportance } = this.data
    const uid = parseInt(elderlyUserId)
    if (!uid || uid <= 0) { wx.showToast({ title: '请输入有效的老人 user_id', icon: 'none' }); return }
    if (!newContent.trim()) { wx.showToast({ title: '请输入内容', icon: 'none' }); return }

    try {
      await createMemory({
        user_id: uid,
        content: newContent.trim(),
        memory_type: newMemoryType.trim() || '通用',
        source: 'admin',
        importance: newImportance
      })
      wx.showToast({ title: '已添加', icon: 'success' })
      this.hideAdd()
      this.loadMemories()
    } catch (err) {
      wx.showToast({ title: err.msg || err.detail || '添加失败', icon: 'none' })
    }
  },

  doDelete(e) {
    const id = e.currentTarget.dataset.id
    const summary = e.currentTarget.dataset.summary || '该条目'
    wx.showModal({
      title: '确认删除',
      content: `确定删除「${summary}」吗？`,
      success: async (res) => {
        if (!res.confirm) return
        try {
          await deleteMemory(id)
          wx.showToast({ title: '已删除', icon: 'success' })
          this.loadMemories()
        } catch (err) {
          wx.showToast({ title: err.msg || err.detail || '删除失败', icon: 'none' })
        }
      }
    })
  },

  goBack() { wx.switchTab({ url: '/pages/index/index' }) },
  goToSettings() { wx.navigateTo({ url: '/subpkg-manage/pages/settings/settings' }) }
})
