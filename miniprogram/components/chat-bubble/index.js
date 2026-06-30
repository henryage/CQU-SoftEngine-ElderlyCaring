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
    messageId: { type: String, value: '' },
    fontSize: { type: String, value: 'normal' }
  },

  data: {
    catImageUrl: '',
    imageUrls: [],
    textFontSize: 36
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
    },
    'fontSize': function(size) {
      var map = { 'normal': 36, 'large': 44, 'xlarge': 52 };
      this.setData({ textFontSize: map[size] || 36 });
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