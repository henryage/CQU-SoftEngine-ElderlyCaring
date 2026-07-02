const { getBindedUsers, getChildSettings, updateChildSettings, getSettingsChanges } = require('../../../utils/api')
const app = getApp()

Page({
  data: {
    bindedUsers: [],
    selectedUserId: null,
    selectedNickname: '',
    settings: { font_size: 'normal', voice_enabled: true, simplified_mode: false },
    changes: [],
    loading: false,
    saving: false,
    fontSizes: ['normal', 'large', 'xlarge']
  },

  onShow() {
    this.loadBindedUsers()
  },

  async loadBindedUsers() {
    try {
      const users = await getBindedUsers()
      this.setData({
        bindedUsers: users || [],
        settings: { font_size: 'normal', voice_enabled: true, simplified_mode: false },
        changes: [],
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
      this.loadSettings(user.user_id)
    }
  },

  async loadSettings(userId) {
    this.setData({ loading: true })
    try {
      const [cfg, changes] = await Promise.all([
        getChildSettings(userId).catch(() => null),
        getSettingsChanges(userId).catch(() => [])
      ])
      this.setData({
        settings: cfg || { font_size: 'normal', voice_enabled: true, simplified_mode: false },
        changes: changes || []
      })
    } catch (err) {
      console.error('加载配置失败:', err)
    } finally {
      this.setData({ loading: false })
    }
  },

  onFontChange(e) {
    const idx = e.detail.value
    this.setData({ 'settings.font_size': this.data.fontSizes[idx] })
  },

  onVoiceToggle(e) {
    this.setData({ 'settings.voice_enabled': e.detail.value })
  },

  onSimpleToggle(e) {
    this.setData({ 'settings.simplified_mode': e.detail.value })
  },

  async doSave() {
    if (!this.data.selectedUserId) return
    this.setData({ saving: true })
    try {
      await updateChildSettings(this.data.selectedUserId, this.data.settings)
      wx.showToast({ title: '配置已下发', icon: 'success' })
      this.loadSettings(this.data.selectedUserId)
    } catch (err) {
      wx.showToast({ title: err.msg || err.detail || '保存失败', icon: 'none' })
    } finally {
      this.setData({ saving: false })
    }
  },

})
