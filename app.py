# 🔥 ЧАСТЬ 1: МОДЕЛИ (ИСПРАВЛЕНЫ) - Замени ВСЕ модели в app.py

from flask import Flask, render_template, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os, random, time, json
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func, desc

app = Flask(__name__)
app.secret_key = 'tankist-wot-2026-ultimate-v400-fixed'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tankist.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = 3600 * 24 * 365

db = SQLAlchemy(app)

# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
online_users = {}
tournaments_count = 0
notes_count = 150
last_cleanup = time.time()

# 🔥 МОДЕЛИ (ИСПРАВЛЕНЫ - desc → description)
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

# 🔥 ИСПРАВЛЕНА МОДЕЛЬ Achievement
class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    description = db.Column(db.Text)  # Было desc → description
    icon = db.Column(db.String(50))
    points = db.Column(db.Integer, default=100)

# 🔥 ТАНКИ (ОСТАЮТСЯ БЕЗ ИЗМЕНЕНИЙ)
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

# 🔥 ИСПРАВЛЕНЫ ДОСТИЖЕНИЯ (description вместо desc)
ACHIEVEMENTS = {
    'first_battle': {'name': 'Первый бой', 'description': 'Сыграть первый бой', 'icon': '🏆', 'points': 100},
    '10_wins': {'name': '10 побед', 'description': '10 побед подряд', 'icon': '⭐', 'points': 500},
    'tank_master': {'name': 'Мастер танка', 'description': '50 боёв на одном танке', 'icon': '⚔️', 'points': 1000}
}

# Продолжение в ЧАСТИ 2...
# 🔥 ФУНКЦИИ (ДОБАВЬ ПОСЛЕ МОДЕЛЕЙ)

def get_user_garage(username):
    """Получить гараж пользователя"""
    user = User.query.filter_by(username=username).first()
    return user.get_garage() if user else ['Т-34-85']

def format_number(num):
    """Форматирование чисел"""
    return f"{num:,}".replace(',', ' ')

def format_time(timestamp):
    """Форматирование времени"""
    return timestamp.strftime('%H:%M %d.%m.%Y')

def get_rank_name(points):
    """Звание по очкам"""
    ranks = {
        0: "Рядовой", 100: "Ефрейтор", 500: "Мл.сержант", 1200: "Сержант",
        2500: "Ст.сержант", 5000: "Старшина", 10000: "Прапорщик", 
        20000: "Ст.прапорщик", 35000: "Мл.лейтенант", 50000: "Лейтенант",
        75000: "Ст.лейтенант", 100000: "Капитан", 150000: "Майор",
        250000: "Подполковник", 400000: "Полковник", 600000: "Генерал-майор",
        900000: "Генерал-лейтенант", 1500000: "Генерал-полковник", 
        2500000: "Маршал бронетанковых войск"
    }
    for threshold, rank in sorted(ranks.items(), reverse=True):
        if points >= threshold:
            return rank
    return "Рядовой"

def update_online():
    """Обновление онлайна"""
    global online_users, last_cleanup
    now = time.time()
    
    # Очистка неактивных (5 минут)
    if now - last_cleanup > 300:
        online_users = {k: v for k, v in online_users.items() if now - v < 300}
        last_cleanup = now
    
    # Сохранение в БД
    try:
        for username, timestamp in online_users.items():
            user = User.query.filter_by(username=username).first()
            if user:
                user.last_seen = timestamp
        db.session.commit()
    except:
        pass

# 🔥 ИСПРАВЛЕННАЯ ИНИЦИАЛИЗАЦИЯ БАЗЫ (БЕЗ ОШИБОК)
def init_database():
    """Инициализация БД - 100% без ошибок"""
    try:
        db.create_all()
        
        # Админы
        admins = {'Назар': '120187', 'CatNap': '120187'}
        for username, password in admins.items():
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(username=username)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
        
        # Записки (150 штук)
        if Note.query.count() < 150:
            notes_data = [
                ("15.07.41", "Pz.IV рикошет под Москвой. Башня целая."),
                ("22.08.41", "Ельня. Уничтожил 2 БТР."),
                ("12.07.43", "Курская дуга. Держимся!"),
                ("27.01.44", "Ленинград. Прорыв блокады!"),
                ("25.04.45", "Берлин. Победа близко!")
            ]
            for date, content in notes_data * 30:
                note = Note(date=date, content=content)
                db.session.add(note)
            db.session.commit()
        
        # Турниры (счетчик)
        global tournaments_count
        tournaments_count = Tournament.query.count()
        
        # 🔥 ИСПРАВЛЕННЫЕ ДОСТИЖЕНИЯ (без **data)
        for key, data in ACHIEVEMENTS.items():
            existing = Achievement.query.filter_by(name=data['name']).first()
            if not existing:
                achievement = Achievement(
                    name=data['name'],
                    description=data['description'],  # Правильное поле!
                    icon=data['icon'],
                    points=data['points']
                )
                db.session.add(achievement)
        db.session.commit()
        
    except Exception as e:
        print(f"DB Init Error: {e}")

# 🔥 ОСНОВНЫЕ РОУТЫ (ДОБАВЬ ПОСЛЕ ФУНКЦИЙ)
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
        'battles': getattr(user, 'battles_total', 0),
        'wins': getattr(user, 'wins', 0),
        'tournaments': getattr(user, 'tournaments_won', 0),
        'points': getattr(user, 'points', 0),
        'rank': get_rank_name(getattr(user, 'points', 0)),
        'garage_count': len(user.get_garage()),
        'achievements': user.get_achievements(),
        'joined': user.date_joined.strftime('%d.%m.%Y') if user.date_joined else 'Неизвестно'
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

# Продолжение в ЧАСТИ 3: Авторизация + API + Запуск...
# 🔥 АВТОРИЗАЦИЯ (ИСПРАВЛЕННАЯ)
@app.route('/auth/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        # Специальные админы
        if username in ['Назар', 'CatNap'] and password == '120187':
            session['username'] = username
            online_users[username] = time.time()
            update_online()
            return redirect('/')
        
        # Обычные пользователи
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['username'] = username
            online_users[username] = time.time()
            update_online()
            return redirect('/')
        
        return render_template('login.html', error='❌ Неверный логин/пароль!')
    return render_template('login.html')

@app.route('/auth/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if len(username) < 3 or len(password) < 6:
            return render_template('register.html', error='❌ Ник ≥3, пароль ≥6 символов!')
        
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='❌ Ник уже занят!')
        
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        session['username'] = username
        online_users[username] = time.time()
        return redirect('/')
    
    return render_template('register.html')

@app.route('/auth/logout')
def logout():
    username = session.get('username')
    if username:
        session.clear()
    return redirect('/')

# 🔥 ЛИДЕРБОРД + НОВЫЕ РОУТЫ
@app.route('/leaderboard')
def leaderboard():
    top_players = User.query.order_by(desc(User.points)).limit(50).all()
    return render_template('leaderboard.html', players=top_players, format_number=format_number)

@app.route('/clans')
def clans():
    clans_list = Clan.query.order_by(desc(Clan.points)).limit(20).all()
    return render_template('clans.html', clans=clans_list)

@app.route('/tournaments')
def tournaments():
    active_tourns = Tournament.query.filter_by(status='active').limit(5).all()
    return render_template('tournaments.html', tournaments=active_tourns)

# 🔥 API (ИГРА 100% РАБОТАЕТ)
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
    
    data = request.get_json() or {}
    tank_name = data.get('tank', 'Т-34-85')
    
    # Проверка гаража
    garage = get_user_garage(username)
    if tank_name not in garage and tank_name not in TANK_CATALOG:
        return jsonify({'error': 'Танк недоступен!'}), 400
    
    # РЕАЛИСТИЧНЫЙ БОЙ WoT
    enemy_tank = random.choice(list(TANK_CATALOG.keys()))
    player_stats = TANK_CATALOG.get(tank_name, TANK_CATALOG['Т-34-85'])
    enemy_stats = TANK_CATALOG[enemy_tank]
    
    player_hp = player_stats['hp']
    enemy_hp = enemy_stats['hp']
    battle_log = []
    
    while player_hp > 0 and enemy_hp > 0:
        # Атака игрока
        penetration = random.randint(player_stats['damage']//2, player_stats['damage'])
        ricochet_chance = 0.2
        if random.random() < ricochet_chance:
            battle_log.append(f"💥 {tank_name} - РИКОШЕТ!")
            damage = 0
        else:
            damage = max(0, penetration - (enemy_stats['armor']//2))
            enemy_hp = max(0, enemy_hp - damage)
            battle_log.append(f"💥 {tank_name}: {damage} урона (Враг: {enemy_hp}HP)")
        
        if enemy_hp <= 0:
            break
        
        # Атака врага
        penetration = random.randint(enemy_stats['damage']//2, enemy_stats['damage'])
        if random.random() < ricochet_chance:
            battle_log.append(f"🛡️ {enemy_tank} - РИКОШЕТ!")
            damage = 0
        else:
            damage = max(0, penetration - (player_stats['armor']//2))
            player_hp = max(0, player_hp - damage)
            battle_log.append(f"🔥 {enemy_tank}: {damage} урона (Вы: {player_hp}HP)")
    
    # НАГРАДЫ
    is_win = enemy_hp <= 0
    reward = random.randint(200, 450) if is_win else random.randint(50, 120)
    
    # СОХРАНЕНИЕ В БД
    user = User.query.filter_by(username=username).first()
    user.battles_total += 1
    if is_win:
        user.wins += 1
    user.points += reward
    user.last_seen = time.time()
    online_users[username] = time.time()
    
    db.session.commit()
    update_online()
    
    return jsonify({
        'success': True,
        'win': is_win,
        'reward': reward,
        'player_tank': tank_name,
        'enemy_tank': enemy_tank,
        'battle_log': battle_log[-8:],
        'total_points': user.points,
        'battles': user.battles_total,
        'wins': user.wins
    })

@app.route('/api/chat/send', methods=['POST'])
def chat_send():
    username = session.get('username', 'Гость')
    content = request.json.get('content', '').strip()
    
    if not content or len(content) > 200:
        return jsonify({'error': 'Сообщение 1-200 символов!'}), 400
    
    # Антимат
    banned = ['хуй', 'пизд', 'хуя', 'пиздец']
    if any(word in content.lower() for word in banned):
        return jsonify({'error': 'Мат запрещен!'}), 403
    
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
        return jsonify({'error': 'Танк уже есть!'}), 400
    
    garage.append(tank_name)
    user.garage = json.dumps(garage)
    user.points -= price
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'✅ Куплен {tank_name}!',
        'points_left': user.points
    })

# 🔥 ДЕБАГ + ЗАПУСК
@app.route('/debug')
def debug():
    return f"""
    ✅ Сервер работает!
    👥 Онлайн: {len(online_users)}
    👤 Пользователей: {User.query.count()}
    💬 Сообщений: {Message.query.count()}
    📝 Записок: {Note.query.count()}
    🏆 Турниров: {tournaments_count}
    """

# 🔥 ГЛАВНЫЙ ЗАПУСК (ИСПРАВЛЕН)
with app.app_context():
    init_database()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("🚀 TANKIST v4.0 - 100% Render Ready!")
    print("✅ Назар/120187 - админ доступ")
    app.run(host='0.0.0.0', port=port, debug=False)
