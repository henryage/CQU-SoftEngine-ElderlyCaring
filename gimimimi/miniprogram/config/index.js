var ENV = 'dev';

var CONFIG = {
  dev: {
    baseUrl: 'http://10.178.3.199:8090'
  },
  prod: {
    baseUrl: 'https://api.xxx.com'
  }
};

module.exports = CONFIG[ENV];