// admin-miniprogram/pages/login/login.js
var auth = require('../../utils/auth.js');

Page({
  data: {
    loading: false
  },

  onLoad: function () {
    if (auth.restoreToken()) {
      wx.checkSession({
        success: function () {
          auth.startHeartbeat();
          wx.switchTab({ url: '/pages/users/users' });
        },
        fail: function () {
          auth.logout();
        }
      });
    }
  },

  handleLogin: function () {
    var that = this;
    if (that.data.loading) return;

    that.setData({ loading: true });
    auth.login().then(function () {
      auth.startHeartbeat();
      wx.switchTab({ url: '/pages/users/users' });
    }).catch(function () {
      that.setData({ loading: false });
    });
  }
});
