var ENV = 'dev';

var CONFIG = {
  dev: {
    baseUrl: '10.242.5.159:8090'
  },
  prod: {
    baseUrl: 'https://api.xxx.com'
  }
};

module.exports = CONFIG[ENV];