#!/bin/bash

# Запускаем Flask сервер в фоновом режиме
cd "$(dirname "$0")"
source .venv/bin/activate

echo "Запуск бэкенд-сервера Flask..."
cd backend
python app.py &
BACKEND_PID=$!

# Ждем, пока сервер запустится
sleep 2

# Запускаем React-приложение
echo "Запуск React-приложения..."
cd ../frontend
npm start &
FRONTEND_PID=$!

# Функция, которая выполняется при завершении скрипта
cleanup() {
    echo "Завершение работы серверов..."
    kill $BACKEND_PID
    kill $FRONTEND_PID
    exit 0
}

# Перехватываем сигналы завершения
trap cleanup SIGINT SIGTERM

# Ждем, пока пользователь не нажмет Ctrl+C
echo "Приложение запущено. Нажмите Ctrl+C для завершения."
wait 