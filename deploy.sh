#!/bin/bash
echo "🚀 Деплой Записок Танкиста на Render.com"

# 1. Создаём репозиторий
git init
git add .
git commit -m "Initial commit: Записки Танкиста v5.0 Ultimate"

# 2. Деплой (замени на свой токен)
git remote add origin https://github.com/YOUR_USERNAME/zapiski-tankista.git
git push -u origin main

echo "✅ Загрузи на Render.com:"
echo "  Build: pip install -r requirements.txt"
echo "  Start: gunicorn app:app"
echo "  Env: SECRET_KEY=supersecret"
