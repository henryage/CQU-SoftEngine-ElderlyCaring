const USE_MOCK = false
const BASE_URL = 'http://10.128.229.199:8090'

const mockDelay = (data, ms = 300) => new Promise(resolve => setTimeout(() => resolve(data), ms))

const api = {
  // ===== 认证 =====
  login: () => null,
  heartbeat: () => null,

  // ===== 绑定管理 (user_child_relation) =====
  bindElderly: () => null,
  unbindElderly: () => null,
  getBindList: () => null,

  // ===== 预警事件 (alert_event) =====
  getAlertList: () => null,
  getAlertDetail: () => null,
  handleAlert: () => null,

  // ===== 行为轨迹 (behavior_trace) =====
  getTraceList: () => null,
  getTraceDetail: () => null,

  // ===== 健康画像 (user_profile + user_profile_dimension) =====
  getHealthProfile: () => null,
  getHealthDimensions: () => null,

  // ===== 用药提醒 (medication_reminder) =====
  getMedicationList: () => null,
  createMedication: () => null,
  updateMedication: () => null,
  deleteMedication: () => null,

  // ===== 亲情通信 (communication_log) =====
  sendMessage: () => null,
  sendVoice: () => null,
  getMessageList: () => null,

  // ===== 定时问候 (greeting_schedule) =====
  getGreetingList: () => null,
  createGreeting: () => null,
  updateGreeting: () => null,
  deleteGreeting: () => null,

  // ===== 问答历史 (message) =====
  getQAHistory: () => null,
  getQADetail: () => null,

  // ===== 远程设置 (user_setting + setting_change) =====
  getSettings: () => null,
  updateSetting: () => null,
  getSettingHistory: () => null,

  // ===== 知识库 (long_term_memory) =====
  getKnowledgeList: () => null,
  createKnowledge: () => null,
  updateKnowledge: () => null,
  deleteKnowledge: () => null,
  getPromptTemplates: () => null,
  updatePromptTemplate: () => null
}

module.exports = { api, BASE_URL }
