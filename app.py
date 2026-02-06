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
@app.route('/index')
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
@login_required
def profile():
    return render_template('profile.html')

@app.route('/blog')
def blog():
    return render_template('blog.html')

@app.route('/api/stats')
def stats():
    with app.app_context():
        from models import User, Post, Battle, Tournament, UserActivity
        import datetime
        
        now = datetime.datetime.utcnow()
        total_users = User.query.count()
        total_posts = Post.query.count()
        today_battles = Battle.query.filter(
            Battle.timestamp >= now.replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        today_tournaments = Tournament.query.filter(
            Tournament.timestamp >= now.replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        
        active_users = UserActivity.query.filter(
            UserActivity.last_activity >= now - datetime.timedelta(minutes=1),
            UserActivity.is_afk == False
        ).count()
        afk_users = UserActivity.query.filter(
            UserActivity.last_activity < now - datetime.timedelta(minutes=1)
        ).count()
        
        return {
            'online': active_users + afk_users,
            'afk': afk_users,
            'battles': today_battles,
            'tournaments': today_tournaments,
            'posts': total_posts,
            'users': total_users
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


