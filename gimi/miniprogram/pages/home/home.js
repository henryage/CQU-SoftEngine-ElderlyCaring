var auth = require('../../utils/auth.js');
var request = require('../../utils/request.js').request;
var speech = require('../../utils/speech.js');

var reminderTimer = null;

Page({
  data: {
    statusBarHeight: 20,
    userId: ''
  },

  onLoad: function() {
    var sys = wx.getSystemInfoSync();
    var app = getApp();
    var refId = app.globalData.refId;
    this.setData({
      statusBarHeight: sys.statusBarHeight || 20,
      userId: refId ? '老人id' + refId : ''
    });
  },

  onShow: function() {
    if (!auth.isTokenValid()) {
      wx.redirectTo({ url: '/pages/index/index' });
      return;
    }
    auth.startHeartbeat();
    this.startReminderPolling();
  },

  onHide: function() {
    auth.stopHeartbeat();
    this.stopReminderPolling();
  },

  onUnload: function() {
    auth.stopHeartbeat();
    this.stopReminderPolling();
  },

  onGoChat: function() {
    wx.navigateTo({ url: '/pages/chat/chat' });
  },

  onGoReminder: function() {
    wx.navigateTo({ url: '/pages/reminder/reminder' });
  },

  onGoEmergency: function() {
    wx.navigateTo({ url: '/pages/emergency/emergency' });
  },

  onGoSettings: function() {
    wx.navigateTo({ url: '/pages/settings/settings' });
  },

  startReminderPolling: function() {
    this.stopReminderPolling();
    this.fetchReminders();
    var that = this;
    reminderTimer = setInterval(function() {
      that.fetchReminders();
    }, 5 * 60 * 1000);
  },

  stopReminderPolling: function() {
    if (reminderTimer) {
      clearInterval(reminderTimer);
      reminderTimer = null;
    }
  },

  fetchReminders: function() {
    var that = this;
    request({ url: '/api/v1/reminder/medication', method: 'GET' }).then(function(data) {
      if (!Array.isArray(data)) return;
      var lastData = wx.getStorageSync('gimi_last_reminders') || [];
      var newOnes = data.filter(function(r) {
        return !lastData.find(function(lr) { return lr.reminder_id === r.reminder_id; });
      });
      if (newOnes.length > 0 && lastData.length > 0) {
        newOnes.forEach(function(r) {
          var text = '喵喵~' + r.remind_time + '啦，该吃' + r.drug_name + '，' + r.dosage + '哦！';
          speech.speak(text);
        });
      }
      wx.setStorageSync('gimi_last_reminders', data);
    }).catch(function() {});
  }
});