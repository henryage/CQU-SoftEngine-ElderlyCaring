// admin-miniprogram/pages/login/login.js
var auth = require('../../utils/auth.js');

Page({
  data: {
    loading: false,
    username: '',
    password: ''
  },

  onLoad: function () {
    if (auth.restoreToken()) {
      wx.switchTab({ url: '/pages/users/users' });
    }
  },

  onUsernameInput: function (e) {
    this.setData({ username: e.detail.value });
  },

  onPasswordInput: function (e) {
    this.setData({ password: e.detail.value });
  },

  handleLogin: function () {
    var that = this;
    if (that.data.loading) return;

    var username = that.data.username.trim();
    var password = that.data.password.trim();

    if (!username) {
      wx.showToast({ title: '请输入用户名', icon: 'none' });
      return;
    }
    if (!password) {
      wx.showToast({ title: '请输入密码', icon: 'none' });
      return;
    }

    that.setData({ loading: true });
    auth.login(username, password).then(function () {
      wx.switchTab({ url: '/pages/users/users' });
    }).catch(function () {
      that.setData({ loading: false });
    });
  }
});
