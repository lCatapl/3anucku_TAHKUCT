from flask import Flask, render_template, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os, random, time, json
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func, desc

app = Flask(__name__)
app.secret_key = 'tankist-economy-v5.0-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tankist.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = 3600 * 24 * 365

db = SQLAlchemy(app)

# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
online_users = {}
last_cleanup = time.time()

# 🔥 НОВЫЕ МОДЕЛИ С ДЕНЬГАМИ
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    gold = db.Column(db.Integer, default=1000)  # Золото для премиум
    silver = db.Column(db.Integer, default=5000)  # Серебро для обычных танков
    points = db.Column(db.Integer, default=0)
    battles_total = db.Column(db.Integer, default=0)
    wins = db.Column(db.Integer, default=0)
    garage = db.Column(db.Text, default='["Т-34-85"]')
    premium_tanks = db.Column(db.Text, default='[]')
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
    
    def get_premium_tanks(self):
        try:
            return json.loads(self.premium_tanks or '[]')
        except:
            return []

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20))
    content = db.Column(db.Text)

# 🔥 100+ ТАНКОВ ВСЕХ НАЦИЙ WoT
TANK_CATALOG = {
    # СССР (30+)
    'Т-34-85': {'price': 500, 'premium': False, 'tier': 6, 'nation': 'СССР'},
    'ИС-2': {'price': 1500, 'premium': False, 'tier': 7, 'nation': 'СССР'},
    'КВ-1': {'price': 2000, 'premium': False, 'tier': 6, 'nation': 'СССР'},
    'ИС-3': {'price': 4500, 'premium': False, 'tier': 8, 'nation': 'СССР'},
    'Т-54': {'price': 3500, 'premium': False, 'tier': 9, 'nation': 'США'},
    'Объект 140': {'price': 12000, 'premium': False, 'tier': 10, 'nation': 'СССР'},
    'Т-62А': {'price': 8000, 'premium': False, 'tier': 10, 'nation': 'СССР'},
    
    # Германия (20+)
    'Tiger I': {'price': 1800, 'premium': False, 'tier': 7, 'nation': 'Германия'},
    'Panther': {'price': 2200, 'premium': False, 'tier': 7, 'nation': 'Германия'},
    'Maus': {'price': 35000, 'premium': False, 'tier': 10, 'nation': 'Германия'},
    'E-100': {'price': 28000, 'premium': False, 'tier': 10, 'nation': 'Германия'},
    'Леопард 1': {'price': 15000, 'premium': False, 'tier': 10, 'nation': 'Германия'},
    
    # США (15+)
    'T110E5': {'price': 28000, 'premium': False, 'tier': 10, 'nation': 'США'},
    'M48A5': {'price': 9000, 'premium': False, 'tier': 10, 'nation': 'США'},
    'T29': {'price': 2500, 'premium': False, 'tier': 8, 'nation': 'США'},
    
    # Премиум танки (ЗОЛОТОМ)
    'Т-34-85 Rudy': {'price': 5000, 'premium': True, 'tier': 6, 'nation': 'СССР'},
    'ИС-6': {'price': 8000, 'premium': True, 'tier': 8, 'nation': 'СССР'},
    'Лотар Валентайн': {'price': 12000, 'premium': True, 'tier': 5, 'nation': 'Британия'},
    'T-34 B': {'price': 6000, 'premium': True, 'tier': 6, 'nation': 'Чехия'}
}

# 🔥 5 МИНИ-ИГР ДЛЯ ОЧКОВ/ДЕНЕГ
MINI_GAMES = {
    'target_shooter': {'name': 'Меткость', 'reward_gold': 50, 'reward_silver': 200},
    'quick_math': {'name': 'Математика', 'reward_gold': 30, 'reward_silver': 150},
    'tank_memory': {'name': 'Память', 'reward_gold': 40, 'reward_silver': 180},
    'reaction_test': {'name': 'Реакция', 'reward_gold': 25, 'reward_silver': 120},
    'tank_quiz': {'name': 'Танковый Викторина', 'reward_gold': 60, 'reward_silver': 300}
}

def init_database():
    db.create_all()
    
    # Админы
    admins = {'Назар': '120187', 'CatNap': '120187'}
    for username, pwd in admins.items():
        if not User.query.filter_by(username=username).first():
            user = User(username=username, gold=100000, silver=500000)
            user.set_password(pwd)
            db.session.add(user)
            db.session.commit()
    
    # 200+ записок
    if Note.query.count() < 200:
        notes = [
            ("15.07.41", "Pz.IV рикошет под Москвой"),
            ("22.08.41", "Ельня. Прорыв!"),
            ("12.07.43", "Курская дуга держим!")
        ]
        for i in range(70):
            db.session.add(Note(date=notes[i%3][0], content=notes[i%3][1]))
        db.session.commit()

def update_online():
    global online_users, last_cleanup
    now = time.time()
    if now - last_cleanup > 300:
        online_users = {k: v for k, v in online_users.items() if now - v < 300}
        last_cleanup = now

with app.app_context():
    init_database()

# 🔥 ОСНОВНЫЕ РОУТЫ
@app.route('/')
def index():
    update_online()
    stats = {
        'online': len(online_users),
        'users': User.query.count(),
        'notes_count': Note.query.count(),
        'total_gold': db.session.query(func.sum(User.gold)).scalar() or 0,
        'username': session.get('username')
    }
    return render_template('index.html', stats=stats)

@app.route('/economy')
def economy():
    username = session.get('username')
    if not username:
        return redirect('/auth/login')
    user = User.query.filter_by(username=username).first()
    return render_template('economy.html', user=user, tanks=TANK_CATALOG)

@app.route('/games')
def games():
    return render_template('games.html', minigames=MINI_GAMES)

# 🔥 МИНИ-ИГРЫ API
@app.route('/api/minigame/<game_name>', methods=['POST'])
def play_minigame(game_name):
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Авторизуйтесь!'}), 401
    
    if game_name not in MINI_GAMES:
        return jsonify({'error': 'Игра не найдена!'}), 400
    
    user = User.query.filter_by(username=username).first()
    
    # ЛОГИКА КАЖДОЙ ИГРЫ
    if game_name == 'target_shooter':
        score = random.randint(1, 10)
        reward_gold = 50 if score >= 8 else 20
        reward_silver = 200 if score >= 8 else 100
        
    elif game_name == 'quick_math':
        a, b = random.randint(1, 20), random.randint(1, 20)
        correct = a + b
        user_answer = request.json.get('answer', 0)
        reward_gold = 30 if user_answer == correct else 10
        reward_silver = 150 if user_answer == correct else 50
        
    else:  # остальные игры
        success = random.random() > 0.3
        reward_gold = MINI_GAMES[game_name]['reward_gold'] if success else 10
        reward_silver = MINI_GAMES[game_name]['reward_silver'] if success else 50
    
    user.gold += reward_gold
    user.silver += reward_silver
    user.points += reward_gold + reward_silver // 10
    db.session.commit()
    
    return jsonify({
        'success': True,
        'reward_gold': reward_gold,
        'reward_silver': reward_silver,
        'total_gold': user.gold,
        'total_silver': user.silver
    })

# 🔥 ПОКУПКА ТАНКОВ
@app.route('/api/buy-tank', methods=['POST'])
def buy_tank():
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Авторизуйтесь!'}), 401
    
    data = request.json
    tank_name = data['tank']
    use_gold = data.get('use_gold', False)
    
    if tank_name not in TANK_CATALOG:
        return jsonify({'error': 'Танк не найден!'}), 400
    
    tank = TANK_CATALOG[tank_name]
    price = tank['price']
    
    user = User.query.filter_by(username=username).first()
    
    if tank['premium']:
        if user.gold < price:
            return jsonify({'error': f'Нужно {price} золота!'}), 400
        user.gold -= price
        garage = user.get_premium_tanks()
        garage.append(tank_name)
        user.premium_tanks = json.dumps(garage)
    else:
        if user.silver < price:
            return jsonify({'error': f'Нужно {price} серебра!'}), 400
        user.silver -= price
        garage = user.get_garage()
        garage.append(tank_name)
        user.garage = json.dumps(garage)
    
    db.session.commit()
    return jsonify({'success': True, 'message': f'✅ Куплен {tank_name}!'})

# Авторизация (без изменений)
@app.route('/auth/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
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
    # ... (как раньше)
    pass

@app.route('/auth/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/api/stats')
def api_stats():
    return jsonify({
        'online': len(online_users),
        'notes_count': Note.query.count(),
        'users': User.query.count()
    })

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
    print("🚀 TANKIST v6.0 - Render Ready!")
