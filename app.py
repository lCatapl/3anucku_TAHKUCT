from flask import Flask, render_template, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import random
import time
import json
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func

app = Flask(__name__)
app.secret_key = 'tankist-wot-2026-ultimate-production-v200'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tankist.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = 3600 * 24 * 30

db = SQLAlchemy(app)

# МОДЕЛИ
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    bio = db.Column(db.Text, default='')
    battles_total = db.Column(db.Integer, default=0)
    wins = db.Column(db.Integer, default=0)
    points = db.Column(db.Integer, default=0)
    garage = db.Column(db.Text, default='["Т-34-85"]')
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.Float, default=time.time())
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_garage(self):
        try:
            return json.loads(self.garage)
        except:
            return ['Т-34-85']

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    role = db.Column(db.String(20), default='Танкист')

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20))
    content = db.Column(db.Text)

# ТАНКИ WoT
TANK_CATALOG = {
    'Т-34-85': {'price': 500, 'hp': 860, 'damage': 250, 'speed': 55, 'tier': 6, 'nation': 'СССР'},
    'ИС-2': {'price': 1500, 'hp': 1270, 'damage': 390, 'speed': 37, 'tier': 7, 'nation': 'СССР'},
    'КВ-1': {'price': 2000, 'hp': 1260, 'damage': 520, 'speed': 35, 'tier': 6, 'nation': 'СССР'},
    'ИС-3': {'price': 4500, 'hp': 1710, 'damage': 441, 'speed': 43, 'tier': 8, 'nation': 'СССР'},
    'Т-54': {'price': 3500, 'hp': 1350, 'damage': 360, 'speed': 56, 'tier': 9, 'nation': 'СССР'},
    'Pz.Kpfw VI Tiger': {'price': 1800, 'hp': 750, 'damage': 220, 'speed': 40, 'tier': 7, 'nation': 'Германия'},
    'Panzer V Panther': {'price': 2200, 'hp': 975, 'damage': 250, 'speed': 55, 'tier': 7, 'nation': 'Германия'},
    'Maus': {'price': 35000, 'hp': 3000, 'damage': 490, 'speed': 20, 'tier': 10, 'nation': 'Германия'},
    'T110E5': {'price': 28000, 'hp': 2250, 'damage': 440, 'speed': 34, 'tier': 10, 'nation': 'США'},
    'AMX 50 B': {'price': 32000, 'hp': 2280, 'damage': 440, 'speed': 65, 'tier': 10, 'nation': 'Франция'}
}

# ЗВАНИЯ РККА
RANK_SYSTEM = {
    0: "Рядовой", 100: "Ефрейтор", 500: "Мл.сержант", 1200: "Сержант",
    2500: "Ст.сержант", 5000: "Старшина", 10000: "Прапорщик", 20000: "Ст.прапорщик",
    35000: "Мл.лейтенант", 50000: "Лейтенант", 75000: "Ст.лейтенант", 100000: "Капитан",
    150000: "Майор", 250000: "Подполковник", 400000: "Полковник", 600000: "Генерал-майор",
    900000: "Генерал-лейтенант", 1500000: "Генерал-полковник", 2500000: "Маршал бронетанковых войск"
}

def init_database():
    try:
        db.create_all()
        admins = {'Назар': '120187', 'CatNap': '120187'}
        for username, password in admins.items():
            if not User.query.filter_by(username=username).first():
                user = User(username=username)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
        
        if not Note.query.first():
            notes = [
                ("15.07.41", "Pz.IV рикошет под Москвой"),
                ("22.08.41", "Ельня. 2 БТР уничтожено"),
                ("12.07.43", "Курская дуга держимся!")
            ]
            for date, content in notes * 10:
                db.session.add(Note(date=date, content=content))
            db.session.commit()
    except Exception as e:
        print(f"DB Init: {e}")

with app.app_context():
    init_database()

def format_number(num):
    return f"{num:,}".replace(',', '.')

def format_time(timestamp):
    return timestamp.strftime('%H:%M %d.%m.%Y')

def get_rank_name(points):
    for threshold, rank in sorted(RANK_SYSTEM.items(), reverse=True):
        if points >= threshold:
            return rank
    return "Рядовой"

def get_next_rank_info(points):
    thresholds = sorted(RANK_SYSTEM.keys())
    for i, thresh in enumerate(thresholds):
        if points < thresh:
            return thresholds[i], list(RANK_SYSTEM.values())[i]
    return 2500000, "Маршал бронетанковых войск"

def get_user_garage(username):
    user = User.query.filter_by(username=username).first()
    return user.get_garage() if user else ['Т-34-85']

def get_server_stats():
    try:
        total_users = User.query.count()
        total_battles = db.session.query(func.sum(User.battles_total)).scalar() or 0
        return {'online': random.randint(3, 12), 'users': total_users, 'battles': total_battles}
    except:
        return {'online': 1, 'users': 1, 'battles': 0}

@app.route('/')
def index():
    return render_template('index.html', stats=get_server_stats(), username=session.get('username'))

@app.route('/profile')
def profile():
    username = session.get('username')
    if not username:
        return render_template('profile.html', guest=True)
    
    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username)
        user.set_password('default')
        db.session.add(user)
        db.session.commit()
    
    next_points, next_rank = get_next_rank_info(user.points)
    progress = min(100, (user.points / max(next_points, 1)) * 100)
    
    stats = {
        'username': user.username,
        'bio': user.bio or '',
        'battles': user.battles_total,
        'wins': user.wins,
        'points': user.points,
        'rank': get_rank_name(user.points),
        'rank_progress': round(progress, 1),
        'next_rank_points': next_points,
        'points_to_next': max(0, next_points - user.points),
        'next_rank': next_rank,
        'joined': format_time(user.date_joined),
        'garage_count': len(user.get_garage())
    }
    return render_template('profile.html', stats=stats, format_number=format_number)

@app.route('/catalog')
def catalog():
    return render_template('catalog.html', tanks=TANK_CATALOG)

@app.route('/garage')
def garage():
    if not session.get('username'):
        return redirect('/auth/login')
    garage = get_user_garage(session['username'])
    return render_template('garage.html', garage=garage, tanks=TANK_CATALOG)

@app.route('/game')
def game():
    if not session.get('username'):
        return redirect('/auth/login')
    garage = get_user_garage(session['username'])
    return render_template('game.html', garage=garage, tanks=TANK_CATALOG)

@app.route('/chat')
def chat():
    messages = Message.query.order_by(Message.timestamp.desc()).limit(50).all()
    messages = messages[::-1]
    return render_template('chat.html', messages=messages, format_time=format_time)

@app.route('/blog')
def blog():
    notes = Note.query.order_by(Note.id.desc()).limit(20).all()
    return render_template('blog.html', notes=notes)

@app.route('/auth/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if username in ['Назар', 'CatNap'] and password == '120187':
            session['username'] = username
            session.permanent = True
            return redirect('/')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['username'] = username
            session.permanent = True
            return redirect('/')
        
        return render_template('login.html', error='Неверный логин/пароль!')
    return render_template('login.html')

@app.route('/auth/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if len(username) < 3 or len(password) < 6:
            return render_template('register.html', error='Ник ≥3, пароль ≥6!')
        
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Имя занято!')
        
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        session['username'] = username
        session.permanent = True
        return redirect('/')
    return render_template('register.html')

@app.route('/auth/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/api/stats')
def api_stats():
    stats = get_server_stats()
    stats['username'] = session.get('username')
    return jsonify(stats)

@app.route('/api/chat/send', methods=['POST'])
def chat_send():
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Авторизуйтесь!'}), 401
    
    content = request.json.get('content', '').strip()
    if not content or len(content) > 200:
        return jsonify({'error': '1-200 символов'}), 400
    
    banned_words = ['хуй', 'пизд', 'хуя']
    if any(word in content.lower() for word in banned_words):
        return jsonify({'error': 'Запрещено!'}), 403
    
    message = Message(username=username, content=content)
    db.session.add(message)
    db.session.commit()
    return jsonify({'status': 'ok'})

@app.route('/api/buy-tank', methods=['POST'])
def buy_tank():
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Авторизуйтесь!'}), 401
    
    tank_name = request.json.get('tank')
    if tank_name not in TANK_CATALOG:
        return jsonify({'error': 'Танк не найден!'}), 400
    
    user = User.query.filter_by(username=username).first()
    price = TANK_CATALOG[tank_name]['price']
    
    if user.points < price:
        return jsonify({'error': f'Нужно {price} очков!'}), 400
    
    garage = user.get_garage()
    if tank_name in garage:
        return jsonify({'error': 'Уже есть!'}), 400
    
    garage.append(tank_name)
    user.garage = json.dumps(garage)
    user.points -= price
    db.session.commit()
    return jsonify({'status': 'ok', 'points_left': user.points})

@app.route('/api/game/tanks')
def api_game_tanks():
    username = session.get('username')
    if not username:
        return jsonify([])
    return jsonify(get_user_garage(username))

@app.route('/api/game/battle', methods=['POST'])
def api_game_battle():
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Авторизуйтесь!'}), 401
    
    tank_name = request.json.get('tank')
    garage = get_user_garage(username)
    if tank_name not in garage:
        return jsonify({'error': 'Танк недоступен!'}), 400
    
    enemy_tank = random.choice(list(TANK_CATALOG.keys()))
    p_stats = TANK_CATALOG[tank_name]
    e_stats = TANK_CATALOG[enemy_tank]
    
    p_hp, e_hp = p_stats['hp'], e_stats['hp']
    battle_log = []
    
    while p_hp > 0 and e_hp > 0:
        dmg = random.randint(p_stats['damage']//3, p_stats['damage'])
        e_hp = max(0, e_hp - dmg)
        battle_log.append(f"{tank_name}: {dmg} урона")
        if e_hp <= 0: break
        
        dmg = random.randint(e_stats['damage']//3, e_stats['damage'])
        p_hp = max(0, p_hp - dmg)
        battle_log.append(f"{enemy_tank}: {dmg} урона")
    
    is_win = e_hp <= 0
    reward = random.randint(150, 300) if is_win else random.randint(25, 75)
    
    user = User.query.filter_by(username=username).first()
    user.battles_total += 1
    if is_win:
        user.wins += 1
    user.points += reward
    db.session.commit()
    
    return jsonify({
        'win': is_win,
        'reward': reward,
        'battle_log': battle_log[-8:]
    })

@app.route('/debug')
def debug():
    return f"✅ Сервер работает! Пользователей: {User.query.count()}"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
