// admin-miniprogram/app.js
var config = require('./config/index.js');
var auth = require('./utils/auth.js');

App({
  onLaunch: function () {
    this.globalData = {
      baseUrl: config.baseUrl,
      token: '',
      refId: null,
      nickname: ''
    };

    var hasToken = auth.restoreToken();
    if (hasToken) {
      wx.checkSession({
        success: function () {
          auth.startHeartbeat();
        },
        fail: function () {
          auth.logout();
        }
      });
    }
  },

  globalData: {
    baseUrl: '',
    token: '',
    refId: null,
    nickname: ''
  }
});
