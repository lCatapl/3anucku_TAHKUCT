from flask import Flask, render_template, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import DevelopmentConfig
from models import User
import os

app = Flask(__name__)
app.config.from_object(DevelopmentConfig)

db = SQLAlchemy(app)

# Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 🔥 РОУТЫ ДЛЯ КНОПОК (ИСПРАВЛЕНО)
@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/game')
@app.route('/game/arena')
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

@app.route('/auth/login')
def login_page():
    return render_template('auth/login.html')

# Blueprints
from blueprints.auth import auth_bp
app.register_blueprint(auth_bp, url_prefix='/auth')

@app.route('/init-db')
def init_db():
    with app.app_context():
        db.create_all()
    return "База данных создана!"

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
