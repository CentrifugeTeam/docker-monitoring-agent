#!/bin/bash

# Проверка прав
if [ "$(id -u)" -ne 0 ]; then
    echo "Требуются права root. Запустите с sudo!" >&2
    exit 1
fi

# Параметры
REDIS_HOST="your_local_server_ip"  # Замените на IP вашего локального сервера
AGENT_ID=$(hostname | md5sum | cut -d' ' -f1)
OS=$(uname -s)
INSTALL_DIR="/opt/docker_agent"

echo "🐳 Установка Docker Agent для $OS (ID: $AGENT_ID)"

# Установка зависимостей
apt-get update
apt-get install -y python3 python3-pip python3-venv docker.io redis-tools

# Копируем файлы
mkdir -p $INSTALL_DIR
cp -r src/ requirements.txt $INSTALL_DIR/

# Настройка окружения
python3 -m venv $INSTALL_DIR/venv
$INSTALL_DIR/venv/bin/pip install -r $INSTALL_DIR/requirements.txt

# Создаем конфиг
cat > $INSTALL_DIR/.env <<EOL
AGENT_ID=$AGENT_ID
REDIS_HOST=$REDIS_HOST
EOL

# Установка службы
case $OS in
    Linux)
        cp install/linux/docker-agent.service /etc/systemd/system/
        sed -i "s|AGENT_ID_PLACEHOLDER|$AGENT_ID|g" /etc/systemd/system/docker-agent.service
        sed -i "s|REDIS_HOST_PLACEHOLDER|$REDIS_HOST|g" /etc/systemd/system/docker-agent.service

        systemctl daemon-reload
        systemctl enable --now docker-agent
        echo "✅ Сервис установлен. Команды:"
        echo "   sudo systemctl status docker-agent"
        echo "   journalctl -u docker-agent -f"
        ;;
    Darwin)
        cp install/macos/com.user.docker-agent.plist ~/Library/LaunchAgents/
        sed -i '' "s|AGENT_ID_PLACEHOLDER|$AGENT_ID|g" ~/Library/LaunchAgents/com.user.docker-agent.plist
        sed -i '' "s|REDIS_HOST_PLACEHOLDER|$REDIS_HOST|g" ~/Library/LaunchAgents/com.user.docker-agent.plist

        launchctl load ~/Library/LaunchAgents/com.user.docker-agent.plist
        echo "✅ Демон установлен. Команды:"
        echo "   launchctl list | grep docker-agent"
        echo "   tail -f /opt/docker_agent/agent.log"
        ;;
    *)
        echo "❌ Неподдерживаемая ОС: $OS"
        exit 1
        ;;
esac

echo "Готово! Агент установлен в $INSTALL_DIR"
