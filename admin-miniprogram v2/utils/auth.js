// admin-miniprogram/utils/auth.js
var request = require('./request.js').request;
var storage = require('./storage.js');

// 管理员登录
function login(username, password) {
  return new Promise(function (resolve, reject) {
    request({
      url: '/api/v1/auth/admin/login',
      method: 'POST',
      data: { username: username, password: password }
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

// token 是否有效
function isTokenValid() {
  var app = getApp();
  return !!(app.globalData && app.globalData.token);
}

// 退出登录
function logout() {
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
  isTokenValid: isTokenValid,
  logout: logout
};
