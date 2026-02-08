# wsgi.py - ГЛАВНЫЙ ФАЙЛ ДЛЯ GUNICORN/RENDER
from app import app as application

if __name__ == "__main__":
    application.run()
