var plugin = requirePlugin('WechatSI');
var storage = require('./storage.js');

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

    var voiceEnabled = storage.get('voiceEnabled', true);
    if (!voiceEnabled) {
      resolve();
      return;
    }

    stopSpeak();
    lastText = text;

    plugin.textToSpeech({
      lang: 'zh_CN',
      tts: true,
      content: text,
      success: function(res) {
        if (!res.filename) {
          resolve();
          return;
        }
        var audio = wx.createInnerAudioContext();
        currentAudio = audio;
        audio.src = res.filename;
        audio.onEnded(function() {
          if (currentAudio === audio) currentAudio = null;
          audio.destroy();
          resolve();
        });
        audio.onError(function(err) {
          console.log('TTS 播放失败:', err);
          if (currentAudio === audio) currentAudio = null;
          audio.destroy();
          resolve();
        });
        audio.play();
      },
      fail: function(err) {
        console.log('TTS 合成失败:', err);
        resolve();
      }
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