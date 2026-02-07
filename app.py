# ========================================
# ЧАСТЬ 1/6 - БАЗА И МОДЕЛИ
# ========================================
from flask import Flask, render_template, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import random
import time
import json
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'tankist-2026-final-super-secret-key-v4'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tankist.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# МОДЕЛИ
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    bio = db.Column(db.Text, default='')
    battles_total = db.Column(db.Integer, default=0)
    wins = db.Column(db.Integer, default=0)
    points = db.Column(db.Integer, default=0)
    garage = db.Column(db.Text, default='["Т-34-85"]')
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.Float, default=time.time)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    role = db.Column(db.String(20), default='Обычный')

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20))
    content = db.Column(db.Text)
    author = db.Column(db.String(50), default='Танкист')

print("✅ ЧАСТЬ 1: МОДЕЛИ СОЗДАНЫ")
# ========================================
# ЧАСТЬ 2/6 - ДАННЫЕ ТАНКОВ + ИНИЦИАЛИЗАЦИЯ
# ========================================
TANK_CATALOG = {
    'Т-34-85': {'price': 500, 'hp': 100, 'damage': 25, 'speed': 45, 'tier': 6},
    'ИС-2': {'price': 1500, 'hp': 150, 'damage': 40, 'speed': 35, 'tier': 7},
    'КВ-1': {'price': 2000, 'hp': 200, 'damage': 30, 'speed': 25, 'tier': 6},
    'Т-34/76': {'price': 300, 'hp': 85, 'damage': 20, 'speed': 50, 'tier': 5},
    'СУ-152': {'price': 2500, 'hp': 120, 'damage': 60, 'speed': 30, 'tier': 7},
    'Т-54': {'price': 3500, 'hp': 110, 'damage': 35, 'speed': 42, 'tier': 8}
}

# 30 ЗВАНИЙ
RANK_SYSTEM = {
    0: "Рядовой", 100: "Ефрейтор", 500: "Мл.Сержант", 1000: "Сержант",
    2500: "Ст.Сержант", 5000: "Старшина", 10000: "Прапорщик", 25000: "Штаб-сержант",
    50000: "Мл.прапорщик", 75000: "Прапорщик", 100000: "Ст.прапорщик",
    150000: "Мл.лейтенант", 200000: "Лейтенант", 300000: "Ст.лейтенант",
    400000: "Капитан", 500000: "Мл.капитан", 600000: "Капитан",
    700000: "Майор", 800000: "Подполковник", 900000: "Полковник",
    1000000: "Генерал-майор", 1500000: "Генерал-лейтенант", 2000000: "Генерал армии",
    3000000: "Маршал", 5000000: "Маршал СССР", 10000000: "Герой Советского Союза"
}

def init_db():
    try:
        db.create_all()
        
        # Админы
        admins = {'Назар': '120187', 'CatNap': '120187'}
        for username, pwd in admins.items():
            if not User.query.filter_by(username=username).first():
                user = User(username=username, garage='["Т-34-85"]')
                user.set_password(pwd)
                db.session.add(user)
                db.session.commit()
        
        # Записки
        if not Note.query.first():
            notes = [
                ("15.07.41", "Под Москвой столкнулся с Pz.IV"),
                ("22.08.41", "Прорыв под Ельней - 2 БТР"),
                ("12.07.43", "Курская дуга - держимся!")
            ]
            for date, text in notes * 50:
                db.session.add(Note(date=date, content=text))
            db.session.commit()
        print("✅ БАЗА ИНИЦИАЛИЗИРОВАНА")
    except Exception as e:
        print(f"❌ Init error: {e}")

with app.app_context():
    init_db()

print("✅ ЧАСТЬ 2: ДАННЫЕ + БАЗА")
# ========================================
# ЧАСТЬ 3/6 - ОСНОВНЫЕ ФУНКЦИИ
# ========================================
def get_rank_name(points):
    for threshold, rank in sorted(RANK_SYSTEM.items(), reverse=True):
        if points >= threshold:
            return rank
    return "Рядовой"

def get_next_rank(points):
    thresholds = sorted(RANK_SYSTEM.keys())
    for i, thresh in enumerate(thresholds):
        if points < thresh:
            return thresh, list(RANK_SYSTEM.values())[i]
    return 10000000, "Герой Советского Союза"

def get_user_garage(username):
    try:
        user = User.query.filter_by(username=username).first()
        return json.loads(user.garage) if user and user.garage else ['Т-34-85']
    except:
        return ['Т-34-85']

def update_user_stats(username, battles=0, wins=0, points=0):
    try:
        user = User.query.filter_by(username=username).first()
        if user:
            user.battles_total += battles
            user.wins += wins
            user.points += points
            user.last_seen = time.time()
            db.session.commit()
            return True
    except:
        pass
    return False

def get_stats():
    try:
        users = User.query.count()
        battles = db.session.query(db.func.sum(User.battles_total)).scalar() or 0
        return {'online': random.randint(1, 10), 'users': users, 'battles': battles}
    except:
        return {'online': 1, 'users': 0, 'battles': 0}

print("✅ ЧАСТЬ 3: ФУНКЦИИ")
# ========================================
# ЧАСТЬ 4/6 - ОСНОВНЫЕ РОУТЫ
# ========================================
@app.route('/')
def index():
    stats = get_stats()
    username = session.get('username', None)
    return render_template('index.html', stats=stats, username=username)

@app.route('/profile')
def profile():
    username = session.get('username')
    if not username:
        return render_template('profile.html', guest=True)
    
    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username, garage='["Т-34-85"]')
            user.set_password('default')
            db.session.add(user)
            db.session.commit()
        
        next_points, next_rank = get_next_rank(user.points)
        progress = min(100, (user.points / next_points) * 100)
        
        stats = {
            'username': user.username,
            'bio': user.bio or '',
            'battles': user.battles_total,
            'wins': user.wins,
            'points': user.points,
            'rank': get_rank_name(user.points),
            'rank_progress': progress,
            'next_rank_points': next_points,
            'points_to_next': next_points - user.points,
            'next_rank': next_rank,
            'garage': json.loads(user.garage)
        }
        return render_template('profile.html', stats=stats)
    except:
        return render_template('profile.html', guest=False, stats={'username': username})

@app.route('/catalog')
def catalog():
    return render_template('catalog.html', tanks=TANK_CATALOG)

@app.route('/garage')
def garage():
    username = session.get('username')
    if not username:
        return redirect('/auth/login')
    garage = get_user_garage(username)
    return render_template('garage.html', garage=garage, tanks=TANK_CATALOG)

@app.route('/game')
def game():
    username = session.get('username')
    if not username:
        return redirect('/auth/login')
    garage = get_user_garage(username)
    return render_template('game.html', garage=garage, tanks=TANK_CATALOG)

@app.route('/chat')
def chat():
    try:
        messages = Message.query.order_by(Message.timestamp.desc()).limit(50).all()[::-1]
    except:
        messages = []
    return render_template('chat.html', messages=messages)

@app.route('/blog')
def blog():
    notes = Note.query.order_by(Note.id.desc()).limit(20).all()
    return render_template('blog.html', notes=notes)

print("✅ ЧАСТЬ 4: РОУТЫ")
# ========================================
# ЧАСТЬ 5/6 - АВТОРИЗАЦИЯ
# ========================================
@app.route('/auth/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        
        # Админы
        if username in ['Назар', 'CatNap'] and password == '120187':
            session['username'] = username
            session['role'] = 'Администратор'
            return redirect('/')
        
        # БД
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['username'] = username
            session['role'] = 'Обычный'
            return redirect('/')
        
        return render_template('login.html', error='Неверный логин/пароль!')
    return render_template('login.html')

@app.route('/auth/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        
        if len(username) < 3 or len(password) < 6:
            return render_template('register.html', error='Ник >3, пароль >6 символов!')
        
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Имя занято!')
        
        user = User(username=username, garage='["Т-34-85"]')
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

print("✅ ЧАСТЬ 5: АВТОРИЗАЦИЯ")
# ========================================
# ЧАСТЬ 6/6 - API + ЗАПУСК
# ========================================
@app.route('/api/stats')
def api_stats():
    return jsonify(get_stats())

@app.route('/api/chat/send', methods=['POST'])
def chat_send():
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Авторизуйтесь!'}), 401
    
    content = request.json.get('content', '').strip()
    if len(content) > 200 or len(content) < 1:
        return jsonify({'error': '1-200 символов'}), 400
    
    banned = ['мат', 'спам', 'бот']
    if any(word in content.lower() for word in banned):
        return jsonify({'error': 'Мут!'}), 403
    
    try:
        msg = Message(username=username, content=content, 
                     role='Администратор' if username in ['Назар', 'CatNap'] else 'Обычный')
        db.session.add(msg)
        db.session.commit()
        return jsonify({'status': 'ok'})
    except:
        return jsonify({'error': 'Ошибка!'}), 500

@app.route('/api/buy-tank', methods=['POST'])
def buy_tank():
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Войдите!'}), 401
    
    tank = request.json.get('tank')
    if tank not in TANK_CATALOG:
        return jsonify({'error': 'Танк не найден!'}), 400
    
    try:
        user = User.query.filter_by(username=username).first()
        price = TANK_CATALOG[tank]['price']
        
        if user.points < price:
            return jsonify({'error': f'Нужно {price} очков!'}), 400
        
        garage = json.loads(user.garage)
        if tank not in garage:
            garage.append(tank)
            user.garage = json.dumps(garage)
            user.points -= price
            db.session.commit()
            return jsonify({'status': 'ok'})
        else:
            return jsonify({'error': 'Уже есть!'}), 400
    except:
        return jsonify({'error': 'Ошибка покупки!'}), 500

@app.route('/api/game/tanks')
def game_tanks():
    username = session.get('username', None)
    if not username:
        return jsonify([])
    return jsonify(get_user_garage(username))

@app.route('/api/game/battle', methods=['POST'])
def game_battle():
    username = session.get('username', None)
    if not username:
        return jsonify({'error': 'Войдите!'}), 401
    
    tank = request.json.get('tank')
    if tank not in TANK_CATALOG:
        return jsonify({'error': 'Танк недоступен!'}), 400
    
    # Бой
    enemy = random.choice(list(TANK_CATALOG.keys()))
    p_stats = TANK_CATALOG[tank]
    e_stats = TANK_CATALOG[enemy]
    
    p_hp, e_hp = p_stats['hp'], e_stats['hp']
    log = []
    
    while p_hp > 0 and e_hp > 0:
        dmg = random.randint(p_stats['damage']//2, p_stats['damage'])
        e_hp = max(0, e_hp - dmg)
        log.append(f"{tank}: {dmg} урона")
        if e_hp <= 0: break
        
        dmg = random.randint(e_stats['damage']//2, e_stats['damage'])
        p_hp = max(0, p_hp - dmg)
        log.append(f"{enemy}: {dmg} урона")
    
    win = e_hp <= 0
    reward = random.randint(120, 200) if win else random.randint(20, 50)
    
    update_user_stats(username, 1, 1 if win else 0, reward)
    
    return jsonify({
        'win': win, 'reward': reward, 'log': log,
        'tank': tank, 'enemy': enemy
    })

@app.route('/init-db')
def init():
    with app.app_context():
        init_db()
    return "База создана!"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)

print("✅ app.py ПОЛНОСТЬЮ РАБОТАЕТ!")
