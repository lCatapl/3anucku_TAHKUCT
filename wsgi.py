#!/usr/bin/env python3
# wsgi.py - Render Gunicorn 100%

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Импорт Flask app напрямую
from app import app

# Render ищет ЭТО
application = app

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
