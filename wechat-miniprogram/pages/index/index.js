const app = getApp()
const { api, BASE_URL } = require('../../utils/api')

Page({
  data: {
    nickname: '',
    cameraPosition: 'back',
    flash: 'off',
    messages: [],
    isConnected: true,
    isThinking: false,
    scrollTop: 0,
    showTextModal: false,
    showEmergencyModal: false,
    showChildModal: false,
    inputText: '',
    childMessage: '',
    toastMessage: '',
    isAutoRecognizing: true,
    currentFrameInterval: 500,
    frameCount: 0,
    networkStatus: 'excellent',
    wsConnected: false
  },

  recognitionTimer: null,
  notificationTimer: null,
  cameraContext: null,
  innerAudioContext: null,
  previousImageSize: 0,
  consecutiveStaticFrames: 0,
  consecutiveMovingFrames: 0,
  lastKeyframeTime: 0,
  lastSpokenResult: '',
  
  frameQueue: [],
  isProcessingFrame: false,
  
  socketTask: null,

  MIN_INTERVAL: 200,
  MAX_INTERVAL: 3000,
  DEFAULT_INTERVAL: 500,
  STATIC_THRESHOLD: 5,
  MOVING_THRESHOLD: 3,

  onLoad() {
    this.cameraContext = wx.createCameraContext()
    this.innerAudioContext = wx.createInnerAudioContext()
    this.loadUserInfo()
    this.checkNetworkStatus()
    this.initWebSocket()
  },

  onShow() {
  },

  onHide() {
    this.stopSmartFrameCapture()
    this.stopNotificationService()
  },

  onUnload() {
    this.stopSmartFrameCapture()
    this.stopNotificationService()
    if (this.innerAudioContext) {
      this.innerAudioContext.destroy()
    }
    this.closeWebSocket()
  },

  loadUserInfo() {
    const nickname = app.getNickname() || '老人'
    this.setData({ nickname })
  },

  checkNetworkStatus() {
    wx.getNetworkType({
      success: (res) => {
        const networkStatus = res.networkType === 'wifi' || res.networkType === '5g' ? 'excellent' :
                             res.networkType === '4g' ? 'good' :
                             res.networkType === '3g' ? 'poor' : 'none'
        this.setData({ networkStatus })
        this.adjustFrameIntervalByNetwork(networkStatus)
      }
    })
  },

  adjustFrameIntervalByNetwork(networkStatus) {
    if (networkStatus === 'excellent') {
      this.setData({ currentFrameInterval: 300 })
    } else if (networkStatus === 'good') {
      this.setData({ currentFrameInterval: 500 })
    } else if (networkStatus === 'poor') {
      this.setData({ currentFrameInterval: 1000 })
    } else {
      this.setData({ currentFrameInterval: 2000 })
    }
    this.restartFrameCaptureTimer()
  },

  initWebSocket() {
    const host = (BASE_URL || '').replace('http://', '').replace('https://', '')
    if (!host) {
      console.warn('WebSocket: BASE_URL 为空，跳过连接')
      return
    }
    this.socketTask = wx.connectSocket({
      url: 'ws://' + host + '/ws/stream',
      header: {
        'Authorization': 'Bearer ' + app.getToken()
      },
      protocols: ['binary']
    })

    this.socketTask.onOpen(() => {
      console.log('WebSocket连接已打开')
      this.setData({ wsConnected: true })
    })

    this.socketTask.onMessage((res) => {
      this.handleWebSocketMessage(res)
    })

    this.socketTask.onClose(() => {
      console.log('WebSocket连接已关闭')
      this.setData({ wsConnected: false })
    })

    this.socketTask.onError((err) => {
      console.error('WebSocket错误:', err)
      this.setData({ wsConnected: false })
    })
  },

  reconnectWebSocket() {
    if (!this.data.wsConnected && this.socketTask) {
      this.initWebSocket()
    }
  },

  closeWebSocket() {
    if (this.socketTask) {
      this.socketTask.close()
      this.socketTask = null
    }
  },

  handleWebSocketMessage(res) {
    try {
      const data = typeof res.data === 'string' ? JSON.parse(res.data) : res.data
      
      if (data.type === 'ai_result') {
        const answer = data.content
        this.processAIResult(answer)
      } else if (data.type === 'frame_ack') {
        console.log('帧已确认:', data.frame_id)
      } else if (data.type === 'system_message') {
        this.showToast(data.message)
      }
    } catch (e) {
      console.error('解析WebSocket消息失败:', e)
    }
  },

  sendFrameViaWebSocket(imagePath) {
    if (!this.data.wsConnected) {
      console.log('WebSocket未连接，跳过帧发送')
      return
    }

    const fs = wx.getFileSystemManager()
    fs.readFile({
      filePath: imagePath,
      encoding: 'base64',
      success: (res) => {
        const frameData = {
          type: 'frame',
          frame_id: Date.now(),
          image: res.data,
          timestamp: Date.now(),
          quality: 'low'
        }
        
        this.socketTask.send({
          data: JSON.stringify(frameData),
          success: () => {
            console.log('帧发送成功')
          },
          fail: (err) => {
            console.error('帧发送失败:', err)
          }
        })
      },
      fail: (err) => {
        console.error('读取图片文件失败:', err)
      }
    })
  },

  onCameraError(e) {
    console.error('摄像头错误:', e.detail)
    this.setData({ isConnected: false })
    wx.showToast({
      title: '摄像头启动失败',
      icon: 'none'
    })
  },

  switchCamera() {
    this.setData({
      cameraPosition: this.data.cameraPosition === 'back' ? 'front' : 'back'
    })
  },

  toggleFlash() {
    const newFlash = this.data.flash === 'off' ? 'on' : 'off'
    this.setData({ flash: newFlash })
  },

  startSmartFrameCapture() {
    this.stopSmartFrameCapture()
    this.consecutiveStaticFrames = 0
    this.consecutiveMovingFrames = 0
    this.previousImageSize = 0
    this.scheduleNextFrameCapture()
  },

  stopSmartFrameCapture() {
    if (this.recognitionTimer) {
      clearTimeout(this.recognitionTimer)
      this.recognitionTimer = null
    }
  },

  scheduleNextFrameCapture() {
    if (!this.data.isAutoRecognizing) return
    
    this.recognitionTimer = setTimeout(() => {
      this.captureFrame()
    }, this.data.currentFrameInterval)
  },

  restartFrameCaptureTimer() {
    this.stopSmartFrameCapture()
    if (this.data.isAutoRecognizing) {
      this.scheduleNextFrameCapture()
    }
  },

  captureFrame() {
    this.cameraContext.takePhoto({
      quality: 'low',
      success: (res) => {
        this.processCapturedFrame(res.tempImagePath)
        this.scheduleNextFrameCapture()
      },
      fail: (err) => {
        console.error('帧捕获失败:', err)
        this.scheduleNextFrameCapture()
      }
    })
  },

  processCapturedFrame(imagePath) {
    const fs = wx.getFileSystemManager()
    
    fs.getFileInfo({
      filePath: imagePath,
      success: (fileInfo) => {
        const currentSize = fileInfo.size
        
        this.analyzeFrameMotion(currentSize)
        
        if (this.data.wsConnected) {
          this.sendFrameViaWebSocket(imagePath)
        } else {
          this.enqueueFrame(imagePath)
        }
        
        this.previousImageSize = currentSize
        this.setData({ frameCount: this.data.frameCount + 1 })
      },
      fail: (err) => {
        console.error('获取文件信息失败:', err)
        if (this.data.wsConnected) {
          this.sendFrameViaWebSocket(imagePath)
        } else {
          this.enqueueFrame(imagePath)
        }
      }
    })
  },

  enqueueFrame(imagePath) {
    this.frameQueue.push(imagePath)
    if (this.frameQueue.length > 10) {
      this.frameQueue.shift()
    }
    this.processNextQueuedFrame()
  },

  processNextQueuedFrame() {
    if (this.isProcessingFrame || this.frameQueue.length === 0) return
    
    this.isProcessingFrame = true
    const imagePath = this.frameQueue.shift()
    
    this.uploadFrameForAI(imagePath)
      .finally(() => {
        this.isProcessingFrame = false
        this.processNextQueuedFrame()
      })
  },

  analyzeFrameMotion(currentSize) {
    if (this.previousImageSize === 0) {
      this.previousImageSize = currentSize
      return
    }

    const sizeDiff = Math.abs(currentSize - this.previousImageSize)
    const isStatic = sizeDiff < 1000

    if (isStatic) {
      this.consecutiveStaticFrames++
      this.consecutiveMovingFrames = 0

      if (this.consecutiveStaticFrames >= this.STATIC_THRESHOLD) {
        let newInterval = this.data.currentFrameInterval * 1.5
        if (newInterval > this.MAX_INTERVAL) {
          newInterval = this.MAX_INTERVAL
        }
        if (newInterval !== this.data.currentFrameInterval) {
          this.setData({ currentFrameInterval: newInterval })
          this.restartFrameCaptureTimer()
        }
      }
    } else {
      this.consecutiveMovingFrames++
      this.consecutiveStaticFrames = 0

      if (this.consecutiveMovingFrames >= this.MOVING_THRESHOLD) {
        let newInterval = this.data.currentFrameInterval * 0.6
        if (newInterval < this.MIN_INTERVAL) {
          newInterval = this.MIN_INTERVAL
        }
        if (newInterval !== this.data.currentFrameInterval) {
          this.setData({ currentFrameInterval: newInterval })
          this.restartFrameCaptureTimer()
        }
      }
    }
  },

  uploadFrameForAI(imagePath) {
    return api.uploadImage(imagePath)
      .then(uploadData => {
        const enhancedUrl = uploadData.enhanced_url
        return api.ask('image', '请分析当前画面内容', enhancedUrl)
      })
      .then(answerData => {
        app.setSessionId(answerData.session_id)
        this.processAIResult(answerData.answer)
      })
      .catch(err => {
        console.log('后台识别跳过:', err.message)
      })
  },

  processAIResult(answer) {
    if (!answer || answer.trim() === '') return

    if (this.isResultDifferent(answer)) {
      this.addMessage(answer)
      this.speak(answer)
      this.lastSpokenResult = answer
    }
  },

  isResultDifferent(newResult) {
    if (!this.lastSpokenResult) return true
    
    const lastKeywords = this.extractKeywords(this.lastSpokenResult)
    const newKeywords = this.extractKeywords(newResult)
    
    const commonCount = lastKeywords.filter(k => newKeywords.includes(k)).length
    
    return commonCount < Math.min(lastKeywords.length, newKeywords.length) * 0.5
  },

  extractKeywords(text) {
    const stopWords = ['我', '看到', '识别', '到', '这', '是', '有', '在', '了', '的', '和', '与', '或', '等', '一些', '一个']
    const words = text.split(/[，。！？、\s]+/).filter(w => w.length > 1 && !stopWords.includes(w))
    return words.slice(0, 5)
  },

  triggerKeyframeCapture(count = 3) {
    const now = Date.now()
    if (now - this.lastKeyframeTime < 500) {
      return
    }

    this.lastKeyframeTime = now
    
    let capturedCount = 0
    const captureNext = () => {
      if (capturedCount >= count) return
      
      this.cameraContext.takePhoto({
        quality: 'high',
        success: (res) => {
          capturedCount++
          if (this.data.wsConnected) {
            this.sendFrameViaWebSocket(res.tempImagePath)
          } else {
            this.uploadFrameForAI(res.tempImagePath)
          }
          
          if (capturedCount < count) {
            setTimeout(captureNext, 100)
          }
        },
        fail: () => {
          capturedCount++
          if (capturedCount < count) {
            setTimeout(captureNext, 100)
          }
        }
      })
    }

    captureNext()
  },

  addMessage(content, type = 'ai') {
    const newMessage = {
      id: Date.now(),
      content,
      type,
      time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    }

    const messages = [...this.data.messages, newMessage]
    if (messages.length > 10) {
      messages.shift()
    }

    this.setData({
      messages,
      scrollTop: 99999
    })
  },

  speak(text) {
    wx.showToast({
      title: '语音播报中...',
      icon: 'none',
      duration: 2000
    })

    if (this.innerAudioContext) {
      this.innerAudioContext.destroy()
    }
    this.innerAudioContext = wx.createInnerAudioContext()

    wx.request({
      url: 'https://tts.baidu.com/text2audio',
      method: 'POST',
      data: {
        tex: text,
        lan: 'zh',
        per: 0,
        spd: 3,
        pit: 5,
        vol: 15
      },
      responseType: 'arraybuffer',
      success: (res) => {
        const audioData = res.data
        const base64Data = wx.arrayBufferToBase64(audioData)
        const audioSrc = `data:audio/mp3;base64,${base64Data}`
        
        this.innerAudioContext.src = audioSrc
        this.innerAudioContext.play()
      },
      fail: (err) => {
        console.error('TTS请求失败:', err)
      }
    })
  },

  startNotificationService() {
    if (this.notificationTimer) {
      clearInterval(this.notificationTimer)
    }

    this.notificationTimer = setInterval(() => {
      this.pushNotification()
    }, 15000)
  },

  stopNotificationService() {
    if (this.notificationTimer) {
      clearInterval(this.notificationTimer)
      this.notificationTimer = null
    }
  },

  pushNotification() {
    const notifications = [
      '提示：我正在观察您周围的环境',
      '建议：将识别对象放在画面中央效果更好',
      '提醒：请按时服药，关爱身体健康',
      '小贴士：遇到紧急情况请点击紧急呼叫按钮',
      '提示：点击打字按钮可以输入问题',
      '建议：保持画面稳定可提高识别准确率',
      '提示：我会根据画面变化自动调整识别频率'
    ]
    
    const message = notifications[Math.floor(Math.random() * notifications.length)]
    this.showToast(message)
    this.speak(message)
  },

  showToast(message) {
    this.setData({ toastMessage: message })
    setTimeout(() => {
      this.hideToast()
    }, 5000)
  },

  hideToast() {
    this.setData({ toastMessage: '' })
  },

  handlePhotoAsk() {
    wx.chooseImage({
      count: 1,
      success: (res) => {
        this.addMessage('📷 已选择图片', 'user')
      },
      fail: (err) => {
        console.error('选择图片失败:', err)
      }
    })
  },

  generateMockResult() {
    const results = [
      '我看到一张桌子，上面放着书籍和杯子。',
      '识别到水果，看起来是苹果和香蕉。',
      '画面中有一只猫，毛色很可爱。',
      '这里有一杯咖啡，香气似乎很浓郁。',
      '我看到一朵玫瑰花，非常漂亮。',
      '这是一辆自行车，停放在路边。',
      '画面中有一本书，似乎是技术类书籍。',
      '识别到绿植，给房间增添了生机。',
      '看到一台笔记本电脑，正在工作中。',
      '画面中有一只小狗，正在玩耍。',
      '我看到一个杯子，里面装着水。',
      '这里有一盆多肉植物，长得很好。'
    ]
    return results[Math.floor(Math.random() * results.length)]
  },

  handleTextAsk() {
    this.setData({ 
      showTextModal: true,
      inputText: ''
    })
  },

  closeTextModal() {
    this.setData({ showTextModal: false })
  },

  onInputText(e) {
    this.setData({ inputText: e.detail.value })
  },

  submitTextAsk() {
    const text = this.data.inputText.trim()
    if (!text) {
      wx.showToast({ title: '请输入问题', icon: 'none' })
      return
    }

    this.closeTextModal()
    this.addMessage(text, 'user')
  },

  handleHistory() {
    wx.navigateTo({
      url: '/pages/result/result'
    })
  },

  handleProfile() {
    wx.navigateTo({
      url: '/pages/profile/profile'
    })
  },

  async handleEmergency() {
    wx.showLoading({ title: '处理中...' })
    
    try {
      await api.emergencyCall()
      wx.hideLoading()
      this.setData({ showEmergencyModal: true })
    } catch (err) {
      wx.hideLoading()
      this.setData({ showEmergencyModal: true })
    }
  },

  closeEmergencyModal() {
    this.setData({ showEmergencyModal: false })
  },

  call120() {
    wx.makePhoneCall({
      phoneNumber: '120',
      fail: () => {
        wx.showToast({ title: '呼叫失败', icon: 'none' })
      }
    })
  },

  handleChildMessage() {
    this.setData({
      showChildModal: true,
      childMessage: ''
    })
  },

  closeChildModal() {
    this.setData({ showChildModal: false })
  },

  onChildMessageInput(e) {
    this.setData({ childMessage: e.detail.value })
  },

  sendChildMessage() {
    const message = this.data.childMessage.trim()
    if (!message) {
      wx.showToast({ title: '请输入内容', icon: 'none' })
      return
    }

    this.closeChildModal()
    this.addMessage(message, 'user')

    api.sendToChild(message)
      .then(() => {
        this.addMessage('消息已发送给子女', 'ai')
        wx.showToast({ title: '发送成功', icon: 'success' })
      })
      .catch((err) => {
        console.error('发送消息失败:', err)
        this.addMessage('消息发送失败，请重试', 'ai')
      })
  }
})