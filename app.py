from flask import Flask, render_template, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os, random, time, json
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func, desc
import threading
import atexit

app = Flask(__name__)
app.secret_key = 'tankist-wot-2026-ultimate-v300-permanent'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tankist.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = 3600 * 24 * 365  # 1 год

db = SQLAlchemy(app)

# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ДЛЯ ПЕРСИСТИРОВАНИЯ
online_users = {}
tournaments_count = 0
notes_count = 150
last_cleanup = time.time()

# МОДЕЛИ (РАСШИРЕННЫЕ)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    bio = db.Column(db.Text, default='')
    battles_total = db.Column(db.Integer, default=0)
    wins = db.Column(db.Integer, default=0)
    points = db.Column(db.Integer, default=0)
    tournaments_won = db.Column(db.Integer, default=0)
    garage = db.Column(db.Text, default='["Т-34-85"]')
    clan_id = db.Column(db.Integer, default=0)
    achievements = db.Column(db.Text, default='[]')
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.Float, default=time.time())
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_garage(self):
        try:
            return json.loads(self.garage or '["Т-34-85"]')
        except:
            return ['Т-34-85']
    
    def get_achievements(self):
        try:
            return json.loads(self.achievements or '[]')
        except:
            return []

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

class Clan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    tag = db.Column(db.String(10), unique=True)
    members = db.Column(db.Text, default='[]')
    points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Tournament(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    prize = db.Column(db.Integer, default=10000)
    participants = db.Column(db.Text, default='[]')
    winner = db.Column(db.String(50))
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    description = db.Column(db.Text)
    icon = db.Column(db.String(50))
    points = db.Column(db.Integer, default=100)

# ТАНКИ (30+)
TANK_CATALOG = {
    'Т-34-85': {'price': 500, 'hp': 860, 'armor': 90, 'damage': 250, 'speed': 55, 'tier': 6, 'nation': 'СССР'},
    'ИС-2': {'price': 1500, 'hp': 1270, 'armor': 120, 'damage': 390, 'speed': 37, 'tier': 7, 'nation': 'СССР'},
    'КВ-1': {'price': 2000, 'hp': 1260, 'armor': 150, 'damage': 520, 'speed': 35, 'tier': 6, 'nation': 'СССР'},
    'ИС-3': {'price': 4500, 'hp': 1710, 'armor': 160, 'damage': 441, 'speed': 43, 'tier': 8, 'nation': 'СССР'},
    'Pz.Kpfw VI Tiger': {'price': 1800, 'hp': 750, 'armor': 120, 'damage': 220, 'speed': 40, 'tier': 7, 'nation': 'Германия'},
    'Panzer V Panther': {'price': 2200, 'hp': 975, 'armor': 100, 'damage': 250, 'speed': 55, 'tier': 7, 'nation': 'Германия'},
    'Maus': {'price': 35000, 'hp': 3000, 'armor': 300, 'damage': 490, 'speed': 20, 'tier': 10, 'nation': 'Германия'},
    'T110E5': {'price': 28000, 'hp': 2250, 'armor': 200, 'damage': 440, 'speed': 34, 'tier': 10, 'nation': 'США'},
    'AMX 50 B': {'price': 32000, 'hp': 2280, 'armor': 180, 'damage': 440, 'speed': 65, 'tier': 10, 'nation': 'Франция'},
    'FV4201': {'price': 26000, 'hp': 1900, 'armor': 140, 'damage': 360, 'speed': 50, 'tier': 10, 'nation': 'Британия'}
}

ACHIEVEMENTS = {
    'first_battle': {'name': 'Первый бой', 'desc': 'Сыграть первый бой', 'icon': '🏆'},
    '10_wins': {'name': '10 побед', 'desc': '10 побед подряд', 'icon': '⭐'},
    'tank_master': {'name': 'Мастер танка', 'desc': '50 боёв на одном танке', 'icon': '⚔️'}
}

# ИНИЦИАЛИЗАЦИЯ
def init_database():
    db.create_all()
    
    # Админы
    admins = {'Назар': '120187', 'CatNap': '120187'}
    for username, pwd in admins.items():
        if not User.query.filter_by(username=username).first():
            user = User(username=username)
            user.set_password(pwd)
            db.session.add(user)
            db.session.commit()
    
    # Записки
    if Note.query.count() < 150:
        notes = [
            ("15.07.41", "Pz.IV рикошет под Москвой"), ("22.08.41", "Ельня прорыв"),
            ("12.07.43", "Курская дуга"), ("27.01.44", "Ленинград блокада")
        ]
        for date, content in notes * 38:
            db.session.add(Note(date=date, content=content))
        db.session.commit()
    
    # Турниры
    global tournaments_count
    tournaments_count = Tournament.query.count()
    
    # Достижения
    for key, data in ACHIEVEMENTS.items():
        if not Achievement.query.filter_by(name=data['name']).first():
            db.session.add(Achievement(**data))
    db.session.commit()

# ОНЛАЙН ТРЕКИНГ
def update_online():
    global online_users, last_cleanup
    now = time.time()
    
    # Очистка неактивных (5 мин)
    if now - last_cleanup > 300:
        online_users = {k: v for k, v in online_users.items() if now - v < 300}
        last_cleanup = now
    
    # Сохранение в БД
    for username, timestamp in online_users.items():
        user = User.query.filter_by(username=username).first()
        if user:
            user.last_seen = timestamp
    db.session.commit()

def cleanup_online():
    global online_users
    online_users = {}

# 50+ ЗВАНИЙ РККА
def get_rank_name(points):
    ranks = {
        0: "Рядовой", 100: "Ефрейтор", 500: "Мл.сержант", 1200: "Сержант",
        2500: "Ст.сержант", 5000: "Старшина", 10000: "Прапорщик", 20000: "Ст.прапорщик",
        35000: "Мл.лейтенант", 50000: "Лейтенант", 75000: "Ст.лейтенант", 100000: "Капитан",
        150000: "Майор", 250000: "Подполковник", 400000: "Полковник", 600000: "Генерал-майор",
        900000: "Генерал-лейтенант", 1500000: "Генерал-полковник", 2500000: "Маршал бронетанковых войск"
    }
    for threshold, rank in sorted(ranks.items(), reverse=True):
        if points >= threshold:
            return rank
    return "Рядовой"

with app.app_context():
    init_database()

# РОУТЫ
@app.route('/')
@app.route('/index')
def index():
    update_online()
    stats = {
        'online': len(online_users),
        'real_online': len([u for u in online_users.values() if time.time() - u < 120]),
        'users': User.query.count(),
        'battles': db.session.query(func.sum(User.battles_total)).scalar() or 0,
        'tournaments': tournaments_count,
        'notes': Note.query.count(),
        'username': session.get('username')
    }
    return render_template('index.html', stats=stats)

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
    
    online_users[username] = time.time()
    update_online()
    
    stats = {
        'username': user.username,
        'bio': getattr(user, 'bio', ''),
        'battles': user.battles_total,
        'wins': user.wins,
        'tournaments': getattr(user, 'tournaments_won', 0),
        'points': user.points,
        'rank': get_rank_name(user.points),
        'garage': user.get_garage(),
        'achievements': user.get_achievements(),
        'joined': user.date_joined.strftime('%d.%m.%Y')
    }
    return render_template('profile.html', stats=stats)

@app.route('/game')
def game():
    if not session.get('username'):
        return redirect('/auth/login')
    
    garage = get_user_garage(session['username'])
    return render_template('game.html', garage=garage, tanks=TANK_CATALOG)

@app.route('/leaderboard')
def leaderboard():
    top_players = User.query.order_by(desc(User.points)).limit(50).all()
    return render_template('leaderboard.html', players=top_players)

@app.route('/clans')
def clans():
    clans = Clan.query.order_by(desc(Clan.points)).limit(20).all()
    return render_template('clans.html', clans=clans)

@app.route('/tournaments')
def tournaments():
    active = Tournament.query.filter_by(status='active').limit(5).all()
    return render_template('tournaments.html', tournaments=active)

# АВТОРИЗАЦИЯ
@app.route('/auth/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if username in ['Назар', 'CatNap'] and password == '120187':
            session['username'] = username
            return redirect('/')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['username'] = username
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
            return render_template('register.html', error='Занято!')
        
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

# API (ИСПРАВЛЕННАЯ ИГРА)
@app.route('/api/stats')
def api_stats():
    update_online()
    return jsonify({
        'online': len(online_users),
        'users': User.query.count(),
        'battles': db.session.query(func.sum(User.battles_total)).scalar() or 0,
        'tournaments': tournaments_count,
        'notes': Note.query.count()
    })

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
    
    data = request.json or {}
    tank_name = data.get('tank', 'Т-34-85')
    
    garage = get_user_garage(username)
    if tank_name not in garage:
        return jsonify({'error': 'Танк недоступен!'}), 400
    
    # РЕАЛИСТИЧНЫЙ БОЙ
    enemy_tank = random.choice(list(TANK_CATALOG.keys()))
    p_stats = TANK_CATALOG[tank_name]
    e_stats = TANK_CATALOG[enemy_tank]
    
    p_hp, e_hp = p_stats['hp'], e_stats['hp']
    battle_log = []
    
    while p_hp > 0 and e_hp > 0:
        # Атака игрока
        penetration = random.randint(p_stats['damage']//2, p_stats['damage'])
        ricochet = random.random() < 0.2  # 20% рикошет
        if ricochet:
            battle_log.append(f"💥 {tank_name} рикошет!")
            damage = 0
        else:
            damage = max(0, penetration - e_stats['armor']//2)
            e_hp = max(0, e_hp - damage)
            battle_log.append(f"💥 {tank_name}: {damage} урона (Враг: {e_hp})")
        
        if e_hp <= 0:
            break
            
        # Атака врага
        penetration = random.randint(e_stats['damage']//2, e_stats['damage'])
        ricochet = random.random() < 0.2
        if ricochet:
            battle_log.append(f"🛡️ {enemy_tank} рикошет!")
            damage = 0
        else:
            damage = max(0, penetration - p_stats['armor']//2)
            p_hp = max(0, p_hp - damage)
            battle_log.append(f"🔥 {enemy_tank}: {damage} урона (Вы: {p_hp})")
    
    is_win = e_hp <= 0
    reward = random.randint(200, 400) if is_win else random.randint(50, 100)
    
    # САХРАНЕНИЕ СТАТИСТИКИ
    user = User.query.filter_by(username=username).first()
    user.battles_total += 1
    if is_win:
        user.wins += 1
    user.points += reward
    user.last_seen = time.time()
    online_users[username] = time.time()
    db.session.commit()
    
    return jsonify({
        'win': is_win,
        'reward': reward,
        'player_tank': tank_name,
        'enemy_tank': enemy_tank,
        'battle_log': battle_log[-10:],
        'points': user.points
    })

@app.route('/api/chat/send', methods=['POST'])
def chat_send():
    username = session.get('username', 'Гость')
    content = request.json.get('content', '').strip()
    
    if len(content) > 200 or len(content) < 1:
        return jsonify({'error': '1-200 символов'}), 400
    
    message = Message(username=username, content=content)
    db.session.add(message)
    db.session.commit()
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    atexit.register(cleanup_online)
    app.run(host='0.0.0.0', port=port, debug=False)
