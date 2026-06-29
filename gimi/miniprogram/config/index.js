var ENV = 'dev';

var CONFIG = {
  dev: {
    baseUrl: 'http://10.128.229.199:8090'
  },
  prod: {
    baseUrl: 'https://api.xxx.com'
  }
};

module.exports = CONFIG[ENV];