var auth = require('../../utils/auth.js');

Page({
  data: {
    statusBarHeight: 20,
    isLoggingIn: false,
    loginError: ''
  },

  onLoad: function() {
    var sys = wx.getSystemInfoSync();
    this.setData({ statusBarHeight: sys.statusBarHeight || 20 });
  },

  onShow: function() {
    var that = this;
    var hasToken = auth.restoreToken();
    if (hasToken && auth.isTokenValid()) {
      wx.redirectTo({ url: '/pages/home/home' });
    }
  },

  onLogin: function() {
    var that = this;
    this.setData({ isLoggingIn: true, loginError: '' });

    auth.login().then(function() {
      wx.redirectTo({ url: '/pages/home/home' });
    }).catch(function(err) {
      that.setData({
        isLoggingIn: false,
        loginError: '登录失败，请检查网络后重试'
      });
    });
  }
});