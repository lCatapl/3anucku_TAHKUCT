#!/usr/bin/env python3
import os, shutil, subprocess
from pathlib import Path

print("🎮 Создаём УЛЬТИМАТИВНЫЙ Записки Танкиста v5.0...")

# Создаём структуру
folders = [
    "blueprints", "static/css", "static/js", "static/models", 
    "static/images/tanks", "static/images/ui", "templates", 
    "migrations", "instance"
]
for folder in folders:
    Path(folder).mkdir(exist_ok=True)

# Копируем все файлы (в реальности они создаются ниже)
files = {
    "requirements.txt": """flask==3.0.0
flask-socketio==5.3.6
flask-login==0.6.3
flask-sqlalchemy==3.1.1
flask-migrate==4.0.7
flask-wtf==1.2.1
flask-talisman==1.1.0
bcrypt==4.1.2
pyotp==2.9.0
eventlet==0.36.1
pillow==10.2.0
wtforms==3.1.2""",
    
    ".env.example": """SECRET_KEY=your-super-secret-key-here
DATABASE_URL=sqlite:///instance/tankist.db
REDIS_URL=redis://localhost:6379
SESSION_SECRET=another-secret
""",

    "docker-compose.yml": """version: '3.8'
services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/tankist
    depends_on:
      - db
      - redis
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: tankist
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
  redis:
    image: redis:7-alpine
""",

    ".gitignore": """__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
instance/
*.db
.migrate/
.DS_Store
node_modules/
""",

    "config.py": '''from flask import Flask
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-change-me'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///instance/tankist.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_TYPE = 'redis'
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379'
    
class DevelopmentConfig(Config):
    DEBUG = True
    
class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
'''
}

# Записываем файлы
for filename, content in files.items():
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)

print("✅ Структура создана! Запускай: python app.py")
