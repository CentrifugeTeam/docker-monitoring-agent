#!/bin/bash

ROLE=$(hostname)

if [[ "$ROLE" == "sender" ]]; then
  echo "[sender] Ждём 3 секунды перед отправкой..."
  sleep 3
  echo "[sender] Отправка файла на receiver (172.28.0.3:9000)"
  nc 172.28.0.3 9000 < testfile.txt
  echo "[sender] Отправка завершена"
else
  echo "[receiver] Ожидание файла на порту 9000..."
  nc -l -p 9000 > received.txt
  echo "[receiver] Файл получен!"
fi

# Блокируем контейнер, чтобы он не вышел
tail -f /dev/null
