var storage = require('../../utils/storage.js');
var req = require('../../utils/request.js');

Page({
  data: {
    statusBarHeight: 20,
    fontSize: 'normal',
    voiceEnabled: true,
    nickname: '',
    showNicknameModal: false,
    nicknameInput: '',
    showBindCodeModal: false,
    bindCode: '',
    bindCodeExpires: 0
  },

  onLoad: function() {
    var sys = wx.getSystemInfoSync();
    var app = getApp();
    var nickname = (app && app.globalData && app.globalData.nickname) || '';
    this.setData({
      statusBarHeight: sys.statusBarHeight || 20,
      fontSize: storage.get('fontSize', 'normal'),
      voiceEnabled: storage.get('voiceEnabled', true),
      nickname: nickname,
      nicknameInput: nickname
    });
  },

  onGoBack: function() {
    wx.navigateBack();
  },

  onSetFontSize: function(e) {
    var size = e.currentTarget.dataset.size;
    storage.set('fontSize', size);
    this.setData({ fontSize: size });
    wx.showToast({ title: '字体大小已设置', icon: 'success' });
  },

  onVoiceToggle: function(e) {
    var enabled = e.detail.value;
    storage.set('voiceEnabled', enabled);
    this.setData({ voiceEnabled: enabled });
  },

  // 昵称修改
  onEditNickname: function() {
    this.setData({
      showNicknameModal: true,
      nicknameInput: this.data.nickname
    });
  },

  onNicknameInput: function(e) {
    this.setData({ nicknameInput: e.detail.value });
  },

  onCancelNickname: function() {
    this.setData({ showNicknameModal: false });
  },

  onConfirmNickname: function() {
    var that = this;
    var newNickname = this.data.nicknameInput.trim();
    if (!newNickname) {
      wx.showToast({ title: '昵称不能为空', icon: 'none' });
      return;
    }
    req.request({
      url: '/api/v1/auth/nickname?nickname=' + encodeURIComponent(newNickname),
      method: 'PUT'
    }).then(function(data) {
      var app = getApp();
      if (app && app.globalData) {
        app.globalData.nickname = newNickname;
      }
      that.setData({
        nickname: newNickname,
        showNicknameModal: false
      });
      wx.showToast({ title: '昵称已更新', icon: 'success' });
    }).catch(function(err) {
      // 错误已在 request 中 toast
    });
  },

  // 生成绑定验证码
  onGenerateBindCode: function() {
    var that = this;
    wx.showLoading({ title: '生成中...' });
    req.request({
      url: '/api/v1/auth/generate-bind-code',
      method: 'POST'
    }).then(function(data) {
      wx.hideLoading();
      that.setData({
        showBindCodeModal: true,
        bindCode: data.code || '',
        bindCodeExpires: data.expires_in_seconds || 300
      });
    }).catch(function(err) {
      wx.hideLoading();
    });
  },

  onCopyBindCode: function() {
    wx.setClipboardData({
      data: this.data.bindCode,
      success: function() {
        wx.showToast({ title: '验证码已复制', icon: 'success' });
      }
    });
  },

  onCloseBindCode: function() {
    this.setData({ showBindCodeModal: false });
  },

  onLogout: function() {
    var that = this;
    wx.showModal({
      title: '退出登录',
      content: '确定要退出登录吗？',
      success: function(res) {
        if (res.confirm) {
          storage.clear();
          wx.redirectTo({ url: '/pages/index/index' });
        }
      }
    });
  }
});