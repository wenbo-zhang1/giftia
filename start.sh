#!/usr/bin/env bash
set -e

echo "============================================"
echo "   XiaoYi 情感陪伴助手 - 一键启动"
echo "============================================"
echo

if [ ! -f ".env" ]; then
    echo "[错误] 未找到 .env 文件，请先复制 .env.example 并填写配置"
    echo "  cp .env.example .env"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到 Python3，请先安装 Python 3.11+"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "[错误] 未找到 Node.js，请先安装 Node.js 18+"
    exit 1
fi

echo "[1/4] 检查 Python 依赖..."
if ! python3 -c "import fastapi" &> /dev/null; then
    echo "      正在安装 Python 依赖..."
    pip3 install -r requirements.txt
else
    echo "      Python 依赖已就绪"
fi

echo "[2/4] 检查前端依赖..."
if [ ! -d "frontend/node_modules" ]; then
    echo "      正在安装前端依赖..."
    cd frontend && npm install && cd ..
else
    echo "      前端依赖已就绪"
fi

echo "[3/4] 启动后端服务 (端口 8000)..."
cd backend && python3 -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!
cd ..

echo "[4/4] 启动前端服务 (端口 3000)..."
cd frontend && npm run dev &
FRONTEND_PID=$!
cd ..

echo
echo "============================================"
echo "   启动完成！"
echo "   后端: http://127.0.0.1:8000"
echo "   前端: http://localhost:3000"
echo "============================================"
echo

cleanup() {
    echo "正在停止服务..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

wait
