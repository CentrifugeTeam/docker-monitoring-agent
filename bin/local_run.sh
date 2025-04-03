#!/bin/bash

# Локальный запуск для разработки
echo "🚀 Запуск агента в режиме разработки"

# Проверка наличия venv
if [ ! -d "venv" ]; then
    echo "Создание виртуального окружения..."
    python3 -m venv venv
fi

# Активация venv
source venv/bin/activate

# Установка зависимостей
echo "Установка зависимостей..."
pip install -r requirements.txt

# Запуск агента
echo "Запуск агента..."
python -m src.agent

# Деактивация venv (по желанию)
deactivate
