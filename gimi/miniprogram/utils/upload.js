var config = require('../config/index.js');
var BASE_URL = config.baseUrl;

function getToken() {
  var app = getApp();
  return (app && app.globalData && app.globalData.token) || '';
}

function uploadImage(filePath) {
  return uploadFile(filePath, 'image');
}

function uploadVoice(filePath) {
  return uploadFile(filePath, 'voice');
}

function uploadFile(filePath, type) {
  return new Promise(function(resolve, reject) {
    var token = getToken();
    var header = {};
    if (token) {
      header['Authorization'] = 'Bearer ' + token;
    }

    wx.showNavigationBarLoading();

    wx.uploadFile({
      url: BASE_URL + '/api/v1/media/upload/' + type,
      filePath: filePath,
      name: 'file',
      header: header,
      timeout: 60000,
      success: function(res) {
        wx.hideNavigationBarLoading();
        try {
          var data = JSON.parse(res.data);
          if (data.code === 0) {
            resolve(data.data);
          } else {
            wx.showToast({ title: data.msg || '上传失败', icon: 'none' });
            reject(data);
          }
        } catch (e) {
          wx.showToast({ title: '上传响应解析失败', icon: 'none' });
          reject(e);
        }
      },
      fail: function(err) {
        wx.hideNavigationBarLoading();
        wx.showToast({ title: '上传失败，请检查网络', icon: 'none' });
        reject(err);
      }
    });
  });
}

module.exports = {
  uploadImage: uploadImage,
  uploadVoice: uploadVoice,
  uploadFile: uploadFile
};