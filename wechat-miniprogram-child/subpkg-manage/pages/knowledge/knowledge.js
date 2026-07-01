const { listMemory, createMemory, getMemory, updateMemory, deleteMemory, setImportance, searchMemory, getBindedUsers } = require('../../../utils/api')

Page({
  data: {
    bindedUsers: [],
    selectedUserId: null,
    selectedNickname: '',
    memories: [],
    loading: false,
    keyword: '',
    // 添加
    showAddModal: false,
    newContent: '',
    newMemoryType: '',
    newImportance: 3,
    // 详情/编辑
    showDetailModal: false,
    editMemoryId: null,
    editContent: '',
    editMemoryType: '',
    editImportance: 3,
    editUserId: null
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
      this.setData({ selectedUserId: user.user_id, selectedNickname: user.nickname, memories: [], keyword: '' })
      this.loadMemories()
    }
  },

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

  async loadMemories() {
    if (!this.data.selectedUserId) return
    this.setData({ loading: true })
    try {
      const res = await listMemory({ user_id: this.data.selectedUserId, page_size: 100 })
      const raw = res.items || res || []
      this.setData({
        memories: raw.map(m => ({
          ...m,
          importanceStars: (m.importance && m.importance > 0) ? '★'.repeat(m.importance) : ''
        }))
      })
    } catch (err) {
      console.error('加载记忆失败:', err)
    } finally {
      this.setData({ loading: false })
    }
  },

  // ── 添加 ──
  showAddModal() { this.setData({ showAddModal: true }) },
  hideAddModal() {
    this.setData({ showAddModal: false, newContent: '', newMemoryType: '', newImportance: 3 })
  },

  onContentInput(e) { this.setData({ newContent: e.detail.value }) },
  onTypeInput(e) { this.setData({ newMemoryType: e.detail.value }) },
  onImportanceInput(e) { this.setData({ newImportance: parseInt(e.detail.value) || 3 }) },

  async doCreate() {
    const { selectedUserId, newContent, newMemoryType, newImportance } = this.data
    if (!selectedUserId) { wx.showToast({ title: '请先选择老人', icon: 'none' }); return }
    if (!newContent.trim()) { wx.showToast({ title: '请输入内容', icon: 'none' }); return }

    try {
      await createMemory({
        user_id: selectedUserId,
        content: newContent.trim(),
        memory_type: newMemoryType.trim() || '通用',
        source: 'admin',
        importance: newImportance
      })
      wx.showToast({ title: '已添加', icon: 'success' })
      this.hideAddModal()
      this.loadMemories()
    } catch (err) {
      wx.showToast({ title: err.msg || err.detail || '添加失败', icon: 'none' })
    }
  },

  // ── 详情/编辑 ──
  async openDetail(e) {
    const id = e.currentTarget.dataset.id
    try {
      const mem = await getMemory(id)
      this.setData({
        showDetailModal: true,
        editMemoryId: id,
        editContent: mem.content || '',
        editMemoryType: mem.memory_type || '',
        editImportance: mem.importance || 3,
        editUserId: mem.user_id
      })
    } catch (err) {
      wx.showToast({ title: '获取详情失败', icon: 'none' })
    }
  },

  hideDetailModal() {
    this.setData({ showDetailModal: false, editMemoryId: null })
  },

  onEditTypeInput(e) { this.setData({ editMemoryType: e.detail.value }) },
  onEditContentInput(e) { this.setData({ editContent: e.detail.value }) },
  onEditImportanceInput(e) { this.setData({ editImportance: parseInt(e.detail.value) || 3 }) },

  async doUpdate() {
    const { editMemoryId, editContent, editMemoryType, editImportance, editUserId } = this.data
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
      this.hideDetailModal()
      this.loadMemories()
    } catch (err) {
      wx.showToast({ title: err.msg || err.detail || '更新失败', icon: 'none' })
    }
  },

  // ── 重要性快速调整 ──
  async adjustImportance(e) {
    const id = e.currentTarget.dataset.id
    const cur = parseInt(e.currentTarget.dataset.importance) || 0
    const next = cur >= 5 ? 1 : cur + 1
    try {
      await setImportance(id, next)
      wx.showToast({ title: `重要性已设为${next}`, icon: 'none', duration: 800 })
      this.loadMemories()
    } catch (err) {
      wx.showToast({ title: err.msg || err.detail || '调整失败', icon: 'none' })
    }
  },

  // ── 删除 ──
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

  stopProp() {}

})
