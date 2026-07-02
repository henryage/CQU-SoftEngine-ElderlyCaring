const { getBindedUsers, bindElderly, unbindElderly } = require('../../../utils/api')
const app = getApp()

Page({
  data: {
    childId: '',
    bindedUsers: [],
    loading: false,
    // 绑定表单
    bindCode: '',
    bindRelation: '子女'
  },

  onShow() {
    this.setData({ childId: app.getChildId() || '' })
    this.loadBindedUsers()
  },

  async loadBindedUsers() {
    this.setData({ loading: true })
    try {
      const users = await getBindedUsers()
      this.setData({ bindedUsers: users || [] })
    } catch (err) {
      console.error('加载绑定列表失败:', err)
      this.setData({ bindedUsers: [] })
    } finally {
      this.setData({ loading: false })
    }
  },

  onCodeInput(e) { this.setData({ bindCode: e.detail.value }) },
  onRelationInput(e) { this.setData({ bindRelation: e.detail.value || '子女' }) },

  async doBind() {
    const code = this.data.bindCode.trim()
    if (!code || code.length !== 6) {
      wx.showToast({ title: '请输入6位邀请码', icon: 'none' })
      return
    }
    try {
      await bindElderly(code, this.data.bindRelation)
      wx.showToast({ title: '绑定成功', icon: 'success' })
      this.setData({ bindCode: '' })
      this.loadBindedUsers()
    } catch (err) {
      wx.showToast({ title: err.msg || err.detail || '绑定失败', icon: 'none' })
    }
  },

  doUnbind(e) {
    const userId = e.currentTarget.dataset.uid
    const nickname = e.currentTarget.dataset.nickname || '该老人'
    wx.showModal({
      title: '确认解绑',
      content: `确定解除与「${nickname}」的绑定关系吗？`,
      success: async (res) => {
        if (!res.confirm) return
        try {
          await unbindElderly(userId)
          wx.showToast({ title: '已解绑', icon: 'success' })
          this.loadBindedUsers()
        } catch (err) {
          wx.showToast({ title: err.msg || err.detail || '解绑失败', icon: 'none' })
        }
      }
    })
  },

})
