from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import DevelopmentConfig
from models import User
import os
from datetime import datetime

# Инициализация ДО создания app
db = SQLAlchemy()

app = Flask(__name__)
app.config.from_object(DevelopmentConfig)
db.init_app(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/auth/login')
def login_page():
    return redirect(url_for('auth.login'))

@app.route('/game')
def game():
    return render_template('game.html')

@app.route('/chat')
def chat():
    return render_template('chat.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')

@app.route('/blog')
def blog():
    return render_template('blog.html')

@app.route('/api/stats')
def stats():
    from models import User, Post, Battle, Tournament, UserActivity
    from datetime import datetime, timedelta
    import time
    
    # Правильный app_context для SQLAlchemy
    try:
        # Подсчёт реальных пользователей
        users_count = User.query.count()
        
        # Активные (последние 60 сек) vs АФК (более 60 сек)
        now = datetime.utcnow()
        recent_activity = UserActivity.query.filter(
            UserActivity.last_activity >= now - timedelta(minutes=1)
        ).count()
        afk_count = UserActivity.query.filter(
            UserActivity.last_activity < now - timedelta(minutes=1)
        ).count()
        
        # Бои и турниры ЗА СЕГОДНЯ (сброс 00:00 UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        battles_today = Battle.query.filter(Battle.timestamp >= today_start).count()
        tournaments_today = Tournament.query.filter(Tournament.timestamp >= today_start).count()
        
        # Посты НАВСЕГДА (не сбрасываются)
        posts_count = Post.query.count()
        
        return {
            'online': recent_activity + afk_count,
            'afk': afk_count,
            'battles': battles_today,
            'tournaments': tournaments_today,
            'posts': posts_count,
            'users': users_count,
            'timestamp': int(time.time())
        }
    except Exception as e:
        # Fallback если БД недоступна
        return {
            'online': 0, 'afk': 0, 'battles': 0, 'tournaments': 0, 
            'posts': 0, 'users': 0, 'error': str(e)
        }

from blueprints.auth import auth_bp
app.register_blueprint(auth_bp, url_prefix='/auth')

@app.route('/init-db')
def init_db():
    with app.app_context():
        db.create_all()
    return "База создана!"

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)






