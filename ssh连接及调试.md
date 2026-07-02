### **ssh开放端口：**

ssh -L 8001:127.0.0.1:8001 -L 8002:127.0.0.1:8002 student@10.246.2.7 -p 12201

Password: group1-ssh-123



***没有意外情况的话，无需重新启动，服务一直在线，只需要连接并开发端口。***

### **启动：**

\# Embedding (:8001)

HF\_HUB\_OFFLINE=1 nohup venv/bin/python3 services/embedding\_service.py > logs/embedding.log 2>\&1 \&



\# VLM (:8002)

HF\_HUB\_OFFLINE=1 nohup venv/bin/python3 services/vlm\_service.py > logs/vlm.log 2>\&1 \&



### **看启动日志**

tail -f logs/embedding.log   # Ctrl+C 退出

tail -f logs/vlm.log



### **推理**

curl -X POST http://127.0.0.1:8001/embed -H "Content-Type: application/json" -d '{"text":"测试文本"}'



curl -X POST http://127.0.0.1:8002/chat -H "Content-Type: application/json" -d '{"messages":\[{"role":"user","content":"你跟Cluade 4.6Opus什么关系"}]}'



### **关闭**

pkill -9 -f embedding\_service

pkill -9 -f vlm\_service

