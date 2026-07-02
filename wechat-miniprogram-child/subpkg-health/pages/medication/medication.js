const { getBindedUsers, listMedications, createMedication, updateMedication, deleteMedication } = require('../../../utils/api')
const app = getApp()

Page({
  data: {
    bindedUsers: [],
    selectedUserId: null,
    selectedNickname: '',
    reminders: [],
    loading: false,
    // 新增/编辑弹窗
    showForm: false,
    editId: null,
    formDrugName: '',
    formRemindTime: '',
    formDosage: '',
    formActive: 1
  },

  onShow() {
    this.loadBindedUsers()
  },

  async loadBindedUsers() {
    try {
      const users = await getBindedUsers()
      this.setData({
        bindedUsers: users || [],
        reminders: [],
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
      this.setData({ selectedUserId: user.user_id, selectedNickname: user.nickname, reminders: [] })
      this.loadReminders(user.user_id)
    }
  },

  async loadReminders(userId) {
    this.setData({ loading: true })
    try {
      const items = await listMedications(userId)
      this.setData({ reminders: items || [] })
    } catch (err) {
      console.error('加载用药提醒失败:', err)
      this.setData({ reminders: [] })
    } finally {
      this.setData({ loading: false })
    }
  },

  // ---- 新增 ----
  showAddForm() {
    this.setData({
      showForm: true, editId: null,
      formDrugName: '', formRemindTime: '', formDosage: '', formActive: 1
    })
  },

  // ---- 编辑 ----
  showEditForm(e) {
    const id = e.currentTarget.dataset.id
    const item = this.data.reminders.find(r => r.reminder_id === id)
    if (item) {
      this.setData({
        showForm: true, editId: id,
        formDrugName: item.drug_name || '',
        formRemindTime: item.remind_time || '',
        formDosage: item.dosage || '',
        formActive: item.active
      })
    }
  },

  hideForm() {
    this.setData({
      showForm: false, editId: null,
      formDrugName: '', formRemindTime: '', formDosage: '', formActive: 1
    })
  },

  onDrugNameInput(e) { this.setData({ formDrugName: e.detail.value }) },
  onRemindTimeInput(e) { this.setData({ formRemindTime: e.detail.value }) },
  onDosageInput(e) { this.setData({ formDosage: e.detail.value }) },
  onActiveToggle() {
    this.setData({ formActive: this.data.formActive === 1 ? 0 : 1 })
  },

  async doSave() {
    const { editId, formDrugName, formRemindTime, formDosage, formActive, selectedUserId } = this.data
    if (!formDrugName.trim()) { wx.showToast({ title: '请输入药品名称', icon: 'none' }); return }
    if (!formRemindTime.trim()) { wx.showToast({ title: '请输入提醒时间', icon: 'none' }); return }

    try {
      if (editId) {
        await updateMedication(editId, {
          drug_name: formDrugName.trim(),
          remind_time: formRemindTime.trim(),
          dosage: formDosage.trim() || undefined,
          active: formActive
        })
        wx.showToast({ title: '已更新', icon: 'success' })
      } else {
        await createMedication(formDrugName.trim(), formRemindTime.trim(), selectedUserId, formDosage.trim() || undefined)
        wx.showToast({ title: '已添加', icon: 'success' })
      }
      this.hideForm()
      this.loadReminders(selectedUserId)
    } catch (err) {
      wx.showToast({ title: err.msg || err.detail || '操作失败', icon: 'none' })
    }
  },

  doDelete(e) {
    const id = e.currentTarget.dataset.id
    const drugName = e.currentTarget.dataset.drug || '该药品'
    wx.showModal({
      title: '确认删除',
      content: `确定删除「${drugName}」的提醒吗？`,
      success: async (res) => {
        if (!res.confirm) return
        try {
          await deleteMedication(id)
          wx.showToast({ title: '已删除', icon: 'success' })
          this.loadReminders(this.data.selectedUserId)
        } catch (err) {
          wx.showToast({ title: err.msg || err.detail || '删除失败', icon: 'none' })
        }
      }
    })
  },

})
