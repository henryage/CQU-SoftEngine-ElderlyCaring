var storage = require('../../utils/storage.js');

Page({
  data: {
    statusBarHeight: 20,
    fontSize: 'normal',
    voiceEnabled: true
  },

  onLoad: function() {
    var sys = wx.getSystemInfoSync();
    this.setData({
      statusBarHeight: sys.statusBarHeight || 20,
      fontSize: storage.get('fontSize', 'normal'),
      voiceEnabled: storage.get('voiceEnabled', true)
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