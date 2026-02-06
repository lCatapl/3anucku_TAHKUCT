from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    avatar = db.Column(db.String(200), default='t34.png')
    points = db.Column(db.Integer, default=0)
    wins = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Tank(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    model_file = db.Column(db.String(50))
    hp = db.Column(db.Integer, default=100)
    damage = db.Column(db.Integer, default=25)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Добавь ПОСЛЕ существующих моделей:
class Battle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Tournament(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class UserActivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    is_afk = db.Column(db.Boolean, default=False)

RANK_NAMES = {
    0: "Новобранец", 100: "Рядовой", 500: "Ефрейтор", 1000: "Капрал",
    2500: "Мастер-капрал", 5000: "Сержант", 10000: "Штаб-сержант",
    25000: "Мастер-сержант", 50000: "Первый сержант", 75000: "Сержант-майор",
    100000: "Уорэнт-офицер 1", 150000: "Подполковник", 200000: "Полковник",
    300000: "Бригадир", 400000: "Генерал-майор", 500000: "Генерал-лейтенант",
    600000: "Генерал", 700000: "Маршал", 800000: "Фельдмаршал", 900000: "Командор",
    950000: "Генералиссимус", 990000: "Легенда", 1000000: "Ветеран"
}
