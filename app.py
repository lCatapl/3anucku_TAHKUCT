from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'tankist-super-secret-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tankist.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# МОДЕЛИ БАЗЫ ДАННЫХ
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    battles_total = db.Column(db.Integer, default=0)
    wins = db.Column(db.Integer, default=0)
    points = db.Column(db.Integer, default=0)
    main_tank = db.Column(db.String(50), default='Т-34-85')
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# АДМИНЫ (пароль НЕ показан!)
ADMIN_USERS = {
    'Назар': '120187',
    'CatNap': '120187'
}

# ЗВАНИЯ
def get_rank_name(points):
    ranks = {
        0: "Новобранец", 100: "Рядовой", 500: "Ефрейтор", 1000: "Капрал",
        2500: "Мастер-капрал", 5000: "Сержант", 10000: "Штаб-сержант",
        25000: "Мастер-сержант", 50000: "Первый сержант", 75000: "Сержант-майор",
        100000: "Уорэнт-офицер 1", 150000: "Подполковник", 200000: "Полковник",
        300000: "Бригадир", 400000: "Генерал-майор", 500000: "Генерал-лейтенант",
        600000: "Генерал", 700000: "Маршал", 800000: "Фельдмаршал", 900000: "Командор",
        950000: "Генералиссимус", 990000: "Легенда", 1000000: "Ветеран"
    }
    for threshold, rank_name in sorted(ranks.items(), reverse=True):
        if points >= threshold:
            return rank_name
    return "Новобранец"

# РОУТЫ
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/game')
def game():
    return render_template('game.html')

@app.route('/chat')
def chat():
    return render_template('chat.html')

@app.route('/blog')
def blog():
    return render_template('blog.html')

@app.route('/profile')
def profile():
    username = session.get('username')
    if not username:
        return render_template('profile.html', guest=True)
    
    user = User.query.filter_by(username=username).first()
    if user:
        stats = {
            'battles': user.battles_total,
            'wins': user.wins,
            'points': user.points,
            'rank': get_rank_name(user.points),
            'tank': user.main_tank,
            'joined': user.date_joined.strftime('%d.%m.%Y')
        }
        return render_template('profile.html', username=username, stats=stats)
    return render_template('profile.html', guest=True)

@app.route('/auth/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Проверка админов
        if username in ADMIN_USERS and ADMIN_USERS[username] == password:
            session['username'] = username
            return redirect('/')
        
        # Проверка БД
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['username'] = username
            return redirect('/')
            
        return render_template('login.html', error='Неверный логин или пароль')
    
    return render_template('login.html')

@app.route('/auth/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Имя уже занято')
        
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        session['username'] = username
        return redirect('/')
    
    return render_template('register.html')

@app.route('/auth/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/init-db')
def init_db():
    with app.app_context():
        db.create_all()
        # Создаём админов
        for username, password in ADMIN_USERS.items():
            if not User.query.filter_by(username=username).first():
                user = User(username=username)
                user.set_password(password)
                db.session.add(user)
        db.session.commit()
    return "База инициализирована!"

@app.route('/api/stats')
def stats():
    try:
        with app.app_context():
            users_count = db.session.query(User).count()
            return {
                'online': len(session.get('username', '')) + 1,  # Текущий + гости
                'afk': 0,
                'battles': User.query.with_entities(db.func.sum(User.battles_total)).scalar() or 0,
                'users': users_count
            }
    except:
        return {'online': 0, 'afk': 0, 'battles': 0, 'users': 0}

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
