const { listMemory, createMemory, getMemory, updateMemory, deleteMemory, setImportance, searchMemory, getBindedUsers } = require('../../../utils/api')

// 辅助：安全的 parseInt，0 不丢
function safeInt(v, fallback = 3) {
  const n = parseInt(v)
  return isNaN(n) ? fallback : n
}

Page({
  data: {
    bindedUsers: [],
    selectedUserId: null,
    selectedNickname: '',
    memories: [],
    loading: false,
    keyword: '',
    activeTimers: {},

    // 添加弹窗
    showAddModal: false,
    newContent: '',
    newMemoryType: '',
    newImportance: 3,
    newDuration: 0,

    // 详情/编辑弹窗
    showDetailModal: false,
    editMemoryId: null,
    editContent: '',
    editMemoryType: '',
    editImportance: 3,
    editDuration: 0,
    editUserId: null
  },

  onShow() {
    this.loadBindedUsers()
  },

  onUnload() {
    this.clearAllTimers()
  },

  // ============ 定时器管理 ============
  timers: {},

  startImportanceTimer(memoryId, durationHours) {
    if (!durationHours || durationHours <= 0) return
    const ms = durationHours * 3600 * 1000
    // 清除旧定时器
    if (this.timers[memoryId]) {
      clearTimeout(this.timers[memoryId])
    }
    const tid = setTimeout(async () => {
      try {
        await setImportance(memoryId, 0)
        delete this.timers[memoryId]
        // 刷新列表
        if (this.data.selectedUserId) {
          this.loadMemories()
        }
      } catch (err) {
        console.error('权重归零失败:', err)
      }
    }, ms)
    this.timers[memoryId] = tid
    // 同步到 data 用于 UI 展示
    const newTimers = { ...this.data.activeTimers, [memoryId]: Date.now() + ms }
    this.setData({ activeTimers: newTimers })
  },

  clearAllTimers() {
    Object.keys(this.timers).forEach(k => clearTimeout(this.timers[k]))
    this.timers = {}
  },

  // ============ 绑定老人 ============
  async loadBindedUsers() {
    try {
      const users = await getBindedUsers()
      this.setData({
        bindedUsers: users || [],
        selectedUserId: null,
        selectedNickname: '',
        memories: [],
        keyword: ''
      })
    } catch (err) {
      console.error('加载绑定列表失败:', err)
    }
  },

  onElderSelect(e) {
    const idx = e.detail.value
    const user = this.data.bindedUsers[idx]
    if (user) {
      this.clearAllTimers()
      this.setData({
        selectedUserId: user.user_id,
        selectedNickname: user.nickname,
        memories: [],
        keyword: '',
        activeTimers: {}
      })
      this.loadMemories()
    }
  },

  // ============ 搜索 ============
  onKeywordInput(e) { this.setData({ keyword: e.detail.value }) },

  async doSearch() {
    if (!this.data.selectedUserId) {
      wx.showToast({ title: '请先选择老人', icon: 'none' })
      return
    }
    const keyword = this.data.keyword.trim()
    this.setData({ loading: true })
    try {
      let res
      if (keyword) {
        res = await searchMemory({ query: keyword, top_k: 20, user_id: this.data.selectedUserId })
        const items = (res.results || res || []).map(m => ({
          ...m,
          importanceStars: (m.importance && m.importance > 0) ? '★'.repeat(m.importance) : ''
        }))
        this.setData({ memories: items })
      } else {
        await this.loadMemories()
      }
    } catch (err) {
      console.error('搜索失败:', err)
    } finally {
      this.setData({ loading: false })
    }
  },

  // ============ 列表 ============
  async loadMemories() {
    if (!this.data.selectedUserId) return
    this.setData({ loading: true })
    try {
      const res = await listMemory({ user_id: this.data.selectedUserId, page_size: 100 })
      const raw = res.items || res || []
      this.setData({
        memories: raw.map(m => ({
          ...m,
          importanceStars: (m.importance && m.importance > 0) ? '★'.repeat(m.importance) : '',
          hasTimer: !!this.data.activeTimers[m.memory_id]
        }))
      })
    } catch (err) {
      console.error('加载记忆失败:', err)
    } finally {
      this.setData({ loading: false })
    }
  },

  // ============ 添加 ============
  showAddModal() { this.setData({ showAddModal: true }) },
  hideAddModal() {
    this.setData({ showAddModal: false, newContent: '', newMemoryType: '', newImportance: 3, newDuration: 0 })
  },

  onContentInput(e) { this.setData({ newContent: e.detail.value }) },
  onTypeInput(e) { this.setData({ newMemoryType: e.detail.value }) },
  onImportanceInput(e) { this.setData({ newImportance: safeInt(e.detail.value, 3) }) },
  onDurationInput(e) { this.setData({ newDuration: safeInt(e.detail.value, 0) }) },

  async doCreate() {
    const { selectedUserId, newContent, newMemoryType, newImportance, newDuration } = this.data
    if (!selectedUserId) { wx.showToast({ title: '请先选择老人', icon: 'none' }); return }
    if (!newContent.trim()) { wx.showToast({ title: '请输入内容', icon: 'none' }); return }

    try {
      const res = await createMemory({
        user_id: selectedUserId,
        content: newContent.trim(),
        memory_type: newMemoryType.trim() || '通用',
        source: 'admin',
        importance: newImportance
      })
      wx.showToast({ title: '已添加', icon: 'success' })
      // 启动有效定时
      const memId = res.memory_id
      if (memId && newDuration > 0) {
        this.startImportanceTimer(memId, newDuration)
      }
      this.hideAddModal()
      this.loadMemories()
    } catch (err) {
      wx.showToast({ title: err.msg || err.detail || '添加失败', icon: 'none' })
    }
  },

  // ============ 详情/编辑 ============
  async openDetail(e) {
    const id = e.currentTarget.dataset.id
    try {
      const mem = await getMemory(id)
      this.setData({
        showDetailModal: true,
        editMemoryId: id,
        editContent: mem.content || '',
        editMemoryType: mem.memory_type || '',
        editImportance: mem.importance ?? 3,
        editDuration: 0,
        editUserId: mem.user_id
      })
    } catch (err) {
      wx.showToast({ title: '获取详情失败', icon: 'none' })
    }
  },

  hideDetailModal() {
    this.setData({
      showDetailModal: false, editMemoryId: null,
      editContent: '', editMemoryType: '', editImportance: 3, editDuration: 0
    })
  },

  onEditTypeInput(e) { this.setData({ editMemoryType: e.detail.value }) },
  onEditContentInput(e) { this.setData({ editContent: e.detail.value }) },
  onEditImportanceInput(e) { this.setData({ editImportance: safeInt(e.detail.value, 3) }) },
  onEditDurationInput(e) { this.setData({ editDuration: safeInt(e.detail.value, 0) }) },

  async doUpdate() {
    const { editMemoryId, editContent, editMemoryType, editImportance, editDuration, editUserId } = this.data
    if (!editContent.trim()) { wx.showToast({ title: '请输入内容', icon: 'none' }); return }

    try {
      await updateMemory(editMemoryId, {
        user_id: editUserId,
        content: editContent.trim(),
        memory_type: editMemoryType.trim() || '通用',
        source: 'admin',
        importance: editImportance
      })
      wx.showToast({ title: '已更新', icon: 'success' })
      // 更新定时器
      if (editDuration > 0) {
        this.startImportanceTimer(editMemoryId, editDuration)
      }
      this.hideDetailModal()
      this.loadMemories()
    } catch (err) {
      wx.showToast({ title: err.msg || err.detail || '更新失败', icon: 'none' })
    }
  },

  // ============ 重要性快速调整 ============
  async adjustImportance(e) {
    const id = e.currentTarget.dataset.id
    const cur = parseInt(e.currentTarget.dataset.importance) || 0
    const next = cur >= 5 ? 0 : cur + 1
    try {
      await setImportance(id, next)
      wx.showToast({ title: `重要性: ${next}`, icon: 'none', duration: 800 })
      this.loadMemories()
    } catch (err) {
      wx.showToast({ title: err.msg || err.detail || '调整失败', icon: 'none' })
    }
  },

  // ============ 删除 ============
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
          // 清除关联定时器
          if (this.timers[id]) {
            clearTimeout(this.timers[id])
            delete this.timers[id]
          }
          const newTimers = { ...this.data.activeTimers }
          delete newTimers[id]
          this.setData({ activeTimers: newTimers })
          wx.showToast({ title: '已删除', icon: 'success' })
          this.loadMemories()
        } catch (err) {
          wx.showToast({ title: err.msg || err.detail || '删除失败', icon: 'none' })
        }
      }
    })
  },

  stopProp() {}

})
