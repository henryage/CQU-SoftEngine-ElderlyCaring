// admin-miniprogram/utils/auth.js
var request = require('./request.js').request;
var storage = require('./storage.js');

var heartbeatTimer = null;

// 管理员微信一键登录
function login() {
  return new Promise(function (resolve, reject) {
    wx.login({
      success: function (loginRes) {
        if (loginRes.code) {
          request({
            url: '/auth/admin/login',
            method: 'POST',
            data: { code: loginRes.code }
          }).then(function (data) {
            var app = getApp();
            app.globalData.token = data.token;
            app.globalData.refId = data.ref_id;
            app.globalData.nickname = data.nickname;
            storage.set('token', data.token);
            storage.set('refId', data.ref_id);
            storage.set('nickname', data.nickname);
            resolve(data);
          }).catch(function (err) {
            reject(err);
          });
        } else {
          wx.showToast({ title: '微信登录失败', icon: 'none' });
          reject(new Error('wx.login failed'));
        }
      },
      fail: function (err) {
        wx.showToast({ title: '微信登录失败', icon: 'none' });
        reject(err);
      }
    });
  });
}

// 恢复本地 token 到 globalData
function restoreToken() {
  var app = getApp();
  var token = storage.get('token');
  var refId = storage.get('refId');
  var nickname = storage.get('nickname');
  if (token) {
    app.globalData.token = token;
    app.globalData.refId = refId;
    app.globalData.nickname = nickname;
    return true;
  }
  return false;
}

// 发送心跳（复用老人端接口）
function sendHeartbeat() {
  request({ url: '/api/v1/auth/heartbeat', method: 'POST' }).catch(function () {});
}

// 启动 30 秒心跳
function startHeartbeat() {
  stopHeartbeat();
  sendHeartbeat();
  heartbeatTimer = setInterval(function () {
    sendHeartbeat();
  }, 30000);
}

// 停止心跳
function stopHeartbeat() {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer);
    heartbeatTimer = null;
  }
}

// token 是否有效
function isTokenValid() {
  var app = getApp();
  return !!(app.globalData && app.globalData.token);
}

// 退出登录
function logout() {
  stopHeartbeat();
  storage.remove('token');
  storage.remove('refId');
  storage.remove('nickname');
  var app = getApp();
  app.globalData.token = '';
  app.globalData.refId = null;
  app.globalData.nickname = '';
}

module.exports = {
  login: login,
  restoreToken: restoreToken,
  sendHeartbeat: sendHeartbeat,
  startHeartbeat: startHeartbeat,
  stopHeartbeat: stopHeartbeat,
  isTokenValid: isTokenValid,
  logout: logout
};
