from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import DevelopmentConfig
import os

app = Flask(__name__)
app.config.from_object(DevelopmentConfig)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'

# Blueprints
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
