#!/bin/bash

set -e  # Остановить скрипт при любой ошибке

# === Проверка прав ===
if [ "$(id -u)" -ne 0 ]; then
    echo "❌ Требуются права root. Запустите с sudo!" >&2
    exit 1
fi

# === Параметры ===
REDIS_HOST="your_local_server_ip"  # ← замените на IP сервера Redis
AGENT_ID=$(hostname | md5 | awk '{print $1}')
OS=$(uname -s)
INSTALL_DIR="/opt/docker_agent"

echo "🐳 Установка Docker Agent для $OS"
echo "🔐 Agent ID: $AGENT_ID"

# === Проверка и установка зависимостей ===
if [ "$OS" = "Linux" ]; then
    echo "📦 Установка зависимостей для Linux"
    apt-get update
    apt-get install -y python3 python3-pip python3-venv docker.io redis-tools

elif [ "$OS" = "Darwin" ]; then
    echo "🛠 Проверка зависимостей для macOS"

    MISSING=0

    if ! command -v docker &>/dev/null; then
        echo "❗ Не найден: docker"
        echo "➡ brew install --cask docker"
        MISSING=1
    fi

    if ! command -v redis-cli &>/dev/null; then
        echo "❗ Не найден: redis-cli"
        echo "➡ brew install redis"
        MISSING=1
    fi

    if ! command -v python3 &>/dev/null; then
        echo "❗ Не найден: python3"
        echo "➡ brew install python"
        MISSING=1
    fi

    if ! command -v pip3 &>/dev/null; then
        echo "❗ Не найден: pip3"
        echo "➡ brew install python"
        MISSING=1
    fi

    if ! python3 -m venv --help &>/dev/null; then
        echo "❗ Не поддерживается venv"
        echo "➡ Обновите python3 через brew: brew install python"
        MISSING=1
    fi

    if [ "$MISSING" -eq 1 ]; then
        echo "⚠ Установите указанные зависимости вручную через brew (без sudo)."
        echo "ℹ После этого перезапустите скрипт:"
        echo "   sudo ./bin/install.sh"
        exit 1
    fi

    echo "✅ Все зависимости найдены, продолжаем установку!"
else
    echo "❌ Неподдерживаемая ОС: $OS"
    exit 1
fi

# === Установка агента ===
echo "📁 Установка в $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp -r src/ requirements.txt "$INSTALL_DIR/"

# === Виртуальное окружение ===
echo "🐍 Настройка виртуального окружения"
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

# === Создание .env ===
echo "📄 Создание конфигурации"
cat > "$INSTALL_DIR/.env" <<EOL
AGENT_ID=$AGENT_ID
REDIS_HOST=$REDIS_HOST
EOL

# === Установка службы ===
echo "🔧 Установка службы"

case $OS in
    Linux)
        SERVICE_PATH="/etc/systemd/system/docker-agent.service"
        cp install/linux/docker-agent.service "$SERVICE_PATH"
        sed -i "s|AGENT_ID_PLACEHOLDER|$AGENT_ID|g" "$SERVICE_PATH"
        sed -i "s|REDIS_HOST_PLACEHOLDER|$REDIS_HOST|g" "$SERVICE_PATH"

        systemctl daemon-reload
        systemctl enable --now docker-agent

        echo "✅ Сервис установлен. Команды:"
        echo "   sudo systemctl status docker-agent"
        echo "   journalctl -u docker-agent -f"
        ;;

    Darwin)
        PLIST_PATH=~/Library/LaunchAgents/com.user.docker-agent.plist
        cp install/macos/com.user.docker-agent.plist "$PLIST_PATH"
        sed -i '' "s|AGENT_ID_PLACEHOLDER|$AGENT_ID|g" "$PLIST_PATH"
        sed -i '' "s|REDIS_HOST_PLACEHOLDER|$REDIS_HOST|g" "$PLIST_PATH"

        launchctl unload "$PLIST_PATH" 2>/dev/null || true
        launchctl load "$PLIST_PATH"

        echo "✅ Демон установлен. Команды:"
        echo "   launchctl list | grep docker-agent"
        echo "   tail -f /opt/docker_agent/agent.log"
        ;;

    *)
        echo "❌ Неподдерживаемая ОС: $OS"
        exit 1
        ;;
esac

echo "🎉 Готово! Агент установлен в $INSTALL_DIR"

# Запуск агента
python3 /opt/docker_agent/run_agent.py

