#!/bin/bash

# Скрипт для инициализации базы данных EcoHaul
# Использование: sudo -u postgres ./scripts/init_db.sh

set -e

echo "🚀 Инициализация базы данных EcoHaul..."

# Переменные из .env
DB_NAME="ecohaul"
DB_USER="postgres"
DB_PASSWORD="Kolobo4ek123"

echo "📝 Шаг 1: Создание базы данных $DB_NAME..."
psql -c "CREATE DATABASE $DB_NAME;" || echo "База данных уже существует"

echo "📝 Шаг 2: Установка пароля для пользователя postgres..."
psql -c "ALTER USER postgres WITH PASSWORD '$DB_PASSWORD';"

echo "📝 Шаг 3: Подключение к базе данных и установка расширений..."
psql -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS postgis;"
psql -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"

echo "📝 Шаг 4: Проверка установленных расширений..."
psql -d $DB_NAME -c "\dx"

echo "✅ База данных успешно инициализирована!"
echo ""
echo "Теперь вы можете:"
echo "1. Создать миграцию: poetry run alembic revision --autogenerate -m \"Initial migration\""
echo "2. Применить миграцию: poetry run alembic upgrade head"
