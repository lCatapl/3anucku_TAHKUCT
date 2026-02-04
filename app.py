from flask import Flask, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os
from config import DevelopmentConfig, ProductionConfig

# Инициализация
app = Flask(__name__)
app.config.from_object(DevelopmentConfig if os.environ.get('FLASK_ENV') == 'development' else ProductionConfig)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'
migrate = Migrate(app, db)

# Blueprints (импорт ПОСЛЕ db.init_app)
from blueprints.auth import auth_bp
from blueprints.game import game_bp
from blueprints.chat import chat_bp
from blueprints.profile import profile_bp
from blueprints.blog import blog_bp

app.register_blueprint(auth_bp)
app.register_blueprint(game_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(blog_bp)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/leaderboard')
def leaderboard():
    from models import User
    top = User.query.order_by(User.points.desc()).limit(10).all()
    return {'players': [{'name': u.username, 'points': u.points} for u in top]}

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
