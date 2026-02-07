from flask import Flask, render_template, request, redirect, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import random
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'tankist-render-2026-zapiski-super-key-ultimate!!!'  # НОВЫЙ КЛЮЧ!
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tankist.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_SECURE'] = False  # Render HTTP
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

db = SQLAlchemy(app)

# МОДЕЛИ (БЕЗ ИЗМЕНЕНИЙ)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    bio = db.Column(db.Text, default='')
    battles_total = db.Column(db.Integer, default=0)
    wins = db.Column(db.Integer, default=0)
    points = db.Column(db.Integer, default=0)
    favorite_tanks = db.Column(db.Text, default='Т-34-85')
    garage = db.Column(db.Text, default='Т-34-85')
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)
    is_muted = db.Column(db.Boolean, default=False)
    mute_until = db.Column(db.DateTime, nullable=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    content = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    role = db.Column(db.String(20), default='Обычный')

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20))
    content = db.Column(db.Text)
    author = db.Column(db.String(50), default='Танкист')

# 🔥 АВТОСОЗДАНИЕ БАЗЫ + АДМИНЫ ПРИ СТАРТЕ
def init_database():
    try:
        db.create_all()
        
        # 🔥 АДМИНЫ ГАРАНТИРОВАННО!
        ADMIN_USERS = {'Назар': '120187', 'CatNap': '120187'}
        for username, password in ADMIN_USERS.items():
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(username=username)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                print(f"✅ Админ {username} создан!")
        
        # Записки
        if Note.query.count() == 0:
            notes_data = [
                ("15.07.41", "Под Москвой Pz.IV рикошет."),
                ("22.08.41", "Ельня. 2 БТР + танк."),
                ("10.01.42", "Старая Русса. Ночь."),
                ("12.07.43", "Курск. Арта бьёт."),
                ("27.01.44", "Ленинград. Прорыв!"),
                ("25.04.45", "Берлин. Победа!")
            ]
            for date, content in notes_data * 25:
                note = Note(date=date, content=content)
                db.session.add(note)
            db.session.commit()
            print("✅ 150 записок созданы!")
            
    except Exception as e:
        print(f"❌ DB Error: {e}")

with app.app_context():
    init_database()

def get_rank_name(points):
    ranks = {0: "Новобранец", 100: "Рядовой", 500: "Ефрейтор", 1000: "Капрал",
             2500: "Мастер-капрал", 5000: "Сержант", 10000: "Штаб-сержант",
             25000: "Мастер-сержант", 50000: "Первый сержант", 75000: "Сержант-майор",
             100000: "Уорэнт-офицер 1", 150000: "Подполковник", 200000: "Полковник",
             300000: "Бригадир", 400000: "Генерал-майор", 500000: "Генерал-лейтенант",
             600000: "Генерал", 700000: "Маршал", 800000: "Фельдмаршал", 900000: "Командор",
             950000: "Генералиссимус", 990000: "Легенда", 1000000: "Ветеран"}
    for threshold, rank_name in sorted(ranks.items(), reverse=True):
        if points >= threshold:
            return rank_name
    return "Новобранец"

def get_next_rank_points(current_points):
    ranks = {0: 100, 100: 500, 500: 1000, 1000: 2500, 2500: 5000, 5000: 10000, 
             10000: 25000, 25000: 50000, 50000: 75000, 75000: 100000}
    for points, next_points in ranks.items():
        if current_points < points:
            return next_points
    return 1000000

# 🔥 ОСНОВНЫЕ РОУТЫ
@app.route('/')
def index():
    stats = get_stats()
    username = session.get('username', None)
    return render_template('index.html', stats=stats, username=username)

@app.route('/profile')
def profile():
    username = session.get('username')
    print(f"🔍 DEBUG /profile: session={session}, username='{username}'")  # DEBUG
    
    if not username:
        return render_template('profile.html', guest=True)
    
    try:
        user = User.query.filter_by(username=username).first()
        print(f"🔍 DEBUG user found: {user.username if user else 'NOT FOUND'}")  # DEBUG
        
        if not user:
            # 🔥 АДМИН В БД!
            if username in ['Назар', 'CatNap']:
                user = User(username=username)
                user.set_password('120187')
                db.session.add(user)
                db.session.commit()
                print(f"✅ Админ {username} добавлен в БД!")
            
            else:
                return render_template('profile.html', guest=True)
        
        next_points = get_next_rank_points(user.points)
        stats = {
            'username': user.username,
            'bio': user.bio or '',
            'battles': user.battles_total,
            'wins': user.wins,
            'points': user.points,
            'rank': get_rank_name(user.points),
            'rank_progress': min(100, (user.points / max(next_points, 1)) * 100),
            'next_rank_points': next_points,
            'favorite_tanks': user.favorite_tanks.split(',') if user.favorite_tanks else ['Т-34-85'],
            'joined': user.date_joined.strftime('%d.%m.%Y') if user.date_joined else 'Сегодня'
        }
        return render_template('profile.html', stats=stats)
    except Exception as e:
        print(f"❌ Profile error: {e}")
        return render_template('profile.html', guest=True)

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

@app.route('/game')
def game():
    return render_template('game.html')

@app.route('/auth/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        
        print(f"🔍 LOGIN ATTEMPT: {username}")  # DEBUG
        
        # 🔥 АДМИНЫ БЕЗ БД!
        if username in ['Назар', 'CatNap'] and password == '120187':
            session['username'] = username
            session['role'] = 'Администратор'
            session.permanent = True
            print(f"✅ АДМИН {username} ВОШЁЛ!")
            return redirect('/')
        
        # БД
        try:
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                session['username'] = username
                session['role'] = 'Обычный'
                session.permanent = True
                print(f"✅ USER {username} ВОШЁЛ!")
                return redirect('/')
        except:
            pass
        
        return render_template('login.html', error='❌ Неверный логин/пароль!')
    
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
            
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            session['username'] = username
            session['role'] = 'Обычный'
            session.permanent = True
            return redirect('/')
        except:
            return render_template('register.html', error='Ошибка регистрации!')
    
    return render_template('register.html')

@app.route('/auth/logout')
def logout():
    session.clear()
    return redirect('/')

def get_stats():
    try:
        users_count = User.query.count()
        total_battles = db.session.query(db.func.sum(User.battles_total)).scalar() or 0
        online = random.randint(2, 12) if session.get('username') else random.randint(1, 5)
        return {'online': online, 'users': users_count, 'battles': total_battles}
    except:
        return {'online': 1 if session.get('username') else 0, 'users': 0, 'battles': 0}

@app.route('/api/stats')
def api_stats():
    return jsonify(get_stats())

# Остальные API без изменений...
wot_tanks = {
    'Т-34-85': {'hp': 100, 'damage': 25, 'speed': 45},
    'ИС-2': {'hp': 150, 'damage': 40, 'speed': 35},
    'КВ-1': {'hp': 200, 'damage': 30, 'speed': 25},
    'Т-34/76': {'hp': 85, 'damage': 20, 'speed': 50},
    'СУ-152': {'hp': 120, 'damage': 60, 'speed': 30},
    'Т-54': {'hp': 110, 'damage': 35, 'speed': 42}
}

@app.route('/api/game/tanks')
def game_tanks():
    return jsonify(list(wot_tanks.keys()))

@app.route('/api/game/battle', methods=['POST'])
def game_battle():
    # Логика боя (без изменений)
    username = session.get('username', 'Гость')
    data = request.json
    player_tank = data.get('player_tank')
    
    if player_tank not in wot_tanks:
        return jsonify({'error': 'Танк не найден!'}), 400
    
    enemy_tank = random.choice(list(wot_tanks.keys()))
    player_stats = wot_tanks[player_tank]
    enemy_stats = wot_tanks[enemy_tank]
    
    player_hp, enemy_hp = player_stats['hp'], enemy_stats['hp']
    battle_log = []
    
    while player_hp > 0 and enemy_hp > 0:
        damage = random.randint(player_stats['damage']//2, player_stats['damage'])
        enemy_hp -= damage
        battle_log.append(f"{player_tank}: {damage} урона (Враг: {max(0,enemy_hp)}HP)")
        if enemy_hp <= 0: break
        
        damage = random.randint(enemy_stats['damage']//2, enemy_stats['damage'])
        player_hp -= damage
        battle_log.append(f"{enemy_tank}: {damage} урона (Вы: {max(0,player_hp)}HP)")
    
    result = 'win' if enemy_hp <= 0 else 'lose'
    reward = 100 if result == 'win' else 25
    
    if username != 'Гость':
        try:
            user = User.query.filter_by(username=username).first()
            if user:
                user.battles_total += 1
                if result == 'win': user.wins += 1
                user.points += reward
                db.session.commit()
        except: pass
    
    return jsonify({
        'result': result, 'reward': reward, 'player_tank': player_tank,
        'enemy_tank': enemy_tank, 'battle_log': battle_log
    })

@app.route('/init-db')
def init_db():
    init_database()
    return "✅ БАЗА + АДМИНЫ СОЗДАНЫ! Назар/CatNap: 120187"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
