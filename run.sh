#!/bin/bash

# arxivAgent 启动脚本

# 检查是否在正确的目录
if [ ! -f "app.py" ]; then
    echo "错误: 请在arxivAgent目录下运行此脚本"
    exit 1
fi

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3"
    exit 1
fi

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 检查依赖
if [ ! -f "venv/installed" ]; then
    echo "安装依赖包..."
    pip install -r requirements.txt
    touch venv/installed
fi

# 确保数据目录存在
mkdir -p data

# 启动应用
echo "启动arxivAgent..."
echo "访问地址: http://localhost:5001"
echo "按 Ctrl+C 停止服务"

python app.py