var request = require('../../utils/request.js').request;
var upload = require('../../utils/upload.js');
var speech = require('../../utils/speech.js');
var storage = require('../../utils/storage.js');

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
    sessionId: null,
    userId: '',
    fontSize: 'normal'
  },

  onLoad: function() {
    var sys = wx.getSystemInfoSync();
    var safeBottom = sys.safeArea ? (sys.screenHeight - sys.safeArea.bottom) : 0;
    var app = getApp();
    var refId = app.globalData.refId;
    this.setData({
      statusBarHeight: sys.statusBarHeight || 20,
      navBarHeight: (sys.statusBarHeight || 20) + 44,
      safeAreaBottom: safeBottom,
      bottomBarHeight: 220 + safeBottom,
      userId: refId ? '老人id' + refId : '',
      fontSize: storage.get('fontSize', 'normal')
    });
    this.recorderManager = null;
    this.cameraContext = null;
    this.initRecorder();
    this.initCamera();
  },

  onShow: function() {
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
      timeout: mediaUrl ? 180000 : 30000,
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