Component({
  properties: {
    devicePosition: {
      type: String,
      value: 'back'
    },
    flash: {
      type: String,
      value: 'off'
    },
    showScanFrame: {
      type: Boolean,
      value: true
    }
  },

  data: {
    cameraContext: null
  },

  lifetimes: {
    attached() {
      this.data.cameraContext = wx.createCameraContext()
    }
  },

  methods: {
    onCameraError(e) {
      this.triggerEvent('error', e.detail)
    },

    switchCamera() {
      const newPosition = this.properties.devicePosition === 'back' ? 'front' : 'back'
      this.setData({
        devicePosition: newPosition
      })
      this.triggerEvent('switch', { devicePosition: newPosition })
    },

    takePhoto(options = {}) {
      return new Promise((resolve, reject) => {
        const { quality = 'high' } = options
        this.data.cameraContext.takePhoto({
          quality,
          success: (res) => {
            this.triggerEvent('photo', res)
            resolve(res)
          },
          fail: (err) => {
            this.triggerEvent('error', err)
            reject(err)
          }
        })
      })
    },

    startRecord(options = {}) {
      return new Promise((resolve, reject) => {
        const { maxDuration = 10, videoQuality = 'high' } = options
        this.data.cameraContext.startRecord({
          maxDuration,
          videoQuality,
          success: (res) => {
            this.triggerEvent('recordstart', res)
            resolve(res)
          },
          fail: (err) => {
            this.triggerEvent('error', err)
            reject(err)
          }
        })
      })
    },

    stopRecord() {
      return new Promise((resolve, reject) => {
        this.data.cameraContext.stopRecord({
          success: (res) => {
            this.triggerEvent('recordend', res)
            resolve(res)
          },
          fail: (err) => {
            this.triggerEvent('error', err)
            reject(err)
          }
        })
      })
    },

    setFlash(flash) {
      this.setData({ flash })
      this.triggerEvent('flashchange', { flash })
    }
  }
})