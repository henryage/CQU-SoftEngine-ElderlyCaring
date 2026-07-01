# 基米管理 — 管理员端微信小程序设计文档

> 版本：V1.0 | 日期：2026-07-01 | 状态：设计完成，待评审

---

## 1. 项目背景

### 1.1 产品定位

"基米管理"是 Gimimimi 模糊视觉辅助问答系统的**管理员端微信小程序**。它是一个全新独立的小程序项目（非老人端分包），为系统管理员提供用户概览、子女账号管理和操作审计能力。

### 1.2 与老人端的关系

| 维度 | 老人端 | 管理员端 |
|------|--------|---------|
| 小程序名称 | Gimimimi（暂） | **基米管理** |
| 项目关系 | 独立项目 | 独立项目（精选复用核心 utils） |
| 目标用户 | 老年人 | 系统管理员 |
| 设计方向 | 适老化（大字体、大按钮、高对比度、深色背景） | 现代化、清爽专业（浅色、蓝色系、标准字号） |
| AI 助手 IP | 橘猫（listen/think/speak 三状态交互） | 橘猫（仅作为品牌 Logo，无交互） |
| 登录方式 | 微信一键登录 → 老人端 token | 微信一键登录 → 管理端 token |
| 核心技术 | 语音录音、拍照上传、TTS 播报 | 列表分页、搜索筛选、数据导出 |

### 1.3 首期范围

首期实现 4 个功能模块，对应 4 个管理端接口：

| # | 功能 | 接口 | 页面 |
|---|------|------|------|
| 1 | 管理员登录 | `POST /auth/admin/login` | `pages/login/` |
| 2 | 老人用户列表 | `GET /admin/users` | `pages/users/` |
| 3 | 子女账号列表 | `GET /admin/children` | `pages/children/` |
| 4 | 审计日志（含导出） | `GET /admin/audit` + `/export` | `pages/audit/` |

> 预警处置（`/alert`）和订阅模板管理（`/subscribe/templates`）不在首期范围内。

---

## 2. 技术方案

### 2.1 代码复用策略（方案 2：精选复用 + 重构）

从老人端项目中**仅复用**以下经过验证的通用基础设施：

| 模块 | 路径 | 复用方式 | 说明 |
|------|------|---------|------|
| `request.js` | `utils/request.js` | 直接复制 | HTTP 封装（JWT 注入、统一 code 0 校验、错误 toast） |
| `storage.js` | `utils/storage.js` | 直接复制 | 本地存储封装（set/get/remove/clear，`gimi_` 前缀） |

**不复用的模块及原因：**

| 模块 | 原因 |
|------|------|
| `auth.js` | 登录接口不同（`/auth/admin/login` vs `/auth/user/login`），需重写 |
| `speech.js` | 管理端不需要 TTS 语音播报 |
| `upload.js` | 管理端不需要图片/语音上传 |
| `chat-bubble/` 组件 | 管理端无对话交互 |
| 所有业务页面 | 管理端功能完全不同 |
| `config/index.js` | API 端点配置不同，需新建 |

### 2.2 项目目录结构

```
admin-miniprogram/
├── app.js                  # 全局入口：token 校验 → 路由分发
├── app.json                # 页面注册 + tabBar 配置 + 权限声明
├── app.wxss                # 全局样式主题（清爽专业型）
├── sitemap.json
├── project.config.json     # 微信项目配置（新 AppID）
├── config/
│   └── index.js            # 环境配置（baseUrl + admin 端点）
├── utils/
│   ├── request.js          # ▲ 复用：HTTP 请求封装
│   ├── storage.js          # ▲ 复用：本地存储封装
│   └── auth.js             # ◈ 重写：管理端 JWT 鉴权
├── pages/
│   ├── login/              # 管理员登录页
│   │   ├── login.js
│   │   ├── login.json
│   │   ├── login.wxml
│   │   └── login.wxss
│   ├── users/              # Tab 1：老人用户列表
│   │   ├── users.js
│   │   ├── users.json
│   │   ├── users.wxml
│   │   └── users.wxss
│   ├── children/           # Tab 2：子女账号列表
│   │   ├── children.js
│   │   ├── children.json
│   │   ├── children.wxml
│   │   └── children.wxss
│   └── audit/              # Tab 3：审计日志
│       ├── audit.js
│       ├── audit.json
│       ├── audit.wxml
│       └── audit.wxss
└── images/                 # 图标资源（橘猫 Logo + Tab 图标）
```

### 2.3 app.json 页面与 Tab 配置

```json
{
  "pages": [
    "pages/login/login",
    "pages/users/users",
    "pages/children/children",
    "pages/audit/audit"
  ],
  "tabBar": {
    "color": "#999999",
    "selectedColor": "#1a73e8",
    "backgroundColor": "#ffffff",
    "borderStyle": "black",
    "list": [
      { "pagePath": "pages/users/users", "text": "用户", "iconPath": "...", "selectedIconPath": "..." },
      { "pagePath": "pages/children/children", "text": "子女", "iconPath": "...", "selectedIconPath": "..." },
      { "pagePath": "pages/audit/audit", "text": "审计", "iconPath": "...", "selectedIconPath": "..." }
    ]
  }
}
```

### 2.4 auth.js 鉴权流程

```
app.onLaunch
  → auth.restoreToken()
    → storage.get('token')
    → 有 token → wx.checkSession()
      → 有效 → wx.switchTab({ url: '/pages/users/users' })
      → 无效 → wx.redirectTo({ url: '/pages/login/login' })
    → 无 token → wx.redirectTo({ url: '/pages/login/login' })

登录按钮点击
  → wx.login() 获取 code
  → POST /auth/admin/login { username, password }
    → 成功 → storage.set('token', token) → wx.switchTab('/pages/users/users')
    → 失败 → toast 提示

request.js 拦截
  → 401 → storage.remove('token') → wx.redirectTo('/pages/login/login')
```

> 注：与老人端不同，管理端登录使用 `username/password`（dev 模式下 admin/admin），但仍通过微信一键登录按钮触发 wx.login 获取 openid。

---

## 3. 页面设计

### 3.1 登录页（`pages/login/`）

**布局：** 居中垂直排列

```
┌─────────────────────────────┐
│         (状态栏)             │
├─────────────────────────────┤
│                             │
│        [橘猫 Logo]          │  ← 品牌标识（与老人端共用同一 IP）
│                             │
│        基米管理              │  ← 主标题（36rpx，深色）
│       安全管理系统            │  ← 副标题（24rpx，灰色）
│                             │
│                             │
│  ┌───────────────────────┐  │
│  │     微信一键登录       │  │  ← 蓝色按钮（#1a73e8，72rpx 高）
│  └───────────────────────┘  │    宽度 80%，圆角 12rpx，字号 32rpx
│                             │
│     登录即表示授权管理       │  ← 辅助说明（22rpx，灰色）
│                             │
└─────────────────────────────┘
```

**交互：**
1. `onLoad` 时调用 `auth.restoreToken()`，有有效 token 直接跳转 `pages/users/`
2. 点击登录按钮 → `wx.login()` → `POST /auth/admin/login` → 保存 token → 跳转
3. 登录失败显示 toast 错误信息

**样式要点：**
- 纯白背景 `#ffffff`
- 无导航栏（`"navigationStyle": "custom"` 或使用默认白色导航栏）

---

### 3.2 用户管理页（`pages/users/`）— Tab 1

**布局：**

```
┌─────────────────────────────┐
│         基米管理              │  ← 导航栏
├─────────────────────────────┤
│ ┌──────────┐ ┌──────────┐  │
│ │   128    │ │    56    │  │  ← 统计卡片（#1a73e8 蓝 / #34a853 绿）
│ │ 老人用户  │ │ 子女账号  │  │     数字 40rpx，标签 24rpx
│ └──────────┘ └──────────┘  │
│                             │
│ ┌─────────────────────────┐ │
│ │ 🔍  搜索姓名或手机号      │ │  ← 搜索栏（白色 bg + 1px 边框 #e0e0e0）
│ └─────────────────────────┘ │     圆角 10rpx，字号 28rpx
│                             │
│  全部用户                    │  ← 分组标题（24rpx，#999）
│                             │
│ ┌─────────────────────────┐ │
│ │ [张] 张爷爷      活跃   │ │  ← 用户卡片
│ │      138****6789        │ │     头像 40x40 圆形，首字，蓝底白字
│ │      绑定 2 位子女       │ │     姓名 30rpx 加粗 | 状态标签 22rpx
│ └─────────────────────────┘ │     手机号 24rpx 脱敏 | 子女信息 24rpx
│ ┌─────────────────────────┐ │
│ │ [李] 李奶奶      活跃   │ │
│ │      159****2345        │ │
│ │      未绑定子女          │ │
│ └─────────────────────────┘ │
│          ...（滚动列表）     │
│                             │
├─────────────────────────────┤
│  👥用户  👨‍👩‍👧子女  📋审计   │  ← Tab Bar
└─────────────────────────────┘
```

**数据流：**
- 加载：`onLoad` → `GET /admin/users?page=1&page_size=20`
- 搜索：输入关键词 → 300ms 防抖 → `GET /admin/users?keyword=xxx`
- 翻页：`onReachBottom` → `page++` → 追加列表
- 刷新：`onPullDownRefresh` → 重置 page=1 → 重新加载

**数据结构映射：**

| 接口字段 | UI 展示 |
|---------|---------|
| `nickname` | 卡片姓名 |
| `user_id` | 脱敏手机号（接口当前未返回 phone，预留字段） |
| `online_status` | 状态标签："online" → 绿色"在线"，其他 → 灰色"离线" |
| `status` | 状态标签：1 → 蓝色"活跃"，0 → 灰色"禁用" |
| `last_heartbeat_at` | 辅助信息（时间戳友好格式化） |
| `created_at` | 辅助信息（注册时间） |

**统计卡片数据来源：**
- 老人用户数：从 `/admin/users` 响应的 `total` 获取
- 子女账号数：从 `/admin/children` 响应的 `total` 获取（首次 `onShow` 时并请求）

---

### 3.3 子女账号页（`pages/children/`）— Tab 2

**布局：** 与用户页结构一致，无统计卡片，直接列表

```
┌─────────────────────────────┐
│         子女账号              │
├─────────────────────────────┤
│ ┌─────────────────────────┐ │
│ │ 🔍  搜索子女昵称或手机号  │ │
│ └─────────────────────────┘ │
│                             │
│  全部子女                    │
│                             │
│ ┌─────────────────────────┐ │
│ │ [子] 子女9               │ │  ← 子女卡片
│ │      dev_child_001       │ │     头像粉色底
│ │      2026-06-30 注册     │ │
│ └─────────────────────────┘ │
│          ...（滚动列表）     │
│                             │
├─────────────────────────────┤
│  👥用户  👨‍👩‍👧子女  📋审计   │
└─────────────────────────────┘
```

**数据流：**
- `GET /admin/children?page=1&page_size=20`
- 搜索、分页、刷新逻辑同用户页

**数据结构映射：**

| 接口字段 | UI 展示 |
|---------|---------|
| `name` | 卡片姓名 |
| `phone` | 手机号 |
| `child_id` | 列表 key |
| `created_at` | 注册时间（友好格式化） |

---

### 3.4 审计日志页（`pages/audit/`）— Tab 3

**布局：**

```
┌─────────────────────────────┐
│         审计日志              │
├─────────────────────────────┤
│ ┌──────────┐ ┌──────────┐  │
│ │ 操作类型 ▼│ │ 操作者 ▼ │  │  ← 双筛选下拉
│ └──────────┘ └──────────┘  │     微信 ActionSheet 实现
│                             │
│ ┌─────────────────────────┐ │
│ │ 2024-07-01 14:30:25    │ │  ← 日志条目（白色卡片）
│ │ 用户登录                │ │     时间 24rpx 灰色
│ │ 操作者：admin           │ │     操作描述 28rpx
│ └─────────────────────────┘ │     操作者 24rpx 灰色
│ ┌─────────────────────────┐ │
│ │ 2024-07-01 14:25:10    │ │
│ │ 查看用户列表            │ │
│ │ 操作者：admin           │ │
│ └─────────────────────────┘ │
│          ...（滚动列表）     │
│                             │
│      [ 导出 CSV ]           │  ← 底部固定按钮
│                             │
├─────────────────────────────┤
│  👥用户  👨‍👩‍👧子女  📋审计   │
└─────────────────────────────┘
```

**筛选器：**
- 操作类型：全部 / login / ask / bind / 其他
- 操作者：全部 / user / child / admin / system
- 选择后立即刷新列表

**数据流：**
- `GET /admin/audit?page=1&page_size=20&operation=xxx&operator_type=xxx`
- 分页、刷新同上述页面

**导出：**
- 点击"导出 CSV"按钮 → `GET /admin/audit/export?format=csv`
- 后端返回文件流，前端使用 `wx.downloadFile` + `wx.openDocument` 打开

---

## 4. 视觉设计规范

### 4.1 色彩体系

| 用途 | 色值 | 说明 |
|------|------|------|
| 页面底色 | `#f5f7fa` | 浅灰蓝，类似微信聊天背景 |
| 卡片底色 | `#ffffff` | 纯白 |
| 卡片阴影 | `0 1px 3px rgba(0,0,0,0.06)` | 极轻阴影 |
| 主色调 | `#1a73e8` | 蓝色（导航选中、按钮、链接） |
| 成功色 | `#34a853` | 绿色（在线状态、子女数字） |
| 警告色 | `#f9ab00` | 黄色（预留） |
| 错误色 | `#ea4335` | 红色（错误提示） |
| 主文字 | `#1a1a2e` | 深灰黑 |
| 辅助文字 | `#999999` | 灰色 |
| 分割线 | `#eeeeee` | 浅灰 |

### 4.2 字号规范

| 层级 | 大小 | 用途 |
|------|------|------|
| H1 | 36rpx | 导航栏标题 |
| H2 | 34rpx | 页面内大标题 |
| Body | 28rpx | 正文、列表内容 |
| Caption | 24rpx | 辅助说明、时间戳 |
| Small | 22rpx | 标签、状态 |

### 4.3 组件规范

| 组件 | 规范 |
|------|------|
| 卡片 | 圆角 12rpx，内边距 24rpx，间距 20rpx |
| 搜索栏 | 高度 72rpx，圆角 10rpx，边框 1px `#e0e0e0` |
| 按钮 | 高度 88rpx，圆角 12rpx，字号 32rpx |
| 头像 | 40x40rpx 圆形，首字居中 28rpx |
| Tab 图标 | 24x24rpx 圆角 6rpx |

### 4.4 与老人端视觉差异总结

| 维度 | 老人端 | 管理员端 |
|------|--------|---------|
| 背景 | 深色半透明遮罩 + 实时相机 | 浅灰白纯色 |
| 主色调 | 绿色/橘色 | 蓝色 `#1a73e8` |
| 字体 | ≥32rpx（最大 40rpx） | 24-34rpx |
| 按钮 | ≥88px（176rpx） | 88rpx |
| 卡片 | 无卡片，对话气泡 | 白色圆角卡片 |
| 交互核心 | 按住说话 | 列表浏览 + 搜索筛选 |
| 橘猫角色 | 核心 AI 助手（三状态动画） | 品牌 Logo（静态） |

---

## 5. 数据流

### 5.1 全局鉴权流

```
App Launch
  │
  ├─ token 有效 ──→ switchTab → users 页
  │
  └─ token 无效 ──→ redirectTo → login 页
                      │
                      └─ 微信登录 → admin token → switchTab → users 页

request.js 全局拦截
  │
  └─ 收到 401 ──→ clear token → redirectTo → login 页
```

### 5.2 页面数据流（以 users 页为例）

```
users.onLoad
  ├─ GET /admin/users?page=1 → 渲染列表 + 统计数
  └─ GET /admin/children → 更新子女统计数

users.onPullDownRefresh
  └─ 重置 page=1 → 重新加载

users.onReachBottom
  └─ page++ → GET /admin/users?page=N → 追加列表

搜索输入 (300ms 防抖)
  └─ 重置 page=1 → GET /admin/users?keyword=xxx → 替换列表
```

---

## 6. 错误处理

| 场景 | 处理方式 |
|------|---------|
| 网络异常 | `request.js` 统一 catch → `wx.showToast({ title: '网络异常', icon: 'none' })` |
| 401 未授权 | `request.js` 拦截 → 清除 token → 跳转登录页 |
| 接口 code ≠ 0 | `request.js` 拦截 → `wx.showToast({ title: msg, icon: 'none' })` |
| 空列表 | 各页面显示"暂无数据"空状态占位 |
| 加载中 | 各页面使用 `wx.showNavigationBarLoading()` + `wx.showLoading()` |
| 导出失败 | toast 提示，不阻断页面操作 |

---

## 7. 实现注意事项

1. **微信一键登录 + admin token**：管理端也使用 `wx.login()` 获取 code，但调用的接口是 `POST /auth/admin/login`，返回 admin 级别 token
2. **用户脱敏处理**：列表中手机号中间四位用 `****` 替代，保护隐私
3. **审计导出**：导出功能通过 `wx.downloadFile` 下载 CSV 文件，再用 `wx.openDocument` 让用户预览或分享
4. **Tab 页面与登录页的关系**：登录页不在 Tab 中，通过 `wx.redirectTo` / `wx.switchTab` 切换
5. **统计卡片数据更新**：用户在"用户"Tab 下拉刷新时，同步更新子女统计数据

---

## 8. 设计评审检查清单

- [x] 无 TBD / TODO / 未完成项
- [x] 各页面设计与接口文档一一对应
- [x] 架构描述与页面功能描述一致
- [x] 首期范围明确（4 功能，不含预警/订阅模板）
- [x] 视觉规范与"清爽专业型"定位一致
- [x] 代码复用范围明确（仅 request.js + storage.js）
- [x] 不与老人端适老化设计混淆
