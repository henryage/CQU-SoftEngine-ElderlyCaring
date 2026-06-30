var request = require('../../utils/request.js').request;

Page({
  data: {
    statusBarHeight: 20,
    resultText: ''
  },

  onLoad: function() {
    var sys = wx.getSystemInfoSync();
    this.setData({ statusBarHeight: sys.statusBarHeight || 20 });
  },

  onGoBack: function() {
    wx.navigateBack();
  },

  onEmergencyCall: function() {
    var that = this;
    wx.showModal({
      title: '确定要通知家人吗？',
      content: '点击确定将通知所有绑定的家人',
      confirmText: '确定通知',
      cancelText: '取消',
      success: function(modalRes) {
        if (modalRes.confirm) {
          request({ url: '/api/v1/alert/emergency/call', method: 'POST' }).then(function() {
            that.setData({ resultText: '已通知家人，请等待。' });
          }).catch(function() {
            that.setData({ resultText: '通知失败，请直接拨打120。' });
          });
        }
      }
    });
  },

  onCall120: function() {
    wx.makePhoneCall({ phoneNumber: '120', fail: function() {} });
  }
});