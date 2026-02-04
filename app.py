from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import LoginManager, login_required, current_user
from flask_talisman import Talisman

from config import DevelopmentConfig, ProductionConfig
from models import db, User, Tank, Score, Post
from blueprints.auth import auth_bp
from blueprints.game import game_bp
from blueprints.chat import chat_bp
from blueprints.blog import blog_bp
from blueprints.profile import profile_bp

# Инициализация
app = Flask(__name__)
app.config.from_object(DevelopmentConfig)
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
talisman = Talisman(app, content_security_policy=None)  # Позволяет inline JS

# Регистрация blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(game_bp, url_prefix='/game')
app.register_blueprint(chat_bp, url_prefix='/chat')
app.register_blueprint(blog_bp, url_prefix='/blog')
app.register_blueprint(profile_bp, url_prefix='/profile')

@app.route('/')
def index():
    """Главная страница - лендинг"""
    return render_template('index.html', user=current_user)

@app.route('/api/leaderboard')
@login_required
def leaderboard():
    """Real-time лидерборд"""
    top_players = User.query.join(Score).order_by(Score.points.desc()).limit(50).all()
    return jsonify([{'name': p.username, 'points': p.scores[0].points} for p in top_players])

@socketio.on('join_game')
def on_join_game(data):
    """WebSocket: подключение к игре"""
    room = data['room']
    join_room(room)
    emit('status', {'msg': f'{request.sid} joined {room}'}, room=room)

@socketio.on('move_tank')
def on_move_tank(data):
    """Физика танка - рассылка позиций"""
    emit('tank_update', data, room=data['room'], include_self=False)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
