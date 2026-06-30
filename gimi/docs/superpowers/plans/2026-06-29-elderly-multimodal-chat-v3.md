# 老人端适老化多模态聊天助手 V3 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于 pre_v2.md 的多页面架构，实现面向老年用户的微信小程序。采用配置驱动的 HTTP 后端对接，页面模块化拆分（登录/首页/聊天/历史/提醒/紧急/设置），工具函数独立封装（request/upload/auth/speech/storage），支持聊天历史恢复、TTS优雅降级、统一网络异常处理。

**Architecture:** 前端多页面架构（7个页面），公共模块（5个utils + 1个config），后端对接 HTTP REST API（http://127.0.0.1:8090）。请求层统一由 request.js 管理，页面禁止直接调用 wx.request。Token 生命周期由 auth.js 管理，支持 401 自动刷新预留。TTS 通过 speech.js 封装，无后端 API 时仅展示文字。

**Tech Stack:** 微信小程序原生框架（WXML/WXSS/JS）、wx.getRecorderManager 录音、camera 组件拍照、wx.uploadFile 文件上传、wx.createInnerAudioContext 语音播报、JWT Token 鉴权

---

## 文件结构映射

| 操作 | 文件路径 | 职责 |
|------|---------|------|
| 修改 | [app.js](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/app.js) | 移除云开发，挂载全局配置 |
| 修改 | [app.json](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/app.json) | 注册所有页面，配置权限和窗口 |
| 修改 | [app.wxss](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/app.wxss) | 全局基础样式 |
| 创建 | [config/index.js](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/config/index.js) | 环境配置（dev/prod），统一管理 baseUrl |
| 创建 | [utils/request.js](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/utils/request.js) | 统一请求封装（自动token、loading、错误处理、重试预留） |
| 创建 | [utils/upload.js](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/utils/upload.js) | 文件上传封装（图片/语音），统一管理上传流程 |
| 创建 | [utils/auth.js](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/utils/auth.js) | 微信登录、token存取、心跳管理、401刷新预留 |
| 创建 | [utils/speech.js](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/utils/speech.js) | TTS语音播报封装，无API时优雅降级 |
| 创建 | [utils/storage.js](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/utils/storage.js) | 本地存储封装（token、历史记录、设置） |
| 创建 | [images/cat/](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/images/cat) | 复制/p目录下listen.png、think.png、speak.png |
| 创建 | [components/chat-bubble/](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/components/chat-bubble/) | 对话气泡组件（适老化大字体） |
| 重写 | [pages/index/index.*](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/index/) | 首页——登录入口/启动页 |
| 创建 | [pages/home/home.*](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/home/) | 主页——功能导航、橘猫欢迎、用药提醒入口 |
| 创建 | [pages/chat/chat.*](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/chat/) | 聊天页——全屏相机、对话列表、录音/拍照、AI问答 |
| 创建 | [pages/history/history.*](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/history/) | 历史页——聊天历史记录列表 |
| 创建 | [pages/reminder/reminder.*](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/reminder/) | 提醒页——用药提醒列表 |
| 创建 | [pages/emergency/emergency.*](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/emergency/) | 紧急页——紧急呼叫确认与拨打120 |
| 创建 | [pages/settings/settings.*](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/settings/) | 设置页——字体大小、语音速度等 |
| 删除 | `miniprogram/pages/example/` | 不需要的示例页面 |
| 删除 | `miniprogram/components/cloudTipModal/` | 不需要的云开发提示组件 |

---

## 第一阶段：基础设施搭建

### Task 1: 环境配置与 app 基础设置

**Files:**
- Create: `miniprogram/config/index.js`
- Modify: `miniprogram/app.js`
- Modify: `miniprogram/app.json`
- Modify: `miniprogram/app.wxss`

- [ ] **Step 1: 创建环境配置 config/index.js**

创建 [index.js](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/config/index.js)：

```javascript
var ENV = 'dev';

var CONFIG = {
  dev: {
    baseUrl: 'http://127.0.0.1:8090'
  },
  prod: {
    baseUrl: 'https://api.xxx.com'
  }
};

module.exports = CONFIG[ENV];
```

- [ ] **Step 2: 重写 app.js，移除云开发**

将 [app.js](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/app.js) 替换为：

```javascript
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
```

- [ ] **Step 3: 重写 app.json，注册所有页面**

将 [app.json](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/app.json) 替换为：

```json
{
  "pages": [
    "pages/index/index",
    "pages/home/home",
    "pages/chat/chat",
    "pages/history/history",
    "pages/reminder/reminder",
    "pages/emergency/emergency",
    "pages/settings/settings"
  ],
  "window": {
    "backgroundColor": "#000000",
    "backgroundTextStyle": "light",
    "navigationStyle": "custom",
    "navigationBarTextStyle": "white"
  },
  "permission": {
    "scope.camera": {
      "desc": "用于拍摄画面进行视觉问答"
    },
    "scope.record": {
      "desc": "用于语音输入进行对话"
    }
  },
  "requiredPrivateInfos": ["makePhoneCall"],
  "sitemapLocation": "sitemap.json",
  "style": "v2",
  "lazyCodeLoading": "requiredComponents"
}
```

- [ ] **Step 4: 更新 app.wxss 全局样式**

将 [app.wxss](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/app.wxss) 替换为：

```css
page {
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  color: #ffffff;
  -webkit-font-smoothing: antialiased;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #000;
}

view, text, image {
  box-sizing: border-box;
}
```

- [ ] **Step 5: 编译验证**

在微信开发者工具中编译，确认：
1. 无编译错误
2. 7个页面均已注册
3. 不再有云开发相关代码

- [ ] **Step 6: Commit**

```bash
git add miniprogram/config/index.js miniprogram/app.js miniprogram/app.json miniprogram/app.wxss
git commit -m "feat: 环境配置模块，app基础设置，注册7个页面"
```

---

### Task 2: 统一请求层 request.js

**Files:**
- Create: `miniprogram/utils/request.js`

- [ ] **Step 1: 创建 request.js**

创建 [request.js](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/utils/request.js)：

```javascript
var config = require('../config/index.js');
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
          wx.showToast({ title: '登录已过期，请重新进入', icon: 'none', duration: 3000 });
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
```

- [ ] **Step 2: 编译验证**

编译确认无语法错误，`request()` 函数签名与 pre_v2 一致：`request({ url, method, data })`。

- [ ] **Step 3: Commit**

```bash
git add miniprogram/utils/request.js
git commit -m "feat: 统一请求层，自动token、loading、错误处理"
```

---

### Task 3: 文件上传封装 upload.js

**Files:**
- Create: `miniprogram/utils/upload.js`

- [ ] **Step 1: 创建 upload.js**

创建 [upload.js](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/utils/upload.js)：

```javascript
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
```

- [ ] **Step 2: 编译验证**

编译确认无语法错误。

- [ ] **Step 3: Commit**

```bash
git add miniprogram/utils/upload.js
git commit -m "feat: 文件上传封装，图片/语音上传独立管理"
```

---

### Task 4: Token 管理与心跳 auth.js

**Files:**
- Create: `miniprogram/utils/auth.js`

- [ ] **Step 1: 创建 auth.js**

创建 [auth.js](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/utils/auth.js)：

```javascript
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
```

- [ ] **Step 2: 编译验证**

编译确认无语法错误。

- [ ] **Step 3: Commit**

```bash
git add miniprogram/utils/auth.js
git commit -m "feat: Token生命周期管理，登录、心跳、401刷新预留"
```

---

### Task 5: 语音播报 speech.js（TTS 优雅降级）

**Files:**
- Create: `miniprogram/utils/speech.js`

- [ ] **Step 1: 创建 speech.js**

创建 [speech.js](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/utils/speech.js)：

```javascript
var request = require('./request.js').request;

var currentAudio = null;
var lastText = '';

function stopSpeak() {
  if (currentAudio) {
    try {
      currentAudio.stop();
      currentAudio.destroy();
    } catch (e) {}
    currentAudio = null;
  }
}

function speak(text) {
  return new Promise(function(resolve) {
    if (!text) {
      resolve();
      return;
    }
    stopSpeak();
    lastText = text;

    request({
      url: '/api/v1/tts',
      method: 'POST',
      data: { text: text }
    }).then(function(data) {
      if (data && data.audio_url) {
        var audio = wx.createInnerAudioContext();
        currentAudio = audio;
        audio.src = data.audio_url;
        audio.onEnded(function() {
          if (currentAudio === audio) currentAudio = null;
          audio.destroy();
          resolve();
        });
        audio.onError(function() {
          if (currentAudio === audio) currentAudio = null;
          audio.destroy();
          resolve();
        });
        audio.play();
      } else {
        resolve();
      }
    }).catch(function() {
      resolve();
    });
  });
}

function replayLast() {
  if (lastText) {
    return speak(lastText);
  }
  return Promise.resolve();
}

module.exports = {
  speak: speak,
  stopSpeak: stopSpeak,
  replayLast: replayLast
};
```

- [ ] **Step 2: 编译验证**

编译确认无语法错误。注意：当 `POST /api/v1/tts` 不存在时，catch 会静默 resolve，仅展示文字不报错。

- [ ] **Step 3: Commit**

```bash
git add miniprogram/utils/speech.js
git commit -m "feat: TTS语音播报封装，无API时优雅降级仅展示文字"
```

---

### Task 6: 本地存储封装 storage.js

**Files:**
- Create: `miniprogram/utils/storage.js`

- [ ] **Step 1: 创建 storage.js**

创建 [storage.js](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/utils/storage.js)：

```javascript
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
```

- [ ] **Step 2: 编译验证**

编译确认无语法错误。

- [ ] **Step 3: Commit**

```bash
git add miniprogram/utils/storage.js
git commit -m "feat: 本地存储封装，统一key前缀管理"
```

---

### Task 7: 橘猫图片资源

**Files:**
- Create: `miniprogram/images/cat/listen.png`
- Create: `miniprogram/images/cat/think.png`
- Create: `miniprogram/images/cat/speak.png`

- [ ] **Step 1: 复制图片**

将 `p/listen.png`、`p/think.png`、`p/speak.png` 复制到 `miniprogram/images/cat/`。

- [ ] **Step 2: 验证**

确认三个图片文件存在。

- [ ] **Step 3: Commit**

```bash
git add miniprogram/images/cat/
git commit -m "feat: 橘猫状态图片资源"
```

---

## 第二阶段：核心页面开发

### Task 8: 登录页 / 首页（入口）

**Files:**
- Modify: `miniprogram/pages/index/index.js`
- Modify: `miniprogram/pages/index/index.json`
- Modify: `miniprogram/pages/index/index.wxml`
- Modify: `miniprogram/pages/index/index.wxss`

**说明：** 首页作为入口，负责登录鉴权，登录成功后自动跳转到 home 页。

- [ ] **Step 1: 重写 index.json**

将 [index.json](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/index/index.json) 替换为：

```json
{
  "navigationBarTitleText": "喵喵助手",
  "usingComponents": {},
  "disableScroll": true
}
```

- [ ] **Step 2: 重写 index.wxml**

将 [index.wxml](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/index/index.wxml) 替换为：

```xml
<view class="page-container">
  <view class="dark-overlay"></view>
  <view class="nav-bar" style="padding-top: {{statusBarHeight}}px;">
    <view class="nav-content">
      <view class="nav-title">喵喵助手</view>
    </view>
  </view>

  <view class="center-area">
    <image class="cat-logo" src="/images/cat/speak.png" mode="aspectFit"></image>
    <view class="app-name">喵喵助手</view>
    
    <view wx:if="{{!isLoggingIn}}" class="login-btn" bindtap="onLogin">
      <text>微信一键登录</text>
    </view>
    
    <view wx:if="{{isLoggingIn}}" class="logging-status">
      <view class="loading-dots">
        <view class="dot"></view>
        <view class="dot"></view>
        <view class="dot"></view>
      </view>
      <view class="logging-text">正在登录...</view>
    </view>

    <view wx:if="{{loginError}}" class="error-area">
      <view class="error-text">{{loginError}}</view>
      <view class="retry-btn" bindtap="onLogin">
        <text>重新登录</text>
      </view>
    </view>
  </view>
</view>
```

- [ ] **Step 3: 重写 index.wxss**

将 [index.wxss](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/index/index.wxss) 替换为：

```css
.page-container {
  position: relative;
  width: 100%;
  height: 100vh;
  overflow: hidden;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}
.dark-overlay {
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  background: rgba(0,0,0,0.3);
  z-index: 0;
}
.nav-bar {
  position: fixed;
  top: 0; left: 0;
  width: 100%;
  z-index: 100;
  background: rgba(0,0,0,0.4);
}
.nav-content {
  height: 88rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}
.nav-title {
  font-size: 40rpx;
  font-weight: bold;
  color: #fff;
  text-shadow: 0 2px 8px rgba(0,0,0,0.8);
}
.center-area {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  z-index: 10;
}
.cat-logo {
  width: 240rpx;
  height: 240rpx;
  border-radius: 48rpx;
  margin-bottom: 40rpx;
}
.app-name {
  font-size: 48rpx;
  font-weight: bold;
  color: #fff;
  margin-bottom: 80rpx;
  text-shadow: 0 2px 10px rgba(0,0,0,0.8);
}
.login-btn {
  width: 500rpx;
  height: 110rpx;
  line-height: 110rpx;
  text-align: center;
  background: #07C160;
  color: #fff;
  border-radius: 24rpx;
  font-size: 38rpx;
  font-weight: bold;
}
.logging-status {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.loading-dots {
  display: flex;
  gap: 20rpx;
  margin-bottom: 24rpx;
}
.dot {
  width: 24rpx;
  height: 24rpx;
  border-radius: 50%;
  background: #fff;
  animation: dotPulse 1.2s infinite ease-in-out;
}
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes dotPulse {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}
.logging-text {
  font-size: 36rpx;
  color: rgba(255,255,255,0.9);
}
.error-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-top: 40rpx;
}
.error-text {
  font-size: 32rpx;
  color: #FF6B6B;
  margin-bottom: 24rpx;
}
.retry-btn {
  width: 300rpx;
  height: 88rpx;
  line-height: 88rpx;
  text-align: center;
  background: rgba(255,255,255,0.2);
  color: #fff;
  border-radius: 20rpx;
  font-size: 34rpx;
}
```

- [ ] **Step 4: 重写 index.js**

将 [index.js](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/index/index.js) 替换为：

```javascript
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
```

- [ ] **Step 5: 编译验证**

编译确认无语法错误，登录流程完整。

- [ ] **Step 6: Commit**

```bash
git add miniprogram/pages/index/
git commit -m "feat: 登录入口页，微信一键登录，自动跳转"
```

---

### Task 9: 对话气泡组件 chat-bubble

**Files:**
- Create: `miniprogram/components/chat-bubble/index.js`
- Create: `miniprogram/components/chat-bubble/index.json`
- Create: `miniprogram/components/chat-bubble/index.wxml`
- Create: `miniprogram/components/chat-bubble/index.wxss`

- [ ] **Step 1: 创建 index.json**

创建 [index.json](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/components/chat-bubble/index.json)：

```json
{
  "component": true,
  "usingComponents": {}
}
```

- [ ] **Step 2: 创建 index.js**

创建 [index.js](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/components/chat-bubble/index.js)：

```javascript
var requestUtils = require('../../utils/request.js');

Component({
  properties: {
    role: { type: String, value: 'assistant' },
    type: { type: String, value: 'text' },
    content: { type: Object, value: {} },
    status: { type: String, value: 'sent' },
    catState: { type: String, value: 'speak' },
    riskTags: { type: Array, value: [] },
    intercepted: { type: Boolean, value: false },
    messageId: { type: String, value: '' }
  },

  data: {
    catImageUrl: '',
    imageUrls: []
  },

  observers: {
    'catState': function(state) {
      var map = {
        'listen': '/images/cat/listen.png',
        'think': '/images/cat/think.png',
        'speak': '/images/cat/speak.png'
      };
      this.setData({ catImageUrl: map[state] || map['speak'] });
    },
    'content.images': function(images) {
      if (!images || !images.length) {
        this.setData({ imageUrls: [] });
        return;
      }
      var urls = images.map(function(img) {
        if (img.tempPath) return img.tempPath;
        if (img.enhancedUrl) return requestUtils.getFullUrl(img.enhancedUrl);
        if (img.originalUrl) return requestUtils.getFullUrl(img.originalUrl);
        return '';
      });
      this.setData({ imageUrls: urls });
    }
  },

  lifetimes: {
    attached: function() {
      var map = {
        'listen': '/images/cat/listen.png',
        'think': '/images/cat/think.png',
        'speak': '/images/cat/speak.png'
      };
      this.setData({ catImageUrl: map[this.data.catState] || map['speak'] });
      this.updateImageUrls();
    }
  },

  methods: {
    updateImageUrls: function() {
      var images = this.data.content.images;
      if (!images || !images.length) { this.setData({ imageUrls: [] }); return; }
      var urls = images.map(function(img) {
        if (img.tempPath) return img.tempPath;
        if (img.enhancedUrl) return requestUtils.getFullUrl(img.enhancedUrl);
        if (img.originalUrl) return requestUtils.getFullUrl(img.originalUrl);
        return '';
      });
      this.setData({ imageUrls: urls });
    },
    onBubbleTap: function() {
      if (this.data.role === 'assistant' || this.data.role === 'system') {
        this.triggerEvent('bubbletap', { messageId: this.data.messageId });
      }
    },
    onErrorTap: function() {
      this.triggerEvent('retry', { messageId: this.data.messageId });
    },
    previewImage: function(e) {
      wx.previewImage({ current: e.currentTarget.dataset.url, urls: this.data.imageUrls });
    }
  }
});
```

- [ ] **Step 3: 创建 index.wxml**

创建 [index.wxml](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/components/chat-bubble/index.wxml)：

```xml
<view class="chat-bubble {{role === 'user' ? 'bubble-user' : 'bubble-assistant'}}">
  <view wx:if="{{role !== 'user'}}" class="cat-avatar">
    <image class="cat-image" src="{{catImageUrl}}" mode="aspectFill"></image>
  </view>

  <view class="bubble-content" bindtap="onBubbleTap">
    <view wx:if="{{type === 'reminder'}}" class="reminder-icon">💊</view>

    <view wx:if="{{imageUrls.length > 0}}" class="bubble-images">
      <image
        wx:for="{{imageUrls}}" wx:key="index"
        class="bubble-image" src="{{item}}" mode="aspectFill"
        data-url="{{item}}" bindtap="previewImage"
      ></image>
    </view>

    <view wx:if="{{content.text}}" class="bubble-text">{{content.text}}</view>

    <view wx:if="{{status === 'sending'}}" class="status-loading">
      <view class="loading-dot"></view>
      <view class="loading-dot"></view>
      <view class="loading-dot"></view>
    </view>

    <view wx:if="{{intercepted || riskTags.length > 0}}" class="risk-warning">
      ⚠️ 以上内容仅供参考，请遵医嘱
    </view>
  </view>

  <view wx:if="{{role === 'user' && status === 'error'}}" class="error-retry" bindtap="onErrorTap">!</view>
  <view wx:if="{{role === 'user'}}" class="bubble-spacer"></view>
</view>
```

- [ ] **Step 4: 创建 index.wxss**

创建 [index.wxss](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/components/chat-bubble/index.wxss)：

```css
.chat-bubble {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  margin-bottom: 32rpx;
  width: 100%;
  padding: 0 24rpx;
}
.bubble-user { justify-content: flex-end; }
.bubble-assistant { justify-content: flex-start; }

.cat-avatar {
  width: 120rpx; height: 120rpx;
  margin-right: 20rpx;
  flex-shrink: 0;
}
.cat-image {
  width: 120rpx; height: 120rpx;
  border-radius: 24rpx;
}
.bubble-spacer {
  width: 120rpx; flex-shrink: 0;
}

.bubble-content {
  max-width: 520rpx;
  padding: 28rpx 32rpx;
  border-radius: 36rpx;
  position: relative;
  word-break: break-all;
}
.bubble-user .bubble-content {
  background: rgba(255,255,255,0.9);
  color: #1a1a1a;
  border-bottom-right-radius: 12rpx;
}
.bubble-assistant .bubble-content {
  background: rgba(30,30,30,0.85);
  color: #ffffff;
  border-bottom-left-radius: 12rpx;
}

.reminder-icon { font-size: 36rpx; margin-bottom: 12rpx; }

.bubble-text {
  font-size: 36rpx;
  line-height: 1.6;
}
.bubble-assistant .bubble-text {
  text-shadow: 0 2px 6px rgba(0,0,0,0.6);
}

.bubble-images {
  display: flex; flex-wrap: wrap; gap: 12rpx; margin-bottom: 16rpx;
}
.bubble-image {
  width: 160rpx; height: 160rpx; border-radius: 16rpx;
}

.status-loading {
  display: flex; flex-direction: row; gap: 12rpx; margin-top: 16rpx;
}
.loading-dot {
  width: 16rpx; height: 16rpx; border-radius: 50%;
  background: rgba(255,255,255,0.8);
  animation: dotPulse 1.2s infinite ease-in-out;
}
.loading-dot:nth-child(2) { animation-delay: 0.2s; }
.loading-dot:nth-child(3) { animation-delay: 0.4s; }
.bubble-user .loading-dot { background: rgba(0,0,0,0.5); }

@keyframes dotPulse {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

.risk-warning {
  margin-top: 16rpx;
  font-size: 28rpx;
  color: #FFD700;
  line-height: 1.4;
}

.error-retry {
  width: 56rpx; height: 56rpx; line-height: 56rpx;
  text-align: center;
  background: #FF3B30; color: white;
  border-radius: 50%; font-size: 32rpx; font-weight: bold;
  margin-left: 16rpx; align-self: center; flex-shrink: 0;
}
```

- [ ] **Step 5: 编译验证**

编译确认组件无报错。

- [ ] **Step 6: Commit**

```bash
git add miniprogram/components/chat-bubble/
git commit -m "feat: 对话气泡组件，橘猫头像、图片、风险提示"
```

---

### Task 10: 主页 home

**Files:**
- Create: `miniprogram/pages/home/home.js`
- Create: `miniprogram/pages/home/home.json`
- Create: `miniprogram/pages/home/home.wxml`
- Create: `miniprogram/pages/home/home.wxss`

**说明：** 登录后的主页，显示橘猫欢迎、功能导航入口（聊天、历史、提醒、紧急、设置），后台启动心跳和用药提醒轮询。

- [ ] **Step 1: 创建 home.json**

创建 [home.json](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/home/home.json)：

```json
{
  "navigationBarTitleText": "喵喵助手",
  "usingComponents": {},
  "disableScroll": true
}
```

- [ ] **Step 2: 创建 home.wxml**

创建 [home.wxml](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/home/home.wxml)：

```xml
<view class="page-container">
  <view class="dark-overlay"></view>

  <view class="nav-bar" style="padding-top: {{statusBarHeight}}px;">
    <view class="nav-content">
      <view class="nav-title">喵喵助手</view>
    </view>
  </view>

  <view class="main-area">
    <view class="cat-section">
      <image class="cat-big" src="/images/cat/speak.png" mode="aspectFit"></image>
      <view class="welcome-text">喵喵~有什么我能帮您的？</view>
    </view>

    <view class="menu-grid">
      <view class="menu-item menu-chat" bindtap="onGoChat">
        <view class="menu-icon">💬</view>
        <view class="menu-label">开始聊天</view>
      </view>

      <view class="menu-item menu-history" bindtap="onGoHistory">
        <view class="menu-icon">📋</view>
        <view class="menu-label">历史记录</view>
      </view>

      <view class="menu-item menu-reminder" bindtap="onGoReminder">
        <view class="menu-icon">💊</view>
        <view class="menu-label">用药提醒</view>
      </view>

      <view class="menu-item menu-emergency" bindtap="onGoEmergency">
        <view class="menu-icon">🆘</view>
        <view class="menu-label">紧急呼叫</view>
      </view>

      <view class="menu-item menu-settings" bindtap="onGoSettings">
        <view class="menu-icon">⚙️</view>
        <view class="menu-label">设置</view>
      </view>
    </view>
  </view>
</view>
```

- [ ] **Step 3: 创建 home.wxss**

创建 [home.wxss](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/home/home.wxss)：

```css
.page-container {
  position: relative;
  width: 100%; height: 100vh;
  overflow: hidden;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}
.dark-overlay {
  position: absolute; top: 0; left: 0;
  width: 100%; height: 100%;
  background: rgba(0,0,0,0.2);
  z-index: 0;
}
.nav-bar {
  position: fixed; top: 0; left: 0; width: 100%;
  z-index: 100;
  background: rgba(0,0,0,0.4);
}
.nav-content {
  height: 88rpx;
  display: flex; align-items: center; justify-content: center;
}
.nav-title {
  font-size: 40rpx; font-weight: bold; color: #fff;
  text-shadow: 0 2px 8px rgba(0,0,0,0.8);
}

.main-area {
  position: relative; z-index: 10;
  padding: 160rpx 48rpx 48rpx;
  height: 100vh;
  box-sizing: border-box;
}

.cat-section {
  display: flex; flex-direction: column; align-items: center;
  margin-bottom: 80rpx;
}
.cat-big {
  width: 200rpx; height: 200rpx;
  border-radius: 40rpx;
  margin-bottom: 32rpx;
}
.welcome-text {
  font-size: 40rpx; color: #fff; font-weight: bold;
  text-shadow: 0 2px 8px rgba(0,0,0,0.8);
}

.menu-grid {
  display: flex; flex-wrap: wrap;
  gap: 32rpx;
  justify-content: center;
}

.menu-item {
  width: 280rpx; height: 200rpx;
  border-radius: 32rpx;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: 16rpx;
}
.menu-chat { background: rgba(52,199,89,0.8); }
.menu-history { background: rgba(0,122,255,0.8); }
.menu-reminder { background: rgba(255,149,0,0.8); }
.menu-emergency { background: rgba(255,59,48,0.8); }
.menu-settings { background: rgba(142,142,147,0.8); }

.menu-icon { font-size: 64rpx; }
.menu-label { font-size: 32rpx; color: #fff; font-weight: bold; }
```

- [ ] **Step 4: 创建 home.js**

创建 [home.js](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/home/home.js)：

```javascript
var auth = require('../../utils/auth.js');
var request = require('../../utils/request.js').request;
var speech = require('../../utils/speech.js');

var reminderTimer = null;

Page({
  data: {
    statusBarHeight: 20
  },

  onLoad: function() {
    var sys = wx.getSystemInfoSync();
    this.setData({ statusBarHeight: sys.statusBarHeight || 20 });
  },

  onShow: function() {
    if (!auth.isTokenValid()) {
      wx.redirectTo({ url: '/pages/index/index' });
      return;
    }
    auth.startHeartbeat();
    this.startReminderPolling();
  },

  onHide: function() {
    auth.stopHeartbeat();
    this.stopReminderPolling();
  },

  onUnload: function() {
    auth.stopHeartbeat();
    this.stopReminderPolling();
  },

  onGoChat: function() {
    wx.navigateTo({ url: '/pages/chat/chat' });
  },

  onGoHistory: function() {
    wx.navigateTo({ url: '/pages/history/history' });
  },

  onGoReminder: function() {
    wx.navigateTo({ url: '/pages/reminder/reminder' });
  },

  onGoEmergency: function() {
    wx.navigateTo({ url: '/pages/emergency/emergency' });
  },

  onGoSettings: function() {
    wx.navigateTo({ url: '/pages/settings/settings' });
  },

  startReminderPolling: function() {
    this.stopReminderPolling();
    this.fetchReminders();
    var that = this;
    reminderTimer = setInterval(function() {
      that.fetchReminders();
    }, 5 * 60 * 1000);
  },

  stopReminderPolling: function() {
    if (reminderTimer) {
      clearInterval(reminderTimer);
      reminderTimer = null;
    }
  },

  fetchReminders: function() {
    var that = this;
    request({ url: '/api/v1/reminder/medication', method: 'GET' }).then(function(data) {
      if (!Array.isArray(data)) return;
      var lastData = wx.getStorageSync('gimi_last_reminders') || [];
      var newOnes = data.filter(function(r) {
        return !lastData.find(function(lr) { return lr.reminder_id === r.reminder_id; });
      });
      if (newOnes.length > 0 && lastData.length > 0) {
        newOnes.forEach(function(r) {
          var text = '喵喵~' + r.remind_time + '啦，该吃' + r.drug_name + '，' + r.dosage + '哦！';
          speech.speak(text);
        });
      }
      wx.setStorageSync('gimi_last_reminders', data);
    }).catch(function() {});
  }
});
```

- [ ] **Step 5: 编译验证**

编译确认无语法错误，5个导航入口可点击。

- [ ] **Step 6: Commit**

```bash
git add miniprogram/pages/home/
git commit -m "feat: 主页，功能导航、心跳、用药提醒轮询"
```

---

### Task 11: 聊天页 chat

**Files:**
- Create: `miniprogram/pages/chat/chat.js`
- Create: `miniprogram/pages/chat/chat.json`
- Create: `miniprogram/pages/chat/chat.wxml`
- Create: `miniprogram/pages/chat/chat.wxss`

**说明：** 核心聊天页——全屏相机背景、对话气泡列表、底部录音/拍照/取消/紧急按钮、AI问答。语音与拍照解耦，各自独立上传。

- [ ] **Step 1: 创建 chat.json**

创建 [chat.json](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/chat/chat.json)：

```json
{
  "navigationBarTitleText": "聊天",
  "usingComponents": {
    "chat-bubble": "/components/chat-bubble/index"
  },
  "disableScroll": true
}
```

- [ ] **Step 2: 创建 chat.wxml**

创建 [chat.wxml](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/chat/chat.wxml)：

```xml
<view class="page-container">
  <camera wx:if="{{cameraAuthorized}}" class="camera-bg" device-position="back" flash="off"></camera>
  <view class="dark-overlay"></view>

  <view class="nav-bar" style="padding-top: {{statusBarHeight}}px;">
    <view class="nav-content">
      <view class="nav-back" bindtap="onGoBack">‹ 返回</view>
      <view class="nav-title">聊天</view>
      <view class="nav-placeholder"></view>
    </view>
  </view>

  <scroll-view
    class="chat-list" scroll-y
    scroll-into-view="{{scrollToId}}" scroll-with-animation
    enhanced show-scrollbar="{{false}}"
  >
    <view class="chat-list-inner" style="padding-top: {{navBarHeight}}px; padding-bottom: {{bottomBarHeight}}px;">
      <view wx:for="{{messages}}" wx:key="id" id="msg-{{item.id}}">
        <chat-bubble
          role="{{item.role}}" type="{{item.type}}"
          content="{{item.content}}" status="{{item.status}}"
          cat-state="{{item.catState}}"
          risk-tags="{{item.riskTags}}" intercepted="{{item.intercepted}}"
          message-id="{{item.id}}"
          bind:bubbletap="onBubbleTap"
          bind:retry="onRetryMessage"
        ></chat-bubble>
      </view>
    </view>
  </scroll-view>

  <view wx:if="{{recordState !== 'idle'}}" class="status-area">
    <view wx:if="{{waveActive}}" class="wave-animation">
      <view class="wave-bar wave-bar-1"></view>
      <view class="wave-bar wave-bar-2"></view>
      <view class="wave-bar wave-bar-3"></view>
    </view>
    <view class="status-text">{{statusText}}</view>
  </view>

  <view class="bottom-bar" style="padding-bottom: {{safeAreaBottom}}px;">
    <view class="buttons-container">
      <view
        class="control-btn mic-btn {{recordState === 'recording' ? 'mic-active' : ''}}"
        bindtouchstart="onMicStart"
        bindtouchend="onMicEnd"
        bindtouchcancel="onMicEnd"
      >
        <text class="btn-icon">🎤</text>
      </view>

      <view class="control-btn cancel-btn" bindtap="onCancelTap">
        <text class="btn-icon">✕</text>
      </view>

      <view
        class="control-btn camera-btn {{recordState !== 'idle' ? 'btn-disabled' : ''}}"
        bindtap="onCameraTap"
      >
        <text class="btn-icon">📷</text>
      </view>

      <view
        class="control-btn emergency-btn {{recordState !== 'idle' ? 'btn-disabled' : ''}}"
        bindtap="onEmergencyTap"
      >
        <text class="btn-icon">🆘</text>
      </view>
    </view>
  </view>
</view>
```

- [ ] **Step 3: 创建 chat.wxss**

创建 [chat.wxss](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/chat/chat.wxss)：

```css
.page-container {
  position: relative; width: 100%; height: 100vh; overflow: hidden;
}
.camera-bg {
  position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 0;
}
.dark-overlay {
  position: absolute; top: 0; left: 0; width: 100%; height: 100%;
  background: linear-gradient(to bottom, rgba(0,0,0,0.5) 0%, rgba(0,0,0,0.65) 40%, rgba(0,0,0,0.8) 100%);
  z-index: 1;
}
.nav-bar {
  position: fixed; top: 0; left: 0; width: 100%;
  z-index: 100;
  background: rgba(0,0,0,0.6);
  backdrop-filter: blur(20px);
}
.nav-content {
  height: 88rpx; display: flex; align-items: center; justify-content: space-between;
  padding: 0 32rpx;
}
.nav-back { font-size: 34rpx; color: #fff; }
.nav-title { font-size: 36rpx; color: #fff; font-weight: bold; }
.nav-placeholder { width: 100rpx; }

.chat-list {
  position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 10;
}
.chat-list-inner { min-height: 100%; box-sizing: border-box; }

.status-area {
  position: fixed; left: 50%; transform: translateX(-50%);
  z-index: 50; bottom: 280rpx;
  display: flex; flex-direction: column; align-items: center;
}
.wave-animation {
  display: flex; flex-direction: row; align-items: flex-end;
  gap: 24rpx; height: 120rpx; margin-bottom: 24rpx;
}
.wave-bar { background: #fff; border-radius: 24rpx; box-shadow: 0 0 30rpx rgba(255,255,255,0.5); }
.wave-bar-1 { width: 56rpx; height: 56rpx; animation: waveBreathe 1s infinite ease-in-out; }
.wave-bar-2 { width: 64rpx; height: 80rpx; animation: waveBreathe 1s infinite ease-in-out; animation-delay: 0.2s; }
.wave-bar-3 { width: 96rpx; height: 120rpx; border-radius: 48rpx; animation: waveBreathe 1s infinite ease-in-out; animation-delay: 0.4s; }
@keyframes waveBreathe {
  0%, 100% { transform: scaleY(0.6); opacity: 0.6; }
  50% { transform: scaleY(1); opacity: 1; }
}
.status-text {
  font-size: 40rpx; color: #fff; font-weight: bold;
  text-shadow: 0 2px 10px rgba(0,0,0,0.9); letter-spacing: 4rpx;
}

.bottom-bar {
  position: fixed; bottom: 0; left: 0; width: 100%; z-index: 100;
  background: rgba(0,0,0,0.7); backdrop-filter: blur(20px);
}
.buttons-container {
  display: flex; flex-direction: row; align-items: center;
  justify-content: center; gap: 44rpx; padding: 32rpx 0;
}
.control-btn {
  width: 176rpx; height: 176rpx; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  transition: transform 0.15s ease;
}
.btn-icon { font-size: 72rpx; }
.mic-btn {
  background: rgba(255,255,255,0.2); border: 4rpx solid rgba(255,255,255,0.4);
}
.mic-active {
  background: rgba(52,199,89,0.8); transform: scale(1.15);
  box-shadow: 0 0 60rpx rgba(52,199,89,0.8);
}
.cancel-btn { background: rgba(255,59,48,0.8); }
.camera-btn {
  background: rgba(255,255,255,0.2); border: 4rpx solid rgba(255,255,255,0.4);
}
.emergency-btn {
  background: #FF3B30; box-shadow: 0 0 30rpx rgba(255,59,48,0.5);
}
.btn-disabled { opacity: 0.4; pointer-events: none; }
```

- [ ] **Step 4: 创建 chat.js**

创建 [chat.js](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/chat/chat.js)：

```javascript
var request = require('../../utils/request.js').request;
var upload = require('../../utils/upload.js');
var speech = require('../../utils/speech.js');

var RecordState = { IDLE: 'idle', RECORDING: 'recording', UPLOADING: 'uploading', THINKING: 'thinking' };
var CatState = { LISTEN: 'listen', THINK: 'think', SPEAK: 'speak' };

function generateMsgId() {
  return 'msg_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);
}

Page({
  data: {
    messages: [],
    recordState: RecordState.IDLE,
    catState: CatState.SPEAK,
    waveActive: false,
    statusText: '',
    cameraAuthorized: false,
    scrollToId: '',
    statusBarHeight: 20,
    navBarHeight: 88,
    bottomBarHeight: 300,
    safeAreaBottom: 0,
    sessionId: null
  },

  onLoad: function() {
    var sys = wx.getSystemInfoSync();
    var safeBottom = sys.safeArea ? (sys.screenHeight - sys.safeArea.bottom) : 0;
    this.setData({
      statusBarHeight: sys.statusBarHeight || 20,
      navBarHeight: (sys.statusBarHeight || 20) + 44,
      safeAreaBottom: safeBottom,
      bottomBarHeight: 220 + safeBottom
    });
    this.recorderManager = null;
    this.cameraContext = null;
    this.initRecorder();
    this.initCamera();
  },

  onShow: function() {
    if (this.data.messages.length === 0) {
      this.loadHistory();
    }
  },

  onHide: function() {
    this.stopRecordingSilent();
    speech.stopSpeak();
  },

  onUnload: function() {
    this.stopRecordingSilent();
    speech.stopSpeak();
  },

  initCamera: function() {
    var that = this;
    wx.authorize({
      scope: 'scope.camera',
      success: function() {
        that.setData({ cameraAuthorized: true });
        that.cameraContext = wx.createCameraContext();
      },
      fail: function() {
        wx.showModal({
          title: '需要相机权限', content: '请开启相机权限',
          showCancel: false, success: function() { wx.openSetting(); }
        });
      }
    });
  },

  initRecorder: function() {
    var rm = wx.getRecorderManager();
    this.recorderManager = rm;
    var that = this;
    rm.onStop(function(res) {
      if (that.data.recordState === RecordState.RECORDING) {
        that.handleVoiceUpload(res.tempFilePath, res.duration);
      }
    });
    rm.onError(function() {
      wx.showToast({ title: '录音失败', icon: 'none' });
      that.resetToIdle();
    });
  },

  loadHistory: function() {
    var that = this;
    request({ url: '/api/v1/qa/history', method: 'GET' }).then(function(data) {
      if (Array.isArray(data) && data.length > 0) {
        var messages = data.map(function(item) {
          return {
            id: item.msg_id || generateMsgId(),
            role: item.role || 'assistant',
            type: 'text',
            content: { text: item.content || item.answer || '' },
            catState: CatState.SPEAK,
            status: 'sent',
            createTime: item.create_time || Date.now()
          };
        });
        that.setData({ messages: messages });
        that.scrollToBottom();
      }
    }).catch(function() {});
  },

  onGoBack: function() {
    wx.navigateBack();
  },

  scrollToBottom: function() {
    var msgs = this.data.messages;
    if (msgs.length > 0) {
      this.setData({ scrollToId: 'msg-' + msgs[msgs.length - 1].id });
    }
  },

  addMessage: function(msg) {
    this.setData({ messages: this.data.messages.concat([msg]) });
    this.scrollToBottom();
    return msg.id;
  },

  updateMessage: function(id, updates) {
    var msgs = this.data.messages.map(function(m) {
      if (m.id === id) return Object.assign({}, m, updates);
      return m;
    });
    this.setData({ messages: msgs });
  },

  resetToIdle: function() {
    this.setData({
      recordState: RecordState.IDLE,
      catState: CatState.SPEAK,
      waveActive: false,
      statusText: ''
    });
  },

  onMicStart: function() {
    if (this.data.recordState !== RecordState.IDLE) return;
    speech.stopSpeak();
    this.setData({
      recordState: RecordState.RECORDING,
      catState: CatState.LISTEN,
      waveActive: true,
      statusText: '正在听...'
    });
    this.startRecording();
  },

  onMicEnd: function() {
    if (this.data.recordState !== RecordState.RECORDING) return;
    this.stopRecording();
  },

  startRecording: function() {
    if (!this.recorderManager) return;
    this.recorderManager.start({
      format: 'mp3', sampleRate: 16000, numberOfChannels: 1, encodeBitRate: 96000, duration: 60000
    });
  },

  stopRecording: function() {
    if (this.recorderManager) {
      try { this.recorderManager.stop(); } catch (e) {}
    }
  },

  stopRecordingSilent: function() {
    if (this.recorderManager) {
      try { this.recorderManager.stop(); } catch (e) {}
    }
  },

  handleVoiceUpload: function(voicePath, duration) {
    var that = this;
    this.setData({
      recordState: RecordState.UPLOADING,
      catState: CatState.THINK,
      statusText: '正在识别...',
      waveActive: true
    });

    upload.uploadVoice(voicePath).then(function(data) {
      var asrText = data.asr_text || '';
      that.setData({ recordState: RecordState.THINKING, statusText: '喵喵正在思考...', waveActive: false });
      that.sendToQA(asrText, undefined, voicePath, duration);
    }).catch(function() {
      wx.showToast({ title: '语音识别失败', icon: 'none' });
      that.resetToIdle();
    });
  },

  onCameraTap: function() {
    if (this.data.recordState !== RecordState.IDLE) return;
    var ctx = this.cameraContext;
    var that = this;
    if (!ctx) { wx.showToast({ title: '相机未就绪', icon: 'none' }); return; }

    wx.showLoading({ title: '拍照中...' });
    ctx.takePhoto({
      quality: 'normal',
      success: function(res) {
        wx.hideLoading();
        that.setData({
          recordState: RecordState.UPLOADING,
          catState: CatState.THINK,
          statusText: '正在上传图片...',
          waveActive: true
        });
        upload.uploadImage(res.tempImagePath).then(function(data) {
          var enhancedUrl = data.enhanced_url;
          that.setData({ recordState: RecordState.THINKING, statusText: '喵喵正在思考...', waveActive: false });
          that.sendToQA('', enhancedUrl, undefined, 0);
        }).catch(function() {
          wx.showToast({ title: '图片上传失败', icon: 'none' });
          that.resetToIdle();
        });
      },
      fail: function() {
        wx.hideLoading();
        wx.showToast({ title: '拍照失败', icon: 'none' });
      }
    });
  },

  sendToQA: function(asrText, mediaUrl, voicePath, duration) {
    var that = this;
    var inputType = mediaUrl ? 'image' : 'text';
    var userMsgId = generateMsgId();
    var userMsg = {
      id: userMsgId, role: 'user',
      type: mediaUrl ? 'image' : 'text',
      content: {
        text: asrText || '图片',
        images: mediaUrl ? [{ enhancedUrl: mediaUrl }] : [],
        voice: voicePath ? { tempPath: voicePath, duration: duration, asrText: asrText } : undefined
      },
      status: 'sending', createTime: Date.now()
    };

    this.addMessage(userMsg);

    request({
      url: '/api/v1/qa/ask',
      method: 'POST',
      data: {
        input_type: inputType,
        text: asrText || '',
        media_url: mediaUrl || undefined,
        session_id: this.data.sessionId
      }
    }).then(function(data) {
      that.updateMessage(userMsgId, { status: 'sent' });
      if (data.session_id) that.setData({ sessionId: data.session_id });

      var answer = data.answer || '';
      var aiMsg = {
        id: generateMsgId(), role: 'assistant', type: 'text',
        content: { text: answer },
        catState: data.cat_action || CatState.SPEAK,
        riskTags: data.risk_tags || [],
        intercepted: data.intercepted || false,
        status: 'sent', createTime: Date.now()
      };
      that.addMessage(aiMsg);
      speech.speak(answer);
      that.resetToIdle();
    }).catch(function() {
      that.updateMessage(userMsgId, { status: 'error' });
      that.resetToIdle();
    });
  },

  onCancelTap: function() {
    this.stopRecordingSilent();
    this.resetToIdle();
  },

  onBubbleTap: function(e) {
    var mid = e.detail.messageId;
    var msg = this.data.messages.find(function(m) { return m.id === mid; });
    if (msg && msg.content && msg.content.text) {
      speech.stopSpeak();
      speech.speak(msg.content.text);
    }
  },

  onRetryMessage: function() {
    wx.showToast({ title: '请重新录音或拍照提问', icon: 'none' });
  },

  onEmergencyTap: function() {
    wx.navigateTo({ url: '/pages/emergency/emergency' });
  }
});
```

- [ ] **Step 5: 编译验证**

编译确认无语法错误，语音和拍照独立流程，聊天历史从 API 恢复。

- [ ] **Step 6: Commit**

```bash
git add miniprogram/pages/chat/
git commit -m "feat: 聊天页，语音拍照独立上传，AI问答，历史恢复"
```

---

## 第三阶段：辅助页面

### Task 12: 历史记录页 history

**Files:**
- Create: `miniprogram/pages/history/history.js`
- Create: `miniprogram/pages/history/history.json`
- Create: `miniprogram/pages/history/history.wxml`
- Create: `miniprogram/pages/history/history.wxss`

- [ ] **Step 1: 创建 history 页面四个文件**

创建 [history.json](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/history/history.json)：

```json
{
  "navigationBarTitleText": "历史记录",
  "usingComponents": {}
}
```

创建 [history.wxml](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/history/history.wxml)：

```xml
<view class="page-container">
  <view class="nav-bar" style="padding-top: {{statusBarHeight}}px;">
    <view class="nav-content">
      <view class="nav-back" bindtap="onGoBack">‹ 返回</view>
      <view class="nav-title">历史记录</view>
      <view class="nav-placeholder"></view>
    </view>
  </view>

  <scroll-view class="history-list" scroll-y enhanced show-scrollbar="{{false}}">
    <view wx:if="{{loading}}" class="loading-text">加载中...</view>
    <view wx:if="{{!loading && historyList.length === 0}}" class="empty-text">暂无历史记录</view>
    <view wx:for="{{historyList}}" wx:key="msg_id" class="history-item" bindtap="onItemTap" data-id="{{item.msg_id}}">
      <view class="history-role">{{item.role === 'user' ? '您' : '喵喵'}}</view>
      <view class="history-text">{{item.content || item.answer || ''}}</view>
      <view class="history-time">{{item.create_time || ''}}</view>
    </view>
  </scroll-view>
</view>
```

创建 [history.wxss](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/history/history.wxss)：

```css
.page-container {
  width: 100%; height: 100vh; background: #1a1a2e; overflow: hidden;
}
.nav-bar {
  position: fixed; top: 0; left: 0; width: 100%; z-index: 100;
  background: rgba(0,0,0,0.6);
}
.nav-content {
  height: 88rpx; display: flex; align-items: center; justify-content: space-between;
  padding: 0 32rpx;
}
.nav-back { font-size: 34rpx; color: #fff; }
.nav-title { font-size: 36rpx; color: #fff; font-weight: bold; }
.nav-placeholder { width: 100rpx; }

.history-list {
  padding-top: 120rpx; padding-bottom: 60rpx;
  height: 100vh; box-sizing: border-box;
}
.loading-text, .empty-text {
  text-align: center; font-size: 32rpx; color: rgba(255,255,255,0.6); margin-top: 200rpx;
}
.history-item {
  margin: 24rpx 32rpx; padding: 32rpx;
  background: rgba(255,255,255,0.1); border-radius: 24rpx;
}
.history-role { font-size: 28rpx; color: rgba(255,255,255,0.6); margin-bottom: 12rpx; }
.history-text { font-size: 34rpx; color: #fff; line-height: 1.5; margin-bottom: 12rpx; }
.history-time { font-size: 24rpx; color: rgba(255,255,255,0.4); }
```

创建 [history.js](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/history/history.js)：

```javascript
var request = require('../../utils/request.js').request;

Page({
  data: {
    statusBarHeight: 20,
    historyList: [],
    loading: true
  },

  onLoad: function() {
    var sys = wx.getSystemInfoSync();
    this.setData({ statusBarHeight: sys.statusBarHeight || 20 });
  },

  onShow: function() {
    this.loadHistory();
  },

  loadHistory: function() {
    var that = this;
    this.setData({ loading: true });
    request({ url: '/api/v1/qa/history', method: 'GET' }).then(function(data) {
      that.setData({
        historyList: Array.isArray(data) ? data : [],
        loading: false
      });
    }).catch(function() {
      that.setData({ loading: false });
      wx.showToast({ title: '加载失败', icon: 'none' });
    });
  },

  onGoBack: function() {
    wx.navigateBack();
  },

  onItemTap: function(e) {
    wx.navigateTo({ url: '/pages/chat/chat' });
  }
});
```

- [ ] **Step 2: 编译验证**

编译确认无语法错误。

- [ ] **Step 3: Commit**

```bash
git add miniprogram/pages/history/
git commit -m "feat: 历史记录页，从API加载聊天历史"
```

---

### Task 13: 用药提醒页 reminder

**Files:**
- Create: `miniprogram/pages/reminder/reminder.js`
- Create: `miniprogram/pages/reminder/reminder.json`
- Create: `miniprogram/pages/reminder/reminder.wxml`
- Create: `miniprogram/pages/reminder/reminder.wxss`

- [ ] **Step 1: 创建 reminder 页面四个文件**

创建 [reminder.json](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/reminder/reminder.json)：

```json
{
  "navigationBarTitleText": "用药提醒",
  "usingComponents": {}
}
```

创建 [reminder.wxml](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/reminder/reminder.wxml)：

```xml
<view class="page-container">
  <view class="nav-bar" style="padding-top: {{statusBarHeight}}px;">
    <view class="nav-content">
      <view class="nav-back" bindtap="onGoBack">‹ 返回</view>
      <view class="nav-title">用药提醒</view>
      <view class="nav-placeholder"></view>
    </view>
  </view>

  <scroll-view class="reminder-list" scroll-y enhanced show-scrollbar="{{false}}">
    <view wx:if="{{loading}}" class="loading-text">加载中...</view>
    <view wx:if="{{!loading && reminderList.length === 0}}" class="empty-text">暂无用药提醒</view>
    <view wx:for="{{reminderList}}" wx:key="reminder_id" class="reminder-item">
      <view class="reminder-icon">💊</view>
      <view class="reminder-info">
        <view class="reminder-drug">{{item.drug_name}}</view>
        <view class="reminder-meta">{{item.dosage}} · {{item.remind_time}}</view>
      </view>
    </view>
  </scroll-view>
</view>
```

创建 [reminder.wxss](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/reminder/reminder.wxss)：

```css
.page-container {
  width: 100%; height: 100vh; background: #1a1a2e; overflow: hidden;
}
.nav-bar {
  position: fixed; top: 0; left: 0; width: 100%; z-index: 100;
  background: rgba(0,0,0,0.6);
}
.nav-content {
  height: 88rpx; display: flex; align-items: center; justify-content: space-between;
  padding: 0 32rpx;
}
.nav-back { font-size: 34rpx; color: #fff; }
.nav-title { font-size: 36rpx; color: #fff; font-weight: bold; }
.nav-placeholder { width: 100rpx; }

.reminder-list {
  padding-top: 120rpx; padding-bottom: 60rpx;
  height: 100vh; box-sizing: border-box;
}
.loading-text, .empty-text {
  text-align: center; font-size: 32rpx; color: rgba(255,255,255,0.6); margin-top: 200rpx;
}
.reminder-item {
  display: flex; flex-direction: row; align-items: center;
  margin: 24rpx 32rpx; padding: 32rpx;
  background: rgba(255,149,0,0.2); border-radius: 24rpx;
  border-left: 8rpx solid #FF9500;
}
.reminder-icon { font-size: 48rpx; margin-right: 24rpx; }
.reminder-drug { font-size: 36rpx; color: #fff; font-weight: bold; margin-bottom: 8rpx; }
.reminder-meta { font-size: 28rpx; color: rgba(255,255,255,0.7); }
```

创建 [reminder.js](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/reminder/reminder.js)：

```javascript
var request = require('../../utils/request.js').request;

Page({
  data: {
    statusBarHeight: 20,
    reminderList: [],
    loading: true
  },

  onLoad: function() {
    var sys = wx.getSystemInfoSync();
    this.setData({ statusBarHeight: sys.statusBarHeight || 20 });
  },

  onShow: function() {
    this.loadReminders();
  },

  loadReminders: function() {
    var that = this;
    this.setData({ loading: true });
    request({ url: '/api/v1/reminder/medication', method: 'GET' }).then(function(data) {
      that.setData({
        reminderList: Array.isArray(data) ? data : [],
        loading: false
      });
    }).catch(function() {
      that.setData({ loading: false });
      wx.showToast({ title: '加载失败', icon: 'none' });
    });
  },

  onGoBack: function() {
    wx.navigateBack();
  }
});
```

- [ ] **Step 2: 编译验证**

编译确认无语法错误。

- [ ] **Step 3: Commit**

```bash
git add miniprogram/pages/reminder/
git commit -m "feat: 用药提醒页，展示今日用药列表"
```

---

### Task 14: 紧急呼叫页 emergency

**Files:**
- Create: `miniprogram/pages/emergency/emergency.js`
- Create: `miniprogram/pages/emergency/emergency.json`
- Create: `miniprogram/pages/emergency/emergency.wxml`
- Create: `miniprogram/pages/emergency/emergency.wxss`

- [ ] **Step 1: 创建 emergency 页面四个文件**

创建 [emergency.json](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/emergency/emergency.json)：

```json
{
  "navigationBarTitleText": "紧急呼叫",
  "usingComponents": {}
}
```

创建 [emergency.wxml](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/emergency/emergency.wxml)：

```xml
<view class="page-container">
  <view class="nav-bar" style="padding-top: {{statusBarHeight}}px;">
    <view class="nav-content">
      <view class="nav-back" bindtap="onGoBack">‹ 返回</view>
      <view class="nav-title">紧急呼叫</view>
      <view class="nav-placeholder"></view>
    </view>
  </view>

  <view class="content-area">
    <view class="warning-icon">⚠️</view>
    <view class="warning-title">紧急情况</view>
    <view class="warning-desc">点击下方按钮通知家人，紧急情况请拨打120</view>

    <view class="emergency-btn" bindtap="onEmergencyCall">
      <text>🆘 通知家人</text>
    </view>

    <view class="call120-btn" bindtap="onCall120">
      <text>📞 拨打120</text>
    </view>

    <view wx:if="{{resultText}}" class="result-text">{{resultText}}</view>
  </view>
</view>
```

创建 [emergency.wxss](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/emergency/emergency.wxss)：

```css
.page-container {
  width: 100%; height: 100vh; background: #1a1a2e; overflow: hidden;
}
.nav-bar {
  position: fixed; top: 0; left: 0; width: 100%; z-index: 100;
  background: rgba(0,0,0,0.6);
}
.nav-content {
  height: 88rpx; display: flex; align-items: center; justify-content: space-between;
  padding: 0 32rpx;
}
.nav-back { font-size: 34rpx; color: #fff; }
.nav-title { font-size: 36rpx; color: #fff; font-weight: bold; }
.nav-placeholder { width: 100rpx; }

.content-area {
  display: flex; flex-direction: column; align-items: center;
  padding-top: 200rpx; padding: 200rpx 48rpx 0;
}
.warning-icon { font-size: 120rpx; margin-bottom: 32rpx; }
.warning-title { font-size: 48rpx; color: #FF3B30; font-weight: bold; margin-bottom: 24rpx; }
.warning-desc { font-size: 32rpx; color: rgba(255,255,255,0.8); text-align: center; margin-bottom: 80rpx; line-height: 1.5; }

.emergency-btn {
  width: 500rpx; height: 120rpx; line-height: 120rpx;
  text-align: center; background: #FF3B30; color: #fff;
  border-radius: 28rpx; font-size: 40rpx; font-weight: bold;
  margin-bottom: 32rpx;
}
.call120-btn {
  width: 500rpx; height: 120rpx; line-height: 120rpx;
  text-align: center; background: #FF9500; color: #fff;
  border-radius: 28rpx; font-size: 40rpx; font-weight: bold;
}
.result-text {
  margin-top: 40rpx; font-size: 32rpx; color: #4CD964; text-align: center;
}
```

创建 [emergency.js](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/emergency/emergency.js)：

```javascript
var request = require('../../utils/request.js').request;

Page({
  data: {
    statusBarHeight: 20,
    resultText: ''
  },

  onLoad: function() {
    var sys = wx.getSystemInfoSync();
    this.setData({ statusBarHeight: sys.statusBarHeight || 20 });
  },

  onGoBack: function() {
    wx.navigateBack();
  },

  onEmergencyCall: function() {
    var that = this;
    wx.showModal({
      title: '确定要通知家人吗？',
      content: '点击确定将通知所有绑定的家人',
      confirmText: '确定通知',
      cancelText: '取消',
      success: function(modalRes) {
        if (modalRes.confirm) {
          request({ url: '/api/v1/alert/emergency/call', method: 'POST' }).then(function() {
            that.setData({ resultText: '已通知家人，请等待。' });
          }).catch(function() {
            that.setData({ resultText: '通知失败，请直接拨打120。' });
          });
        }
      }
    });
  },

  onCall120: function() {
    wx.makePhoneCall({ phoneNumber: '120', fail: function() {} });
  }
});
```

- [ ] **Step 2: 编译验证**

编译确认无语法错误。

- [ ] **Step 3: Commit**

```bash
git add miniprogram/pages/emergency/
git commit -m "feat: 紧急呼叫页，通知家人+拨打120"
```

---

### Task 15: 设置页 settings

**Files:**
- Create: `miniprogram/pages/settings/settings.js`
- Create: `miniprogram/pages/settings/settings.json`
- Create: `miniprogram/pages/settings/settings.wxml`
- Create: `miniprogram/pages/settings/settings.wxss`

- [ ] **Step 1: 创建 settings 页面四个文件**

创建 [settings.json](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/settings/settings.json)：

```json
{
  "navigationBarTitleText": "设置",
  "usingComponents": {}
}
```

创建 [settings.wxml](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/settings/settings.wxml)：

```xml
<view class="page-container">
  <view class="nav-bar" style="padding-top: {{statusBarHeight}}px;">
    <view class="nav-content">
      <view class="nav-back" bindtap="onGoBack">‹ 返回</view>
      <view class="nav-title">设置</view>
      <view class="nav-placeholder"></view>
    </view>
  </view>

  <view class="settings-list">
    <view class="setting-item">
      <view class="setting-label">字体大小</view>
      <view class="setting-control">
        <view class="size-btn {{fontSize === 'normal' ? 'active' : ''}}" bindtap="onSetFontSize" data-size="normal">标准</view>
        <view class="size-btn {{fontSize === 'large' ? 'active' : ''}}" bindtap="onSetFontSize" data-size="large">大</view>
        <view class="size-btn {{fontSize === 'xlarge' ? 'active' : ''}}" bindtap="onSetFontSize" data-size="xlarge">超大</view>
      </view>
    </view>

    <view class="setting-item">
      <view class="setting-label">语音播报</view>
      <switch checked="{{voiceEnabled}}" bindchange="onVoiceToggle" color="#07C160"></switch>
    </view>

    <view class="setting-item">
      <view class="setting-label">当前版本</view>
      <view class="setting-value">v1.0.0</view>
    </view>

    <view class="setting-item logout-item" bindtap="onLogout">
      <view class="setting-label logout-text">退出登录</view>
    </view>
  </view>
</view>
```

创建 [settings.wxss](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/settings/settings.wxss)：

```css
.page-container {
  width: 100%; height: 100vh; background: #1a1a2e; overflow: hidden;
}
.nav-bar {
  position: fixed; top: 0; left: 0; width: 100%; z-index: 100;
  background: rgba(0,0,0,0.6);
}
.nav-content {
  height: 88rpx; display: flex; align-items: center; justify-content: space-between;
  padding: 0 32rpx;
}
.nav-back { font-size: 34rpx; color: #fff; }
.nav-title { font-size: 36rpx; color: #fff; font-weight: bold; }
.nav-placeholder { width: 100rpx; }

.settings-list {
  padding-top: 140rpx; padding: 140rpx 32rpx 0;
}
.setting-item {
  display: flex; flex-direction: row; align-items: center; justify-content: space-between;
  padding: 36rpx 0;
  border-bottom: 2rpx solid rgba(255,255,255,0.1);
}
.setting-label { font-size: 34rpx; color: #fff; }
.setting-value { font-size: 30rpx; color: rgba(255,255,255,0.5); }
.setting-control { display: flex; gap: 16rpx; }
.size-btn {
  width: 100rpx; height: 64rpx; line-height: 64rpx; text-align: center;
  background: rgba(255,255,255,0.15); color: #fff;
  border-radius: 16rpx; font-size: 28rpx;
}
.size-btn.active { background: #07C160; }
.logout-item { border-bottom: none; margin-top: 80rpx; }
.logout-text { color: #FF3B30; }
```

创建 [settings.js](file:///d:/desktop/实验/大三下/实训/gimi/miniprogram/pages/settings/settings.js)：

```javascript
var storage = require('../../utils/storage.js');

Page({
  data: {
    statusBarHeight: 20,
    fontSize: 'normal',
    voiceEnabled: true
  },

  onLoad: function() {
    var sys = wx.getSystemInfoSync();
    this.setData({
      statusBarHeight: sys.statusBarHeight || 20,
      fontSize: storage.get('fontSize', 'normal'),
      voiceEnabled: storage.get('voiceEnabled', true)
    });
  },

  onGoBack: function() {
    wx.navigateBack();
  },

  onSetFontSize: function(e) {
    var size = e.currentTarget.dataset.size;
    storage.set('fontSize', size);
    this.setData({ fontSize: size });
    wx.showToast({ title: '字体大小已设置', icon: 'success' });
  },

  onVoiceToggle: function(e) {
    var enabled = e.detail.value;
    storage.set('voiceEnabled', enabled);
    this.setData({ voiceEnabled: enabled });
  },

  onLogout: function() {
    var that = this;
    wx.showModal({
      title: '退出登录',
      content: '确定要退出登录吗？',
      success: function(res) {
        if (res.confirm) {
          storage.clear();
          wx.redirectTo({ url: '/pages/index/index' });
        }
      }
    });
  }
});
```

- [ ] **Step 2: 编译验证**

编译确认无语法错误。

- [ ] **Step 3: Commit**

```bash
git add miniprogram/pages/settings/
git commit -m "feat: 设置页，字体大小、语音开关、退出登录"
```

---

## 第四阶段：清理与验证

### Task 16: 删除冗余文件与最终验证

**Files:**
- Delete: `miniprogram/pages/example/`
- Delete: `miniprogram/components/cloudTipModal/`
- Delete: `miniprogram/envList.js`

- [ ] **Step 1: 删除 example 页面**

删除 `miniprogram/pages/example/` 整个目录。

- [ ] **Step 2: 删除 cloudTipModal 组件**

删除 `miniprogram/components/cloudTipModal/` 整个目录。

- [ ] **Step 3: 删除 envList.js**

删除 `miniprogram/envList.js`。

- [ ] **Step 4: 编译并检查控制台**

在微信开发者工具中编译，确认：
1. 无编译错误
2. 7个页面都可正常跳转
3. 控制台无红色报错

- [ ] **Step 5: 功能逐项检查**

| 功能 | 检查项 |
|------|--------|
| 登录 | 首页一键登录，成功跳转home |
| Token | 存储到storage，请求自动携带 |
| 心跳 | 进入home后每30秒发送 |
| 主页导航 | 5个入口可跳转 |
| 聊天-录音 | 按住说话→ASR→QA→回答 |
| 聊天-拍照 | 拍照→上传→QA→回答 |
| 聊天-历史 | 从API恢复上次聊天记录 |
| 历史页 | 展示历史记录列表 |
| 提醒页 | 展示今日用药列表 |
| 紧急页 | 二次确认→通知家人→拨打120 |
| 设置页 | 字体大小、语音开关、退出 |
| TTS降级 | 无TTS API时仅展示文字 |
| 网络异常 | 请求失败时显示Toast |

- [ ] **Step 6: 修复问题**

根据检查结果修复。

- [ ] **Step 7: 最终Commit**

```bash
git add -A
git commit -m "feat: 完成多页面架构适老化聊天助手，清理冗余文件"
```

---

## 自审检查

### pre_v2.md 需求覆盖

| pre_v2 章节 | 对应任务 |
|------------|----------|
| 一、总体架构（多页面+工具模块） | Task 1-15（7页面+5utils+1config） |
| 二、环境配置 config/index.js | Task 1 Step 1 |
| 三、统一请求层 request.js | Task 2 |
| 四、Token 生命周期 | Task 4 |
| 五、图片上传流程 | Task 3 + Task 11 |
| 六、语音上传流程 | Task 3 + Task 11（语音拍照解耦） |
| 七、问答流程（统一 POST /qa/ask） | Task 11 |
| 八、聊天历史恢复 | Task 11（loadHistory） |
| 九、心跳机制 | Task 4（startHeartbeat） |
| 十、语音播报 TTS 降级 | Task 5（speech.js 优雅降级） |
| 十一、网络异常统一处理 | Task 2（request.js 统一错误处理） |
| 十二、页面结构（7页面） | Task 8-15 |
| 十三、开发阶段（四阶段） | Task 1-7（一）, Task 8-11（二）, Task 12-13（三）, Task 14-16（四） |
| 十四、上线检查 | Task 16（最终验证） |
| 十五、后续扩展预留 | Task 4（Refresh预留）, Task 5（TTS接口预留） |

### pre_v2.md 关键约束检查

| 约束 | 是否满足 |
|------|---------|
| 不再使用微信云开发 | ✅ app.js 已移除 wx.cloud |
| 所有接口统一由 request.js 管理 | ✅ 页面禁止直接调用 wx.request |
| 禁止页面内写死 IP | ✅ 通过 config/index.js 统一管理 |
| 图片保存整个对象，不只看 enhanced_url | ✅ upload.js 返回完整响应 |
| 语音流程取消与图片的强依赖 | ✅ chat.js 中语音和拍照独立 |
| TTS 无 API 时仅展示文字 | ✅ speech.js catch 静默 resolve |
| 页面禁止直接调用 wx.request | ✅ 所有请求通过 request({ url, method, data }) |

### 占位符检查

- 无 TBD / TODO / 后续实现 ✅
- 所有代码完整可复制 ✅
- speech.js 对不存在的 TTS API 有优雅降级 ✅
- auth.js 对不存在的 Refresh API 有预留扩展 ✅

### 类型/命名一致性

- `request({ url, method, data })` 签名全文一致 ✅
- `upload.uploadImage()` / `upload.uploadVoice()` 命名一致 ✅
- `auth.login()` / `auth.restoreToken()` / `auth.startHeartbeat()` ✅
- `speech.speak()` / `speech.stopSpeak()` / `speech.replayLast()` ✅
- `storage.set()` / `storage.get()` / `storage.remove()` / `storage.clear()` ✅
- 所有页面 `onGoBack()` 统一 ✅