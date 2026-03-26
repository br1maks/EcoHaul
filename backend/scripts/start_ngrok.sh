#!/bin/bash

# ========================================
# Скрипт быстрого запуска ngrok
# ========================================

echo "🌐 Запуск ngrok для webhook..."
echo ""

# Проверка что ngrok установлен
if ! command -v ngrok &> /dev/null; then
    exit 1
fi

echo "✅ ngrok найден"
echo ""

# Проверка что сервер запущен на порту 8001
if ! lsof -i:8001 > /dev/null 2>&1; then
    echo "⚠️  Сервер не запущен на порту 8001"
    echo "📝 Запустите сервер в другом терминале:"
    echo "   ./start_sandbox.sh"
    echo ""
    read -p "Продолжить запуск ngrok? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "========================================="
echo "🎉 Запуск ngrok..."
echo "========================================="
echo ""
echo "💡 После запуска:"
echo "   1. Скопируйте Forwarding URL (https://...ngrok.io)"
echo "   2. Зайдите в YooKassa: https://yookassa.ru/"
echo "   3. Настройки → Уведомления → Добавить webhook"
echo "   4. URL: https://ВАШ-URL.ngrok.io/api/v1/payments/yookassa/webhook"
echo "   5. События: payment.succeeded, payment.canceled"
echo ""
echo "⚡ Для остановки нажмите Ctrl+C"
echo ""
echo "========================================="
echo ""

ngrok http 8001
