# Агент для сбора данных о docker контейнерах и отправка их на сервер( Docker Monitoring Agent )

## Для разработчиков (локальный запуск)

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/your-repo/docker-agent.git
   cd docker-agent
   ```

2. Запустите агент в режиме разработки:
   ```bash
   chmod +x bin/local_run.sh
   ./bin/local_run.sh
   ```

   Это:
   - Создаст виртуальное окружение (если его нет)
   - Установит зависимости
   - Запустит агент с выводом в консоль

## Для пользователей (установка)

### Linux/macOS
```bash
# Скачать и установить
curl -sSL https://example.com/bin/install.sh | sudo bash
```

### Ручная установка
1. Скачайте архив с агентом
2. Распакуйте и выполните:
   ```bash
   sudo chmod +x bin/install.sh
   sudo ./bin/install.sh
   ```

## Управление агентом

### Linux
```bash
# Статус
sudo systemctl status docker-agent

# Логи
journalctl -u docker-agent -f

# Перезапуск
sudo systemctl restart docker-agent
```

### macOS
```bash
# Проверить работу
launchctl list | grep docker-agent

# Логи
tail -f /opt/docker_agent/agent.log

# Перезапуск
launchctl unload ~/Library/LaunchAgents/com.user.docker-agent.plist
launchctl load ~/Library/LaunchAgents/com.user.docker-agent.plist
```

## Удаление
```bash
# Linux
sudo systemctl stop docker-agent
sudo rm -rf /opt/docker_agent /etc/systemd/system/docker-agent.service

# macOS
launchctl unload ~/Library/LaunchAgents/com.user.docker-agent.plist
rm -rf /opt/docker_agent ~/Library/LaunchAgents/com.user.docker-agent.plist
```

## Структура проекта

