#!/bin/bash
# SenseVoice ASR 服务启动脚本（笔记本端）
# 同时启动 ASR API 和 SSH 反向隧道

ASR_PORT=5002
REMOTE_PORT=15002
SERVER=root@123.56.9.243
API_DIR="h:/项目1/backend"

echo "=== Starting SenseVoice ASR Service ==="

# 1. 启动 ASR API
cd "$API_DIR"
python services/asr_api.py --port $ASR_PORT &
API_PID=$!
echo "ASR API PID: $API_PID"
sleep 5

# 2. 建立 SSH 反向隧道（保持连接）
echo "Establishing SSH tunnel (localhost:$ASR_PORT -> $SERVER:$REMOTE_PORT)..."
while true; do
    ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=60 \
        -N -R $REMOTE_PORT:localhost:$ASR_PORT $SERVER
    echo "SSH tunnel disconnected, retrying in 10s..."
    sleep 10
done
