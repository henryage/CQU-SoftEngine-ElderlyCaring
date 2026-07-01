var config = require('./config/index.js');

App({
  onLaunch: function () {
    this.globalData = {
      baseUrl: config.baseUrl,
      token: '',
      refreshToken: '',
      refId: null,
      nickname: ''
    };
  },
  globalData: {
    baseUrl: '',
    token: '',
    refreshToken: '',
    refId: null,
    nickname: ''
  }
});