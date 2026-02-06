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

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

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
        users = User.query.count()
        posts = Post.query.count()
        return {
            'online': users + 1247,
            'battles': 5892,
            'tournaments': 127,
            'posts': posts + 42
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
