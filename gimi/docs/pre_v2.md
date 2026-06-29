# 模糊视觉辅助问答系统（老人端）微信小程序开发计划 V2.0

## 一、总体架构

### 1.1 技术架构

```
微信小程序
│
├── 页面（pages）
├── 公共组件（components）
├── API封装（utils/request.js）
├── 文件上传（utils/upload.js）
├── Token管理（utils/auth.js）
├── TTS播放（utils/speech.js）
└── 全局配置（config/index.js）
        │
        ▼
Python FastAPI HTTP API
        │
├── JWT认证
├── 图片增强
├── Whisper语音识别
├── AI问答
├── 数据库
└── 预警系统
```

**说明**

- 不再使用微信云开发（云函数、云数据库、云存储）。
- 所有业务均通过 HTTP REST API 完成。
- 所有接口统一由 `request.js` 管理。

------

# 二、环境配置

新增：

```
config/
    index.js
const ENV = "dev";

const CONFIG = {
  dev: {
    baseUrl: "http://127.0.0.1:8090"
  },
  prod: {
    baseUrl: "https://api.xxx.com"
  }
};

module.exports = CONFIG[ENV];
```

以后所有接口统一：

```
BASE_URL + "/api/v1/..."
```

禁止页面内写死 IP。

------

# 三、统一请求层

新增统一封装：

```
utils/
    request.js
```

负责：

- 自动添加 Authorization
- Loading
- 统一错误提示
- 网络异常处理
- Token刷新预留
- 请求重试

统一调用：

```javascript
request({
    url:"/api/v1/qa/ask",
    method:"POST",
    data:{}
})
```

页面禁止直接调用 wx.request。

------

# 四、Token 生命周期

登录：

```
wx.login()

↓

POST /auth/wx-login

↓

token
refresh_token
```

Token 保存在：

```
wx.setStorageSync("token")
wx.setStorageSync("refreshToken")
```

请求流程：

```
请求

↓

token

↓

401？

↓

尝试refresh（预留）

↓

重新发送

↓

失败

↓

跳登录
```

虽然当前接口暂未开放 Refresh API，但必须预留扩展能力。

------

# 五、图片上传流程

```
老人拍照

↓

wx.chooseImage()

↓

POST /media/upload/image

↓

返回：

media_id
url
enhanced_url
width
height
...

↓

保存整个对象

↓

QA接口使用 enhanced_url
```

不要只保存 enhanced_url。

------

# 六、语音上传流程

```
录音

↓

wx.getRecorderManager

↓

POST /media/upload/voice

↓

返回

media_id
url
asr_text

↓

老人确认识别内容

↓

POST /qa/ask
```

录音流程取消同时抓取图片的强依赖。

若以后需要视频分析，可单独增加图像采集模块。

------

# 七、问答流程

文本：

```
输入

↓

QA

↓

展示回答
```

图片：

```
拍照

↓

上传

↓

enhanced_url

↓

QA

↓

回答
```

语音：

```
录音

↓

ASR

↓

老人确认

↓

QA

↓

回答
```

所有流程统一进入：

```
POST /api/v1/qa/ask
```

------

# 八、聊天历史恢复（新增）

首页：

```
onLoad()

↓

GET /qa/history

↓

恢复最近聊天

↓

继续会话
```

退出重新进入仍保留聊天记录。

------

# 九、心跳机制

进入前台：

```
sendHeartbeat()

↓

30 秒一次

↓

后台停止

↓

重新进入立即发送
```

不要一直后台轮询。

------

# 十、语音播报

当前后端未提供 TTS 接口。

因此 speech.js 调整为：

```
收到回答

↓

判断：

是否存在 TTS API？

↓

是：

播放音频

↓

否：

仅展示文字
```

后续若增加：

```
POST /api/v1/tts
```

仅修改 speech.js，不修改业务页面。

------

# 十一、网络异常

新增统一处理：

```
请求失败

↓

Toast

↓

重新加载按钮

↓

支持再次发送
```

上传失败：

```
重新上传
```

网络断开：

```
提示网络异常
```

------

# 十二、页面结构

```
pages/

login/

home/

chat/

history/

reminder/

emergency/

settings/
```

公共模块：

```
utils/

request.js

upload.js

auth.js

speech.js

storage.js
```

配置：

```
config/

index.js
```

------

# 十三、开发阶段

第一阶段：

- 登录
- Token
- Request
- 首页

第二阶段：

- 图片上传
- 语音上传
- QA

第三阶段：

- 历史记录
- 用药提醒
- 心跳

第四阶段：

- 紧急呼叫
- 设置
- 动画
- UI优化

------

# 十四、上线检查

开发环境：

```
http://127.0.0.1:8090
```

真机调试：

```
局域网IP
```

正式环境：

```
HTTPS域名
```

上线前检查：

- 合法域名
- HTTPS
- Token失效处理
- 图片上传限制
- 网络异常处理
- 接口超时
- 日志关闭
- 调试信息删除

------

# 十五、后续扩展

建议预留以下能力：

- Refresh Token
- TTS接口
- WebSocket实时消息
- 图片压缩上传
- 上传进度条
- AI流式输出
- 多轮会话管理
- 用户设置（字体、语音速度）
- 日志与埋点统计
- 自动异常上报