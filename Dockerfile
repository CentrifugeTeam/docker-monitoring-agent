# Используем официальный Python образ с Alpine (легковесный)
FROM python:3.9-alpine

# Устанавливаем зависимости для сборки Python пакетов
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    && pip install --no-cache-dir --upgrade pip

# Создаем пользователя для безопасности
RUN adduser -D agentuser
USER agentuser
WORKDIR /home/agentuser/app

# Копируем только необходимые файлы
COPY --chown=agentuser:agentuser requirements.txt .
COPY --chown=agentuser:agentuser config.yml .
COPY --chown=agentuser:agentuser run_agent.py .
COPY --chown=agentuser:agentuser config ./config
COPY --chown=agentuser:agentuser src ./src

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Удаляем ненужные зависимости для сборки
USER root
RUN apk del .build-deps
USER agentuser

# Переменные окружения
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/home/agentuser/app

# Точка входа
CMD ["python", "run_agent.py"]
