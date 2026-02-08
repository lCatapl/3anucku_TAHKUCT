from flask import Flask, render_template, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os, random, time, json
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func

# Flask app
app = Flask(__name__)
app.secret_key = 'tankist-super-secret-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tankist.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Глобальные переменные
online_users = {}
tournaments_count = 0

# МОДЕЛИ БД
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    gold = db.Column(db.Integer, default=1000)
    silver = db.Column(db.Integer, default=5000)
    points = db.Column(db.Integer, default=0)
    battles = db.Column(db.Integer, default=0)
    wins = db.Column(db.Integer, default=0)
    garage = db.Column(db.Text, default=json.dumps(['Т-34-85']))
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.Float)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_garage(self):
        try:
            return json.loads(self.garage)
        except:
            return ['Т-34-85']

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20))
    content = db.Column(db.Text)

# Данные танков
TANK_CATALOG = {
    'Т-34-85': {'price': 500, 'currency': 'silver', 'tier': 6},
    'ИС-2': {'price': 1500, 'currency': 'silver', 'tier': 7},
    'Tiger I': {'price': 2000, 'currency': 'silver', 'tier': 7},
    'ИС-6': {'price': 5000, 'currency': 'gold', 'tier': 8},
    'Maus': {'price': 25000, 'currency': 'gold', 'tier': 10}
}

MINI_GAMES = {
    'targets': '🎯 Стрельба по мишеням',
    'math': '➕ Быстрая математика', 
    'memory': '🧠 Тест памяти',
    'reaction': '⚡ Реакция'
}

# Инициализация БД
def init_db():
    db.create_all()
    
    # Админы
    admins = {'Назар': '120187', 'CatNap': '120187'}
    for name, pwd in admins.items():
        if not User.query.filter_by(username=name).first():
            user = User(username=name, gold=999999, silver=999999)
            user.set_password(pwd)
            db.session.add(user)
    
    # Записки
    if Note.query.count() < 100:
        notes = [
            ("15.07.41", "Pz.IV рикошет под Москвой"),
            ("12.07.43", "Курская дуга - держимся!"),
            ("25.04.45", "Берлин. Победа близко!")
        ]
        for date, text in notes * 34:
            db.session.add(Note(date=date, content=text))
    
    db.session.commit()

# Главная страница - ДОЛЖНА РАБОТАТЬ!
@app.route('/')
@app.route('/index')
@app.route('/home')
def index():
    stats = {
        'online': len(online_users),
        'users': User.query.count(),
        'notes': Note.query.count(),
        'username': session.get('username', None)
    }
    return render_template('index.html', stats=stats) or '''
    <!DOCTYPE html>
    <html>
    <head><title>ТанкИСТ</title>
    <meta charset="utf-8">
    <style>
    body { font-family: Arial; background: #1a1a1a; color: #fff; text-align: center; padding: 50px; }
    .stats { background: #333; padding: 20px; border-radius: 10px; max-width: 600px; margin: 0 auto; }
    .btn { background: #4CAF50; color: white; padding: 15px 32px; text-decoration: none; 
           border-radius: 5px; font-size: 18px; margin: 10px; display: inline-block; }
    </style>
    </head>
    <body>
    <h1>🚀 ТАНКИСТ v6.0 ✅</h1>
    <div class="stats">
        <h2>📊 СТАТИСТИКА</h2>
        <p>👥 Онлайн: ''' + str(stats['online']) + '''</p>
        <p>👤 Игроков: ''' + str(stats['users']) + '''</p>
        <p>📝 Записок: ''' + str(stats['notes']) + '''</p>
    </div>
    ''' + ('''
    <p><a href="/auth/login" class="btn">🔐 ВОЙТИ (Назар/120187)</a></p>
    ''' if not stats['username'] else f'''
    <p>👋 Привет, {stats["username"]}! <a href="/economy" class="btn">🏪 МАГАЗИН</a>
    <a href="/games" class="btn">🎮 ИГРЫ</a></p>
    ''') + '''
    </body></html>
    '''

# Логин
@app.route('/auth/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        # Быстрый логин админов
        if username in ['Назар', 'CatNap'] and password == '120187':
            session['username'] = username
            online_users[username] = time.time()
            return redirect('/')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['username'] = username
            online_users[username] = time.time()
            return redirect('/')
        
        return '''
        <!DOCTYPE html>
        <html><head><title>Логин</title>
        <style>body{font-family:Arial;background:#1a1a1a;color:#fff;padding:50px;text-align:center;}
        input{padding:10px;margin:10px;font-size:18px;border-radius:5px;border:none;} 
        .btn{background:#4CAF50;color:white;padding:15px;font-size:18px;border:none;border-radius:5px;cursor:pointer;}
        </style></head>
        <body><h2>❌ Неверный логин/пароль!</h2>
        <form method="POST">
        <input name="username" placeholder="Назар" required>
        <input name="password" type="password" placeholder="120187" required>
        <br><button class="btn">Войти</button>
        </form></body></html>
        '''
    
    return '''
    <!DOCTYPE html>
    <html><head><title>ТанкИСТ - Логин</title>
    <style>body{font-family:Arial;background:#1a1a1a;color:#fff;padding:50px;text-align:center;}
    input{padding:15px;margin:10px;font-size:20px;border-radius:10px;border:none;width:300px;}
    .btn{background:#4CAF50;color:white;padding:15px 40px;font-size:20px;border:none;border-radius:10px;cursor:pointer;}
    </style></head>
    <body>
    <h1>🚀 ТАНКИСТ</h1>
    <h2>🔐 ВХОД</h2>
    <form method="POST">
    <input name="username" placeholder="Назар" required><br>
    <input name="password" type="password" placeholder="120187" required><br>
    <button class="btn">🚀 ИГРАТЬ</button>
    </form>
    </body></html>
    '''

@app.route('/auth/logout')
def logout():
    session.clear()
    return redirect('/')

# Игры
@app.route('/games')
def games():
    if not session.get('username'):
        return redirect('/auth/login')
    return '''
    <!DOCTYPE html>
    <html><head><title>Игры</title>
    <style>body{background:#1a1a1a;color:#fff;font-family:Arial;padding:20px;}
    .game-btn{background:#4CAF50;color:white;padding:20px;border-radius:10px;display:block;
    margin:20px auto;width:400px;font-size:24px;border:none;cursor:pointer;text-decoration:none;}
    </style></head>
    <body>
    <h1>🎮 МИНИ-ИГРЫ (Зарабатывай деньги!)</h1>
    <a href="/api/game/targets" class="game-btn">🎯 Стрельба по мишеням</a>
    <a href="/api/game/math" class="game-btn">➕ Быстрая математика</a>
    <a href="/economy" class="game-btn">🏪 МАГАЗИН ТАНКОВ</a>
    <a href="/" class="game-btn">🏠 ГЛАВНАЯ</a>
    </body></html>
    '''

# API для игр
@app.route('/api/game/<game_type>')
def api_game(game_type):
    if not session.get('username'):
        return jsonify({'error': 'login required'})
    
    user = User.query.filter_by(username=session['username']).first()
    reward_gold = random.randint(20, 80)
    reward_silver = random.randint(100, 400)
    
    user.gold += reward_gold
    user.silver += reward_silver
    user.points += reward_gold + reward_silver // 10
    user.last_seen = time.time()
    online_users[session['username']] = time.time()
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'reward_gold': reward_gold,
        'reward_silver': reward_silver,
        'total_gold': user.gold,
        'total_silver': user.silver,
        'message': f'✅ +{reward_gold}💰 +{reward_silver}⭐'
    })

# Экономика
@app.route('/economy')
def economy():
    if not session.get('username'):
        return redirect('/auth/login')
    
    user = User.query.filter_by(username=session['username']).first()
    return f'''
    <!DOCTYPE html>
    <html><head><title>Экономика</title>
    <style>body{{background:#1a1a1a;color:#fff;font-family:Arial;padding:20px;}}
    .balance{{background:#333;padding:20px;border-radius:10px;margin:20px 0;}}
    .tank{{background:#444;padding:20px;margin:20px;border-radius:10px;}}
    .buy-btn{{background:#gold;color:black;padding:10px;border-radius:5px;cursor:pointer;}}
    </style></head>
    <body>
    <h1>🏪 МАГАЗИН ТАНКОВ</h1>
    <div class="balance">
    <h2>💰 {user.gold} ЗОЛОТА | ⭐ {user.silver} СЕРЕБРА</h2>
    </div>
    <div class="tank">
    <h3>Т-34-85 (500⭐)</h3><button class="buy-btn" onclick="buyTank('Т-34-85',500,'silver')">Купить</button>
    </div>
    <div class="tank">
    <h3>ИС-2 (1500⭐)</h3><button class="buy-btn" onclick="buyTank('ИС-2',1500,'silver')">Купить</button>
    </div>
    <a href="/games" style="background:#4CAF50;color:white;padding:20px;border-radius:10px;display:block;margin:20px auto;width:400px;font-size:24px;text-decoration:none;">🎮 ИГРАТЬ ЕЩЁ</a>
    </body></html>
    <script>
    async function buyTank(tank,price,currency) {{
        const res = await fetch('/api/buy-tank', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{tank: tank, price: price, currency: currency}})
        }});
        const data = await res.json();
        alert(data.message || data.error);
        location.reload();
    }}
    </script>
    '''

# Статистика API
@app.route('/api/stats')
def stats():
    return jsonify({
        'online': len(online_users),
        'users': User.query.count(),
        'notes': Note.query.count()
    })

# Инициализация при запуске
with app.app_context():
    init_db()

# 🔥 Render + Local - ГЛАВНЫЙ ЗАПУСК
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
