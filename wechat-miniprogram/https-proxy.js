# 微信小程序 HTTPS 代理脚本
# 运行方式: node https-proxy.js
# 在后端机器(10.128.229.199)上运行，将 8443 端口的 HTTPS 请求转发到本地 8090

const https = require('https')
const http = require('http')
const fs = require('fs')
const { execSync } = require('child_process')

// 自动生成自签证书
try {
  if (!fs.existsSync('cert.pem') || !fs.existsSync('key.pem')) {
    console.log('正在生成自签证书...')
    execSync('openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=10.128.229.199"', { stdio: 'inherit' })
  }
} catch (e) {
  console.error('openssl 未安装，请手动安装或使用下方 PowerShell 方案')
  process.exit(1)
}

const options = {
  key: fs.readFileSync('key.pem'),
  cert: fs.readFileSync('cert.pem')
}

https.createServer(options, (req, res) => {
  console.log(`[HTTPS] ${req.method} ${req.url}`)
  
  const proxy = http.request({
    hostname: '127.0.0.1',
    port: 8090,
    path: req.url,
    method: req.method,
    headers: req.headers
  }, (proxyRes) => {
    res.writeHead(proxyRes.statusCode, proxyRes.headers)
    proxyRes.pipe(res)
  })

  req.pipe(proxy)
  proxy.on('error', (err) => {
    console.error('代理错误:', err.message)
    res.writeHead(502)
    res.end('Backend unavailable')
  })
}).listen(8443, '0.0.0.0', () => {
  console.log('HTTPS 代理已启动: https://10.128.229.199:8443')
  console.log('小程序 BASE_URL 改为: https://10.128.229.199:8443')
})