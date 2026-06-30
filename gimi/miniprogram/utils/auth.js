var request = require('./request.js').request;

var heartbeatTimer = null;

function login() {
  return new Promise(function(resolve, reject) {
    wx.login({
      success: function(loginRes) {
        if (loginRes.code) {
          request({
            url: '/api/v1/auth/wx-login',
            method: 'POST',
            data: { code: loginRes.code, user_type: 'user' }
          }).then(function(data) {
            var app = getApp();
            app.globalData.token = data.token;
            app.globalData.refreshToken = data.refresh_token;
            app.globalData.refId = data.ref_id;
            app.globalData.nickname = data.nickname;
            wx.setStorageSync('token', data.token);
            wx.setStorageSync('refreshToken', data.refresh_token);
            wx.setStorageSync('refId', data.ref_id);
            resolve(data);
          }).catch(function(err) {
            reject(err);
          });
        } else {
          wx.showToast({ title: '微信登录失败', icon: 'none' });
          reject(new Error('wx.login failed'));
        }
      },
      fail: function(err) {
        wx.showToast({ title: '微信登录失败', icon: 'none' });
        reject(err);
      }
    });
  });
}

function restoreToken() {
  var app = getApp();
  var token = wx.getStorageSync('token');
  var refreshToken = wx.getStorageSync('refreshToken');
  var refId = wx.getStorageSync('refId');
  if (token) {
    app.globalData.token = token;
    app.globalData.refreshToken = refreshToken;
    app.globalData.refId = refId;
    return true;
  }
  return false;
}

function sendHeartbeat() {
  request({ url: '/api/v1/auth/heartbeat', method: 'POST' }).catch(function() {});
}

function startHeartbeat() {
  stopHeartbeat();
  sendHeartbeat();
  heartbeatTimer = setInterval(function() {
    sendHeartbeat();
  }, 30000);
}

function stopHeartbeat() {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer);
    heartbeatTimer = null;
  }
}

function isTokenValid() {
  var app = getApp();
  return !!(app.globalData && app.globalData.token);
}

module.exports = {
  login: login,
  restoreToken: restoreToken,
  sendHeartbeat: sendHeartbeat,
  startHeartbeat: startHeartbeat,
  stopHeartbeat: stopHeartbeat,
  isTokenValid: isTokenValid
};