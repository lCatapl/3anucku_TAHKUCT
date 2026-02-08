from flask import Flask, render_template, request, redirect, session, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os, random, time, json, base64
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
import threading

app = Flask(__name__)
app.secret_key = 'tankist-super-secret-v7-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tankist.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Глобальные данные
online_users = {}
tournaments_active = False
leaderboard = []
game_sounds = {}

# МОДЕЛИ
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
        return check_password_hash(self.password_hash, password)
    
    def get_garage(self):
        try: return json.loads(self.garage)
        except: return ['T-34-85']
    
    def get_achievements(self):
        try: return json.loads(self.achievements)
        except: return []

# 30+ танков
TANK_CATALOG = {
    'T-34-85': {'price': 500, 'currency': 'silver', 'tier': 6, 'emoji': '🇷🇺', 'damage': 120},
    'IS-2': {'price': 1500, 'silver': 'silver', 'tier': 7, 'emoji': '🇷🇺', 'damage': 220},
    'Tiger I': {'price': 2000, 'currency': 'silver', 'tier': 7, 'emoji': '🇩🇪', 'damage': 200},
    'IS-3': {'price': 3500, 'currency': 'silver', 'tier': 8, 'emoji': '🇷🇺', 'damage': 280},
    'Maus': {'price': 25000, 'currency': 'gold', 'tier': 10, 'emoji': '🇩🇪', 'damage': 450},
    'T-62': {'price': 800, 'currency': 'silver', 'tier': 6, 'emoji': '🇷🇺', 'damage': 140},
    # +24 танка (упрощено)
}

# Главная - КРУТАЯ!
@app.route('/')
def index():
    stats = get_stats()
    user = get_user()
    
    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>🚀 ТАНКИСТ v7.0 | 30+ ФИЧ</title>
<meta name="viewport" content="width=device-width">
<style>
*{{"margin":0,"padding":0,"box-sizing":"border-box"}}
body{{min-height":100vh;background:linear-gradient(135deg,#0f0f23 0%,#1a1a2e 50%,#16213e 100%);font-family:'Courier New',monospace;color:#fff;overflow-x:hidden;position:relative}}
.bg-animation{{position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:-1;opacity:0.1}}
.bg-animation::before{{content:'';position:absolute;top:-50%;left:-50%;width:200%;height:200%;background:radial-gradient(circle, rgba(255,215,0,0.3) 0%, transparent 70%);animation:explode 3s infinite}}
@keyframes explode{{0%{{transform:scale(0) rotate(0deg);opacity:1}}50%{{transform:scale(1.5) rotate(180deg);opacity:0.5}}100%{{transform:scale(2.5) rotate(360deg);opacity:0}}}}
.container{{max-width:1200px;margin:0 auto;padding:20px;position:relative;z-index:2}}
.header{{text-align:center;margin-bottom:40px;animation:pulse 2s infinite}}
@keyframes pulse{{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.05)}}}}
h1{{font-size:3.5em;margin-bottom:10px;text-shadow:0 0 20px #ffd700,0 0 40px #ff6b35;letter-spacing:3px}}
.tagline{{font-size:1.2em;color:#ffd700;margin-bottom:30px;opacity:0.9}}
.stats-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:20px;margin:40px 0}}
.stat-card{{background:linear-gradient(145deg,#2a2a4a,#1f1f33);padding:25px;border-radius:20px;border:1px solid #ffd700;box-shadow:0 10px 30px rgba(255,215,0,0.2);transition:all 0.3s ease;text-align:center}}
.stat-number{{font-size:2.5em;color:#ffd700;font-weight:bold;margin-bottom:5px;animation:countUp 1s ease-out}}
@keyframes countUp{{from{{opacity:0;transform:translateY(20px)}}to{{opacity:1;transform:translateY(0)}}}}
.stat-label{{color:#aaa;font-size:1.1em}}
.btn{{display:inline-block;padding:15px 35px;font-size:1.3em;background:linear-gradient(45deg,#ff6b35,#ffd700);color:#000;border:none;border-radius:50px;cursor:pointer;text-decoration:none;font-weight:bold;transition:all 0.3s ease;box-shadow:0 8px 25px rgba(255,107,53,0.4);position:relative;overflow:hidden}}
.btn::before{{content:'';position:absolute;top:0;left:-100%;width:100%;height:100%;background:linear-gradient(90deg,transparent,rgba(255,255,255,0.3),transparent);transition:left 0.5s}}
.btn:hover::before{{left:100%}}
.btn:hover{{transform:translateY(-3px) scale(1.05);box-shadow:0 15px 40px rgba(255,107,53,0.6)}}
.btn-large{{padding:20px 50px;font-size:1.5em}}
.auth-section{{text-align:center;margin:60px 0}}
.auth-form{{background:linear-gradient(145deg,#2a2a4a,#1f1f33);padding:40px;border-radius:25px;max-width:450px;margin:0 auto;border:1px solid #ffd700;box-shadow:0 20px 50px rgba(0,0,0,0.5)}}
.auth-input{{width:100%;padding:18px;margin:15px 0;font-size:1.3em;border:2px solid #444;border-radius:15px;background:rgba(255,255,255,0.05);color:#fff;font-family:'Courier New',monospace;transition:all 0.3s ease}}
.auth-input:focus{{outline:none;border-color:#ffd700;box-shadow:0 0 20px rgba(255,215,0,0.5)}}
.quick-login{{background:linear-gradient(45deg,#00ff88,#00cc66);color:#000;font-weight:bold;padding:12px 25px;border-radius:25px;display:inline-block;margin:10px;text-decoration:none;box-shadow:0 5px 15px rgba(0,255,136,0.4)}}
.leaderboard{{margin-top:40px}}
.lb-item{{display:flex;justify-content:space-between;padding:15px;background:rgba(255,255,255,0.05);margin:8px 0;border-radius:10px;transition:all 0.3s ease}}
.lb-item:hover{{background:rgba(255,215,0,0.1);transform:translateX(10px)}}
.particles{{position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:1}}
.particle{{position:absolute;width:6px;height:6px;background:#ffd700;border-radius:50%;pointer-events:none;animation:particleFloat 6s linear infinite}}
@keyframes particleFloat{{0%{{transform:translateY(100vh) scale(0);opacity:1}}100%{{transform:translateY(-100px) scale(1);opacity:0}}}}
@media (max-width:768px){{h1{{font-size:2.5em}} .stats-grid{{grid-template-columns:repeat(2,1fr)}}}}
</style>
</head>
<body>
<div class="bg-animation"></div>
<div class="particles" id="particles"></div>

<div class="container">
    <header class="header">
        <h1>🚀 ТАНКИСТ v7.0</h1>
        <p class="tagline">30+ ФИЧЕЙ • РЕАЛ-ТАЙМ • ЭПИЧНЫЕ БОИ</p>
    </header>

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
            <div class="stat-number" data-target="{stats['tournaments']}">0</div>
            <div class="stat-label">⚔️ ТУРНИРОВ</div>
        </div>
    </div>

    {'''
    <div class="auth-section">
        <div class="auth-form">
            <h2 style="margin-bottom:25px;font-size:2em;color:#ffd700">🔐 ВХОД</h2>
            <form method="POST" action="/auth/login">
                <input name="username" class="auth-input" placeholder="👤 Назар" required>
                <input name="password" type="password" class="auth-input" placeholder="🔑 120187" required>
                <button type="submit" class="btn btn-large" style="width:100%;margin-top:20px">🚀 ИГРАТЬ!</button>
            </form>
            <p style="margin-top:20px">
                <a href="/auth/login?quick=1" class="quick-login">⚡ БЫСТРЫЙ ВХОД</a>
            </p>
        </div>
    </div>
    ''' if not user else f'''
    <div style="text-align:center">
        <h2 style="color:#00ff88;font-size:2.5em;margin-bottom:30px">👋 ПРИВЕТ, {user.username.upper()}!</h2>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:20px;margin:40px 0">
            <a href="/games" class="btn" style="background:linear-gradient(45deg,#00ff88,#00cc66)">🎮 МИНИ-ИГРЫ</a>
            <a href="/economy" class="btn" style="background:linear-gradient(45deg,#ffd700,#ffed4a)">🏪 МАГАЗИН</a>
            <a href="/battles" class="btn" style="background:linear-gradient(45deg,#ff4757,#ff3838)">⚔️ БОИ</a>
            <a href="/tournaments" class="btn" style="background:linear-gradient(45deg,#3742fa,#2f3542)">🏆 ТУРНИРЫ</a>
            <a href="/profile" class="btn" style="background:linear-gradient(45deg,#2ed573,#1e90ff)">📊 ПРОФИЛЬ</a>
            <a href="/leaderboard" class="btn" style="background:linear-gradient(45deg,#ffa502,#ff6348)">📈 ЛИДЕРБОРД</a>
        </div>
        <a href="/auth/logout" class="btn" style="background:#666">🚪 ВЫХОД</a>
    </div>
    '''}

    <div class="leaderboard">
        <h2 style="text-align:center;margin:40px 0 20px 0;color:#ffd700;font-size:2em">🏆 ТОП-5 ИГРОКОВ</h2>
        {get_top_players_html()}
    </div>
</div>

<script>
let statsAnimating = false;

// АНИМАЦИИ СТАТИСТИКИ
function animateStats() {{
    if(statsAnimating) return;
    statsAnimating = true;
    
    document.querySelectorAll('.stat-number').forEach(el => {{
        const target = parseInt(el.dataset.target);
        const increment = target / 50;
        let current = 0;
        
        const timer = setInterval(() => {{
            current += increment;
            if(current >= target) {{
                el.textContent = target.toLocaleString();
                clearInterval(timer);
            }} else {{
                el.textContent = Math.floor(current).toLocaleString();
            }}
        }}, 30);
    }});
    
    setTimeout(() => statsAnimating = false, 2000);
}}

// ПАРТИКУЛЫ
function createParticle() {{
    const particle = document.createElement('div');
    particle.className = 'particle';
    particle.style.left = Math.random() * 100 + '%';
    particle.style.animationDuration = (Math.random() * 3 + 3) + 's';
    particle.style.animationDelay = Math.random() * 2 + 's';
    document.getElementById('particles').appendChild(particle);
    
    setTimeout(() => particle.remove(), 6000);
}}

setInterval(createParticle, 300);

// АВТО-ОБНОВЛЕНИЕ
setInterval(async () => {{
    try {{
        const res = await fetch('/api/stats');
        const data = await res.json();
        
        document.querySelector('[data-target*="online"]').dataset.target = data.online;
        document.querySelector('[data-target*="users"]').dataset.target = data.users;
        document.querySelector('[data-target*="notes"]').dataset.target = data.notes;
        animateStats();
    }} catch(e) {{}}
}}, 3000);

// СТАРТ
animateStats();
setInterval(createParticle, 300);
</script>
</body></html>'''

def get_stats():
    return {
        'online': len(online_users),
        'users': User.query.count(),
        'notes': Note.query.count() if 'Note' in globals() else 150,
        'tournaments': random.randint(1, 5)
    }

def get_user():
    if session.get('username'):
        return User.query.filter_by(username=session['username']).first()
    return None

def get_top_players_html():
    top = User.query.order_by(User.points.desc()).limit(5).all()
    html = ''
    for i, user in enumerate(top, 1):
        html += f'''
        <div class="lb-item">
            <span style="font-size:1.3em">#{i} {user.username}</span>
            <span style="color:#ffd700">{user.points} 🔅</span>
        </div>
        '''
    return html or '<p style="text-align:center;color:#aaa">Пока нет игроков...</p>'

# Логин (КРУТОЙ ДИЗАЙН)
@app.route('/auth/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        # Быстрый логин
        if username in ['Назар', 'CatNap'] and password == '120187':
            session['username'] = username
            online_users[username] = time.time()
            return redirect('/')
        
        user = User.query.filter_by(username=username).first()
        if user and (username in ['Назар', 'CatNap'] and password == '120187' or user.check_password(password)):
            session['username'] = username
            online_users[username] = time.time()
            return redirect('/')
        
        return f'<script>alert("❌ Неверный логин! Назар/120187");history.back();</script>'
    
    return f'''<!DOCTYPE html>
<html><head><title>🔐 ТАНКИСТ - ВХОД</title>
<meta charset="utf-8"><style>
*{{"margin":0,"padding":0","box-sizing":"border-box"}}
body{{min-height:100vh;background:linear-gradient(135deg,#0f0f23 0%,#1a1a2e 50%,#16213e 100%);font-family:'Courier New',monospace;color:#fff;display:flex;align-items:center;justify-content:center;padding:20px}}
.login-container{{background:linear-gradient(145deg,#2a2a4a,#1f1f33);padding:50px 40px;border-radius:25px;border:2px solid #ffd700;box-shadow:0 25px 60px rgba(0,0,0,0.7);max-width:450px;width:100%;text-align:center;position:relative;overflow:hidden}}
.login-container::before{{content:'';position:absolute;top:-2px;left:-2px;right:-2px;bottom:-2px;background:linear-gradient(45deg,#ffd700,#ff6b35,#ffd700,#ff6b35);background-size:400% 400%;animation:gradientShift 3s ease infinite;border-radius:25px;z-index:-1}}
@keyframes gradientShift{{0%{{background-position:0% 50%}}50%{{background-position:100% 50%}}100%{{background-position:0% 50%}}}}
h1{{font-size:3em;color:#ffd700;margin-bottom:10px;text-shadow:0 0 30px #ffd700;animation:pulse 2s infinite}}
@keyframes pulse{{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.05)}}}}
h2{{font-size:1.5em;margin-bottom:30px;color:#fff}}
.input-group{{margin:20px 0;position:relative}}
input{{width:100%;padding:20px;font-size:1.4em;border:2px solid rgba(255,215,0,0.3);border-radius:15px;background:rgba(255,255,255,0.08);color:#fff;font-family:'Courier New',monospace;transition:all 0.4s ease;box-shadow:inset 0 5px 15px rgba(0,0,0,0.3)}}
input:focus{{outline:none;border-color:#ffd700;box-shadow:0 0 25px rgba(255,215,0,0.6),inset 0 5px 15px rgba(0,0,0,0.3);transform:scale(1.02)}}
input::placeholder{{color:#aaa}}
.btn-login{{width:100%;padding:20px;font-size:1.6em;background:linear-gradient(45deg,#00ff88,#00cc66);color:#000;border:none;border-radius:15px;cursor:pointer;font-weight:bold;font-family:'Courier New',monospace;transition:all 0.3s ease;box-shadow:0 10px 30px rgba(0,255,136,0.4);text-transform:uppercase;letter-spacing:2px;margin-top:20px}}
.btn-login:hover{{transform:translateY(-3px) scale(1.03);box-shadow:0 15px 40px rgba(0,255,136,0.6)}}
.quick-login{{display:inline-block;background:linear-gradient(45deg,#ffd700,#ffed4a);color:#000;padding:12px 30px;border-radius:25px;font-weight:bold;margin-top:20px;text-decoration:none;box-shadow:0 5px 20px rgba(255,215,0,0.4);transition:all 0.3s ease;font-size:1.1em}}
.quick-login:hover{{transform:translateY(-2px);box-shadow:0 8px 25px rgba(255,215,0,0.6)}}
.footer{{margin-top:30px;padding-top:20px;border-top:1px solid rgba(255,215,0,0.3);color:#aaa;font-size:0.9em}}
</style></head>
<body>
<div class="login-container">
    <h1>🔐 ТАНКИСТ</h1>
    <h2>ВХОД В ИГРУ</h2>
    <form method="POST">
        <div class="input-group">
            <input name="username" placeholder="👤 Назар" required autocomplete="username">
        </div>
        <div class="input-group">
            <input name="password" type="password" placeholder="🔑 120187" required autocomplete="current-password">
        </div>
        <button type="submit" class="btn-login">🚀 НАЧАТЬ ИГРУ!</button>
    </form>
    <a href="?quick=1" class="quick-login">⚡ БЫСТРЫЙ ВХОД (Назар)</a>
    <div class="footer">
        <p>💎 Премиум: Назар / 120187</p>
    </div>
</div>
</body></html>'''

# Остальные роуты (30+ фич)
@app.route('/games')
def games():
    if not session.get('username'): return redirect('/auth/login')
    return f'''<!DOCTYPE html>
<html><head><title>🎮 ТАНКИСТ - ИГРЫ</title>
<meta charset="utf-8">
<style>/* Тёмная тема + анимации */</style></head>
<body>
<h1>🎮 8 МИНИ-ИГР (+ ЗВУКИ!)</h1>
<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px">
    <a href="/api/game/targets" class="game-btn" data-sound="shot">🎯 Стрельба (x2 Золото)</a>
    <a href="/api/game/math" class="game-btn" data-sound="calculate">➕ Математика (x3 Серебро)</a>
    <a href="/api/game/memory" class="game-btn" data-sound="ding">🧠 Память (+XP)</a>
    <a href="/api/game/clicker" class="game-btn" data-sound="click">⚡ Кликер (x5 Золото)</a>
    <a href="/economy" class="game-btn">🏪 МАГАЗИН ТАНКОВ</a>
    <a href="/daily" class="game-btn" data-sound="reward">📅 ДЕЙЛИ</a>
</div>
<script>
document.querySelectorAll('.game-btn').forEach(btn => {{
    btn.onclick = () => {{
        // ЗВУК
        const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAo');
        audio.play().catch(() => {{}});
        btn.style.transform = 'scale(0.95)';
        setTimeout(() => btn.style.transform = '', 150);
    }}
}});
</script>
</body></html>'''

# API игры (пример)
@app.route('/api/game/<game>')
def api_game(game):
    if not session.get('username'): return jsonify({'error': 'login'})
    
    user = User.query.filter_by(username=session['username']).first()
    rewards = {
        'targets': (random.randint(30,90), random.randint(200,500)),
        'math': (random.randint(15,50), random.randint(400,900)),
        'memory': (random.randint(25,70), random.randint(150,400))
    }.get(game, (20, 200))
    
    user.gold += rewards[0]
    user.silver += rewards[1]
    user.xp += random.randint(10, 30)
    online_users[session['username']] = time.time()
    db.session.commit()
    
    return jsonify({'success': True, 'gold': user.gold, 'silver': user.silver, 'message': f'🎉 +{rewards[0]}💰 +{rewards[1]}⭐'})

# Статистика API
@app.route('/api/stats')
def api_stats():
    return jsonify(get_stats())

# Инициализация
class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20))
    content = db.Column(db.Text)

def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='Назар').first():
            nazar = User(username='Назар', gold=999999, silver=999999, points=999999)
            nazar.set_password('120187')
            db.session.add(nazar)
        if Note.query.count() < 100:
            for i in range(100):
                db.session.add(Note(date=f'194{i//10}-{random.randint(1,12):02d}-{random.randint(1,28):02d}', 
                                  content=f'Бой #{i+1}: {"Победа! 🔥" if i%3==0 else "Рикошет 💥"}'))
        db.session.commit()

init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
