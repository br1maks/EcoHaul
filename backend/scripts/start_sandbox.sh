#!/bin/bash

# ========================================
# Скрипт быстрого запуска SANDBOX режима
# ========================================

echo "🚀 Запуск EcoHaul API в SANDBOX режиме..."
echo ""

# Проверка что .env.sandbox существует
if [ ! -f .env.sandbox ]; then
    echo "❌ Ошибка: файл .env.sandbox не найден!"
    echo "📝 Создайте его из примера:"
    echo "   cp .env.sandbox.example .env.sandbox"
    echo "   nano .env.sandbox"
    exit 1
fi

# Проверка ключей YooKassa
if grep -q "123456" .env.sandbox && grep -q "test_AbCdEf123456" .env.sandbox; then
    echo "⚠️  ВНИМАНИЕ: В .env.sandbox используются примерные ключи!"
    echo "📝 Замените их на реальные тестовые ключи от YooKassa:"
    echo "   nano .env.sandbox"
    echo ""
    read -p "Продолжить с примерными ключами? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "✅ Файл .env.sandbox найден"
echo ""

# Проверка что PostgreSQL запущен
if ! systemctl is-active --quiet postgresql; then
    echo "⚠️  PostgreSQL не запущен. Попытка запустить..."
    sudo systemctl start postgresql
    if [ $? -ne 0 ]; then
        echo "❌ Не удалось запустить PostgreSQL"
        exit 1
    fi
fi

echo "✅ PostgreSQL запущен"
echo ""

# Проверка что база ecohaul_sandbox существует
DB_EXISTS=$(PGPASSWORD=Kolobo4ek123 psql -U postgres -lqt 2>/dev/null | cut -d \| -f 1 | grep -w ecohaul_sandbox | wc -l)

if [ "$DB_EXISTS" -eq 0 ]; then
    echo "⚠️  База данных ecohaul_sandbox не найдена"
    echo "📝 Создайте её командой:"
    echo "   psql -U postgres -c 'CREATE DATABASE ecohaul_sandbox;'"
    echo ""
    read -p "Попытаться создать автоматически? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        PGPASSWORD=Kolobo4ek123 psql -U postgres -c "CREATE DATABASE ecohaul_sandbox;" 2>/dev/null
        if [ $? -eq 0 ]; then
            echo "✅ База ecohaul_sandbox создана"
        else
            echo "❌ Не удалось создать базу. Создайте вручную:"
            echo "   sudo -u postgres psql -c 'CREATE DATABASE ecohaul_sandbox;'"
            exit 1
        fi
    else
        exit 1
    fi
else
    echo "✅ База данных ecohaul_sandbox существует"
fi

echo ""

# Применение миграций
echo "📦 Применение миграций..."
export ENV_FILE=.env.sandbox
poetry run alembic upgrade head

if [ $? -ne 0 ]; then
    echo "❌ Ошибка при применении миграций"
    exit 1
fi

echo "✅ Миграции применены"
echo ""

# Создание директории для логов
mkdir -p logs
echo "✅ Директория logs создана"
echo ""

# Запуск сервера
echo "========================================="
echo "🎉 Запуск сервера на http://localhost:8000"
echo "========================================="
echo ""
echo "📚 Swagger UI: http://localhost:8000/api/docs"
echo "🔍 Health check: http://localhost:8000/health"
echo ""
echo "⚡ Для остановки нажмите Ctrl+C"
echo ""
echo "💡 В другом терминале запустите ngrok:"
echo "   ~/ngrok http 8000"
echo ""
echo "========================================="
echo ""

poetry run uvicorn app.main:app --reload --env-file .env.sandbox --port 8000
