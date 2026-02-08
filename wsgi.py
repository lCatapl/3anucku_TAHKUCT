# wsgi.py - ДОЛЖЕН БЫТЬ В КОРНЕ ПРОЕКТА
from app import app as application

if __name__ == "__main__":
    application.run()
