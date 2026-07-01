var PREFIX = 'gimi_';

function set(key, value) {
  try {
    wx.setStorageSync(PREFIX + key, value);
  } catch (e) {}
}

function get(key, defaultValue) {
  try {
    var val = wx.getStorageSync(PREFIX + key);
    return val !== '' && val !== undefined ? val : (defaultValue || null);
  } catch (e) {
    return defaultValue || null;
  }
}

function remove(key) {
  try {
    wx.removeStorageSync(PREFIX + key);
  } catch (e) {}
}

function clear() {
  try {
    wx.clearStorageSync();
  } catch (e) {}
}

module.exports = {
  set: set,
  get: get,
  remove: remove,
  clear: clear
};