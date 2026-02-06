from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import DevelopmentConfig
from models import User
import os
from datetime import datetime

# Инициализация ДО создания app
db = SQLAlchemy()

app = Flask(__name__)
app.config.from_object(DevelopmentConfig)
db.init_app(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/auth/login', methods=['GET', 'POST'])
def auth_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Простая проверка (замени на свою БД логику)
        if username == 'admin' and password == '123':  # ТЕСТОВЫЕ ДАННЫЕ
            session['user_id'] = username
            session['username'] = username
            return redirect('/')
        else:
            return render_template('login.html', error='Неверный логин/пароль')
    
    return render_template('login.html')

@app.route('/auth/logout')
def auth_logout():
    session.clear()
    return redirect('/')

@app.route('/auth/register', methods=['GET', 'POST'])
def auth_register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        session['user_id'] = username
        session['username'] = username
        return redirect('/')
    return '''
    <h1>Регистрация</h1>
    <form method="post">
        Имя: <input name="username"><br>
        Пароль: <input name="password" type="password"><br>
        <input type="submit">
    </form>
    '''

@app.route('/game')
def game():
    return render_template('game.html')

@app.route('/chat')
def chat():
    return render_template('chat.html')

@app.route('/profile')
def profile():
    username = session.get('username', None)
    
    if not username:
        return render_template('profile.html', guest=True)
    
    try:
        with app.app_context():
            from models import User
            
            # НАХОДИМ ТОЧНОГО пользователя по сессии
            user = User.query.filter_by(username=username).first()
            
            if user:
                # РЕАЛЬНЫЕ ДАННЫЕ ИЗ БД
                real_stats = {
                    'battles': getattr(user, 'battles_total', 0),
                    'wins': getattr(user, 'wins', 0),
                    'points': getattr(user, 'points', 0),
                    'rank': get_rank_name(getattr(user, 'points', 0)),
                    'tank': getattr(user, 'main_tank', 'Т-34-85'),
                    'joined': getattr(user, 'date_joined', 'Неизвестно').strftime('%d.%m.%Y')
                }
            else:
                # Создаём запись если нет
                user = User(username=username, battles_total=0, wins=0, points=0)
                db.session.add(user)
                db.session.commit()
                real_stats = {'battles': 0, 'wins': 0, 'points': 0, 'rank': 'Новобранец', 'tank': 'Т-34-85'}
                
        return render_template('profile.html', 
                             username=username, 
                             stats=real_stats,
                             guest=False)
                             
    except Exception as e:
        # Fallback с реальными сессионными данными
        return f'''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Профиль {username} - Записки Танкиста</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gradient-to-br from-gray-900 to-black min-h-screen p-8">
    <div class="max-w-2xl mx-auto">
        <h1 class="text-4xl font-bold mb-8 text-center text-white">👤 ПРОФИЛЬ {username}</h1>
        <div class="bg-gray-800 p-8 rounded-2xl text-white">
            <h3 class="text-2xl font-bold mb-6">📊 ТВОЯ РЕАЛЬНАЯ СТАТИСТИКА</h3>
            <div class="grid md:grid-cols-2 gap-6 text-lg">
                <div>🎯 Всего боёв: <span class="text-yellow-400 font-bold text-2xl">{session.get("battles_total", 0)}</span></div>
                <div>🏆 Побед: <span class="text-green-400 font-bold text-2xl">{session.get("wins", 0)}</span></div>
                <div>⭐ Очки опыта: <span class="text-blue-400 font-bold text-2xl">{session.get("points", 0)}</span></div>
                <div>⚔️ Звание: <span class="text-purple-400 font-bold text-xl">{get_rank_name(session.get("points", 0))}</span></div>
            </div>
            <div class="mt-8 p-6 bg-gray-900 rounded-xl text-center">
                <div class="w-24 h-24 bg-gradient-to-r from-gray-600 to-gray-400 rounded-full mx-auto mb-4 flex items-center justify-center">
                    <span class="text-xl font-bold">T34</span>
                </div>
                <h3 class="text-xl font-bold mb-1">{session.get("main_tank", "Т-34-85")}</h3>
                <p class="text-gray-400">Регистрация: {session.get("joined_date", "Сегодня")}</p>
            </div>
        </div>
    </div>
</body>
</html>
'''

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

@app.route('/blog')
def blog():
    return render_template('blog.html')

@app.route('/api/stats')
def stats():
    from models import User, Post, Battle, Tournament, UserActivity
    from datetime import datetime, timedelta
    import time
    
    # Правильный app_context для SQLAlchemy
    try:
        # Подсчёт реальных пользователей
        users_count = User.query.count()
        
        # Активные (последние 60 сек) vs АФК (более 60 сек)
        now = datetime.utcnow()
        recent_activity = UserActivity.query.filter(
            UserActivity.last_activity >= now - timedelta(minutes=1)
        ).count()
        afk_count = UserActivity.query.filter(
            UserActivity.last_activity < now - timedelta(minutes=1)
        ).count()
        
        # Бои и турниры ЗА СЕГОДНЯ (сброс 00:00 UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        battles_today = Battle.query.filter(Battle.timestamp >= today_start).count()
        tournaments_today = Tournament.query.filter(Tournament.timestamp >= today_start).count()
        
        # Посты НАВСЕГДА (не сбрасываются)
        posts_count = Post.query.count()
        
        return {
            'online': recent_activity + afk_count,
            'afk': afk_count,
            'battles': battles_today,
            'tournaments': tournaments_today,
            'posts': posts_count,
            'users': users_count,
            'timestamp': int(time.time())
        }
    except Exception as e:
        # Fallback если БД недоступна
        return {
            'online': 0, 'afk': 0, 'battles': 0, 'tournaments': 0, 
            'posts': 0, 'users': 0, 'error': str(e)
        }

from blueprints.auth import auth_bp
app.register_blueprint(auth_bp, url_prefix='/auth')

@app.route('/init-db')
def init_db():
    with app.app_context():
        db.create_all()
    return "База создана!"

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)









