var request = require('../../utils/request.js').request;

Page({
  data: {
    statusBarHeight: 20,
    reminderList: [],
    loading: true
  },

  onLoad: function() {
    var sys = wx.getSystemInfoSync();
    this.setData({ statusBarHeight: sys.statusBarHeight || 20 });
  },

  onShow: function() {
    this.loadReminders();
  },

  loadReminders: function() {
    var that = this;
    this.setData({ loading: true });
    request({ url: '/api/v1/reminder/medication', method: 'GET' }).then(function(data) {
      that.setData({
        reminderList: Array.isArray(data) ? data : [],
        loading: false
      });
    }).catch(function() {
      that.setData({ loading: false });
      wx.showToast({ title: '加载失败', icon: 'none' });
    });
  },

  onGoBack: function() {
    wx.navigateBack();
  }
});