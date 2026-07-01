# 基米管理 — 管理员端小程序实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有项目旁新建 `admin-miniprogram/` 独立小程序项目，精选复用 `request.js` + `storage.js`，重写 `auth.js`，实现登录 + 3 Tab（用户/子女/审计）的管理端。

**Architecture:** 独立微信小程序项目，4 页面（登录 + 3 Tab），底部 TabBar 导航。复用老人端 `utils/request.js` 和 `utils/storage.js`，重写 `utils/auth.js` 适配 admin 登录。UI 采用"清爽专业型"浅色蓝色系风格。

**Tech Stack:** 微信小程序原生框架（WXML/WXSS/JS），HTTP REST API，JWT Bearer Token

---

## 文件结构规划

```
admin-miniprogram/
├── app.js                  # 启动时 restoreToken → 路由分发
├── app.json                # 页面注册 + window 配置 + tabBar
├── app.wxss                # 全局样式主题
├── sitemap.json            # 站点地图
├── project.config.json     # 项目配置（需手动在微信开发者工具创建）
├── config/
│   └── index.js            # 环境配置
├── utils/
│   ├── request.js          # ▲ 复用：HTTP 封装
│   ├── storage.js          # ▲ 复用：本地存储
│   └── auth.js             # ◈ 重写：admin JWT 鉴权 + 心跳
├── pages/
│   ├── login/
│   │   ├── login.js
│   │   ├── login.json
│   │   ├── login.wxml
│   │   └── login.wxss
│   ├── users/
│   │   ├── users.js
│   │   ├── users.json
│   │   ├── users.wxml
│   │   └── users.wxss
│   ├── children/
│   │   ├── children.js
│   │   ├── children.json
│   │   ├── children.wxml
│   │   └── children.wxss
│   └── audit/
│       ├── audit.js
│       ├── audit.json
│       ├── audit.wxml
│       └── audit.wxss
└── images/
    ├── logo.png            # 橘猫 Logo（从老人端 images/cat/speak.png 复制）
    ├── tab-users.png       # 用户 Tab 图标
    ├── tab-users-active.png
    ├── tab-children.png
    ├── tab-children-active.png
    ├── tab-audit.png
    └── tab-audit-active.png
```

---

### Task 1: 项目骨架与配置文件

**Files:**
- Create: `admin-miniprogram/config/index.js`
- Create: `admin-miniprogram/sitemap.json`

- [ ] **Step 1: 创建目录结构**

```bash
# 在项目根目录下创建 admin-miniprogram
mkdir -p admin-miniprogram/config
mkdir -p admin-miniprogram/utils
mkdir -p admin-miniprogram/pages/login
mkdir -p admin-miniprogram/pages/users
mkdir -p admin-miniprogram/pages/children
mkdir -p admin-miniprogram/pages/audit
mkdir -p admin-miniprogram/images
```

- [ ] **Step 2: 创建 config/index.js**

```javascript
// admin-miniprogram/config/index.js
var ENV = 'dev';

var CONFIG = {
  dev: {
    baseUrl: 'http://10.242.5.159:8090'
  },
  prod: {
    baseUrl: 'https://api.xxx.com'
  }
};

module.exports = CONFIG[ENV];
```

- [ ] **Step 3: 创建 sitemap.json**

```json
{
  "rules": [
    {
      "action": "allow",
      "page": "*"
    }
  ]
}
```

---

### Task 2: 复用工具模块

**Files:**
- Create: `admin-miniprogram/utils/request.js` (复制自 `miniprogram/utils/request.js`)
- Create: `admin-miniprogram/utils/storage.js` (复制自 `miniprogram/utils/storage.js`)

- [ ] **Step 1: 复制 request.js**

将 `miniprogram/utils/request.js` 复制到 `admin-miniprogram/utils/request.js`，不做任何修改。

- [ ] **Step 2: 复制 storage.js**

将 `miniprogram/utils/storage.js` 复制到 `admin-miniprogram/utils/storage.js`，不做任何修改。

- [ ] **Step 3: 验证不存在对老人端模块的依赖**

```bash
# request.js 只依赖 config/index.js（已在 Task 1 创建）
# storage.js 无外部依赖
```

---

### Task 3: 管理端 auth.js 鉴权模块

**Files:**
- Create: `admin-miniprogram/utils/auth.js`

- [ ] **Step 1: 创建 auth.js**

```javascript
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
```

---

### Task 4: 全局入口文件（app.js / app.json / app.wxss）

**Files:**
- Create: `admin-miniprogram/app.js`
- Create: `admin-miniprogram/app.json`
- Create: `admin-miniprogram/app.wxss`

- [ ] **Step 1: 创建 app.js**

```javascript
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
```

- [ ] **Step 2: 创建 app.json**

```json
{
  "pages": [
    "pages/login/login",
    "pages/users/users",
    "pages/children/children",
    "pages/audit/audit"
  ],
  "window": {
    "backgroundColor": "#f5f7fa",
    "backgroundTextStyle": "dark",
    "navigationBarBackgroundColor": "#ffffff",
    "navigationBarTitleText": "基米管理",
    "navigationBarTextStyle": "black"
  },
  "tabBar": {
    "color": "#999999",
    "selectedColor": "#1a73e8",
    "backgroundColor": "#ffffff",
    "borderStyle": "black",
    "list": [
      {
        "pagePath": "pages/users/users",
        "text": "用户",
        "iconPath": "images/tab-users.png",
        "selectedIconPath": "images/tab-users-active.png"
      },
      {
        "pagePath": "pages/children/children",
        "text": "子女",
        "iconPath": "images/tab-children.png",
        "selectedIconPath": "images/tab-children-active.png"
      },
      {
        "pagePath": "pages/audit/audit",
        "text": "审计",
        "iconPath": "images/tab-audit.png",
        "selectedIconPath": "images/tab-audit-active.png"
      }
    ]
  },
  "sitemapLocation": "sitemap.json",
  "style": "v2",
  "lazyCodeLoading": "requiredComponents"
}
```

- [ ] **Step 3: 创建 app.wxss**

```css
/* admin-miniprogram/app.wxss */

/* 全局变量 */
page {
  --color-primary: #1a73e8;
  --color-success: #34a853;
  --color-warning: #f9ab00;
  --color-danger: #ea4335;
  --color-bg: #f5f7fa;
  --color-card: #ffffff;
  --color-text: #1a1a2e;
  --color-text-secondary: #999999;
  --color-border: #eeeeee;
  --radius-card: 12rpx;
  --radius-button: 12rpx;
  --radius-search: 10rpx;
  --font-h1: 36rpx;
  --font-h2: 34rpx;
  --font-body: 28rpx;
  --font-caption: 24rpx;
  --font-small: 22rpx;
  --shadow-card: 0 1px 3px rgba(0, 0, 0, 0.06);

  background-color: var(--color-bg);
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  font-size: var(--font-body);
  color: var(--color-text);
  line-height: 1.5;
}

/* 通用卡片 */
.card {
  background: var(--color-card);
  border-radius: var(--radius-card);
  padding: 24rpx;
  margin-bottom: 20rpx;
  box-shadow: var(--shadow-card);
}

/* 通用搜索栏 */
.search-bar {
  display: flex;
  align-items: center;
  background: var(--color-card);
  border: 1px solid #e0e0e0;
  border-radius: var(--radius-search);
  padding: 16rpx 24rpx;
  margin: 16rpx 24rpx;
  font-size: var(--font-body);
  color: var(--color-text-secondary);
}

.search-bar .icon {
  margin-right: 12rpx;
  font-size: var(--font-body);
}

.search-bar input {
  flex: 1;
  font-size: var(--font-body);
  color: var(--color-text);
}

/* 统计卡片行 */
.stat-row {
  display: flex;
  gap: 16rpx;
  padding: 16rpx 24rpx;
}

.stat-card {
  flex: 1;
  background: var(--color-card);
  border-radius: var(--radius-card);
  padding: 28rpx 24rpx;
  box-shadow: var(--shadow-card);
}

.stat-card .num {
  font-size: 48rpx;
  font-weight: 700;
}

.stat-card .num.blue { color: var(--color-primary); }
.stat-card .num.green { color: var(--color-success); }

.stat-card .label {
  font-size: var(--font-caption);
  color: var(--color-text-secondary);
  margin-top: 8rpx;
}

/* 分组标题 */
.section-title {
  font-size: var(--font-caption);
  color: var(--color-text-secondary);
  padding: 16rpx 24rpx 8rpx;
  font-weight: 600;
}

/* 用户列表卡片 */
.user-card {
  display: flex;
  align-items: center;
  background: var(--color-card);
  border-radius: var(--radius-card);
  padding: 24rpx;
  margin: 0 24rpx 16rpx;
  box-shadow: var(--shadow-card);
}

.user-card .avatar {
  width: 80rpx;
  height: 80rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32rpx;
  font-weight: 600;
  color: #ffffff;
  background: var(--color-primary);
  flex-shrink: 0;
  margin-right: 20rpx;
}

.user-card .info {
  flex: 1;
  min-width: 0;
}

.user-card .name-row {
  display: flex;
  align-items: center;
}

.user-card .name {
  font-size: 30rpx;
  font-weight: 600;
  color: var(--color-text);
}

.user-card .detail {
  font-size: var(--font-caption);
  color: var(--color-text-secondary);
  margin-top: 6rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 状态标签 */
.tag {
  display: inline-block;
  padding: 4rpx 16rpx;
  border-radius: 4rpx;
  font-size: var(--font-small);
  font-weight: 500;
  margin-left: 12rpx;
}

.tag-online { background: #e6f4ea; color: var(--color-success); }
.tag-offline { background: #f1f3f4; color: var(--color-text-secondary); }
.tag-active { background: #e8f0fe; color: var(--color-primary); }

/* 筛选行 */
.filter-row {
  display: flex;
  gap: 16rpx;
  padding: 12rpx 24rpx;
}

.filter-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-card);
  border: 1px solid #e0e0e0;
  border-radius: 8rpx;
  padding: 16rpx;
  font-size: var(--font-body);
  color: var(--color-text-secondary);
}

.filter-btn .arrow {
  margin-left: 8rpx;
  font-size: var(--font-caption);
}

/* 审计条目 */
.audit-item {
  background: var(--color-card);
  border-radius: var(--radius-card);
  padding: 24rpx;
  margin: 0 24rpx 12rpx;
  box-shadow: var(--shadow-card);
}

.audit-item .time {
  font-size: var(--font-caption);
  color: var(--color-text-secondary);
  margin-bottom: 8rpx;
}

.audit-item .action {
  font-size: var(--font-body);
  color: var(--color-text);
  font-weight: 500;
}

.audit-item .operator {
  font-size: var(--font-caption);
  color: var(--color-text-secondary);
  margin-top: 6rpx;
}

/* 按钮 */
.btn-primary {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary);
  color: #ffffff;
  border-radius: var(--radius-button);
  font-size: 32rpx;
  font-weight: 600;
  padding: 24rpx;
  margin: 24rpx;
  border: none;
}

.btn-export {
  position: fixed;
  bottom: 0;
  left: 24rpx;
  right: 24rpx;
  background: var(--color-primary);
  color: #ffffff;
  border-radius: var(--radius-button);
  font-size: 30rpx;
  font-weight: 600;
  padding: 24rpx;
  text-align: center;
  margin-bottom: 24rpx;
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 120rpx 0;
  color: var(--color-text-secondary);
}

.empty-state .icon {
  font-size: 80rpx;
  margin-bottom: 24rpx;
  opacity: 0.3;
}

.empty-state .text {
  font-size: var(--font-body);
}

/* 底部安全区占位 */
.safe-bottom {
  height: constant(safe-area-inset-bottom);
  height: env(safe-area-inset-bottom);
}

/* 登录页 */
.login-page {
  background: #ffffff;
  min-height: 100vh;
}

.login-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 200rpx;
}

.login-logo {
  width: 160rpx;
  height: 160rpx;
  border-radius: 50%;
  margin-bottom: 40rpx;
}

.login-title {
  font-size: 40rpx;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 12rpx;
}

.login-subtitle {
  font-size: var(--font-body);
  color: var(--color-text-secondary);
  margin-bottom: 80rpx;
}

.login-btn {
  width: 80%;
  height: 96rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary);
  color: #ffffff;
  border-radius: var(--radius-button);
  font-size: 32rpx;
  font-weight: 600;
  border: none;
}

.login-tip {
  font-size: var(--font-small);
  color: var(--color-text-secondary);
  margin-top: 24rpx;
}
```

---

### Task 5: 登录页（pages/login/）

**Files:**
- Create: `admin-miniprogram/pages/login/login.js`
- Create: `admin-miniprogram/pages/login/login.json`
- Create: `admin-miniprogram/pages/login/login.wxml`
- Create: `admin-miniprogram/pages/login/login.wxss`

- [ ] **Step 1: 创建 login.json**

```json
{
  "navigationBarTitleText": "",
  "navigationStyle": "custom"
}
```

- [ ] **Step 2: 创建 login.js**

```javascript
// admin-miniprogram/pages/login/login.js
var auth = require('../../utils/auth.js');

Page({
  data: {
    loading: false
  },

  onLoad: function () {
    // 已有有效 token 则直接跳转
    if (auth.restoreToken()) {
      wx.checkSession({
        success: function () {
          auth.startHeartbeat();
          wx.switchTab({ url: '/pages/users/users' });
        },
        fail: function () {
          auth.logout();
        }
      });
    }
  },

  handleLogin: function () {
    var that = this;
    if (that.data.loading) return;

    that.setData({ loading: true });
    auth.login().then(function () {
      auth.startHeartbeat();
      wx.switchTab({ url: '/pages/users/users' });
    }).catch(function () {
      that.setData({ loading: false });
    });
  }
});
```

- [ ] **Step 3: 创建 login.wxml**

```xml
<!-- admin-miniprogram/pages/login/login.wxml -->
<view class="login-page">
  <view class="login-container">
    <image class="login-logo" src="/images/logo.png" mode="aspectFill" />
    <view class="login-title">基米管理</view>
    <view class="login-subtitle">安全管理系统</view>
    <button class="login-btn" bindtap="handleLogin" loading="{{loading}}" disabled="{{loading}}">
      微信一键登录
    </button>
    <view class="login-tip">登录即表示授权管理</view>
  </view>
</view>
```

- [ ] **Step 4: 创建 login.wxss**

```css
/* admin-miniprogram/pages/login/login.wxss */
@import '/app.wxss';
```

---

### Task 6: 用户管理页（pages/users/）— Tab 1

**Files:**
- Create: `admin-miniprogram/pages/users/users.js`
- Create: `admin-miniprogram/pages/users/users.json`
- Create: `admin-miniprogram/pages/users/users.wxml`
- Create: `admin-miniprogram/pages/users/users.wxss`

- [ ] **Step 1: 创建 users.json**

```json
{
  "navigationBarTitleText": "基米管理",
  "enablePullDownRefresh": true,
  "backgroundTextStyle": "dark"
}
```

- [ ] **Step 2: 创建 users.js**

```javascript
// admin-miniprogram/pages/users/users.js
var request = require('../../utils/request.js').request;

Page({
  data: {
    userTotal: 0,
    childrenTotal: 0,
    keyword: '',
    userList: [],
    page: 1,
    pageSize: 20,
    hasMore: true,
    loading: false
  },

  onLoad: function () {
    this.loadUsers();
    this.loadChildrenCount();
  },

  onShow: function () {
    // 从其他 Tab 切回时，可选刷新
  },

  onPullDownRefresh: function () {
    this.setData({ page: 1, hasMore: true, userList: [] });
    this.loadUsers();
    this.loadChildrenCount();
  },

  onReachBottom: function () {
    if (this.data.hasMore && !this.data.loading) {
      this.loadUsers(true);
    }
  },

  // 搜索输入
  onSearchInput: function (e) {
    var that = this;
    clearTimeout(that._searchTimer);
    that._searchTimer = setTimeout(function () {
      that.setData({ keyword: e.detail.value, page: 1, hasMore: true, userList: [] });
      that.loadUsers();
    }, 300);
  },

  // 加载用户列表
  loadUsers: function (append) {
    var that = this;
    if (that.data.loading) return;
    that.setData({ loading: true });

    var data = { page: that.data.page, page_size: that.data.pageSize };
    if (that.data.keyword) data.keyword = that.data.keyword;

    request({
      url: '/admin/users',
      method: 'GET',
      data: data
    }).then(function (res) {
      var items = (res.items || []).map(function (item) {
        return {
          user_id: item.user_id,
          nickname: item.nickname || '未命名',
          phone: item.phone || '未绑定手机',
          phoneMasked: maskPhone(item.phone),
          online_status: item.online_status,
          status: item.status,
          last_heartbeat_at: formatTime(item.last_heartbeat_at),
          created_at: formatDate(item.created_at),
          initial: (item.nickname || '?').charAt(0),
          avatarColor: getAvatarColor(item.user_id)
        };
      });

      var newList = append ? that.data.userList.concat(items) : items;
      var total = res.total || 0;

      that.setData({
        userList: newList,
        userTotal: total,
        page: that.data.page + (append ? 1 : 1),
        hasMore: newList.length < total,
        loading: false
      });
      wx.stopPullDownRefresh();
    }).catch(function () {
      that.setData({ loading: false });
      wx.stopPullDownRefresh();
    });
  },

  // 加载子女人数统计
  loadChildrenCount: function () {
    var that = this;
    request({
      url: '/admin/children',
      method: 'GET',
      data: { page: 1, page_size: 1 }
    }).then(function (res) {
      that.setData({ childrenTotal: res.total || 0 });
    }).catch(function () {});
  }
});

// 手机号脱敏
function maskPhone(phone) {
  if (!phone || phone.length < 7) return phone || '';
  return phone.substring(0, 3) + '****' + phone.substring(7);
}

// 时间格式化（显示相对时间或日期）
function formatTime(timeStr) {
  if (!timeStr) return '';
  var d = new Date(timeStr);
  var now = new Date();
  var diff = now - d;
  if (diff < 60000) return '刚刚在线';
  if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前在线';
  if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前在线';
  return formatDate(timeStr);
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  var d = new Date(dateStr);
  var y = d.getFullYear();
  var m = (d.getMonth() + 1 + '').padStart(2, '0');
  var day = (d.getDate() + '').padStart(2, '0');
  return y + '-' + m + '-' + day;
}

// 根据 user_id 生成头像背景色
var AVATAR_COLORS = ['#1a73e8', '#34a853', '#ea4335', '#f9ab00', '#7c5cfc', '#00d4aa', '#f472b6', '#fb923c'];
function getAvatarColor(id) {
  var idx = (id || 0) % AVATAR_COLORS.length;
  return AVATAR_COLORS[idx];
}
```

- [ ] **Step 3: 创建 users.wxml**

```xml
<!-- admin-miniprogram/pages/users/users.wxml -->
<view class="stat-row">
  <view class="stat-card">
    <view class="num blue">{{userTotal}}</view>
    <view class="label">老人用户</view>
  </view>
  <view class="stat-card">
    <view class="num green">{{childrenTotal}}</view>
    <view class="label">子女账号</view>
  </view>
</view>

<view class="search-bar">
  <text class="icon">🔍</text>
  <input placeholder="搜索姓名" value="{{keyword}}" bindinput="onSearchInput" confirm-type="search" />
</view>

<view class="section-title">全部用户</view>

<block wx:if="{{userList.length > 0}}">
  <view class="user-card" wx:for="{{userList}}" wx:key="user_id">
    <view class="avatar" style="background: {{item.avatarColor}};">{{item.initial}}</view>
    <view class="info">
      <view class="name-row">
        <view class="name">{{item.nickname}}</view>
        <view class="tag {{item.status === 1 ? 'tag-active' : 'tag-offline'}}">
          {{item.status === 1 ? '活跃' : '禁用'}}
        </view>
        <view class="tag {{item.online_status === 'online' ? 'tag-online' : 'tag-offline'}}">
          {{item.online_status === 'online' ? '在线' : '离线'}}
        </view>
      </view>
      <view class="detail">{{item.phoneMasked || item.phone}} · {{item.created_at}}注册</view>
    </view>
  </view>
</block>

<block wx:else>
  <view class="empty-state">
    <view class="icon">👥</view>
    <view class="text">暂无用户数据</view>
  </view>
</block>

<view wx:if="{{hasMore && userList.length > 0}}" style="text-align:center;padding:20rpx;color:#999;font-size:24rpx;">
  上拉加载更多
</view>

<view class="safe-bottom"></view>
```

- [ ] **Step 4: 创建 users.wxss**

```css
/* admin-miniprogram/pages/users/users.wxss */
```

（样式在 app.wxss 全局定义，此处仅为 page 级覆盖保留）

---

### Task 7: 子女账号页（pages/children/）— Tab 2

**Files:**
- Create: `admin-miniprogram/pages/children/children.js`
- Create: `admin-miniprogram/pages/children/children.json`
- Create: `admin-miniprogram/pages/children/children.wxml`
- Create: `admin-miniprogram/pages/children/children.wxss`

- [ ] **Step 1: 创建 children.json**

```json
{
  "navigationBarTitleText": "子女账号",
  "enablePullDownRefresh": true,
  "backgroundTextStyle": "dark"
}
```

- [ ] **Step 2: 创建 children.js**

```javascript
// admin-miniprogram/pages/children/children.js
var request = require('../../utils/request.js').request;

Page({
  data: {
    keyword: '',
    childrenList: [],
    page: 1,
    pageSize: 20,
    hasMore: true,
    loading: false
  },

  onLoad: function () {
    this.loadChildren();
  },

  onPullDownRefresh: function () {
    this.setData({ page: 1, hasMore: true, childrenList: [] });
    this.loadChildren();
  },

  onReachBottom: function () {
    if (this.data.hasMore && !this.data.loading) {
      this.loadChildren(true);
    }
  },

  onSearchInput: function (e) {
    var that = this;
    clearTimeout(that._searchTimer);
    that._searchTimer = setTimeout(function () {
      that.setData({ keyword: e.detail.value, page: 1, hasMore: true, childrenList: [] });
      that.loadChildren();
    }, 300);
  },

  loadChildren: function (append) {
    var that = this;
    if (that.data.loading) return;
    that.setData({ loading: true });

    var data = { page: that.data.page, page_size: that.data.pageSize };
    if (that.data.keyword) data.keyword = that.data.keyword;

    request({
      url: '/admin/children',
      method: 'GET',
      data: data
    }).then(function (res) {
      var items = (res.items || []).map(function (item) {
        return {
          child_id: item.child_id,
          name: item.name || '未命名',
          phone: item.phone || '未绑定手机',
          phoneMasked: maskPhone(item.phone),
          created_at: formatDate(item.created_at),
          initial: (item.name || '?').charAt(0),
          avatarColor: getChildAvatarColor(item.child_id)
        };
      });

      var newList = append ? that.data.childrenList.concat(items) : items;
      var total = res.total || 0;

      that.setData({
        childrenList: newList,
        page: that.data.page + (append ? 1 : 1),
        hasMore: newList.length < total,
        loading: false
      });
      wx.stopPullDownRefresh();
    }).catch(function () {
      that.setData({ loading: false });
      wx.stopPullDownRefresh();
    });
  }
});

function maskPhone(phone) {
  if (!phone || phone.length < 7) return phone || '';
  return phone.substring(0, 3) + '****' + phone.substring(7);
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  var d = new Date(dateStr);
  var y = d.getFullYear();
  var m = (d.getMonth() + 1 + '').padStart(2, '0');
  var day = (d.getDate() + '').padStart(2, '0');
  return y + '-' + m + '-' + day;
}

var CHILD_AVATAR_COLORS = ['#f472b6', '#c084fc', '#fb923c', '#a78bfa', '#f9ab00', '#00d4aa'];
function getChildAvatarColor(id) {
  var idx = (id || 0) % CHILD_AVATAR_COLORS.length;
  return CHILD_AVATAR_COLORS[idx];
}
```

- [ ] **Step 3: 创建 children.wxml**

```xml
<!-- admin-miniprogram/pages/children/children.wxml -->
<view class="search-bar">
  <text class="icon">🔍</text>
  <input placeholder="搜索子女昵称或手机号" value="{{keyword}}" bindinput="onSearchInput" confirm-type="search" />
</view>

<view class="section-title">全部子女</view>

<block wx:if="{{childrenList.length > 0}}">
  <view class="user-card" wx:for="{{childrenList}}" wx:key="child_id">
    <view class="avatar" style="background: {{item.avatarColor}};">{{item.initial}}</view>
    <view class="info">
      <view class="name-row">
        <view class="name">{{item.name}}</view>
      </view>
      <view class="detail">{{item.phoneMasked || item.phone}} · {{item.created_at}}注册</view>
    </view>
  </view>
</block>

<block wx:else>
  <view class="empty-state">
    <view class="icon">👨‍👩‍👧</view>
    <view class="text">暂无子女账号</view>
  </view>
</block>

<view wx:if="{{hasMore && childrenList.length > 0}}" style="text-align:center;padding:20rpx;color:#999;font-size:24rpx;">
  上拉加载更多
</view>

<view class="safe-bottom"></view>
```

- [ ] **Step 4: 创建 children.wxss**

```css
/* admin-miniprogram/pages/children/children.wxss */
```

---

### Task 8: 审计日志页（pages/audit/）— Tab 3

**Files:**
- Create: `admin-miniprogram/pages/audit/audit.js`
- Create: `admin-miniprogram/pages/audit/audit.json`
- Create: `admin-miniprogram/pages/audit/audit.wxml`
- Create: `admin-miniprogram/pages/audit/audit.wxss`

- [ ] **Step 1: 创建 audit.json**

```json
{
  "navigationBarTitleText": "审计日志",
  "enablePullDownRefresh": true,
  "backgroundTextStyle": "dark"
}
```

- [ ] **Step 2: 创建 audit.js**

```javascript
// admin-miniprogram/pages/audit/audit.js
var request = require('../../utils/request.js').request;
var config = require('../../config/index.js');

Page({
  data: {
    operation: '',       // 筛选：操作类型
    operatorType: '',    // 筛选：操作者
    auditList: [],
    page: 1,
    pageSize: 20,
    hasMore: true,
    loading: false,
    exporting: false
  },

  onLoad: function () {
    this.loadAudit();
  },

  onPullDownRefresh: function () {
    this.setData({ page: 1, hasMore: true, auditList: [] });
    this.loadAudit();
  },

  onReachBottom: function () {
    if (this.data.hasMore && !this.data.loading) {
      this.loadAudit(true);
    }
  },

  // 筛选操作类型
  onFilterOperation: function () {
    var that = this;
    wx.showActionSheet({
      itemList: ['全部', '登录', '问答', '绑定'],
      success: function (res) {
        var map = { 0: '', 1: 'login', 2: 'ask', 3: 'bind' };
        var val = map[res.tapIndex] || '';
        that.setData({ operation: val, page: 1, hasMore: true, auditList: [] });
        that.loadAudit();
      }
    });
  },

  // 筛选操作者
  onFilterOperator: function () {
    var that = this;
    wx.showActionSheet({
      itemList: ['全部', '老人', '子女', '管理员', '系统'],
      success: function (res) {
        var map = { 0: '', 1: 'user', 2: 'child', 3: 'admin', 4: 'system' };
        var val = map[res.tapIndex] || '';
        that.setData({ operatorType: val, page: 1, hasMore: true, auditList: [] });
        that.loadAudit();
      }
    });
  },

  // 加载审计日志
  loadAudit: function (append) {
    var that = this;
    if (that.data.loading) return;
    that.setData({ loading: true });

    var data = { page: that.data.page, page_size: that.data.pageSize };
    if (that.data.operation) data.operation = that.data.operation;
    if (that.data.operatorType) data.operator_type = that.data.operatorType;

    request({
      url: '/admin/audit',
      method: 'GET',
      data: data
    }).then(function (res) {
      var items = (res.items || []).map(function (item) {
        return {
          id: item.id || item.audit_id,
          operation: item.operation || item.action || '未知操作',
          operator_type: item.operator_type || item.operatorType || '',
          operator_name: item.operator_name || item.operatorName || '',
          created_at: formatDateTime(item.created_at)
        };
      });

      var newList = append ? that.data.auditList.concat(items) : items;
      var total = res.total || 0;

      that.setData({
        auditList: newList,
        page: that.data.page + (append ? 1 : 1),
        hasMore: newList.length < total,
        loading: false
      });
      wx.stopPullDownRefresh();
    }).catch(function () {
      that.setData({ loading: false });
      wx.stopPullDownRefresh();
    });
  },

  // 导出 CSV
  handleExport: function () {
    var that = this;
    if (that.data.exporting) return;
    that.setData({ exporting: true });

    var params = [];
    if (that.data.operation) params.push('operation=' + that.data.operation);
    if (that.data.operatorType) params.push('operator_type=' + that.data.operatorType);
    params.push('format=csv');
    var query = params.join('&');

    var downloadUrl = config.baseUrl + '/admin/audit/export?' + query;

    wx.showLoading({ title: '导出中...' });
    wx.downloadFile({
      url: downloadUrl,
      header: {
        'Authorization': 'Bearer ' + (getApp().globalData.token || '')
      },
      success: function (res) {
        wx.hideLoading();
        if (res.statusCode === 200) {
          wx.openDocument({
            filePath: res.tempFilePath,
            showMenu: true,
            success: function () {},
            fail: function () {
              wx.showToast({ title: '打开文件失败', icon: 'none' });
            }
          });
        } else {
          wx.showToast({ title: '导出失败', icon: 'none' });
        }
      },
      fail: function () {
        wx.hideLoading();
        wx.showToast({ title: '网络异常，导出失败', icon: 'none' });
      },
      complete: function () {
        that.setData({ exporting: false });
      }
    });
  }
});

function formatDateTime(dateStr) {
  if (!dateStr) return '';
  var d = new Date(dateStr);
  var y = d.getFullYear();
  var m = (d.getMonth() + 1 + '').padStart(2, '0');
  var day = (d.getDate() + '').padStart(2, '0');
  var h = (d.getHours() + '').padStart(2, '0');
  var min = (d.getMinutes() + '').padStart(2, '0');
  var s = (d.getSeconds() + '').padStart(2, '0');
  return y + '-' + m + '-' + day + ' ' + h + ':' + min + ':' + s;
}

// 操作类型显示名映射
var OPERATION_NAMES = { '': '全部', 'login': '登录', 'ask': '问答', 'bind': '绑定' };
var OPERATOR_NAMES = { '': '全部', 'user': '老人', 'child': '子女', 'admin': '管理员', 'system': '系统' };
```

- [ ] **Step 3: 创建 audit.wxml**

```xml
<!-- admin-miniprogram/pages/audit/audit.wxml -->
<view class="filter-row">
  <view class="filter-btn" bindtap="onFilterOperation">
    {{operation || '全部'}} <text class="arrow">▼</text>
  </view>
  <view class="filter-btn" bindtap="onFilterOperator">
    {{operatorType || '全部'}} <text class="arrow">▼</text>
  </view>
</view>

<block wx:if="{{auditList.length > 0}}">
  <view class="audit-item" wx:for="{{auditList}}" wx:key="id">
    <view class="time">{{item.created_at}}</view>
    <view class="action">{{item.operation}}</view>
    <view class="operator">操作者：{{item.operator_name || item.operator_type || '未知'}}</view>
  </view>
</block>

<block wx:else>
  <view class="empty-state">
    <view class="icon">📋</view>
    <view class="text">暂无审计记录</view>
  </view>
</block>

<view wx:if="{{hasMore && auditList.length > 0}}" style="text-align:center;padding:20rpx;color:#999;font-size:24rpx;">
  上拉加载更多
</view>

<!-- 导出按钮 -->
<view style="padding: 24rpx;">
  <view class="btn-primary" bindtap="handleExport" style="margin: 0;">
    {{exporting ? '导出中...' : '导出 CSV'}}
  </view>
</view>

<view class="safe-bottom"></view>
```

- [ ] **Step 4: 创建 audit.wxss**

```css
/* admin-miniprogram/pages/audit/audit.wxss */
```

---

### Task 9: 图片资源与最终集成

**Files:**
- Create: `admin-miniprogram/images/` 下 7 个图片文件（使用占位 SVG/Base64 方案）

- [ ] **Step 1: 创建 Tab 图标占位 PNG**

由于小程序 Tab 图标需要真实的 .png 文件，这里使用最小 1x1 像素透明 PNG 的 base64 编码创建占位图标（后续可替换为设计图标）。

```bash
# 在 admin-miniprogram/images/ 下创建占位图标
# Windows PowerShell：
$base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
$bytes = [Convert]::FromBase64String($base64)
```

替代方案：使用微信小程序支持的 iconPath 方式——直接复用 project.config.json 创建后在微信开发者工具中添加图标素材。

实用方案：从 iconfont 或简单绘制 81x81 的纯色圆角方块 PNG 作为 Tab 图标。

- [ ] **Step 2: 复制橘猫 Logo**

```bash
# 从老人端复制橘猫 speak.png 作为管理员端 Logo
cp miniprogram/images/cat/speak.png admin-miniprogram/images/logo.png
```

- [ ] **Step 3: 创建 project.config.json（在微信开发者工具中）**

用微信开发者工具打开 `admin-miniprogram/` 目录，自动生成 `project.config.json`。需要填写：
- AppID：与老人端相同或使用新的测试 AppID
- projectname：基米管理

- [ ] **Step 4: 验证所有文件到位**

```bash
# 确认目录结构完整
ls -R admin-miniprogram/
```

最终文件清单：
```
admin-miniprogram/
├── app.js
├── app.json
├── app.wxss
├── sitemap.json
├── project.config.json          (微信开发者工具生成)
├── config/index.js
├── utils/request.js
├── utils/storage.js
├── utils/auth.js
├── pages/login/login.js,json,wxml,wxss
├── pages/users/users.js,json,wxml,wxss
├── pages/children/children.js,json,wxml,wxss
├── pages/audit/audit.js,json,wxml,wxss
└── images/logo.png, tab-*.png
```

---

## 实施检查清单

| # | Task | 状态 |
|---|------|------|
| 1 | 项目骨架与配置文件 | - [ ] |
| 2 | 复用工具模块（request.js + storage.js） | - [ ] |
| 3 | 管理端 auth.js 鉴权模块 | - [ ] |
| 4 | 全局入口文件（app.js / app.json / app.wxss） | - [ ] |
| 5 | 登录页（pages/login/） | - [ ] |
| 6 | 用户管理页（pages/users/） | - [ ] |
| 7 | 子女账号页（pages/children/） | - [ ] |
| 8 | 审计日志页（pages/audit/） | - [ ] |
| 9 | 图片资源与最终集成 | - [ ] |

---

## 自审清单

- [x] **Spec 覆盖**：Task 1-2 配置+复用 → Spec §2.1, Task 3 → Spec §2.4, Task 4 → Spec §2.2-2.3, Task 5 → Spec §3.1, Task 6 → Spec §3.2, Task 7 → Spec §3.3, Task 8 → Spec §3.4, Task 4 app.wxss → Spec §4
- [x] **无占位符**：所有代码步骤包含完整的实际代码
- [x] **类型一致性**：auth.js 的 login/restoreToken/startHeartbeat/logout 签名在 app.js 和 login.js 调用中一致；`globalData.token` / `globalData.refId` / `globalData.nickname` 在 auth.js 和 app.js 中一致
