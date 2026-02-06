#!/bin/bash

# arxivAgent 停止脚本

# 查找并终止arxivAgent进程
PID=$(ps aux | grep "python.*app.py" | grep -v grep | awk '{print $2}')

if [ -n "$PID" ]; then
    echo "正在停止arxivAgent (PID: $PID)..."
    kill $PID
    sleep 2
    
    # 检查是否还有残留进程
    if ps -p $PID > /dev/null; then
        echo "强制终止..."
        kill -9 $PID
    fi
    
    echo "arxivAgent已停止"
else
    echo "未找到运行中的arxivAgent进程"
fi