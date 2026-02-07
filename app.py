from flask import Flask, render_template, request, redirect, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import random
import time
from collections import defaultdict
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'tankist-render-2026-zapiski-super-key-ultimate-v3!!!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tankist.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

db = SQLAlchemy(app)

# 🔥 ПОЛНЫЕ МОДЕЛИ БД
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    bio = db.Column(db.Text, default='')
    battles_total = db.Column(db.Integer, default=0)
    wins = db.Column(db.Integer, default=0)
    points = db.Column(db.Integer, default=0)
    garage = db.Column(db.Text, default='Т-34-85')  # JSON танков гаража
    favorite_tanks = db.Column(db.Text, default='Т-34-85')
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.Float, default=time.time)
    is_muted = db.Column(db.Boolean, default=False)
    mute_until = db.Column(db.DateTime, nullable=True)
    
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

# 🔥 ГАРАЖ И КАТАЛОГ - РЕАЛЬНЫЕ ТАНКИ WoT
TANK_CATALOG = {
    'Т-34-85': {'price': 500, 'hp': 100, 'damage': 25, 'speed': 45, 'tier': 6, 'nation': 'СССР'},
    'ИС-2': {'price': 1500, 'hp': 150, 'damage': 40, 'speed': 35, 'tier': 7, 'nation': 'СССР'},
    'КВ-1': {'price': 2000, 'hp': 200, 'damage': 30, 'speed': 25, 'tier': 6, 'nation': 'СССР'},
    'Т-34/76': {'price': 300, 'hp': 85, 'damage': 20, 'speed': 50, 'tier': 5, 'nation': 'СССР'},
    'СУ-152': {'price': 2500, 'hp': 120, 'damage': 60, 'speed': 30, 'tier': 7, 'nation': 'СССР'},
    'Т-54': {'price': 3500, 'hp': 110, 'damage': 35, 'speed': 42, 'tier': 8, 'nation': 'СССР'},
    'Т-10М': {'price': 8000, 'hp': 180, 'damage': 50, 'speed': 38, 'tier': 10, 'nation': 'СССР'},
    'ИС-7': {'price': 12000, 'hp': 250, 'damage': 70, 'speed': 30, 'tier': 10, 'nation': 'СССР'},
    'КР-1': {'price': 20000, 'hp': 375, 'damage': 95, 'speed': 28, 'tier': 11, 'nation': 'СССР'}
}

# АКТИВНОСТЬ
last_activity = defaultdict(lambda: time.time())

def init_database():
    db.create_all()
    
    ADMIN_USERS = {'Назар': '120187', 'CatNap': '120187'}
    for username, password in ADMIN_USERS.items():
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username, garage='Т-34-85')
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
    
    if Note.query.count() == 0:
        notes_data = [
            ("15.07.41", "Под Москвой Pz.IV рикошет. Башня целая."),
            ("22.08.41", "Ельня. 2 БТР + 1 танк. Прорыв обороны!"),
            ("10.01.42", "Старая Русса. Ночной бой с пулемётчиками."),
            ("12.07.43", "Курская дуга. Артиллерия бьёт по позициям."),
            ("27.01.44", "Ленинград. Прорыв блокады! Т-34 рвёт!"),
            ("25.04.45", "Берлин. Последний бой. До Победы рукой подать!")
        ]
        for date, content in notes_data * 25:
            note = Note(date=date, content=content)
            db.session.add(note)
        db.session.commit()

with app.app_context():
    init_database()

# 🔥 ВСЕ ЗВАНИЯ - ПОЛНЫЙ СПИСОК
def get_rank_name(points):
    ranks = {
        0: "Рядовой", 100: "Ефрейтор", 500: "Мл.Сержант", 1000: "Сержант",
        2500: "Ст.Сержант", 5000: "Старшина", 10000: "Прапорщик", 25000: "Штаб-сержант",
        50000: "Мл.прапорщик", 75000: "Прапорщик", 100000: "Ст.прапорщик",
        150000: "Мл.лейтенант", 200000: "Лейтенант", 300000: "Ст.лейтенант",
        400000: "Капитан", 500000: "Мл.капитан", 600000: "Капитан",
        700000: "Майор", 800000: "Подполковник", 900000: "Полковник",
        1000000: "Генерал-майор", 1200000: "Генерал-лейтенант", 1500000: "Генерал армии",
        2000000: "Маршал", 3000000: "Маршал Советского Союза", 5000000: "Герой"
    }
    for threshold, rank_name in sorted(ranks.items(), reverse=True):
        if points >= threshold:
            return rank_name
    return "Рядовой"

def get_next_rank_info(current_points):
    rank_thresholds = {
        "Рядовой": 100, "Ефрейтор": 500, "Мл.Сержант": 1000, "Сержант": 2500,
        "Ст.Сержант": 5000, "Старшина": 10000, "Прапорщик": 25000,
        "Штаб-сержант": 50000, "Мл.прапорщик": 75000, "Прапорщик": 100000,
        "Ст.прапорщик": 150000, "Мл.лейтенант": 200000, "Лейтенант": 300000,
        "Ст.лейтенант": 400000, "Капитан": 500000, "Мл.капитан": 600000,
        "Капитан": 700000, "Майор": 800000, "Подполковник": 900000,
        "Полковник": 1000000, "Генерал-майор": 1200000, "Генерал-лейтенант": 1500000,
        "Генерал армии": 2000000, "Маршал": 3000000, "Маршал Советского Союза": 5000000
    }
    
    current_rank = get_rank_name(current_points)
    next_threshold = rank_thresholds.get(current_rank, 5000000)
    
    next_rank = "Герой"
    for rank, threshold in rank_thresholds.items():
        if threshold > current_points and threshold > next_threshold:
            next_rank = rank
            next_threshold = threshold
            break
    
    return next_threshold, next_rank

def get_real_stats():
    try:
        total_users = User.query.count()
        total_battles = db.session.query(db.func.sum(User.battles_total)).scalar() or 0
        
        cutoff = time.time() - 300
        now = time.time()
        online_count = afk_count = 0
        
        for user in User.query.all():
            if user.last_seen > cutoff:
                online_count += 1
                if now - user.last_seen > 60:
                    afk_count += 1
        
        return {
            'online': online_count,
            'real_online': max(0, online_count - afk_count),
            'afk': afk_count,
            'users': total_users,
            'battles': total_battles
        }
    except:
        return {'online': 1, 'real_online': 1, 'afk': 0, 'users': 0, 'battles': 0}

def update_user_activity(username):
    try:
        user = User.query.filter_by(username=username).first()
        if user:
            user.last_seen = time.time()
            db.session.commit()
    except:
        pass

# 🔥 РОУТЫ
@app.route('/')
def index():
    stats = get_real_stats()
    username = session.get('username')
    return render_template('index.html', stats=stats, username=username)

@app.route('/profile')
def profile():
    username = session.get('username')
    print(f"🔍 SESSION DEBUG: {session.get('username')}")
    
    if not username:
        return render_template('profile.html', guest=True)
    
    update_user_activity(username)
    
    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username, garage='Т-34-85')
            user.set_password('default')
            db.session.add(user)
            db.session.commit()
        
        next_points, next_rank = get_next_rank_info(user.points)
        progress = min(100, (user.points / max(next_points, 1)) * 100)
        
        stats = {
            'username': user.username,
            'bio': user.bio or '',
            'battles': getattr(user, 'battles_total', 0),
            'wins': getattr(user, 'wins', 0),
            'points': getattr(user, 'points', 0),
            'rank': get_rank_name(getattr(user, 'points', 0)),
            'rank_progress': progress,
            'next_rank_points': next_points,
            'points_to_next': max(0, next_points - getattr(user, 'points', 0)),
            'next_rank': next_rank,
            'joined': getattr(user, 'date_joined', datetime.now()).strftime('%d.%m.%Y'),
            'garage': eval(getattr(user, 'garage', "['Т-34-85']")) if getattr(user, 'garage') else ['Т-34-85']
        }
        return render_template('profile.html', stats=stats)
    except Exception as e:
        print(f"❌ Profile error: {e}")
        return render_template('profile.html', guest=False, stats={'username': username, 'rank': 'Рядовой'})

@app.route('/catalog')
def catalog():
    return render_template('catalog.html', tanks=TANK_CATALOG)

@app.route('/garage')
def garage():
    username = session.get('username')
    if not username:
        return redirect('/auth/login')
    
    try:
        user = User.query.filter_by(username=username).first()
        user_garage = eval(user.garage) if user.garage else ['Т-34-85']
    except:
        user_garage = ['Т-34-85']
    
    return render_template('garage.html', garage=user_garage, tanks=TANK_CATALOG)

@app.route('/game')
def game():
    username = session.get('username')
    if not username:
        return redirect('/auth/login')
    return render_template('game.html')

@app.route('/chat')
def chat():
    try:
        messages = Message.query.order_by(Message.timestamp.desc()).limit(50).all()[::-1]
    except:
        messages = []
    return render_template('chat.html', messages=messages)

@app.route('/blog')
def blog():
    try:
        notes = Note.query.order_by(Note.id.desc()).limit(20).all()
    except:
        notes = []
    return render_template('blog.html', notes=notes)

# АВТОРИЗАЦИЯ
@app.route('/auth/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        
        # Админы
        if username in ['Назар', 'CatNap'] and password == '120187':
            session['username'] = username
            session['role'] = 'Администратор'
            session.permanent = True
            return redirect('/')
        
        # БД
        try:
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                session['username'] = username
                session['role'] = 'Обычный'
                session.permanent = True
                return redirect('/')
        except:
            pass
        
        return render_template('login.html', error='Неверный логин/пароль!')
    return render_template('login.html')

@app.route('/auth/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        
        if len(username) < 3 or len(password) < 6:
            return render_template('register.html', error='Ник >3, пароль >6!')
        
        try:
            if User.query.filter_by(username=username).first():
                return render_template('register.html', error='Имя занято!')
            
            user = User(username=username, garage='Т-34-85')
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            session['username'] = username
            session['role'] = 'Обычный'
            session.permanent = True
            return redirect('/')
        except:
            return render_template('register.html', error='Ошибка!')
    return render_template('register.html')

@app.route('/auth/logout')
def logout():
    session.clear()
    return redirect('/')

# API
@app.route('/api/stats')
def api_stats():
    stats = get_real_stats()
    stats['username'] = session.get('username')
    return jsonify(stats)

@app.route('/api/chat/send', methods=['POST'])
def chat_send():
    username = session.get('username', 'Гость')
    content = request.json.get('content', '').strip()
    
    if not content or len(content) > 200 or not session.get('username'):
        return jsonify({'error': 'Ошибка отправки!'}), 400
    
    banned_words = ['мат', 'спам', 'бот', 'хуй', 'пизд', 'хуя', 'пиздец']
    if any(word in content.lower() for word in banned_words):
        return jsonify({'error': 'Нарушение правил!'}), 403
    
    try:
        role = 'Администратор' if username in ['Назар', 'CatNap'] else 'Обычный'
        msg = Message(username=username, content=content, role=role)
        db.session.add(msg)
        db.session.commit()
        return jsonify({'status': 'ok'})
    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({'error': 'Ошибка сервера!'}), 500

@app.route('/api/buy-tank', methods=['POST'])
def buy_tank():
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Авторизуйтесь!'}), 401
    
    data = request.json
    tank_name = data.get('tank')
    
    if tank_name not in TANK_CATALOG:
        return jsonify({'error': 'Танк не найден!'}), 400
    
    try:
        user = User.query.filter_by(username=username).first()
        user_points = getattr(user, 'points', 0)
        price = TANK_CATALOG[tank_name]['price']
        
        if user_points < price:
            return jsonify({'error': f'Нужно {price} очков!'}), 400
        
        garage = eval(user.garage) if user.garage else []
        if tank_name not in garage:
            garage.append(tank_name)
            user.garage = str(garage)
            user.points -= price
            db.session.commit()
            return jsonify({'status': 'ok', 'points_left': user.points})
        else:
            return jsonify({'error': 'Танк уже есть!'}), 400
    except:
        return jsonify({'error': 'Ошибка покупки!'}), 500

@app.route('/api/game/tanks')
def game_tanks():
    username = session.get('username')
    if not username:
        return jsonify([])
    
    try:
        user = User.query.filter_by(username=username).first()
        garage = eval(user.garage) if user.garage else ['Т-34-85']
        return jsonify([{'name': t, **TANK_CATALOG[t]} for t in garage])
    except:
        return jsonify([{'name': 'Т-34-85', **TANK_CATALOG['Т-34-85']}])

@app.route('/api/game/battle', methods=['POST'])
def game_battle():
    username = session.get('username', 'Гость')
    data = request.json
    player_tank = data.get('player_tank')
    
    if not username or player_tank not in TANK_CATALOG:
        return jsonify({'error': 'Ошибка!'}), 400
    
    enemy_tank = random.choice(list(TANK_CATALOG.keys()))
    player_stats = TANK_CATALOG[player_tank]
    enemy_stats = TANK_CATALOG[enemy_tank]
    
    player_hp, enemy_hp = player_stats['hp'], enemy_stats['hp']
    battle_log = []
    
    while player_hp > 0 and enemy_hp > 0:
        damage = random.randint(player_stats['damage']//2, player_stats['damage'])
        enemy_hp -= damage
        battle_log.append(f"{player_tank}: {damage} урона (Враг: {max(0,enemy_hp)})")
        if enemy_hp <= 0: break
        
        damage = random.randint(enemy_stats['damage']//2, enemy_stats['damage'])
        player_hp -= damage
        battle_log.append(f"{enemy_tank}: {damage} урона (Вы: {max(0,player_hp)})")
    
    result = 'win' if enemy_hp <= 0 else 'lose'
    reward = random.randint(120, 180) if result == 'win' else random.randint(25, 50)
    
    try:
        user = User.query.filter_by(username=username).first()
        if user:
            user.battles_total += 1
            if result == 'win': user.wins += 1
            user.points += reward
            user.last_seen = time.time()
            db.session.commit()
    except:
        pass
    
    return jsonify({
        'result': result, 'reward': reward, 'player_tank': player_tank,
        'enemy_tank': enemy_tank, 'battle_log': battle_log
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
