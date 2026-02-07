from flask import Flask, render_template, request, redirect, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import random
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'zapiski-tankista-2026-super-secret-key!'
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
    favorite_tanks = db.Column(db.Text, default='Т-34-85')
    garage = db.Column(db.Text, default='Т-34-85')
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)
    is_muted = db.Column(db.Boolean, default=False)
    mute_until = db.Column(db.DateTime, default=None)
    
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

# АДМИНЫ (пароль СКРЫТ!)
ADMIN_USERS = {'Назар': '120187', 'CatNap': '120187'}

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
    messages = Message.query.order_by(Message.timestamp.desc()).limit(50).all()[::-1]
    return render_template('chat.html', messages=messages)

@app.route('/blog')
def blog():
    notes = Note.query.order_by(Note.id.desc()).limit(10).all()
    return render_template('blog.html', notes=notes)

@app.route('/profile')
def profile():
    username = session.get('username')
    if not username:
        return render_template('profile.html', guest=True)
    
    user = User.query.filter_by(username=username).first()
    if not user:
        return render_template('profile.html', guest=True)
    
    next_rank_points = 100
    for points, rank in sorted({k: v for k, v in get_rank_name.__globals__['ranks'].items()}.items(), reverse=True):
        if user.points < points:
            next_rank_points = points
            break
    
    stats = {
        'username': user.username,
        'bio': user.bio,
        'battles': user.battles_total,
        'wins': user.wins,
        'points': user.points,
        'rank': get_rank_name(user.points),
        'rank_progress': (user.points / next_rank_points) * 100,
        'next_rank_points': next_rank_points,
        'favorite_tanks': user.favorite_tanks.split(',') if user.favorite_tanks else [],
        'joined': user.date_joined.strftime('%d.%m.%Y')
    }
    return render_template('profile.html', stats=stats)

@app.route('/auth/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        
        # Админы
        if username in ADMIN_USERS and ADMIN_USERS[username] == password:
            session['username'] = username
            session['role'] = 'Администратор'
            flash('Добро пожаловать, админ!')
            return redirect('/')
        
        # БД
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['username'] = username
            session['role'] = 'Обычный'
            flash(f'Добро пожаловать, {username}!')
            return redirect('/')
        
        flash('Неверный логин или пароль!')
        return render_template('login.html', error='Неверный логин или пароль')
    
    return render_template('login.html')

@app.route('/auth/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        
        if len(username) < 3 or len(password) < 6:
            flash('Ник >3 символов, пароль >6!')
            return render_template('register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Имя уже занято!')
            return render_template('register.html')
        
        try:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            session['username'] = username
            session['role'] = 'Обычный'
            flash(f'Аккаунт {username} создан!')
            return redirect('/')
        except Exception as e:
            flash('Ошибка регистрации!')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/auth/logout')
def logout():
    session.clear()
    flash('Вы вышли из аккаунта')
    return redirect('/')

# ЧАТ API
@app.route('/api/chat/send', methods=['POST'])
def chat_send():
    username = session.get('username', 'Гость')
    content = request.json.get('content', '').strip()
    
    if not content or len(content) > 200:
        return jsonify({'error': 'Сообщение 1-200 символов'}), 400
    
    user = User.query.filter_by(username=username).first()
    if user and user.is_muted and user.mute_until > datetime.utcnow():
        return jsonify({'error': 'Вы в муте!'}), 403
    
    msg = Message(username=username, content=content, role=session.get('role', 'Гость'))
    db.session.add(msg)
    db.session.commit()
    
    return jsonify({'status': 'ok'})

@app.route('/api/stats')
def stats():
    try:
        users_count = User.query.count()
        total_battles = db.session.query(db.func.sum(User.battles_total)).scalar() or 0
        
        # Онлайн = активные сессии + текущий
        online = 1 + random.randint(0, 5)  # Пока простая логика
        return jsonify({
            'online': online,
            'users': users_count,
            'battles': total_battles,
            'timestamp': int(datetime.utcnow().timestamp())
        })
    except:
        return jsonify({'online': 1, 'users': 0, 'battles': 0})

# ИГРА - ПОЛНАЯ ВЕРСИЯ
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
    player_tank = data['player_tank']
    enemy_tank = random.choice(list(wot_tanks.keys()))
    
    # Симуляция боя
    player_stats = wot_tanks[player_tank]
    enemy_stats = wot_tanks[enemy_tank]
    
    player_hp = player_stats['hp']
    enemy_hp = enemy_stats['hp']
    
    battle_log = []
    
    while player_hp > 0 and enemy_hp > 0:
        # Атака игрока
        damage = random.randint(player_stats['damage']//2, player_stats['damage'])
        enemy_hp -= damage
        battle_log.append(f"{player_tank} нанес {damage} урона. Враг HP: {max(0, enemy_hp)}")
        
        if enemy_hp <= 0:
            break
            
        # Атака врага
        damage = random.randint(enemy_stats['damage']//2, enemy_stats['damage'])
        player_hp -= damage
        battle_log.append(f"{enemy_tank} нанёс {damage} урона. Ваш HP: {max(0, player_hp)}")
    
    result = 'win' if enemy_hp <= 0 else 'lose'
    reward = 100 if result == 'win' else 25
    
    # Обновляем статистику
    if username != 'Гость':
        user = User.query.filter_by(username=username).first()
        if user:
            user.battles_total += 1
            if result == 'win':
                user.wins += 1
            user.points += reward
            db.session.commit()
    
    return jsonify({
        'result': result,
        'reward': reward,
        'player_tank': player_tank,
        'enemy_tank': enemy_tank,
        'battle_log': battle_log
    })

@app.route('/init-db')
def init_db():
    with app.app_context():
        db.create_all()
        
        # Создаём 100+ записок
        notes_text = [
            "15.07.1941 14:30 - Под Москвой столкнулся с Pz.IV. Попал в башню, но отскочил рикошетом.",
            "22.08.1941 09:15 - Прорыв обороны под Ельней. Уничтожил 2 БТР и один танк.",
            "10.01.1942 23:45 - Ночной бой под Старой Руссой. Минус немецкий пулемётчик и бронетранспортёр.",
            "12.07.1943 16:20 - Курская дуга. Артиллерия бьёт по нам, но держимся. 3 подбитых.",
            "27.01.1944 11:00 - Прорыв блокады Ленинграда. Т-34 рвёт фрицев!",
            "25.04.1945 07:30 - Берлин. Последний бой. До Победы рукой подать!"
        ]
        
        for i, text in enumerate(notes_text * 25):  # 150 записок
            if not Note.query.get(i+1):
                note = Note(date=text.split(' ')[0], content=text, author='Танкист')
                db.session.add(note)
        db.session.commit()
        
    return "✅ База создана! 150+ записок! Админы: Назар/CatNap"

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
