#!/bin/bash
# 稳定 ASR 反代：笔记本端持续重启 SSH 反向隧道（反抖）
# 新API：脚本控制与 netstat 端口清理，防止僵尸占用

ASR_PORT=5002
REMOTE_PORT=15002
SERVER=root@123.56.9.243
API_DIR="h:/项目1/backend"
LOG="h:/项目1/scripts/asr_tunnel.log"

echo "=== 启动 ASR 反代: 笔记本 $ASR_PORT ← 服务器 $REMOTE_PORT ===" | tee -a $LOG

# 0. 清理服务器上残留的端口占用（上次退出导致的僵尸 sshd 进程）
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 清理服务器残留端口 $REMOTE_PORT ..." | tee -a $LOG
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 $SERVER \
  "fuser -k $REMOTE_PORT/tcp 2>/dev/null; sleep 2; (ss -tlnp 2>/dev/null | grep $REMOTE_PORT || echo 'port cleared')" 2>&1 | tee -a $LOG

# 1. 确保本机的 asr_api.py 还在跑；如果没起来就启动
if ! curl -s -m 3 http://localhost:$ASR_PORT/health > /dev/null 2>&1; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] asr_api.py 未运行，启动..." | tee -a $LOG
  cd "$API_DIR"
  nohup python services/asr_api.py --port $ASR_PORT >> "h:/项目1/scripts/asr_api.log" 2>&1 &
  echo "asr_api PID=$!" | tee -a $LOG
  # 等模型加载完（可能 5~30 秒）
  for i in $(seq 1 30); do
    sleep 2
    if curl -s -m 3 http://localhost:$ASR_PORT/health > /dev/null 2>&1; then
      echo "asr_api ready after $((i*2))s" | tee -a $LOG
      break
    fi
  done
else
  echo "asr_api 已在 5002 运行" | tee -a $LOG
fi

# 2. 循环建立反向隧道，断线自动重试
while true; do
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 建立 SSH 反代 $REMOTE_PORT:$ASR_PORT ..." | tee -a $LOG
  ssh -o StrictHostKeyChecking=no \
      -o ServerAliveInterval=60 \
      -o ServerAliveCountMax=3 \
      -o ExitOnForwardFailure=yes \
      -N -R $REMOTE_PORT:localhost:$ASR_PORT $SERVER
  EXIT_CODE=$?
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 反代断开 (exit=$EXIT_CODE)，5 秒后重连..." | tee -a $LOG

  # 清理服务器残留，避免端口被僵尸 sshd 占住造成下次 ExitOnForwardFailure
  ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 $SERVER \
    "fuser -k $REMOTE_PORT/tcp 2>/dev/null; true" 2>/dev/null || true
  sleep 5
done
