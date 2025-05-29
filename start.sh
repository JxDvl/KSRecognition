#!/bin/bash

# Flask сервер
cd "$(dirname "$0")"
source .venv/bin/activate

echo "Запуск бэкенд-сервера Flask..."
cd backend
python app.py &
BACKEND_PID=$!

sleep 10

# React
echo "Запуск React-приложения..."
cd ../frontend
npm start &
FRONTEND_PID=$!

cleanup() {
    echo "Завершение работы серверов..."
    kill $BACKEND_PID
    kill $FRONTEND_PID
    exit 0
}

# Перехватывание сигналов завершения
trap cleanup SIGINT SIGTERM

# Ctrl+C - Завершение
echo "Приложение запущено. Нажмите Ctrl+C для завершения."
wait 