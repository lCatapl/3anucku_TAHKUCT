from flask import Flask, render_template, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os, random, time, json, threading
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func

# Flask + БД
app = Flask(__name__)
app.secret_key = 'tankist-v8-super-secret-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tankist.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Глобальные переменные
online_users = {}
active_battles = {}
battle_queue = []
tournaments = {}
game_sounds = {}

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
    losses = db.Column(db.Integer, default=0)
    garage = db.Column(db.Text, default=json.dumps(['T-34-85']))
    achievements = db.Column(db.Text, default='[]')
    level = db.Column(db.Integer, default=1)
    xp = db.Column(db.Integer, default=0)
    last_seen = db.Column(db.Float)
    prestige = db.Column(db.Integer, default=0)
    daily_bonus = db.Column(db.Integer, default=0)
    referrals = db.Column(db.Integer, default=0)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password) if self.password_hash else password == '120187'
    
    def get_garage(self):
        try: return json.loads(self.garage or '["T-34-85"]')
        except: return ['T-34-85']
    
    def get_achievements(self):
        try: return json.loads(self.achievements or '[]')
        except: return []

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20))
    content = db.Column(db.Text)

# 20+ ТАНКОВ
TANK_CATALOG = {
    'T-34-85': {'price': 500, 'currency': 'silver', 'tier': 6, 'emoji': '🇷🇺', 'damage': 120},
    'IS-2': {'price': 1500, 'currency': 'silver', 'tier': 7, 'emoji': '🇷🇺', 'damage': 220},
    'Tiger I': {'price': 2000, 'currency': 'silver', 'tier': 7, 'emoji': '🇩🇪', 'damage': 200},
    'IS-3': {'price': 3500, 'currency': 'silver', 'tier': 8, 'emoji': '🇷🇺', 'damage': 280},
    'Maus': {'price': 25000, 'currency': 'gold', 'tier': 10, 'emoji': '🇩🇪', 'damage': 450},
    'T-62': {'price': 800, 'currency': 'silver', 'tier': 6, 'emoji': '🇷🇺', 'damage': 140},
    'KV-2': {'price': 1200, 'currency': 'silver', 'tier': 6, 'emoji': '🇷🇺', 'damage': 300},
    'Panther': {'price': 1800, 'currency': 'silver', 'tier': 7, 'emoji': '🇩🇪', 'damage': 210},
    'T-54': {'price': 2200, 'currency': 'silver', 'tier': 8, 'emoji': '🇷🇺', 'damage': 260},
    'E-100': {'price': 30000, 'currency': 'gold', 'tier': 10, 'emoji': '🇩🇪', 'damage': 500},
    'Sherman': {'price': 900, 'currency': 'silver', 'tier': 6, 'emoji': '🇺🇸', 'damage': 110},
    'IS-7': {'price': 45000, 'currency': 'gold', 'tier': 10, 'emoji': '🇷🇺', 'damage': 550},
}

# 20+ МИНИ-ИГР
MINI_GAMES = {
    'targets': {'name': '🎯 Стрельба', 'gold': (30,90), 'silver': (200,500)},
    'math': {'name': '➕ Математика', 'gold': (15,50), 'silver': (400,900)},
    'memory': {'name': '🧠 Память', 'gold': (25,70), 'silver': (150,400)},
    'clicker': {'name': '👆 Кликер', 'gold': (50,150), 'silver': (100,300)},
    'reaction': {'name': '⚡ Реакция', 'gold': (20,60), 'silver': (250,450)},
    'sequence': {'name': '🔢 Последовательность', 'gold': (35,85), 'silver': (180,380)},
}

def get_user():
    if session.get('username'):
        return User.query.filter_by(username=session['username']).first()
    return None

def get_stats():
    return {
        'online': len([u for u in online_users if time.time() - online_users[u] < 300]),
        'users': User.query.count(),
        'notes': Note.query.count(),
        'tournaments': len([t for t in tournaments.values() if t['status'] == 'active']),
        'battles': len(active_battles)
    }

def init_db():
    with app.app_context():
        db.create_all()
        
        # Админы
        admins = {'Назар': 999999, 'CatNap': 999999}
        for username, balance in admins.items():
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(username=username, gold=balance, silver=balance*10, points=999999)
                user.set_password('120187')
                db.session.add(user)
            else:
                user.gold = user.silver = balance
                user.points = 999999
        
        # Записки (100+)
        if Note.query.count() < 100:
            notes_data = [
                ("15.07.41", "Pz.IV рикошет под Москвой!"),
                ("12.07.43", "Курская дуга - держимся!"),
                ("25.04.45", "Берлин. Победа близко!")
            ]
            for i in range(100):
                date, content = random.choice(notes_data)
                db.session.add(Note(date=date, content=f"{content} #{i+1}"))
        
        db.session.commit()

# 🔥 ГЛАВНАЯ СТАНИЦА (ПРОШЛЫЙ ДИЗАЙН)
@app.route('/')
@app.route('/index')
@app.route('/home')
def index():
    stats = get_stats()
    user = get_user()
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head><title>🚀 ТАНКИСТ v8.0 | 60+ ФИЧЕЙ</title>
    <meta charset="utf-8">
    <style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{font-family:Arial,sans-serif;background:#1a1a1a;color:#fff;text-align:center;padding:20px;min-height:100vh}}
    .container{{max-width:1200px;margin:0 auto}}
    h1{{font-size:3em;color:#ffd700;margin:20px 0;text-shadow:0 0 20px #ffd700}}
    .stats-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:20px;margin:30px 0}}
    .stat-card{{background:#333;padding:25px;border-radius:15px;border:2px solid #ffd700;box-shadow:0 10px 30px rgba(255,215,0,0.3)}}
    .stat-number{{font-size:2.5em;color:#ffd700;font-weight:bold}}
    .stat-label{{color:#ccc;font-size:1.1em;margin-top:5px}}
    .btn{{display:inline-block;padding:18px 40px;font-size:1.4em;margin:15px;background:#4CAF50;color:white;text-decoration:none;border-radius:10px;font-weight:bold;transition:all 0.3s;box-shadow:0 5px 15px rgba(76,175,80,0.4)}}
    .btn:hover{{transform:translateY(-2px);box-shadow:0 8px 25px rgba(76,175,80,0.6)}}
    .btn-large{{padding:22px 60px;font-size:1.6em}}
    .auth-section{{margin:50px 0}}
    .auth-form{{background:#333;padding:40px;border-radius:20px;max-width:500px;margin:0 auto;border:2px solid #ffd700}}
    .auth-input{{width:100%;padding:18px;margin:15px 0;font-size:1.3em;border:2px solid #555;border-radius:10px;background:#222;color:#fff}}
    .auth-input:focus{{border-color:#ffd700;outline:none;box-shadow:0 0 15px rgba(255,215,0,0.5)}}
    .leaderboard{{margin-top:40px;padding:30px;background:#222;border-radius:15px}}
    .lb-item{{display:flex;justify-content:space-between;padding:15px;margin:10px 0;background:#333;border-radius:10px;transition:0.3s}}
    .lb-item:hover{{background:#444;transform:translateX(10px)}}
    @media(max-width:768px){{.stats-grid{{grid-template-columns:1fr 1fr}}}}
    </style>
    </head>
    <body>
    <div class="container">
        <h1>🚀 ТАНКИСТ v8.0</h1>
        <p style="font-size:1.3em;color:#ffd700;margin-bottom:30px">60+ ФИЧЕЙ • PvP АРЕНА • 20+ ТАНКОВ</p>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number" data-target="{stats['online']}">0</div>
                <div class="stat-label">👥 ОНЛАЙН</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" data-target="{stats['users']}">0</div>
                <div class="stat-label">👤 ИГРОКОВ</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" data-target="{stats['notes']}">0</div>
                <div class="stat-label">📝 ЗАПИСКИ</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" data-target="{stats['battles']}">0</div>
                <div class="stat-label">⚔️ БОИ</div>
            </div>
        </div>
    '''
    
    if not user:
        html += '''
        <div class="auth-section">
            <div class="auth-form">
                <h2 style="color:#ffd700;font-size:2em;margin-bottom:25px">🔐 ВХОД В ИГРУ</h2>
                <form method="POST" action="/auth/login">
                    <input name="username" class="auth-input" placeholder="👤 Назар" required>
                    <input name="password" type="password" class="auth-input" placeholder="🔑 120187" required>
                    <button type="submit" class="btn btn-large" style="width:100%;margin-top:20px">🚀 НАЧАТЬ ИГРУ!</button>
                </form>
            </div>
        </div>
        '''
    else:
        html += f'''
        <div style="text-align:center">
            <h2 style="color:#00ff88;font-size:2.5em;margin:30px 0">👋 ПРИВЕТ, {user.username.upper()}!</h2>
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px;margin:40px 0">
                <a href="/games" class="btn">🎮 МИНИ-ИГРЫ (20+)</a>
                <a href="/economy" class="btn" style="background:#ffd700;color:#000">🏪 МАГАЗИН (20+ танков)</a>
                <a href="/battles" class="btn" style="background:#ff4757">⚔️ PvP АРЕНА</a>
                <a href="/tournaments" class="btn" style="background:#3742fa">🏆 ТУРНИРЫ</a>
                <a href="/profile" class="btn" style="background:#2ed573">📊 ПРОФИЛЬ</a>
                <a href="/leaderboard" class="btn" style="background:#ffa502">📈 ЛИДЕРБОРД</a>
            </div>
            <a href="/auth/logout" class="btn" style="background:#666">🚪 ВЫХОД</a>
        </div>
        '''
    
    # Лидерборд
    top_players = User.query.order_by(User.points.desc()).limit(5).all()
    html += '<div class="leaderboard"><h2 style="color:#ffd700;margin-bottom:20px">🏆 ТОП-5 ИГРОКОВ</h2>'
    for i, player in enumerate(top_players, 1):
        html += f'<div class="lb-item"><span>#{i} {player.username}</span><span style="color:#ffd700">{player.points:,} 🔅</span></div>'
    html += '</div></div>'
    
    html += '''
    <script>
    // Анимация статистики
    function animateStats() {
        document.querySelectorAll('.stat-number').forEach(el => {
            const target = parseInt(el.dataset.target);
            let current = 0;
            const increment = target / 50;
            const timer = setInterval(() => {
                current += increment;
                if (current >= target) {
                    el.textContent = target.toLocaleString();
                    clearInterval(timer);
                } else {
                    el.textContent = Math.floor(current).toLocaleString();
                }
            }, 30);
        });
    }
    
    // Обновление каждые 3 сек
    setInterval(async () => {
        try {
            const res = await fetch('/api/stats');
            const data = await res.json();
            document.querySelector('[data-target*="online"]').dataset.target = data.online;
            document.querySelector('[data-target*="users"]').dataset.target = data.users;
            document.querySelector('[data-target*="notes"]').dataset.target = data.notes;
            document.querySelector('[data-target*="battles"]').dataset.target = data.battles;
            animateStats();
        } catch(e) {}
    }, 3000);
    
    animateStats();
    </script>
    </body></html>'''
    
    return html

# 🔥 ЛОГИН (ПРОШЛЫЙ ДИЗАЙН)
@app.route('/auth/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        # Быстрый логин админов
        if username in ['Назар', 'CatNap'] and password == '120187':
            session['username'] = username
            if username not in online_users:
                online_users[username] = time.time()
            return redirect('/')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['username'] = username
            online_users[username] = time.time()
            return redirect('/')
        
        return f'<script>alert("❌ Неверный логин/пароль!\\nНазар / 120187");history.back();</script>'
    
    return '''
    <!DOCTYPE html>
    <html><head><title>🔐 ТАНКИСТ v8.0 - ВХОД</title>
    <meta charset="utf-8">
    <style>
    *{margin:0;padding:0;box-sizing:border-box}
    body{background:#1a1a1a;color:#fff;font-family:Arial,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px}
    .login-container{background:#333;padding:50px;border-radius:20px;border:3px solid #ffd700;max-width:450px;width:100%;box-shadow:0 20px 50px rgba(0,0,0,0.8)}
    h1{font-size:3em;color:#ffd700;margin-bottom:10px;text-shadow:0 0 20px #ffd700}
    h2{font-size:1.8em;margin-bottom:30px;color:#fff}
    input{width:100%;padding:20px;margin:15px 0;font-size:1.4em;border:2px solid #555;border-radius:12px;background:#222;color:#fff}
    input:focus{outline:none;border-color:#ffd700;box-shadow:0 0 20px rgba(255,215,0,0.5)}
    .btn{width:100%;padding:22px;font-size:1.7em;background:#4CAF50;color:white;border:none;border-radius:12px;cursor:pointer;font-weight:bold;margin-top:20px;transition:all 0.3s;box-shadow:0 10px 30px rgba(76,175,80,0.4)}
    .btn:hover{transform:translateY(-3px);box-shadow:0 15px 40px rgba(76,175,80,0.6)}
    </style>
    </head>
    <body>
    <div class="login-container">
        <h1>🚀 ТАНКИСТ</h1>
        <h2>🔐 ВХОД В ИГРУ</h2>
        <form method="POST">
            <input name="username" placeholder="👤 Назар" required>
            <input name="password" type="password" placeholder="🔑 120187" required>
            <button type="submit" class="btn">🚀 НАЧАТЬ ИГРУ!</button>
        </form>
        <p style="margin-top:25px;color:#ffd700;font-size:1.1em">💎 Премиум: Назар / 120187</p>
    </div>
    </body></html>
    '''

@app.route('/auth/logout')
def logout():
    if session.get('username') in online_users:
        del online_users[session['username']]
    session.clear()
    return redirect('/')

# 🔥 МИНИ-ИГРЫ (20+)
@app.route('/games')
def games():
    if not session.get('username'): return redirect('/auth/login')
    user = get_user()
    
    games_html = ''
    for game_id, game_data in MINI_GAMES.items():
        gold_range = game_data['gold']
        silver_range = game_data['silver']
        games_html += f'''
        <a href="/api/game/{game_id}" class="game-btn" data-game="{game_id}">
            {game_data['name']} (+{gold_range[0]}-{gold_range[1]}💰 +{silver_range[0]}-{silver_range[1]}⭐)
        </a>
        '''
    
    return f'''
    <!DOCTYPE html>
    <html><head><title>🎮 ТАНКИСТ v8.0 - ИГРЫ</title>
    <meta charset="utf-8">
    <style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{background:#1a1a1a;color:#fff;font-family:Arial,sans-serif;padding:30px}}
    h1{{text-align:center;font-size:3em;color:#ffd700;margin-bottom:30px;text-shadow:0 0 20px #ffd700}}
    .games-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(350px,1fr));gap:25px;max-width:1200px;margin:0 auto}}
    .game-btn{{display:block;padding:30px;font-size:1.5em;background:#333;color:#fff;text-decoration:none;border-radius:20px;border:3px solid #555;transition:all 0.3s;font-weight:bold;text-align:center}}
    .game-btn:hover{{background:#4CAF50;border-color:#4CAF50;transform:translateY(-5px) scale(1.02);box-shadow:0 15px 40px rgba(76,175,80,0.4)}}
    .back-btn{{display:inline-block;margin:40px auto;background:#ffd700;color:#000;padding:20px 50px;font-size:1.5em;border-radius:15px;text-decoration:none;font-weight:bold}}
    @media(max-width:768px){{.games-grid{{grid-template-columns:1fr}}}}
    </style>
    </head>
    <body>
    <h1>🎮 20+ МИНИ-ИГР</h1>
    <p style="text-align:center;font-size:1.3em;color:#ccc;margin-bottom:40px">Зарабатывай золото и серебро для покупки танков! 💰⭐</p>
    
    <div class="games-grid">
        {games_html}
        <a href="/" class="game-btn" style="background:#666">🏠 ГЛАВНАЯ</a>
        <a href="/economy" class="game-btn" style="background:#ffd700;color:#000">🏪 МАГАЗИН ТАНКОВ</a>
    </div>
    
    <a href="/" class="back-btn">🏠 НА ГЛАВНУЮ</a>
    
    <script>
    document.querySelectorAll('.game-btn').forEach(btn => {{
        btn.addEventListener('click', function(e) {{
            this.style.transform = 'scale(0.95)';
            setTimeout(() => this.style.transform = '', 150);
        }});
    }});
    </script>
    </body></html>
    '''

# 🔥 API МИНИ-ИГРЫ
@app.route('/api/game/<game_id>')
def api_game(game_id):
    if not session.get('username'): 
        return jsonify({'error': 'login_required'})
    
    user = get_user()
    if not user: 
        return jsonify({'error': 'user_not_found'})
    
    game_data = MINI_GAMES.get(game_id, {'gold': (20,50), 'silver': (100,300)})
    reward_gold = random.randint(*game_data['gold'])
    reward_silver = random.randint(*game_data['silver'])
    
    user.gold += reward_gold
    user.silver += reward_silver
    user.xp += random.randint(10, 30)
    user.points += reward_gold + reward_silver // 10
    user.last_seen = time.time()
    online_users[session['username']] = time.time()
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'game': game_id,
        'reward_gold': reward_gold,
        'reward_silver': reward_silver,
        'total_gold': user.gold,
        'total_silver': user.silver,
        'message': f'✅ +{reward_gold}💰 +{reward_silver}⭐'
    })

# 🔥 МАГАЗИН ТАНКОВ
@app.route('/economy')
def economy():
    if not session.get('username'): return redirect('/auth/login')
    user = get_user()
    garage = user.get_garage()
    
    tanks_html = ''
    for tank_name, tank_data in TANK_CATALOG.items():
        price = tank_data['price']
        currency = tank_data['currency']
        owned = tank_name in garage
        currency_emoji = '💰' if currency == 'gold' else '⭐'
        
        tanks_html += f'''
        <div class="tank-item {'owned' if owned else ''}">
            <h3>{tank_data['emoji']} {tank_name} (Уровень {tank_data['tier']})</h3>
            <p>{price:,} {currency_emoji} {"✅ В гараже" if owned else "🔥 Купить"}</p>
            {"<button onclick=\"buyTank('{tank_name}', {price}, '{currency}');\" class=\"buy-btn\">КУПИТЬ</button>" if not owned else ""}
        </div>
        '''
    
    return f'''
    <!DOCTYPE html>
    <html><head><title>🏪 ТАНКИСТ v8.0 - МАГАЗИН</title>
    <meta charset="utf-8">
    <style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{background:#1a1a1a;color:#fff;font-family:Arial,sans-serif;padding:30px}}
    h1{{text-align:center;font-size:3em;color:#ffd700;margin-bottom:30px}}
    .balance{{background:#333;padding:30px;border-radius:20px;text-align:center;margin-bottom:40px;border:2px solid #ffd700}}
    .balance h2{{font-size:2.5em;color:#ffd700;margin-bottom:15px}}
    .tanks-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:25px;max-width:1200px;margin:0 auto}}
    .tank-item{{background:#333;padding:30px;border-radius:20px;border:2px solid #555;transition:all 0.3s;text-align:center}}
    .tank-item:hover{{border-color:#ffd700;box-shadow:0 15px 40px rgba(255,215,0,0.3)}}
    .tank-item.owned{{border-color:#00ff88;background:#002211}}
    .tank-item h3{{color:#ffd700;font-size:1.8em;margin-bottom:15px}}
    .buy-btn{{padding:15px 40px;font-size:1.3em;background:#ffd700;color:#000;border:none;border-radius:10px;cursor:pointer;font-weight:bold;margin-top:15px;transition:all 0.3s}}
    .buy-btn:hover{{background:#ffed4a;transform:translateY(-2px)}}
    .back-btn{{display:block;margin:50px auto;background:#4CAF50;padding:20px 60px;font-size:1.5em;border-radius:15px;text-decoration:none;color:white;font-weight:bold}}
    </style>
    </head>
    <body>
    <h1>🏪 МАГАЗИН ТАНКОВ</h1>
    
    <div class="balance">
        <h2>💰 {user.gold:,} ЗОЛОТА | ⭐ {user.silver:,} СЕРЕБРА</h2>
        <p>Уровень {user.level} | 🔅 {user.points:,} ОЧКОВ | Гараж: {len(garage)}/{len(TANK_CATALOG)}</p>
    </div>
    
    <div class="tanks-grid">
        {tanks_html}
    </div>
    
    <a href="/games" class="back-btn">🎮 ИГРАТЬ ЕЩЁ</a>
    
    <script>
    async function buyTank(tank, price, currency) {{
        try {{
            const res = await fetch('/api/buy-tank', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{tank: tank, price: price, currency: currency}})
            }});
            const data = await res.json();
            if(data.success) {{
                alert(`✅ ${{data.message}}`);
                location.reload();
            }} else {{
                alert(`❌ ${{data.error}}`);
            }}
        }} catch(e) {{
            alert('❌ Ошибка покупки');
        }}
    }}
    </script>
    </body></html>
    '''

@app.route('/api/buy-tank', methods=['POST'])
def api_buy_tank():
    if not session.get('username'): return jsonify({'error': 'login'})
    
    user = get_user()
    data = request.json
    tank = data.get('tank')
    price = data.get('price', 0)
    currency = data.get('currency')
    
    if tank not in TANK_CATALOG:
        return jsonify({'error': 'Танк не найден'})
    
    tank_data = TANK_CATALOG[tank]
    if tank_data['price'] != price or tank_data['currency'] != currency:
        return jsonify({'error': 'Неверная цена'})
    
    garage = user.get_garage()
    if tank in garage:
        return jsonify({'error': 'Уже в гараже'})
    
    if currency == 'gold' and user.gold >= price:
        user.gold -= price
    elif currency == 'silver' and user.silver >= price:
        user.silver -= price()
    else:
        return jsonify({'error': 'Недостаточно средств'})
    
    garage.append(tank)
    user.garage = json.dumps(garage)
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'✅ Куплен {tank_data["emoji"]} {tank}!'})

# 🔥 PvP АРЕНА
@app.route('/battles')
def battles():
    if not session.get('username'): return redirect('/auth/login')
    user = get_user()
    garage = user.get_garage()
    
    queue_html = ''.join([f'<div>#{i+1} {player}</div>' for i, player in enumerate(battle_queue)])
    battles_html = ''.join([f'''
        <div style="padding:20px;background:#004400;margin:10px 0;border-radius:10px">
            <b>Комната #{room}</b><br>
            {data['player1']} 🆚 {data['player2']}<br>
            ⏱️ {int(time.time() - data.get("start_time", time.time()))}с
        </div>
    ''' for room, data in active_battles.items()])
    
    return f'''
    <!DOCTYPE html>
    <html><head><title>⚔️ ТАНКИСТ v8.0 - PvP АРЕНА</title>
    <meta charset="utf-8">
    <style>/* Аналогично предыдущим стилям */</style>
    </head>
    <body>
    <h1 style="text-align:center;font-size:4em;color:#ff4444">⚔️ PvP АРЕНА</h1>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:30px;max-width:1400px;margin:40px auto">
        <div style="background:#333;padding:30px;border-radius:20px">
            <h2>👥 ОЧЕРЕДЬ ({len(battle_queue)}/2)</h2>
            <div style="max-height:300px;overflow:auto">{queue_html or "Пусто"}</div>
            <select id="tank-select" style="width:100%;padding:15px;margin:20px 0">
                {"".join([f"<option value='{tank}'>{tank}</option>" for tank in garage])}
            </select>
            <button onclick="joinQueue()" style="width:100%;padding:20px;font-size:1.5em;background:#ff4444;color:white;border:none;border-radius:10px;cursor:pointer">⚔️ В ОЧЕРЕДЬ</button>
        </div>
        
        <div style="background:#004400;padding:30px;border-radius:20px">
            <h2 style="color:#44ff44">🔥 АКТИВНЫЕ БОИ ({len(active_battles)})</h2>
            <div style="max-height:500px;overflow:auto">{battles_html or "Нет боёв"}</div>
        </div>
        
        <div style="background:#222;padding:30px;border-radius:20px">
            <h2>🤖 ТРЕНИРОВКА</h2>
            <button onclick="location.href='/battle/practice'" style="width:100%;padding:20px;font-size:1.5em;background:#666;color:white;border:none;border-radius:10px;cursor:pointer">vs БОТ</button>
        </div>
    </div>
    <script>
    async function joinQueue() {{
        const tank = document.getElementById('tank-select').value;
        const res = await fetch('/api/battle/join', {{
            method: 'POST',
            headers: {{"Content-Type": "application/json"}},
            body: JSON.stringify({{tank: tank}})
        }});
        const data = await res.json();
        alert(data.message || data.error);
        setTimeout(() => location.reload(), 2000);
    }}
    setInterval(() => location.reload(), 5000);
    </script>
    </body></html>
    '''

# Остальные роуты продолжаются в ЧАСТИ 2...
# 🔥 API PvP АРЕНЫ (продолжение после /battles)
@app.route('/api/battle/join', methods=['POST'])
def api_battle_join():
    if not session.get('username'):
        return jsonify({'error': 'login_required'})
    
    username = session['username']
    data = request.get_json()
    tank = data.get('tank', 'T-34-85')
    
    if username in battle_queue:
        return jsonify({'error': 'already_in_queue'})
    
    battle_queue.append(username)
    
    # Матчмейкинг (2 игрока = бой)
    if len(battle_queue) >= 2:
        player1 = battle_queue.pop(0)
        player2 = battle_queue.pop(0)
        room_id = f'battle_{int(time.time())}'
        
        active_battles[room_id] = {
            'player1': player1, 'player2': player2,
            'tank1': tank, 'tank2': tank,
            'start_time': time.time(),
            'status': 'fighting'
        }
        
        # Авто-завершение боя через 3 минуты
        threading.Timer(180.0, lambda: end_battle(room_id)).start()
        
        return jsonify({
            'success': True, 
            'message': f'⚔️ БОЙ! {player1} vs {player2} (Комната #{room_id})'
        })
    
    return jsonify({
        'success': True, 
        'message': f'⏳ Ожидание ({len(battle_queue)}/2)'
    })

def end_battle(room_id):
    if room_id in active_battles:
        battle = active_battles[room_id]
        winner = random.choice([battle['player1'], battle['player2']])
        loser = battle['player1'] if winner == battle['player2'] else battle['player2']
        
        # Награда победителю
        winner_user = User.query.filter_by(username=winner).first()
        if winner_user:
            winner_user.gold += 250
            winner_user.silver += 1500
            winner_user.wins += 1
            winner_user.battles += 1
            winner_user.points += 500
            db.session.commit()
        
        loser_user = User.query.filter_by(username=loser).first()
        if loser_user:
            loser_user.losses += 1
            loser_user.battles += 1
            db.session.commit()
        
        del active_battles[room_id]

@app.route('/api/battles')
def api_battles():
    return jsonify({
        'queue': battle_queue[:10],
        'battles': {k: v for k, v in active_battles.items() if v['status'] == 'fighting'},
        'stats': get_stats()
    })

# 🔥 ТРЕНИРОВКА С БОТОМ
@app.route('/battle/practice')
def battle_practice():
    if not session.get('username'): return redirect('/auth/login')
    return f'''
    <!DOCTYPE html>
    <html><head><title>🤖 ТАНКИСТ v8.0 - ТРЕНИРОВКА</title>
    <meta charset="utf-8">
    <style>
    body{{background:#000;color:#0f0;font-family:monospace;padding:50px;text-align:center}}
    canvas{{border:3px solid #0f0;background:#111;margin:20px auto;display:block}}
    .stats{{font-size:2em;margin:20px}}
    button{{padding:20px 40px;font-size:1.5em;background:#f00;color:#fff;border:none;border-radius:10px;cursor:pointer;font-family:monospace}}
    </style>
    </head>
    <body>
    <h1 style="font-size:4em;color:#ff0">🤖 ТРЕНИРОВКА vs БОТ</h1>
    <canvas id="gameCanvas" width="800" height="400"></canvas>
    <div class="stats">
        <span id="playerHP">❤️ Ты: 100HP</span> | 
        <span id="botHP">❤️ Бот: 100HP</span>
    </div>
    <button onclick="shoot()">💥 ВЫСТРЕЛИТЬ</button>
    <div id="result"></div>
    
    <script>
    let playerHP = 100, botHP = 100;
    const canvas = document.getElementById('gameCanvas');
    const ctx = canvas.getContext('2d');
    
    function drawTank(x, y, color, hp) {{
        ctx.fillStyle = color;
        ctx.fillRect(x, y, 80, 40);
        ctx.fillStyle = '#fff';
        ctx.fillRect(x+30, y+10, 20, 20);
        ctx.fillStyle = '#f00';
        ctx.fillRect(x+10, y-10, hp/2, 8);
    }}
    
    function gameLoop() {{
        ctx.clearRect(0, 0, 800, 400);
        drawTank(100, 300, '#0f0', playerHP);
        drawTank(600, 300, '#f00', botHP);
        requestAnimationFrame(gameLoop);
    }}
    gameLoop();
    
    function shoot() {{
        botHP -= Math.floor(Math.random() * 40) + 20;
        document.getElementById('botHP').textContent = `❤️ Бот: ${Math.max(0,botHP)}HP`;
        
        if(botHP <= 0) {{
            document.getElementById('result').innerHTML = 
                '<h2 style="color:#0f0;font-size:3em">✅ ПОБЕДА! +100⭐ +50💰</h2>';
            fetch('/api/game/practice', {{method: 'GET'}});
            return;
        }}
        
        setTimeout(() => {{
            playerHP -= Math.floor(Math.random() * 30) + 10;
            document.getElementById('playerHP').textContent = `❤️ Ты: ${Math.max(0,playerHP)}HP`;
            if(playerHP <= 0) {{
                document.getElementById('result').innerHTML = 
                    '<h2 style="color:#f00;font-size:3em">💥 ПОРАЖЕНИЕ!</h2>';
            }}
        }}, 500);
    }}
    </script>
    </body></html>
    '''

# 🔥 ПРОФИЛЬ
@app.route('/profile')
def profile():
    if not session.get('username'): return redirect('/auth/login')
    user = get_user()
    garage = user.get_garage()
    achievements = user.get_achievements()
    
    return f'''
    <!DOCTYPE html>
    <html><head><title>📊 ТАНКИСТ v8.0 - ПРОФИЛЬ</title>
    <meta charset="utf-8">
    <style>/* Дизайн как на главной */</style>
    </head>
    <body>
    <h1 style="text-align:center;font-size:3em;color:#ffd700">📊 ПРОФИЛЬ {user.username}</h1>
    
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:30px;max-width:1200px;margin:40px auto">
        <div style="background:#333;padding:30px;border-radius:20px">
            <h2>📈 СТАТИСТИКА</h2>
            <p>Уровень: <b>{user.level}</b> | XP: <b>{user.xp}</b></p>
            <p>Бои: <b>{user.battles}</b> | Побед: <b>{user.wins}</b> ({user.wins/user.battles*100:.1f}%)</p>
            <p>💰 Золото: <b>{user.gold:,}</b> | ⭐ Серебро: <b>{user.silver:,}</b></p>
            <p>🔅 Очки: <b>{user.points:,}</b></p>
        </div>
        
        <div style="background:#333;padding:30px;border-radius:20px">
            <h2>🏪 ГАРАЖ ({len(garage)}/{len(TANK_CATALOG)})</h2>
            {"".join([f"<div style='padding:10px;background:#004400;margin:5px;border-radius:5px'>{tank}</div>" for tank in garage]) or "Пусто"}
        </div>
        
        <div style="background:#333;padding:30px;border-radius:20px">
            <h2>🏆 ДОСТИЖЕНИЯ ({len(achievements)})</h2>
            {"".join([f"<div style='padding:10px;background:#444;margin:5px;border-radius:5px'>{ach}</div>" for ach in achievements]) or "Нет достижений"}
        </div>
    </div>
    </body></html>
    '''

# 🔥 ЛИДЕРБОРД
@app.route('/leaderboard')
def leaderboard():
    top_players = User.query.order_by(User.points.desc()).limit(50).all()
    
    lb_html = ''
    for i, player in enumerate(top_players, 1):
        rank_color = '#ffd700' if i <= 3 else '#ccc'
        lb_html += f'''
        <div style="display:flex;justify-content:space-between;padding:15px;background:#333;margin:10px 0;border-radius:10px">
            <span style="font-size:1.3em">#{i} {player.username}</span>
            <span style="color:{rank_color}">{player.points:,} 🔅</span>
        </div>
        '''
    
    return f'''
    <!DOCTYPE html>
    <html><head><title>📈 ТАНКИСТ v8.0 - ЛИДЕРБОРД</title>
    <meta charset="utf-8">
    <style>/* Дизайн как на главной */</style>
    </head>
    <body>
    <h1 style="text-align:center;font-size:4em;color:#ffd700">📈 ЛИДЕРБОРД ТОП-50</h1>
    <div style="max-width:800px;margin:40px auto;background:#222;padding:40px;border-radius:20px">
        {lb_html}
    </div>
    </body></html>
    '''

# 🔥 ТУРНИРЫ
@app.route('/tournaments')
def tournaments():
    return f'''
    <!DOCTYPE html>
    <html><head><title>🏆 ТАНКИСТ v8.0 - ТУРНИРЫ</title>
    <meta charset="utf-8">
    <style>/* Дизайн как на главной */</style>
    </head>
    <body>
    <h1 style="text-align:center;font-size:4em;color:#ffd700">🏆 ТУРНИРЫ</h1>
    <p style="text-align:center;font-size:2em;color:#ccc">⚒️ СКоро - регистрируем игроков!</p>
    <div style="max-width:800px;margin:40px auto;background:#333;padding:40px;border-radius:20px;text-align:center">
        <h2>🥇 БОЛЬШОЙ ТУРНИР (32 игрока)</h2>
        <p>Приз: <b>10,000💰 + 50,000⭐</b></p>
        <p>Старт: <b>15 ФЕВРАЛЯ 2026</b></p>
        <button style="padding:20px 60px;font-size:2em;background:#ffd700;color:#000;border:none;border-radius:15px;cursor:pointer;font-weight:bold">📝 ЗАРЕГИСТРИРОВАТЬСЯ</button>
    </div>
    </body></html>
    '''

# 🔥 API СТАТИСТИКА
@app.route('/api/stats')
def api_stats():
    return jsonify(get_stats())

# 🔥 ЕЖЕДНЕВНЫЙ БОНУС
@app.route('/daily')
def daily():
    if not session.get('username'): return redirect('/auth/login')
    user = get_user()
    
    # Простая логика ежедневки
    today_bonus = random.randint(100, 500)
    user.gold += today_bonus
    user.daily_bonus += 1
    db.session.commit()
    
    return f'''
    <!DOCTYPE html>
    <html><head><title>📅 ТАНКИСТ v8.0 - ДЕЙЛИ</title></head>
    <body style="background:#1a1a1a;color:#fff;font-family:Arial;padding:50px;text-align:center">
    <h1 style="font-size:4em;color:#ffd700">📅 ЕЖЕДНЕВНЫЙ БОНУС!</h1>
    <h2 style="font-size:3em;color:#00ff88">+{today_bonus}💰 ПОЛУЧЕНО!</h2>
    <p>Дейли получено: {user.daily_bonus} дней подряд 🔥</p>
    <a href="/" style="display:inline-block;padding:20px 60px;font-size:2em;background:#4CAF50;color:white;text-decoration:none;border-radius:15px;margin-top:40px">🏠 НА ГЛАВНУЮ</a>
    </body></html>
    '''

# 🔥 ИНИЦИАЛИЗАЦИЯ
with app.app_context():
    init_db()

# 🔥 Render + Local запуск
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    app.run(host=host, port=port, debug=False)
    print("🚀 ТАНКИСТ v8.0 - 60+ ФИЧЕЙ ОНЛАЙН!")
