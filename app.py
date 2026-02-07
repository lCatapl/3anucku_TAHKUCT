from flask import Flask, render_template, request, redirect, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import random
import time
from collections import defaultdict
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'tankist-render-2026-zapiski-super-key-ultimate!!!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tankist.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

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
    favorite_tanks = db.Column(db.Text, default='Т-34-85')
    garage = db.Column(db.Text, default='Т-34-85')
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
    username = db.Column(db.String(50))
    content = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    role = db.Column(db.String(20), default='Обычный')

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20))
    content = db.Column(db.Text)
    author = db.Column(db.String(50), default='Танкист')

# АКТИВНОСТЬ ПОЛЬЗОВАТЕЛЕЙ
last_activity = defaultdict(lambda: time.time())

def init_database():
    try:
        db.create_all()
        
        ADMIN_USERS = {'Назар': '120187', 'CatNap': '120187'}
        for username, password in ADMIN_USERS.items():
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(username=username)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                print(f"✅ Админ {username} создан!")
        
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

def get_next_rank_info(current_points):
    rank_thresholds = {
        "Новобранец": 100, "Рядовой": 500, "Ефрейтор": 1000, "Капрал": 2500,
        "Мастер-капрал": 5000, "Сержант": 10000, "Штаб-сержант": 25000,
        "Мастер-сержант": 50000, "Первый сержант": 75000, "Сержант-майор": 100000,
        "Уорэнт-офицер 1": 150000, "Подполковник": 200000, "Полковник": 300000
    }
    
    current_rank = get_rank_name(current_points)
    next_rank_threshold = rank_thresholds.get(current_rank, 1000000)
    
    if current_points >= next_rank_threshold:
        next_rank_threshold = 1000000
    
    next_rank_name = "Ветеран"
    for rank_name, threshold in rank_thresholds.items():
        if threshold > current_points:
            next_rank_name = rank_name
            next_rank_threshold = threshold
            break
    
    return next_rank_threshold, next_rank_name

def get_real_stats():
    try:
        total_users = User.query.count()
        total_battles = db.session.query(db.func.sum(User.battles_total)).scalar() or 0
        
        cutoff = time.time() - 300  # 5 минут
        now = time.time()
        
        online_count = 0
        afk_count = 0
        
        for user in User.query.all():
            if user.last_seen > cutoff:
                online_count += 1
                if now - user.last_seen > 60:  # 1 минута AFK
                    afk_count += 1
        
        real_online = online_count - afk_count
        return {
            'online': online_count,
            'real_online': max(0, real_online),
            'afk': afk_count,
            'users': total_users,
            'battles': total_battles
        }
    except:
        return {'online': 0, 'real_online': 0, 'afk': 0, 'users': 0, 'battles': 0}

def update_user_activity(username):
    last_activity[username] = time.time()
    try:
        user = User.query.filter_by(username=username).first()
        if user:
            user.last_seen = time.time()
            db.session.commit()
    except:
        pass

# РОУТЫ
@app.route('/')
def index():
    stats = get_real_stats()
    username = session.get('username', None)
    return render_template('index.html', stats=stats, username=username)

@app.route('/profile')
def profile():
    username = session.get('username')
    if not username:
        return render_template('profile.html', guest=True)
    
    update_user_activity(username)
    
    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            if username in ['Назар', 'CatNap']:
                user = User(username=username)
                user.set_password('120187')
                db.session.add(user)
                db.session.commit()
            else:
                return render_template('profile.html', guest=True)
        
        next_points, next_rank = get_next_rank_info(user.points)
        progress = min(100, (user.points / max(next_points, 1)) * 100)
        
        stats = {
            'username': user.username,
            'bio': user.bio or '',
            'battles': user.battles_total,
            'wins': user.wins,
            'points': user.points,
            'rank': get_rank_name(user.points),
            'rank_progress': progress,
            'next_rank_points': next_points,
            'points_to_next': max(0, next_points - user.points),
            'next_rank': next_rank,
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
        
        if username in ['Назар', 'CatNap'] and password == '120187':
            session['username'] = username
            session['role'] = 'Администратор'
            session.permanent = True
            update_user_activity(username)
            return redirect('/')
        
        try:
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                session['username'] = username
                session['role'] = 'Обычный'
                session.permanent = True
                update_user_activity(username)
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
            update_user_activity(username)
            return redirect('/')
        except:
            return render_template('register.html', error='Ошибка регистрации!')
    return render_template('register.html')

@app.route('/auth/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/api/stats')
def api_stats():
    stats = get_real_stats()
    stats['username'] = session.get('username', None)
    return jsonify(stats)

@app.route('/api/chat/send', methods=['POST'])
def chat_send():
    username = session.get('username', 'Гость')
    content = request.json.get('content', '').strip()
    
    update_user_activity(username)
    
    if not content or len(content) > 200:
        return jsonify({'error': '1-200 символов'}), 400
    
    banned_words = ['блять', 'хер', 'сука', 'хуй', 'пизда']
    if any(word in content.lower() for word in banned_words):
        return jsonify({'error': 'Нарушение правил!'}), 403
    
    role = 'Администратор' if username in ['Назар', 'CatNap'] else session.get('role', 'Обычный')
    
    try:
        msg = Message(username=username, content=content, role=role)
        db.session.add(msg)
        db.session.commit()
        return jsonify({'status': 'ok'})
    except:
        return jsonify({'error': 'Ошибка чата'}), 500

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
    username = session.get('username', 'Гость')
    data = request.json
    player_tank = data.get('player_tank')
    
    update_user_activity(username)
    
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
    reward = 150 if result == 'win' else 30
    
    if username != 'Гость':
        try:
            user = User.query.filter_by(username=username).first()
            if user:
                user.battles_total += 1
                if result == 'win':
                    user.wins += 1
                user.points += reward
                user.last_seen = time.time()
                db.session.commit()
        except:
            pass
    
    return jsonify({
        'result': result, 'reward': reward, 'player_tank': player_tank,
        'enemy_tank': enemy_tank, 'battle_log': battle_log
    })

@app.route('/init-db')
def init_db():
    init_database()
    return "✅ БАЗА + АДМИНЫ СОЗДАНЫ!"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
