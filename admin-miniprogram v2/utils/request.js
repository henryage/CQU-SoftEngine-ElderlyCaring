var config = require('../config/index.js');
var storage = require('./storage.js');
var BASE_URL = config.baseUrl;

function getToken() {
  var app = getApp();
  return (app && app.globalData && app.globalData.token) || '';
}

function request(options) {
  var opts = options || {};
  return new Promise(function(resolve, reject) {
    var header = {
      'Content-Type': 'application/json'
    };
    if (opts.header) {
      Object.keys(opts.header).forEach(function(key) {
        header[key] = opts.header[key];
      });
    }
    var token = getToken();
    if (token) {
      header['Authorization'] = 'Bearer ' + token;
    }

    wx.showNavigationBarLoading();

    wx.request({
      url: BASE_URL + (opts.url || ''),
      method: opts.method || 'GET',
      data: opts.data || {},
      header: header,
      timeout: opts.timeout || 30000,
      success: function(res) {
        wx.hideNavigationBarLoading();
        if (res.statusCode === 401) {
          // token 过期或无效，清除并跳转登录页
          storage.remove('token');
          storage.remove('refId');
          storage.remove('nickname');
          var app = getApp();
          if (app && app.globalData) {
            app.globalData.token = '';
            app.globalData.refId = null;
            app.globalData.nickname = '';
          }
          wx.showToast({ title: '登录已过期，请重新登录', icon: 'none', duration: 2000 });
          setTimeout(function () {
            wx.reLaunch({ url: '/pages/login/login' });
          }, 1500);
          reject(new Error('Unauthorized'));
          return;
        }
        if (res.statusCode >= 200 && res.statusCode < 300) {
          if (res.data && res.data.code === 0) {
            resolve(res.data.data);
          } else {
            var msg = (res.data && res.data.msg) || '请求失败';
            wx.showToast({ title: msg, icon: 'none', duration: 2000 });
            reject(res.data || new Error(msg));
          }
        } else {
          wx.showToast({ title: '服务器错误 ' + res.statusCode, icon: 'none' });
          reject(new Error('HTTP ' + res.statusCode));
        }
      },
      fail: function(err) {
        wx.hideNavigationBarLoading();
        wx.showToast({ title: '网络连接失败，请检查网络', icon: 'none' });
        reject(err);
      }
    });
  });
}

function getFullUrl(path) {
  if (!path) return '';
  if (path.indexOf('http') === 0) return path;
  return BASE_URL + path;
}

module.exports = {
  BASE_URL: BASE_URL,
  request: request,
  getFullUrl: getFullUrl
};
