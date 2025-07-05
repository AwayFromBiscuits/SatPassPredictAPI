#!/bin/bash

APP_NAME="satpredict"
SERVICE_FILE="/etc/systemd/system/$APP_NAME.service"
CONTROL_CMD="/usr/local/bin/$APP_NAME"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_FILE="$SCRIPT_DIR/satpredict.py"

PYTHON=$(which python3)
UVICORN=$(which uvicorn)

install_python() {
    echo "正在安装Python..."

    if [ -f /etc/debian_version ]; then
        sudo apt update
        sudo apt install -y python3
    elif [ -f /etc/redhat-release ]; then
        sudo yum install -y python3
    else
        echo "未知操作系统，请手动安装Python及pip..."
        exit 1
    fi
}

install_pip() {
    echo "正在安装pip..."

    if [ -f /etc/debian_version ]; then
        sudo apt update
        sudo apt install -y python3-pip
    elif [ -f /etc/redhat-release ]; then
        sudo yum install -y python3-pip
    else
        echo "未知操作系统，请手动安装Python及pip..."
        exit 1
    fi
}

if [ -f "$SERVICE_FILE" ] || [ -f "$CONTROL_CMD" ]; then
    echo "检测到 $APP_NAME 已安装..."
    read -p "是否重新安装？这将删除现有配置 (y/N): " CONFIRM
    case "$CONFIRM" in
        [yY][eE][sS]|[yY])
            echo "重新安装进行中..."
            sudo systemctl stop $APP_NAME 2>/dev/null
            sudo systemctl disable $APP_NAME 2>/dev/null
            sudo rm -f "$SERVICE_FILE"
            sudo rm -f "$CONTROL_CMD"
            sudo systemctl daemon-reload
            ;;
        *)
            echo "已取消安装！"
            exit 0
            ;;
    esac
fi

if command -v python &> /dev/null; then
   :
elif command -v python3 &> /dev/null; then
   :
else install_python
fi

if command -v pip &> /dev/null; then
    PIP_CMD="pip"
elif command -v pip3 &> /dev/null; then
   PIP_CMD="pip3"
else
   install_pip
   PIP_CMD="pip3"
fi

$PIP_CMD install fastapi uvicorn skyfield numpy httpx apscheduler python-dotenv > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "pip依赖安装失败..."
    exit 1
fi

read -p "请输入监听IP（默认0.0.0.0）: " HOST
HOST=${HOST:-0.0.0.0}
read -p "请输入监听端口（默认8000）: " PORT
PORT=${PORT:-8000}

sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Satellite Prediction FastAPI Service
After=network.target

[Service]
ExecStart=$UVICORN satpredict:app --host $HOST --port $PORT
WorkingDirectory=$SCRIPT_DIR
Restart=always
RestartSec=5
User=root
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

sudo tee "$CONTROL_CMD" > /dev/null <<'EOF'
#!/bin/bash

case "$1" in
    start)
        sudo systemctl start satpredict
        ;;
    stop)
        sudo systemctl stop satpredict
        ;;
    restart)
        sudo systemctl restart satpredict
        ;;
    enable)
        sudo systemctl enable satpredict
        ;;
    disable)
        sudo systemctl disable satpredict
        ;;
    status)
        systemctl status satpredict
        ;;
    log)
        journalctl -u satpredict -f
        ;;
    *)
        echo "Usage: satpredict {start|stop|restart|enable|disable|status|log}"
        exit 1
        ;;
esac
EOF

sudo chmod +x "$CONTROL_CMD"

echo "安装成功，正在启动服务..."

sudo systemctl daemon-reload
sudo systemctl enable "$APP_NAME"
sudo systemctl restart "$APP_NAME"

echo ""
echo "安装完成！"
echo ""
echo "try: satpredict start"
