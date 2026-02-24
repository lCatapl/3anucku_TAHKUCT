from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import json, sqlite3, hashlib, time, os, random, threading
from datetime import datetime, timedelta
from collections import defaultdict
import bcrypt
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import Length, Regexp, EqualTo, DataRequired
from flask_wtf.csrf import CSRFProtect
import secrets
import logging
from datetime import datetime
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = 'super-secret-tank-key-2026'

import time
import random
from collections import defaultdict

from werkzeug.security import generate_password_hash

# ⭐ ЛУЧШАЯ ФУНКЦИЯ РЕГИСТРАЦИИ
from werkzeug.security import generate_password_hash
from datetime import datetime

def ensure_database():
    """Создаёт таблицу players если её нет + добавляет админов"""
    db_path = 'database.db'
    
    # Создать БД и таблицу
    conn = sqlite3.connect(db_path, check_same_thread=False)
    cursor = conn.cursor()
    
    # Таблица players (полная структура)
    cursor.execute('''CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        silver INTEGER DEFAULT 750,
        gold INTEGER DEFAULT 0,
        wins INTEGER DEFAULT 0,
        battles INTEGER DEFAULT 0,
        crystal INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        is_admin INTEGER DEFAULT 0,
        created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 👑 АДМИНЫ (всегда создаются)
    admins = [
        ('Назар', generate_password_hash('120187'), 5000, 100, 0, 0, 10, 1, 1),
        ('CatNap', generate_password_hash('120187'), 5000, 100, 0, 0, 10, 1, 1)
    ]
    
    for admin_data in admins:
        cursor.execute('''INSERT OR REPLACE INTO players 
                         (username, password, silver, gold, wins, battles, crystal, level, is_admin)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', admin_data)
    
    conn.commit()
    conn.close()
    print("✅ БД готова! Назар/120187, CatNap/120187")

# 🔥 ВЫЗЫВАЕМ ПЕРВЫМ ДЕЛОМ
ensure_database()

def register_new_player(username, password):
    """Регистрация с лучшими стартовыми значениями"""
    conn = get_db()
    cursor = conn.cursor()
    
    password_hash = generate_password_hash(password)
    
    # 🚀 СТАРТОВЫЙ ПАКЕТ НОВИЧКА (как в WoT)
    start_package = {
        'silver': 5000,     # 7+ боёв MS-1
        'gold': 0,          # Только донат
        'wins': 0,
        'battles': 0, 
        'crystal': 0,       # Премиум валюта
        'level': 1,         # Ранг новичка
    }
    
    cursor.execute('''INSERT OR IGNORE INTO players 
                     (username, password, silver, gold, wins, battles, crystal, level, created)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (username, password_hash,
                   start_package['silver'], 
                   start_package['gold'],
                   start_package['wins'], 
                   start_package['battles'],
                   start_package['crystal'], 
                   start_package['level'],
                   datetime.now()))
    
    conn.commit()
    conn.close()
    print(f"🎉 Новый игрок: {username} [{start_package['silver']} серебра]")
    return True

# 🔥 СИСТЕМА 4 ВАЛЮТ
CURRENCIES = {
    'silver': {'emoji': '🪙', 'name': 'Серебро', 'color': 'gray'},
    'gold': {'emoji': '⭐', 'name': 'Золото', 'color': 'yellow'}, 
    'crystal': {'emoji': '💎', 'name': 'Кристаллы', 'color': 'purple'},
    'bond': {'emoji': '🏅', 'name': 'Бонды', 'color': 'bronze'}  # НОВАЯ!
}
# 🆕 БОНДЫ - для эксклюзивных предметов/премиум аккаунтов

# 🔥 СИСТЕМА УРОВНЕЙ И ЗВАНИЙ
RANK_SYSTEM = {
    0: {'name': 'Рекрут', 'color': 'gray'},
    10: {'name': 'Лейтенант', 'color': 'green'}, 
    100: {'name': 'Капитан', 'color': 'blue'},
    1000: {'name': 'Майор', 'color': 'purple'},
    10000: {'name': 'Полковник', 'color': 'gold'},
    100000: {'name': 'Генерал', 'color': 'red'},
    1000000: {'name': 'Легенда', 'color': 'rainbow'}
}

def get_player_level(xp):
    for level, req_xp in sorted(RANK_SYSTEM.items(), reverse=True):
        if xp >= req_xp:
            return level, RANK_SYSTEM[level]['name'], RANK_SYSTEM[level]['color']
    return 0, 'Рекрут', 'gray'

def player_has_tank(player_id, tank_id):
    try:
        conn = sqlite3.connect('garage.db')
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM garage WHERE player_id = ? AND tank_id = ?", (player_id, tank_id))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    except:
        return False

# ФИЛЬТРЫ JINJA
from datetime import datetime as dt

# 🔥 ГЛОБАЛЬНЫЕ ФИЛЬТРЫ
@app.template_filter('numberformat')
def numberformat(value):
    try:
        val = int(value or 0)
        if val >= 1_000_000: return f'{val//1000000}M'
        if val >= 1_000: return f'{val//1000}K'
        return f'{val:,}'
    except: return '0'

@app.template_filter('datetimeformat')
def datetimeformat(value):
    try:
        return dt.fromtimestamp(float(value or 0)).strftime('%d.%m.%Y')
    except: return '—'

@app.template_filter('format_number')
def format_number(value):
    if value is None:
        return '0'
    return f'{int(value):,}'.replace(',', ' ')

# 🔥 LIVE СТАТИСТИКА
@app.route('/api/stats')
def api_stats():
    conn = get_db()  # твоя функция подключения к БД
    cursor = conn.cursor()
    
    # Общее количество игроков
    cursor.execute('SELECT COUNT(*) FROM players')
    total_players = cursor.fetchone()[0]
    
    # Всего боёв
    cursor.execute('SELECT SUM(battles) FROM players')
    total_battles = cursor.fetchone()[0] or 0
    
    # Онлайн (последние 5 минут)
    cursor.execute('SELECT COUNT(*) FROM players WHERE last_activity > datetime("now", "-5 minutes")')
    online = cursor.fetchone()[0]
    
    conn.close()
    return jsonify({
        'players': total_players,
        'battles': total_battles,
        'online': online,
        'avg_winrate': f"{(cursor.execute('SELECT AVG(wins*100.0/battles) FROM players WHERE battles>0').fetchone()[0] or 0):.1f}%"
    })

@app.route('/sw.js')
@app.route('/manifest.json')
@app.route('/robots.txt')
def static_files():
    return '', 204  # No content

# 🔥 ИНИЦИАЛИЗАЦИЯ БД GARAGE
def init_garage_db():
    conn = sqlite3.connect('garage.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS garage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER,
        tank_id TEXT,
        level INTEGER DEFAULT 1,
        modules TEXT DEFAULT '',
        UNIQUE(player_id, tank_id)
    )''')
    conn.commit()
    conn.close()

@app.route('/profile/<int:user_id>')
def public_profile(user_id):
    player = get_player(user_id, public=True)  # public=True = без приватной инфы
    if not player:
        flash('Игрок не найден!')
        return redirect(url_for('index'))
    
    # Коллекция
    collection_count = sum(1 for tank_id in COLLECTION_TANKS if player_has_tank(user_id, tank_id))
    collection_total = len(COLLECTION_TANKS)
    
    # Уровень
    player['level'], player['rank'], player['rank_color'] = get_player_level(player.get('xp', 0))
    player['next_level'] = next((k for k in RANK_SYSTEM if k > player['level']), max(RANK_SYSTEM.keys()))
    player['next_rank_name'] = RANK_SYSTEM[player['next_level']]['name']
    player['progress'] = min(100, (player.get('xp', 0) / next((k for k in RANK_SYSTEM if k > player['level']), 999)) * 100)
    
    player['collection_count'] = collection_count
    player['collection_total'] = collection_total
    
    return render_template('profile.html', player=player, COLLECTION_TANKS=COLLECTION_TANKS)

def get_player(user_id, public=False):
    try:
        conn = sqlite3.connect('players.db')
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, silver, gold, wins, battles, role, xp, crystal, bond, created, last_activity
            FROM players WHERE id = ?
        """, (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            wins, battles = row[4], row[5]
            winrate = (wins / max(battles, 1)) * 100
            created = datetime.fromtimestamp(row[10]).strftime('%d.%m.%Y')
            
            player = {
                'id': row[0], 'username': row[1], 'silver': row[2], 'gold': row[3],
                'wins': row[4], 'battles': row[5], 'winrate': round(winrate, 1),
                'role': row[6], 'xp': row[7], 'crystal': row[8], 'bond': row[9],
                'created': created
            }
            
            if not public:
                player['email'] = get_user_email(user_id)  # только для себя
            
            return player
        return None
    except:
        return None

# 🔥 ТАНКИ С ТИЕРАМИ И ВАЛЮТАМИ
# 🔥 КОЛЛЕКЦИОННЫЕ ТАНКИ (только витрина, НЕ для боя)
COLLECTION_TANKS = {
    "tiger_legend": {
        "name": "Тигр Легенда", 
        "tier": 10, 
        "type": "ТТ", 
        "price": 1000, 
        "hp": 2800, 
        "damage": 390, 
        "pen": 237, 
        "speed": 45, 
        "premium": False,
        "currency": "crystal"
    },
    "is7_crystal": {
        "name": "ИС-7 Кристалл", 
        "tier": 10, 
        "type": "ТТ", 
        "price": 1500, 
        "hp": 3200, 
        "damage": 490, 
        "pen": 297, 
        "speed": 50, 
        "premium": False,
        "currency": "crystal"
    },
    "e100_diamond": {
        "name": "E-100 Бриллиант", 
        "tier": 10, 
        "type": "ТТ", 
        "price": 2500, 
        "hp": 3600, 
        "damage": 580, 
        "pen": 326, 
        "speed": 35, 
        "premium": False,
        "currency": "crystal"
    },
    "obj268_legend": {
        "name": "Об. 268 Легенда", 
        "tier": 10, 
        "type": "ИТ", 
        "price": 1800, 
        "hp": 2200, 
        "damage": 720, 
        "pen": 350, 
        "speed": 42, 
        "premium": False,
        "currency": "crystal"
    },
    "t95_diamond": {
        "name": "T95 Алмаз", 
        "tier": 10, 
        "type": "ТТ", 
        "price": 2200, 
        "hp": 3400, 
        "damage": 490, 
        "pen": 295, 
        "speed": 32, 
        "premium": False,
        "currency": "crystal"
    }
}

# =================================
# ✅ ПОЛНЫЙ СПИСОК 60+ ТАНКОВ v9.9
# =================================
TANKS = {
    # 🔥 I УРОВЕНЬ - ЛЕГЕНДЫ ВОЙНЫ
    "ms1": {"name": "МС-1 (Т-18)", "tier": 1, "type": "LT", "price": 2500, "hp": 240, "damage": 40, "pen": 28, "speed": 30, "premium": False},
    # 🛡️ II УРОВЕНЬ
    "t26": {"name": "Т-26 об.1933", "tier": 2, "type": "LT", "price": 4500, "hp": 460, "damage": 70, "pen": 45, "speed": 33, "premium": False},
    # ⚔️ III УРОВЕНЬ
    "bt2": {"name": "БТ-2", "tier": 3, "type": "LT", "price": 8500, "hp": 680, "damage": 85, "pen": 58, "speed": 56, "premium": False},
    "t46": {"name": "Т-46", "tier": 3, "type": "LT", "price": 9500, "hp": 720, "damage": 90, "pen": 62, "speed": 48, "premium": False},
    "su76i": {"name": "СУ-76и", "tier": 3, "type": "TD", "price": 7200, "hp": 620, "damage": 110, "pen": 56, "speed": 42, "premium": True},
    # 🎯 IV УРОВЕНЬ
    "t28": {"name": "Т-28", "tier": 4, "type": "MT", "price": 16500, "hp": 950, "damage": 110, "pen": 68, "speed": 42, "premium": False},
    "t34": {"name": "Т-34", "tier": 5, "type": "MT", "price": 28500, "hp": 1280, "damage": 180, "pen": 125, "speed": 55, "premium": False},
    "kv1": {"name": "КВ-1", "tier": 5, "type": "HT", "price": 32000, "hp": 860, "damage": 300, "pen": 61, "speed": 35, "premium": False},
    "su85": {"name": "СУ-85", "tier": 4, "type": "TD", "price": 19500, "hp": 780, "damage": 240, "pen": 145, "speed": 55, "premium": False},
    # 🏆 V УРОВЕНЬ
    "t34_85": {"name": "Т-34-85", "tier": 6, "type": "MT", "price": 45000, "hp": 1350, "damage": 180, "pen": 158, "speed": 55, "premium": False},
    "kv2": {"name": "КВ-2", "tier": 6, "type": "HT", "price": 52000, "hp": 860, "damage": 910, "pen": 86, "speed": 35, "premium": False},
    "is": {"name": "ИС", "tier": 6, "type": "HT", "price": 48500, "hp": 1200, "damage": 390, "pen": 175, "speed": 37, "premium": False},
    # ⚡ VI УРОВЕНЬ
    "t44": {"name": "Т-44", "tier": 8, "type": "MT", "price": 145000, "hp": 1620, "damage": 320, "pen": 220, "speed": 52, "premium": False},
    "is2": {"name": "ИС-2", "tier": 7, "type": "HT", "price": 85000, "hp": 1470, "damage": 390, "pen": 200, "speed": 37, "premium": False},
    "su100": {"name": "СУ-100", "tier": 6, "type": "TD", "price": 62000, "hp": 1220, "damage": 390, "pen": 225, "speed": 50, "premium": False},
    # 🔥 VII УРОВЕНЬ
    "obj244": {"name": "Объект 244", "tier": 7, "type": "HT", "price": 95000, "hp": 1600, "damage": 440, "pen": 234, "speed": 42, "premium": True},
    "t43": {"name": "Т-43", "tier": 7, "type": "MT", "price": 78000, "hp": 1470, "damage": 280, "pen": 200, "speed": 52, "premium": False},
    # 🛡️ VIII УРОВЕНЬ - МЕТА ТАНКИ
    "is3": {"name": "ИС-3", "tier": 8, "type": "HT", "price": 185000, "hp": 1850, "damage": 490, "pen": 252, "speed": 40, "premium": False},
    "t44_100": {"name": "Т-44-100", "tier": 8, "type": "MT", "price": 185000, "hp": 1620, "damage": 440, "pen": 259, "speed": 52, "premium": True},
    "obj432": {"name": "Объект 432", "tier": 8, "type": "MT", "price": 165000, "hp": 1520, "damage": 320, "pen": 220, "speed": 52, "premium": False},
    "obj252u": {"name": "Объект 252У", "tier": 8, "type": "HT", "price": 195000, "hp": 2000, "damage": 440, "pen": 270, "speed": 35, "premium": True},
    # 🎯 IX УРОВЕНЬ
    "obj430u": {"name": "Объект 430У", "tier": 9, "type": "MT", "price": 380000, "hp": 1860, "damage": 390, "pen": 252, "speed": 50, "premium": False},
    "is4m": {"name": "ИС-4М", "tier": 9, "type": "HT", "price": 420000, "hp": 2250, "damage": 490, "pen": 270, "speed": 32, "premium": False},
    "obj257": {"name": "Объект 257", "tier": 9, "type": "HT", "price": 410000, "hp": 2100, "damage": 490, "pen": 270, "speed": 34, "premium": False},
    # 🏆 X УРОВЕНЬ - ЛУЧШИЕ СССР
    "obj140": {"name": "Объект 140", "tier": 10, "type": "MT", "price": 950000, "hp": 1940, "damage": 440, "pen": 258, "speed": 55, "premium": False},
    "t62a": {"name": "Т-62А", "tier": 10, "type": "MT", "price": 920000, "hp": 2120, "damage": 360, "pen": 264, "speed": 50, "premium": False},
    "obj907": {"name": "Объект 907", "tier": 10, "type": "MT", "price": 960000, "hp": 1960, "damage": 390, "pen": 270, "speed": 52, "premium": False},
    "obj268v4": {"name": "Объект 268 Вариант 4", "tier": 10, "type": "TD", "price": 980000, "hp": 2120, "damage": 490, "pen": 299, "speed": 42, "premium": False},
    "is7": {"name": "ИС-7", "tier": 10, "type": "HT", "price": 990000, "hp": 2300, "damage": 490, "pen": 270, "speed": 30, "premium": False},
    "stii": {"name": "СТ-II", "tier": 10, "type": "HT", "price": 940000, "hp": 2250, "damage": 440, "pen": 252, "speed": 28, "premium": False},
    "obj263": {"name": "Объект 263", "tier": 10, "type": "TD", "price": 1250000, "hp": 2120, "damage": 490, "pen": 299, "speed": 45, "premium": True},
    "obj279": {"name": "Объект 279(e)", "tier": 10, "type": "HT", "price": 1350000, "hp": 2400, "damage": 490, "pen": 299, "speed": 28, "premium": True},
    # 🔥 XI УРОВЕНЬ 2026 (Update 2.1.1)
    "kr1": {"name": "КР-1", "tier": 11, "type": "HT", "price": 4500000, "hp": 2600, "damage": 550, "pen": 320, "speed": 30, "premium": True},
    "obj120": {"name": "Объект 120", "tier": 11, "type": "MT", "price": 4200000, "hp": 2200, "damage": 520, "pen": 310, "speed": 60, "premium": True},
    "bzt70": {"name": "BZT-70", "tier": 11, "type": "HT", "price": 4600000, "hp": 2700, "damage": 600, "pen": 330, "speed": 28, "premium": True},
    # 🎮 ПРЕМИУМНЫЕ СССР (любимцы игроков)
    "t44_122": {"name": "Т-44-122", "tier": 7, "type": "MT", "price": 125000, "hp": 1470, "damage": 440, "pen": 234, "speed": 52, "premium": True},
    "obj258": {"name": "Объект 258", "tier": 10, "type": "LT", "price": 880000, "hp": 1750, "damage": 360, "pen": 264, "speed": 68, "premium": False},

    # 🔥 I УРОВЕНЬ - ЛЕГЕНДАРНЫЕ ПУШКИ
    "leichter_pz1": {"name": "Leichter Pz.Kpfw. I", "tier": 1, "type": "LT", "price": 2800, "hp": 270, "damage": 45, "pen": 32, "speed": 38, "premium": False},
    # 🛡️ II УРОВЕНЬ
    "pz2": {"name": "Pz.Kpfw. II", "tier": 2, "type": "LT", "price": 5200, "hp": 520, "damage": 75, "pen": 52, "speed": 40, "premium": False},
    "pz38t": {"name": "Pz.Kpfw. 38(t)", "tier": 3, "type": "LT", "price": 7800, "hp": 680, "damage": 90, "pen": 64, "speed": 42, "premium": False},
    # ⚔️ III УРОВЕНЬ
    "pz3j": {"name": "Pz.Kpfw. III J", "tier": 4, "type": "MT", "price": 12500, "hp": 880, "damage": 120, "pen": 78, "speed": 40, "premium": False},
    "stug3b": {"name": "StuG III Ausf. B", "tier": 4, "type": "TD", "price": 14800, "hp": 820, "damage": 280, "pen": 110, "speed": 32, "premium": False},
    # 🎯 IV УРОВЕНЬ
    "pz4h": {"name": "Pz.Kpfw. IV Ausf. H", "tier": 5, "type": "MT", "price": 28500, "hp": 1050, "damage": 160, "pen": 125, "speed": 40, "premium": False},
    "hetzer": {"name": "Hetzer", "tier": 5, "type": "TD", "price": 32000, "hp": 960, "damage": 320, "pen": 138, "speed": 42, "premium": False},
    # 🏆 V УРОВЕНЬ
    "panzerh": {"name": "Panzer IV H", "tier": 6, "type": "MT", "price": 48500, "hp": 1270, "damage": 200, "pen": 158, "speed": 38, "premium": False},
    "jagpanzeriv": {"name": "Jagdpanzer IV", "tier": 6, "type": "TD", "price": 52000, "hp": 1180, "damage": 440, "pen": 203, "speed": 38, "premium": False},
    # ⚡ VI УРОВЕНЬ - ИКОНЫ ВОЙНЫ
    "tiger1": {"name": "Tiger I", "tier": 7, "type": "HT", "price": 85000, "hp": 1880, "damage": 440, "pen": 237, "speed": 45, "premium": False},
    "panther": {"name": "Panther", "tier": 7, "type": "MT", "price": 78000, "hp": 1650, "damage": 350, "pen": 198, "speed": 55, "premium": False},
    "ferdinand": {"name": "Ferdinand", "tier": 7, "type": "TD", "price": 92000, "hp": 1620, "damage": 490, "pen": 237, "speed": 30, "premium": False},
    # 🛡️ VII УРОВЕНЬ
    "e75": {"name": "E 75", "tier": 9, "type": "HT", "price": 390000, "hp": 2100, "damage": 490, "pen": 270, "speed": 28, "premium": False},
    "pantherii": {"name": "Panther II", "tier": 8, "type": "MT", "price": 185000, "hp": 1850, "damage": 390, "pen": 252, "speed": 55, "premium": False},
    # 🔥 VIII УРОВЕНЬ - МЕТА ГЕРМАНИЯ
    "tiger2": {"name": "Tiger II", "tier": 8, "type": "HT", "price": 195000, "hp": 1950, "damage": 440, "pen": 264, "speed": 38, "premium": False},
    "leopard1": {"name": "Leopard 1", "tier": 10, "type": "LT", "price": 890000, "hp": 1850, "damage": 400, "pen": 264, "speed": 65, "premium": False},
    "rhm_borsig": {"name": "Rhm.-Borsig Waffenträger", "tier": 8, "type": "TD", "price": 225000, "hp": 1750, "damage": 490, "pen": 280, "speed": 45, "premium": False},
    "jagdpanzer_e100": {"name": "Jagdpanzer E 100", "tier": 10, "type": "TD", "price": 1150000, "hp": 2400, "damage": 1150, "pen": 299, "speed": 28, "premium": True},
    # 🎯 IX УРОВЕНЬ
    "e50": {"name": "E 50", "tier": 9, "type": "MT", "price": 420000, "hp": 1960, "damage": 440, "pen": 270, "speed": 52, "premium": False},
    "vte100": {"name": "VK 100.01 (P)", "tier": 8, "type": "HT", "price": 155000, "hp": 1800, "damage": 440, "pen": 252, "speed": 22, "premium": False},
    # 🏆 X УРОВЕНЬ - СУПЕРТЯЖИ
    "e100": {"name": "E 100", "nation": "Germany", "tier": 10, "type": "HT", "price": 1050000, "hp": 2400, "damage": 490, "pen": 299, "speed": 25, "premium": False},
    "maus": {"name": "Maus", "nation": "Germany", "tier": 10, "type": "HT", "price": 3500000, "hp": 3000, "damage": 490, "pen": 299, "speed": 20, "premium": True},
    "e50m": {"name": "E 50 M", "nation": "Germany", "tier": 10, "type": "MT", "price": 1220000, "hp": 1960, "damage": 440, "pen": 270, "speed": 52, "premium": True},
    "vk7201": {"name": "VK 72.01 (K)", "nation": "Germany", "tier": 10, "type": "HT", "price": 1350000, "hp": 2350, "damage": 490, "pen": 299, "speed": 25, "premium": True},
    "obj268": {"name": "Объект 268", "nation": "Germany", "tier": 10, "type": "TD", "price": 970000, "hp": 1940, "damage": 490, "pen": 299, "speed": 38, "premium": False},
    # 🔥 XI УРОВЕНЬ 2026 (Новые супертяжи)
    "taschenratte": {"name": "Taschenratte", "tier": 11, "type": "HT", "price": 4600000, "hp": 2700, "damage": 550, "pen": 330, "speed": 25, "premium": True},
    "panzer_vii": {"name": "Panzer VII", "tier": 11, "type": "HT", "price": 4800000, "hp": 2800, "damage": 600, "pen": 340, "speed": 22, "premium": True},
    # 🎮 ПРЕМИУМНЫЕ ГЕРМАНЦЫ
    "lowe": {"name": "Löwe", "tier": 8, "type": "HT", "price": 235000, "hp": 2100, "damage": 490, "pen": 270, "speed": 35, "premium": True},
    "pro_art": {"name": "Progetto M35 mod. 46", "tier": 8, "type": "MT", "price": 165000, "hp": 1580, "damage": 340, "pen": 234, "speed": 58, "premium": False},

    # 🔥 I УРОВЕНЬ - АМЕРИКАНСКИЕ КЛАССИКИ
    "m2lt": {"name": "M2 Light", "tier": 1, "type": "LT", "price": 3200, "hp": 300, "damage": 50, "pen": 35, "speed": 42, "premium": False},
    # 🛡️ II УРОВЕНЬ
    "m2a2": {"name": "M2A2", "tier": 2, "type": "LT", "price": 5800, "hp": 580, "damage": 80, "pen": 55, "speed": 45, "premium": False},
    # ⚔️ III УРОВЕНЬ
    "m3stuart": {"name": "M3 Stuart", "tier": 3, "type": "LT", "price": 9800, "hp": 720, "damage": 95, "pen": 68, "speed": 61, "premium": False},
    "bt7a1": {"name": "MT-25", "tier": 6, "type": "LT", "price": 125000, "hp": 1220, "damage": 160, "pen": 145, "speed": 72, "premium": True},
    # 🎯 IV УРОВЕНЬ
    "m4a3": {"name": "M4A3 Sherman", "tier": 5, "type": "MT", "price": 28500, "hp": 1180, "damage": 180, "pen": 148, "speed": 48, "premium": False},
    "t67": {"name": "T67", "tier": 4, "type": "TD", "price": 19800, "hp": 880, "damage": 240, "pen": 170, "speed": 62, "premium": False},
    # 🏆 V УРОВЕНЬ
    "t29": {"name": "T29", "tier": 7, "type": "HT", "price": 65000, "hp": 1650, "damage": 400, "pen": 224, "speed": 35, "premium": False},
    "m4a32e8": {"name": "M4A3E8 Sherman", "tier": 6, "type": "MT", "price": 48500, "hp": 1350, "damage": 200, "pen": 158, "speed": 48, "premium": False},
    "t92htc": {"name": "T92 HMC", "tier": 8, "type": "ARTY", "price": 175000, "hp": 1650, "damage": 1100, "pen": 86, "speed": 40, "premium": False},
    # ⚡ VI УРОВЕНЬ
    "m44": {"name": "M44", "tier": 6, "type": "TD", "price": 62000, "hp": 1220, "damage": 280, "pen": 200, "speed": 58, "premium": False},
    "m26e4": {"name": "SuperPershing", "tier": 7, "type": "MT", "price": 85000, "hp": 1650, "damage": 280, "pen": 215, "speed": 50, "premium": True},
    # 🛡️ VII УРОВЕНЬ
    "t20": {"name": "T20", "tier": 7, "type": "MT", "price": 78000, "hp": 1470, "damage": 280, "pen": 200, "speed": 52, "premium": False},
    "t32": {"name": "T32", "tier": 8, "type": "HT", "price": 185000, "hp": 1850, "damage": 400, "pen": 252, "speed": 42, "premium": False},
    "t25at": {"name": "T25 AT", "tier": 7, "type": "TD", "price": 92000, "hp": 1620, "damage": 400, "pen": 258, "speed": 38, "premium": False},
    # 🔥 VIII УРОВЕНЬ - АМЕРИКАНСКАЯ МЕТА
    "t32": {"name": "T32", "tier": 8, "type": "HT", "price": 185000, "hp": 1850, "damage": 400, "pen": 252, "speed": 42, "premium": False},
    "m48a5": {"name": "M48A5 Patton", "tier": 10, "type": "MT", "price": 920000, "hp": 1960, "damage": 360, "pen": 264, "speed": 50, "premium": False},
    "t69": {"name": "T69", "tier": 9, "type": "MT", "price": 380000, "hp": 1860, "damage": 360, "pen": 252, "speed": 52, "premium": False},
    # 🎯 IX УРОВЕНЬ
    "m103": {"name": "M103", "tier": 9, "type": "HT", "price": 420000, "hp": 2250, "damage": 400, "pen": 252, "speed": 32, "premium": False},
    "t54e1": {"name": "T54E1", "tier": 9, "type": "MT", "price": 410000, "hp": 2100, "damage": 400, "pen": 270, "speed": 52, "premium": False},
    # 🏆 X УРОВЕНЬ - АМЕРИКАНСКИЕ ТИТАНЫ
    "t110e5": {"name": "T110E5", "tier": 10, "type": "HT", "price": 1020000, "hp": 2250, "damage": 400, "pen": 252, "speed": 32, "premium": False},
    "t95e6": {"name": "T95E6", "tier": 10, "type": "HT", "price": 1010000, "hp": 2250, "damage": 400, "pen": 252, "speed": 30, "premium": False},
    "sheridan": {"name": "M551 Sheridan", "tier": 10, "type": "LT", "price": 870000, "hp": 1620, "damage": 400, "pen": 268, "speed": 70, "premium": False},
    "t110e3": {"name": "T110E3", "tier": 10, "type": "TD", "price": 1240000, "hp": 2250, "damage": 400, "pen": 252, "speed": 28, "premium": True},
    "t57heavy": {"name": "T57 Heavy", "tier": 10, "type": "HT", "price": 1180000, "hp": 2250, "damage": 400, "pen": 252, "speed": 34, "premium": True},
    "t34": {"name": "T34", "tier": 9, "type": "HT", "price": 450000, "hp": 2100, "damage": 400, "pen": 252, "speed": 35, "premium": True},
    # 🔥 XI УРОВЕНЬ 2026 (Новые американцы)
    "t803": {"name": "T-803", "tier": 11, "type": "HT", "price": 4550000, "hp": 2550, "damage": 520, "pen": 310, "speed": 32, "premium": True},
    "patton_xi": {"name": "Patton XI", "tier": 11, "type": "MT", "price": 4400000, "hp": 2200, "damage": 480, "pen": 320, "speed": 55, "premium": True},
    # 🎮 ПРЕМИУМНЫЕ США
    "skipped": {"name": "Skippé", "tier": 8, "type": "MT", "price": 235000, "hp": 2100, "damage": 390, "pen": 270, "speed": 52, "premium": True},

    # 🔥 I УРОВЕНЬ - БРИТАНСКИЕ КЛАССИКИ
    "crusader": {"name": "Cruiser Mk. I", "tier": 1, "type": "LT", "price": 2900, "hp": 280, "damage": 48, "pen": 34, "speed": 40, "premium": False},
    # 🛡️ II УРОВЕНЬ
    "cruiser_mk3": {"name": "Cruiser Mk. III", "tier": 2, "type": "LT", "price": 5500, "hp": 540, "damage": 78, "pen": 54, "speed": 42, "premium": False},
    "matilda1": {"name": "Matilda LVT", "tier": 4, "type": "LT", "price": 16500, "hp": 950, "damage": 110, "pen": 68, "speed": 42, "premium": True},
    # ⚔️ III УРОВЕНЬ
    "cruiser_mk4": {"name": "Cruiser Mk. IV", "tier": 4, "type": "MT", "price": 12500, "hp": 880, "damage": 120, "pen": 78, "speed": 45, "premium": False},
    "valentine": {"name": "Valentine", "tier": 4, "type": "LT", "price": 14800, "hp": 820, "damage": 110, "pen": 70, "speed": 38, "premium": False},
    # 🎯 IV УРОВЕНЬ
    "covenanter": {"name": "Covenanter", "tier": 5, "type": "LT", "price": 28500, "hp": 1180, "damage": 180, "pen": 125, "speed": 62, "premium": False},
    "churchill1": {"name": "Churchill I", "tier": 5, "type": "HT", "price": 32000, "hp": 1270, "damage": 200, "pen": 158, "speed": 27, "premium": False},
    # 🏆 V УРОВЕНЬ
    "excelsior": {"name": "Excelsior", "tier": 6, "type": "HT", "price": 48500, "hp": 1350, "damage": 240, "pen": 175, "speed": 32, "premium": True},
    "achilles": {"name": "Achilles", "tier": 6, "type": "TD", "price": 52000, "hp": 1180, "damage": 280, "pen": 200, "speed": 42, "premium": False},
    # ⚡ VI УРОВЕНЬ
    "caernarvon": {"name": "Caernarvon", "tier": 8, "type": "HT", "price": 185000, "hp": 1850, "damage": 400, "pen": 252, "speed": 34, "premium": False},
    "cromwell": {"name": "Cromwell", "tier": 6, "type": "MT", "price": 62000, "hp": 1220, "damage": 200, "pen": 158, "speed": 64, "premium": False},
    "at8": {"name": "AT 8", "tier": 6, "type": "TD", "price": 65000, "hp": 1220, "damage": 280, "pen": 200, "speed": 28, "premium": False},
    # 🛡️ VII УРОВЕНЬ
    "centurion1": {"name": "Centurion Mk. I", "tier": 7, "type": "MT", "price": 78000, "hp": 1470, "damage": 280, "pen": 215, "speed": 50, "premium": False},
    "crusader_5inch": {"name": "Crusader 5-inch", "tier": 7, "type": "MT", "price": 85000, "hp": 1650, "damage": 350, "pen": 198, "speed": 58, "premium": True},
    # 🔥 VIII УРОВЕНЬ - БРИТАНСКАЯ МЕТА
    "conqueror": {"name": "Conqueror", "tier": 9, "type": "HT", "price": 420000, "hp": 2100, "damage": 400, "pen": 245, "speed": 34, "premium": False},
    "centurion_action": {"name": "Centurion Action X", "tier": 10, "type": "MT", "price": 920000, "hp": 1950, "damage": 360, "pen": 264, "speed": 50, "premium": False},
    "fv215b": {"name": "FV215b (183)", "tier": 10, "type": "TD", "price": 1030000, "hp": 2200, "damage": 400, "pen": 257, "speed": 34, "premium": False},
    "turtle_mk1": {"name": "Turtle Mk. I", "tier": 10, "type": "HT", "price": 1150000, "hp": 2400, "damage": 400, "pen": 257, "speed": 28, "premium": True},
    # 🎯 IX УРОВЕНЬ
    "super_conqueror": {"name": "Super Conqueror", "tier": 10, "type": "HT", "price": 1080000, "hp": 2150, "damage": 400, "pen": 270, "speed": 36, "premium": False},
    "tortoise": {"name": "Tortoise", "tier": 9, "type": "TD", "price": 420000, "hp": 2000, "damage": 400, "pen": 280, "speed": 20, "premium": False},
    "fv4004": {"name": "FV4004 Conway", "tier": 9, "type": "TD", "price": 410000, "hp": 1500, "damage": 400, "pen": 270, "speed": 38, "premium": False},
    # 🏆 X УРОВЕНЬ - БРИТАНСКИЕ ТИТАНЫ
    "chieftain_mk6": {"name": "Chieftain Mk. 6", "tier": 10, "type": "HT", "price": 1060000, "hp": 2100, "damage": 400, "pen": 270, "speed": 38, "premium": False},
    "fv217_badger": {"name": "FV217 Badger", "tier": 10, "type": "TD", "price": 1070000, "hp": 1940, "damage": 400, "pen": 270, "speed": 34, "premium": False},
    "concept_no5": {"name": "Concept No. 5", "tier": 10, "type": "MT", "price": 895000, "hp": 1800, "damage": 430, "pen": 260, "speed": 58, "premium": True},
    # 🔥 XI УРОВЕНЬ 2026 (Новые британцы)
    "chieftain_xi": {"name": "Chieftain XI", "tier": 11, "type": "HT", "price": 4450000, "hp": 2350, "damage": 520, "pen": 310, "speed": 36, "premium": True},
    "saladin_xi": {"name": "Saladin XI", "tier": 11, "type": "LT", "price": 4300000, "hp": 1750, "damage": 430, "pen": 300, "speed": 72, "premium": True},
    # 🎮 ПРЕМИУМНЫЕ БРИТАНЦЫ
    "toga": {"name": "TOG II*", "tier": 9, "type": "HT", "price": 450000, "hp": 2350, "damage": 400, "pen": 245, "speed": 22, "premium": True},
    "at15": {"name": "AT 15", "tier": 8, "type": "TD", "price": 225000, "hp": 1750, "damage": 400, "pen": 280, "speed": 20, "premium": False},

    # 🔥 I УРОВЕНЬ - САМУРАИ ТАНКОВ
    "ha_go": {"name": "Ha-Go", "tier": 2, "type": "LT", "price": 4800, "hp": 520, "damage": 75, "pen": 52, "speed": 45, "premium": False},
    # 🛡️ II УРОВЕНЬ
    "ke_ni_a": {"name": "Ke-Ni A", "tier": 3, "type": "LT", "price": 8500, "hp": 680, "damage": 90, "pen": 64, "speed": 48, "premium": False},
    # ⚔️ III УРОВЕНЬ
    "chi_ha": {"name": "Chi-Ha", "tier": 4, "type": "MT", "price": 14500, "hp": 880, "damage": 120, "pen": 78, "speed": 42, "premium": False},
    "ho_ni_i": {"name": "Ho-Ni I", "tier": 3, "type": "TD", "price": 12500, "hp": 820, "damage": 240, "pen": 110, "speed": 38, "premium": False},
    # 🎯 IV УРОВЕНЬ
    "chi_he": {"name": "Chi-He", "tier": 5, "type": "MT", "price": 28500, "hp": 1180, "damage": 180, "pen": 125, "speed": 45, "premium": False},
    "type3_ho_ni_iii": {"name": "Type 3 Ho-Ni III", "tier": 5, "type": "TD", "price": 32000, "hp": 960, "damage": 320, "pen": 138, "speed": 40, "premium": False},
    # 🏆 V УРОВЕНЬ
    "chi_nu": {"name": "Chi-Nu", "tier": 6, "type": "MT", "price": 48500, "hp": 1350, "damage": 200, "pen": 158, "speed": 45, "premium": False},
    "ji_ro": {"name": "Type 95 Ji-Ro", "tier": 6, "type": "TD", "price": 52000, "hp": 1180, "damage": 440, "pen": 203, "speed": 38, "premium": False},
    # ⚡ VI УРОВЕНЬ
    "o_i": {"name": "O-I", "tier": 6, "type": "HT", "price": 65000, "hp": 1470, "damage": 440, "pen": 237, "speed": 28, "premium": False},
    "sta_1": {"name": "STA-1", "tier": 10, "type": "MT", "price": 910000, "hp": 1960, "damage": 360, "pen": 264, "speed": 53, "premium": False},
    # 🛡️ VII УРОВЕНЬ
    "sta_2": {"name": "STA-2", "tier": 9, "type": "MT", "price": 360000, "hp": 1750, "damage": 360, "pen": 240, "speed": 55, "premium": False},
    "chi_to_sp": {"name": "Chi-To SP", "tier": 7, "type": "TD", "price": 85000, "hp": 1650, "damage": 320, "pen": 205, "speed": 40, "premium": False},
    # 🔥 VIII УРОВЕНЬ - ЯПОНСКАЯ МЕТА
    "ho_ri_ii": {"name": "Ho-Ri II", "tier": 8, "type": "TD", "price": 195000, "hp": 1620, "damage": 490, "pen": 237, "speed": 30, "premium": False},
    "type61": {"name": "Type 61", "tier": 10, "type": "MT", "price": 6100000, "hp": 2200, "damage": 520, "pen": 310, "speed": 50, "premium": True},
    # 🎯 IX УРОВЕНЬ
    "ho_ri_i": {"name": "Ho-Ri I", "tier": 9, "type": "TD", "price": 3650000, "hp": 2000, "damage": 490, "pen": 280, "speed": 30, "premium": False},
    "type4_heavy": {"name": "Type 4 Heavy", "tier": 10, "type": "HT", "price": 3600000, "hp": 2400, "damage": 490, "pen": 299, "speed": 25, "premium": False},
    # 🏆 X УРОВЕНЬ - ЯПОНСКИЕ ТИТАНЫ
    "type71": {"name": "Type 71", "tier": 10, "type": "HT", "price": 1040000, "hp": 2250, "damage": 490, "pen": 270, "speed": 32, "premium": False},
    "ho_ri_3": {"name": "Ho-Ri 3", "tier": 10, "type": "TD", "price": 1090000, "hp": 2120, "damage": 490, "pen": 299, "speed": 38, "premium": True},
    "stb_1": {"name": "STB-1", "tier": 10, "type": "MT", "price": 950000, "hp": 1950, "damage": 360, "pen": 264, "speed": 50, "premium": False},
    "type5_heavy": {"name": "Type 5 Heavy", "tier": 10, "type": "HT", "price": 6100000, "hp": 2600, "damage": 550, "pen": 320, "speed": 25, "premium": True},
    # 🔥 XI УРОВЕНЬ 2026 (Новые японцы)
    "type57": {"name": "Type 57", "tier": 11, "type": "HT", "price": 2680000, "hp": 2700, "damage": 600, "pen": 340, "speed": 28, "premium": True},
    "o_ho": {"name": "O-Ho", "tier": 11, "type": "HT", "price": 2550000, "hp": 2800, "damage": 600, "pen": 330, "speed": 25, "premium": True},
    # 🎮 ПРЕМИУМНЫЕ ЯПОНЦЫ
    "mitsu_108": {"name": "Mitsubishi 108", "tier": 8, "type": "MT", "price": 410000, "hp": 1750, "damage": 360, "pen": 240, "speed": 55, "premium": False},

    # 🔥 I УРОВЕНЬ - КИТАЙСКИЕ КОРНИ
    "nc31": {"name": "NC-31", "tier": 1, "type": "LT", "price": 3200, "hp": 300, "damage": 50, "pen": 35, "speed": 45, "premium": False},
    # 🛡️ II УРОВЕНЬ
    "vae_type_b": {"name": "VAE Type B", "tier": 2, "type": "LT", "price": 5800, "hp": 580, "damage": 80, "pen": 55, "speed": 48, "premium": False},
    # ⚔️ III УРОВЕНЬ
    "chi_ha_chinese": {"name": "Chi-Ha (китайская)", "tier": 3, "type": "MT", "price": 9800, "hp": 720, "damage": 95, "pen": 68, "speed": 42, "premium": False},
    "su76g_ft": {"name": "СУ-76G FT", "tier": 4, "type": "TD", "price": 14800, "hp": 820, "damage": 280, "pen": 110, "speed": 40, "premium": True},
    # 🎯 IV УРОВЕНЬ
    "m5a1_stuart": {"name": "M5A1 Stuart", "tier": 4, "type": "LT", "price": 16500, "hp": 950, "damage": 110, "pen": 68, "speed": 62, "premium": False},
    "60g_ft": {"name": "60G FT", "tier": 5, "type": "HT", "price": 28500, "hp": 1180, "damage": 180, "pen": 125, "speed": 35, "premium": False},
    # 🏆 V УРОВЕНЬ
    "type_t34": {"name": "Type T-34", "tier": 5, "type": "MT", "price": 48500, "hp": 1350, "damage": 200, "pen": 158, "speed": 55, "premium": False},
    "wz131g_ft": {"name": "WZ-131G FT", "tier": 6, "type": "HT", "price": 52000, "hp": 1180, "damage": 440, "pen": 203, "speed": 38, "premium": False},
    # ⚡ VI УРОВЕНЬ
    "type58": {"name": "Type 58", "tier": 6, "type": "MT", "price": 62000, "hp": 1220, "damage": 200, "pen": 158, "speed": 50, "premium": False},
    "59_16": {"name": "59-16", "tier": 6, "type": "LT", "price": 65000, "hp": 1220, "damage": 160, "pen": 145, "speed": 72, "premium": False},
    # 🛡️ VII УРОВЕНЬ
    "wz111_1_4": {"name": "WZ-111 1-4", "tier": 7, "type": "HT", "price": 85000, "hp": 1650, "damage": 350, "pen": 198, "speed": 35, "premium": False},
    "wz120": {"name": "WZ-120", "tier": 7, "type": "MT", "price": 78000, "hp": 1470, "damage": 280, "pen": 215, "speed": 52, "premium": False},
    # 🔥 VIII УРОВЕНЬ - КИТАЙСКАЯ МЕТА
    "wz132a": {"name": "WZ-132A", "tier": 8, "type": "MT", "price": 195000, "hp": 1620, "damage": 360, "pen": 252, "speed": 55, "premium": False},
    "wz111_5a": {"name": "WZ-113G FT", "tier": 10, "type": "HT", "price": 1000000, "hp": 2250, "damage": 400, "pen": 252, "speed": 32, "premium": False},
    "bz58": {"name": "BZ-58-2", "tier": 8, "type": "MT", "price": 225000, "hp": 1750, "damage": 490, "pen": 280, "speed": 45, "premium": True},
    # 🎯 IX УРОВЕНЬ
    "wz113g_ft": {"name": "WZ-113G FT", "tier": 9, "type": "HT", "price": 420000, "hp": 2100, "damage": 400, "pen": 252, "speed": 34, "premium": False},
    "wz132_5": {"name": "WZ-132-5", "tier": 9, "type": "MT", "price": 410000, "hp": 1960, "damage": 360, "pen": 264, "speed": 52, "premium": False},
    # 🏆 X УРОВЕНЬ - КИТАЙСКИЕ ДРАКОНЫ
    "wz113": {"name": "113", "tier": 10, "type": "MT", "price": 930000, "hp": 1960, "damage": 360, "pen": 264, "speed": 50, "premium": False},
    "wz111_5a": {"name": "WZ-111 5A", "tier": 10, "type": "HT", "price": 1000000, "hp": 2250, "damage": 400, "pen": 252, "speed": 32, "premium": False},
    "114_sp2": {"name": "114 SP2", "tier": 10, "type": "TD", "price": 1070000, "hp": 1940, "damage": 490, "pen": 299, "speed": 40, "premium": True},
    "121": {"name": "121", "tier": 10, "type": "MT", "price": 950000, "hp": 1950, "damage": 360, "pen": 264, "speed": 50, "premium": False},
    "wz132": {"name": "WZ-132", "tier": 10, "type": "MT", "price": 910000, "hp": 1960, "damage": 360, "pen": 264, "speed": 52, "premium": False},
    # 🔥 XI УРОВЕНЬ 2026 (Новые китайцы)
    "ptz78": {"name": "PTZ-78", "tier": 11, "type": "TD", "price": 4500000, "hp": 2200, "damage": 550, "pen": 320, "speed": 55, "premium": True},
    "wz111_qilin": {"name": "WZ-111 Qilin", "tier": 11, "type": "HT", "price": 4600000, "hp": 2600, "damage": 600, "pen": 340, "speed": 30, "premium": True},
    # 🎮 ПРЕМИУМНЫЕ КИТАЙЦЫ
    "t34_2g_ft": {"name": "T-34-2G FT", "tier": 6, "type": "MT", "price": 125000, "hp": 1470, "damage": 440, "pen": 234, "speed": 52, "premium": True},
    "bz166": {"name": "BZ-166", "tier": 9, "type": "MT", "price": 450000, "hp": 2100, "damage": 400, "pen": 270, "speed": 52, "premium": True},

    # 🔥 I УРОВЕНЬ - ИТАЛЬЯНСКИЕ ЛЕГЕНДЫ
    "fiat_3000": {"name": "Fiat 3000B", "tier": 1, "type": "LT", "price": 3100, "hp": 290, "damage": 49, "pen": 36, "speed": 38, "premium": False},
    # 🛡️ II УРОВЕНЬ
    "l6_40": {"name": "L6/40", "tier": 2, "type": "LT", "price": 5600, "hp": 560, "damage": 82, "pen": 56, "speed": 42, "premium": False},
    # ⚔️ III УРОВЕНЬ
    "m13_40": {"name": "Fiat M13/40", "tier": 4, "type": "MT", "price": 14800, "hp": 880, "damage": 120, "pen": 78, "speed": 42, "premium": False},
    # 🎯 IV УРОВЕНЬ
    "p40": {"name": "P40 Conte di Cavour", "tier": 5, "type": "HT", "price": 28500, "hp": 1180, "damage": 180, "pen": 125, "speed": 35, "premium": False},
    "semovente_75_18": {"name": "Semovente 75/18", "tier": 4, "type": "TD", "price": 16500, "hp": 950, "damage": 280, "pen": 110, "speed": 38, "premium": False},
    # 🏆 V УРОВЕНЬ
    "p43": {"name": "P43", "tier": 6, "type": "HT", "price": 48500, "hp": 1350, "damage": 240, "pen": 175, "speed": 32, "premium": False},
    "progetto_m35": {"name": "Progetto M35 mod. 46", "tier": 8, "type": "MT", "price": 165000, "hp": 1580, "damage": 340, "pen": 234, "speed": 58, "premium": False},
    # ⚡ VI УРОВЕНЬ
    "progetto_46": {"name": "Progetto 46", "tier": 7, "type": "MT", "price": 78000, "hp": 1470, "damage": 280, "pen": 215, "speed": 60, "premium": True},
    "of40": {"name": "OF-40", "tier": 6, "type": "MT", "price": 62000, "hp": 1220, "damage": 200, "pen": 158, "speed": 55, "premium": False},
    # 🛡️ VII УРОВЕНЬ
    "progetto_65": {"name": "Progetto 65", "tier": 9, "type": "MT", "price": 380000, "hp": 1860, "damage": 360, "pen": 252, "speed": 60, "premium": False},
    "liberator": {"name": "Lancia Liberator", "tier": 7, "type": "TD", "price": 92000, "hp": 1620, "damage": 400, "pen": 258, "speed": 38, "premium": False},
    # 🔥 VIII УРОВЕНЬ - ИТАЛЬЯНСКАЯ МЕТА
    "progetto_m35": {"name": "Progetto M35 mod. 46", "tier": 8, "type": "MT", "price": 165000, "hp": 1580, "damage": 340, "pen": 234, "speed": 58, "premium": False},
    "rhm_borsig": {"name": "Rhm.-Borsig Waffenträger", "tier": 9, "type": "TD", "price": 360000, "hp": 1750, "damage": 490, "pen": 280, "speed": 45, "premium": False},
    "centauro": {"name": "OTO Melara Centauro", "tier": 8, "type": "LT", "price": 195000, "hp": 1620, "damage": 360, "pen": 252, "speed": 70, "premium": False},
    # 🎯 IX УРОВЕНЬ
    "minotauro": {"name": "Minotauro", "tier": 10, "type": "TD", "price": 420000, "hp": 2000, "damage": 400, "pen": 270, "speed": 38, "premium": False},
    "prototipo": {"name": "Prototipo Standard B", "tier": 9, "type": "MT", "price": 410000, "hp": 1960, "damage": 360, "pen": 264, "speed": 58, "premium": False},
    # 🏆 X УРОВЕНЬ - ИТАЛЬЯНСКИЕ ТИТАНЫ
    "progetto_65": {"name": "Progetto 65", "tier": 10, "type": "MT", "price": 920000, "hp": 1950, "damage": 360, "pen": 264, "speed": 60, "premium": False},
    "vi_caro": {"name": "Vi.Caro", "tier": 10, "type": "HT", "price": 1050000, "hp": 2250, "damage": 400, "pen": 252, "speed": 32, "premium": False},
    "rinoceronte": {"name": "Rinoceronte", "tier": 10, "type": "HT", "price": 1150000, "hp": 2400, "damage": 400, "pen": 257, "speed": 28, "premium": True},
    # 🔥 XI УРОВЕНЬ 2026 (Новые итальянцы)
    "progetto_65_xi": {"name": "Progetto 65 XI", "tier": 11, "type": "MT", "price": 4500000, "hp": 2200, "damage": 520, "pen": 310, "speed": 65, "premium": True},
    "serpente": {"name": "Serpente", "tier": 11, "type": "TD", "price": 4600000, "hp": 2400, "damage": 550, "pen": 330, "speed": 40, "premium": True},
    # 🎮 ПРЕМИУМНЫЕ ИТАЛЬЯНЦЫ
    "bisonte_c45": {"name": "Bisonte C45", "tier": 8, "type": "TD", "price": 225000, "hp": 1750, "damage": 400, "pen": 280, "speed": 45, "premium": True},
    "carro_45t": {"name": "Carro 45 t", "tier": 9, "type": "HT", "price": 450000, "hp": 2350, "damage": 400, "pen": 245, "speed": 32, "premium": True},

    # 🔥 I УРОВЕНЬ - ПОЛЬСКИЕ ЛЕГЕНДЫ
    "pzinz_4tp": {"name": "PZInż 4TP", "tier": 1, "type": "LT", "price": 3000, "hp": 285, "damage": 47, "pen": 35, "speed": 40, "premium": False},
    # 🛡️ II УРОВЕНЬ
    "tks": {"name": "TKS z n.k.m. 20 mm", "tier": 2, "type": "LT", "price": 5400, "hp": 550, "damage": 80, "pen": 55, "speed": 45, "premium": True},
    "7tp": {"name": "7TP", "tier": 3, "type": "LT", "price": 9800, "hp": 720, "damage": 95, "pen": 68, "speed": 42, "premium": False},
    # ⚔️ III УРОВЕНЬ
    "10tp": {"name": "10TP", "tier": 4, "type": "MT", "price": 14500, "hp": 880, "damage": 120, "pen": 78, "speed": 48, "premium": False},
    # 🎯 IV УРОВЕНЬ
    "14tp": {"name": "14TP", "tier": 5, "type": "MT", "price": 28500, "hp": 1180, "damage": 180, "pen": 125, "speed": 52, "premium": False},
    "25tp_ksust": {"name": "25TP KSUST", "tier": 5, "type": "MT", "price": 32000, "hp": 1270, "damage": 200, "pen": 158, "speed": 50, "premium": False},
    # 🏆 V УРОВЕНЬ
    "ds_pzinz": {"name": "DS PZInż", "tier": 5, "type": "MT", "price": 48500, "hp": 1350, "damage": 240, "pen": 175, "speed": 50, "premium": False},
    "pudel": {"name": "Pudel", "tier": 6, "type": "MT", "price": 125000, "hp": 1470, "damage": 440, "pen": 234, "speed": 52, "premium": True},
    # ⚡ VI УРОВЕНЬ
    "bugi": {"name": "B.U.G.I.", "tier": 6, "type": "MT", "price": 62000, "hp": 1220, "damage": 240, "pen": 175, "speed": 55, "premium": False},
    "t34_85_rudy": {"name": "T34-85 Rudy", "tier": 6, "type": "MT", "price": 65000, "hp": 1220, "damage": 200, "pen": 158, "speed": 55, "premium": True},
    # 🛡️ VII УРОВЕНЬ
    "cs44": {"name": "CS-44", "tier": 7, "type": "MT", "price": 78000, "hp": 1470, "damage": 280, "pen": 215, "speed": 52, "premium": False},
    "cs52_lis": {"name": "CS 52 LIS", "tier": 7, "type": "MT", "price": 85000, "hp": 1650, "damage": 350, "pen": 198, "speed": 58, "premium": True},
    # 🔥 VIII УРОВЕНЬ - ПОЛЬСКАЯ МЕТА
    "cs53": {"name": "CS-53", "tier": 8, "type": "MT", "price": 185000, "hp": 1850, "damage": 300, "pen": 252, "speed": 50, "premium": False},
    "50tp_prototip": {"name": "50TP Prototyp", "tier": 8, "type": "HT", "price": 195000, "hp": 1950, "damage": 400, "pen": 252, "speed": 35, "premium": True},
    "zadymka": {"name": "Zadymka", "tier": 5, "type": "TD", "price": 52000, "hp": 1180, "damage": 440, "pen": 203, "speed": 38, "premium": False},
    # 🎯 IX УРОВЕНЬ
    "cs59": {"name": "CS-59", "tier": 9, "type": "MT", "price": 420000, "hp": 2100, "damage": 360, "pen": 264, "speed": 52, "premium": False},
    "gonkiewicz": {"name": "Gonkiewicza", "tier": 9, "type": "TD", "price": 410000, "hp": 2000, "damage": 490, "pen": 292, "speed": 30, "premium": False},
    # 🏆 X УРОВЕНЬ - ПОЛЬСКИЕ ТИТАНЫ
    "cs63": {"name": "CS-63", "tier": 10, "type": "MT", "price": 950000, "hp": 1950, "damage": 360, "pen": 264, "speed": 58, "premium": False},
    "60tp": {"name": "60TP Lewandowskiego", "tier": 10, "type": "HT", "price": 1050000, "hp": 2250, "damage": 400, "pen": 252, "speed": 32, "premium": False},
    "blyskawica": {"name": "Błyskawica", "tier": 10, "type": "TD", "price": 1090000, "hp": 2120, "damage": 490, "pen": 321, "speed": 38, "premium": False},
    # 🔥 XI УРОВЕНЬ 2026 (Новые поляки)
    "husaria_xi": {"name": "Husaria XI", "tier": 11, "type": "HT", "price": 4550000, "hp": 2550, "damage": 520, "pen": 310, "speed": 34, "premium": True},
    "orzel_xi": {"name": "Orzeł XI", "tier": 11, "type": "MT", "price": 4400000, "hp": 2200, "damage": 480, "pen": 320, "speed": 60, "premium": True},
    # 🎮 ПРЕМИУМНЫЕ ПОЛЯКИ
    "burza": {"name": "Burza", "tier": 6, "type": "TD", "price": 125000, "hp": 1220, "damage": 400, "pen": 258, "speed": 38, "premium": False},
    "kilana": {"name": "Kilana", "tier": 8, "type": "TD", "price": 225000, "hp": 1750, "damage": 490, "pen": 280, "speed": 45, "premium": False},

    # 🔥 I УРОВЕНЬ - ШВЕДСКИЕ СНАЙПЕРЫ
    "strv_fm21": {"name": "Strv fm/21", "tier": 1, "type": "LT", "price": 3900, "hp": 310, "damage": 52, "pen": 38, "speed": 40, "premium": False},
    # 🛡️ II УРОВЕНЬ
    "strv_m38": {"name": "Strv m/38", "tier": 2, "type": "LT", "price": 38500, "hp": 580, "damage": 85, "pen": 60, "speed": 44, "premium": False},
    # ⚔️ III УРОВЕНЬ
    "strv_m40l": {"name": "Strv m/40L", "tier": 3, "type": "LT", "price": 135500, "hp": 720, "damage": 95, "pen": 68, "speed": 48, "premium": False},
    # 🎯 IV УРОВЕНЬ
    "sav_m43": {"name": "Sav m/43", "tier": 4, "type": "TD", "price": 140000, "hp": 880, "damage": 240, "pen": 175, "speed": 45, "premium": False},
    # 🏆 V УРОВЕНЬ
    "lago": {"name": "Lago", "tier": 5, "type": "LT", "price": 394000, "hp": 1180, "damage": 180, "pen": 125, "speed": 62, "premium": False},
    "ikv103": {"name": "Ikv 103", "tier": 7, "type": "TD", "price": 386000, "hp": 1650, "damage": 360, "pen": 252, "speed": 45, "premium": False},
    # ⚡ VI УРОВЕНЬ
    "strv_m42": {"name": "Strv m/42", "tier": 6, "type": "MT", "price": 933000, "hp": 1220, "damage": 240, "pen": 175, "speed": 55, "premium": False},
    "ikv65_ii": {"name": "Ikv 65 II", "tier": 6, "type": "TD", "price": 910000, "hp": 1220, "damage": 280, "pen": 200, "speed": 58, "premium": False},
    # 🛡️ VII УРОВЕНЬ
    "strv74": {"name": "Strv 74", "tier": 7, "type": "MT", "price": 1420000, "hp": 1470, "damage": 280, "pen": 215, "speed": 52, "premium": False},
    "ikv90b": {"name": "Ikv 90 Typ B", "tier": 7, "type": "TD", "price": 1410000, "hp": 1620, "damage": 400, "pen": 258, "speed": 38, "premium": False},
    # 🔥 VIII УРОВЕНЬ - ШВЕДСКАЯ МЕТА
    "leo": {"name": "Leo", "tier": 8, "type": "LT", "price": 2620000, "hp": 1620, "damage": 360, "pen": 252, "speed": 70, "premium": False},
    "udes03": {"name": "UDES 03", "tier": 8, "type": "TD", "price": 2540000, "hp": 1750, "damage": 490, "pen": 280, "speed": 45, "premium": False},
    "emil1": {"name": "Emil I", "tier": 8, "type": "HT", "price": 2510000, "hp": 1850, "damage": 400, "pen": 252, "speed": 42, "premium": False},
    # 🎯 IX УРОВЕНЬ
    "udes14_5": {"name": "UDES 14/5", "tier": 9, "type": "MT", "price": 3600000, "hp": 1960, "damage": 390, "pen": 270, "speed": 60, "premium": False},
    "strv103_0": {"name": "Strv 103A", "tier": 9, "type": "TD", "price": 3550000, "hp": 2000, "damage": 440, "pen": 292, "speed": 50, "premium": False},
    "emil2": {"name": "Emil II", "tier": 9, "type": "HT", "price": 3480000, "hp": 2100, "damage": 400, "pen": 270, "speed": 38, "premium": False},
    # 🏆 X УРОВЕНЬ - ШВЕДСКИЕ ТИТАНЫ
    "udes16": {"name": "UDES 15/16", "tier": 10, "type": "MT", "price": 6100000, "hp": 1950, "damage": 440, "pen": 270, "speed": 58, "premium": False},
    "strv103b": {"name": "Strv 103B", "tier": 10, "type": "TD", "price": 6100000, "hp": 2120, "damage": 440, "pen": 292, "speed": 50, "premium": False},
    "kranvagn": {"name": "Kranvagn", "tier": 10, "type": "HT", "price": 6100000, "hp": 2250, "damage": 400, "pen": 270, "speed": 34, "premium": False},
    # 🔥 XI УРОВЕНЬ 2026 (Новые шведы)
    "udes15_16": {"name": "UDES 15/16 XI", "tier": 11, "type": "MT", "price": 4500000, "hp": 2200, "damage": 520, "pen": 310, "speed": 65, "premium": True},
    "strv107": {"name": "Strv 107", "tier": 11, "type": "TD", "price": 4600000, "hp": 2400, "damage": 550, "pen": 330, "speed": 45, "premium": True},
    # 🎮 ПРЕМИУМНЫЕ ШВЕДЫ
    "strv_m42_57": {"name": "Strv m/42-57", "tier": 8, "type": "HT", "price": 79800, "hp": 1850, "damage": 400, "pen": 252, "speed": 42, "premium": True},
    "lansen_c": {"name": "Lansen C", "tier": 10, "type": "MT", "price": 8700, "hp": 1950, "damage": 390, "pen": 270, "speed": 58, "premium": True},

    # 🔥 I УРОВЕНЬ - ЧЕШСКИЕ ЛЕГЕНДЫ
    "lt_vz38": {"name": "LT vz. 38", "tier": 1, "type": "LT", "price": 3100, "hp": 290, "damage": 49, "pen": 36, "speed": 42, "premium": False},
    # 🛡️ II УРОВЕНЬ
    "st_vz39": {"name": "ST vz. 39", "tier": 2, "type": "LT", "price": 5800, "hp": 580, "damage": 80, "pen": 55, "speed": 45, "premium": False},
    # ⚔️ III УРОВЕНЬ
    "vz38_39t": {"name": "Vz.38-39T", "tier": 3, "type": "LT", "price": 9800, "hp": 720, "damage": 95, "pen": 68, "speed": 48, "premium": False},
    # 🎯 IV УРОВЕНЬ
    "sh_02_a": {"name": "ŠH 02A", "tier": 4, "type": "MT", "price": 16500, "hp": 950, "damage": 110, "pen": 68, "speed": 50, "premium": False},
    "vz55": {"name": "Vz. 55", "tier": 4, "type": "HT", "price": 18500, "hp": 880, "damage": 120, "pen": 78, "speed": 32, "premium": False},
    # 🏆 V УРОВЕНЬ
    "vz68": {"name": "Vz. 68", "tier": 5, "type": "MT", "price": 28500, "hp": 1180, "damage": 180, "pen": 125, "speed": 52, "premium": False},
    "skoda_t25": {"name": "Škoda T 25", "tier": 6, "type": "MT", "price": 48500, "hp": 1350, "damage": 200, "pen": 158, "speed": 55, "premium": False},
    # ⚡ VI УРОВЕНЬ
    "t50a": {"name": "T 50 a", "tier": 6, "type": "LT", "price": 62000, "hp": 1220, "damage": 160, "pen": 145, "speed": 72, "premium": False},
    "skoda_t56": {"name": "Škoda T 56", "tier": 8, "type": "HT", "price": 185000, "hp": 1850, "damage": 400, "pen": 252, "speed": 42, "premium": False},
    # 🛡️ VII УРОВЕНЬ
    "tvp_vz61": {"name": "TVP VTU Koncept", "tier": 7, "type": "MT", "price": 78000, "hp": 1470, "damage": 280, "pen": 215, "speed": 60, "premium": False},
    "vz55_2": {"name": "Vz. 55 2", "tier": 7, "type": "HT", "price": 85000, "hp": 1650, "damage": 350, "pen": 198, "speed": 35, "premium": False},
    # 🔥 VIII УРОВЕНЬ - ЧЕШСКАЯ МЕТА
    "tvp_t50": {"name": "TVP T 50/51", "tier": 8, "type": "MT", "price": 195000, "hp": 1620, "damage": 360, "pen": 252, "speed": 65, "premium": False},
    "skoda_t50": {"name": "Škoda T 50", "tier": 8, "type": "MT", "price": 185000, "hp": 1580, "damage": 340, "pen": 234, "speed": 58, "premium": False},
    "vz71": {"name": "Vz. 71", "tier": 8, "type": "HT", "price": 225000, "hp": 1950, "damage": 400, "pen": 252, "speed": 38, "premium": False},
    # 🎯 IX УРОВЕНЬ
    "tvp50_51": {"name": "TVP 50/51", "tier": 9, "type": "MT", "price": 420000, "hp": 2100, "damage": 360, "pen": 264, "speed": 58, "premium": False},
    "skoda_t123": {"name": "Škoda T 123", "tier": 9, "type": "TD", "price": 410000, "hp": 2000, "damage": 490, "pen": 292, "speed": 38, "premium": False},
    # 🏆 X УРОВЕНЬ - ЧЕШСКИЕ ТИТАНЫ
    "tvp_t50": {"name": "TVP T 50", "tier": 10, "type": "MT", "price": 950000, "hp": 1950, "damage": 360, "pen": 264, "speed": 65, "premium": False},
    "vz83": {"name": "Vz. 83", "tier": 10, "type": "HT", "price": 1050000, "hp": 2250, "damage": 400, "pen": 252, "speed": 32, "premium": False},
    "skoda_t140": {"name": "Škoda T 140", "tier": 10, "type": "MT", "price": 920000, "hp": 1960, "damage": 360, "pen": 264, "speed": 52, "premium": False},
    # 🔥 XI УРОВЕНЬ 2026 (Новые чехи)
    "tvp_xi": {"name": "TVP XI", "tier": 11, "type": "MT", "price": 4500000, "hp": 2200, "damage": 520, "pen": 310, "speed": 70, "premium": True},
    "vz83_xi": {"name": "Vz. 83 XI", "tier": 11, "type": "HT", "price": 4600000, "hp": 2550, "damage": 550, "pen": 330, "speed": 34, "premium": True},
    # 🎮 ПРЕМИУМНЫЕ ЧЕХИ
    "st_i": {"name": "ST-1", "tier": 10, "type": "HT", "price": 1150000, "hp": 2400, "damage": 400, "pen": 257, "speed": 28, "premium": True},
    "vz36": {"name": "Vz. 36", "tier": 6, "type": "TD", "price": 125000, "hp": 1220, "damage": 400, "pen": 258, "speed": 38, "premium": True},
}

# 🔥 ОЧЕРЕДЬ БОЁВ (глобальная)
battle_queue = defaultdict(list)  # {tier: [{'player_id': 1, 'tank_id': 't34'}]}

# 🔥 СТАТИСТИКА ONLINE
last_activity = {}  # {player_id: timestamp}

# Получить все танки для боя/покупки
def get_combat_tanks():
    return {**TANKS, **COLLECTION_TANKS}  # TANKS = обычные+премиум

# Проверить коллекционный ли танк
def is_collection_tank(tank_id):
    return tank_id in COLLECTION_TANKS

# Магазин показывает все
all_tanks = {**TANKS, **COLLECTION_TANKS}

# Гараж боевых танков (исключая коллекционные)
combat_tanks = {k: v for k, v in all_tanks.items() if not is_collection_tank(k)}

def get_stats():
    try:
        conn = sqlite3.connect('players.db')
        cursor = conn.cursor()
        
        # Всего игроков
        cursor.execute("SELECT COUNT(*) FROM players")
        total = cursor.fetchone()[0]
        
        # Активные (последние 5 мин)
        now = time.time()
        online = sum(1 for last_time in last_activity.values() if now - last_time < 300)
        
        # АФК
        afk = len(last_activity) - online
        
        # Золото
        cursor.execute("SELECT SUM(gold) FROM players")
        gold = cursor.fetchone()[0] or 0
        
        conn.close()
        return {
            'online': online, 
            'afk': afk, 
            'total': total,
            'gold': int(gold)
        }
    except:
        return {'online': 1, 'afk': 0, 'total': 1, 'gold': 1000000}

# Обновляем активность
def update_player_activity(player_id):
    try:
        conn = sqlite3.connect('players.db')
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE players SET last_activity = ? WHERE id = ?", 
            (time.time(), player_id)
        )
        conn.commit()
        conn.close()
    except:
        pass

@app.route('/battle_queue/<int:tier>')
def battle_queue_page(tier):
    if not validate_session():
        return redirect(url_for('login'))
    
    player = get_player(session['user_id'])
    waiting = battle_queue[tier]
    
    return render_template('battle_queue.html', player=player, tier=tier, waiting=waiting)

@app.route('/join_queue/<int:tier>/<tank_id>')
def join_queue(tier, tank_id):
    if not validate_session():
        return jsonify({'error': 'Не авторизован'})
    
    player_id = session['user_id']
    player = get_player(player_id)
    
    # Проверяем гараж
    if not has_tank(player_id, tank_id):
        return jsonify({'error': 'Танк не в гараже'})
    
    # Добавляем в очередь
    battle_queue[tier].append({'player_id': player_id, 'tank_id': tank_id})
    update_activity(player_id)
    
    return jsonify({'success': True, 'message': f'Ждёшь бой {tier} уровня!'})

def has_tank(player_id, tank_id):
    try:
        conn = sqlite3.connect('garage.db')
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM garage WHERE player_id = ? AND tank_id = ?", (player_id, tank_id))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    except:
        return False

def find_opponent(tier):
    # Ищем в очереди того же тиера
    if battle_queue[tier]:
        return battle_queue[tier].pop(0)
    # Создаём бота
    bot_tanks = [tid for tid, tank in TANKS.items() if tank['tier'] == tier]
    return {'player_id': 'bot', 'tank_id': random.choice(bot_tanks)}

# 1️⃣ FLASK APP
app = Flask(__name__)
app.secret_key = '3anucku-tankuct-2026-super-secret-key-alexin-kaluga-secure-v9.9'

# 2️⃣ ERROR HANDLERS (ПЕРЕД ФИЛЬТРАМИ!)
@app.errorhandler(500)
def internal_error(error):
    return "🚫 Серверная ошибка! Проверь логи Render.", 500

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html', player=None), 404  # ← player=None!

# 3️⃣ Jinja2 ФИЛЬТР ДЛЯ ЧИСЕЛ (ОБЯЗАТЕЛЬНО!)
def comma(value):
    try:
        return "{:,}".format(int(value)).replace(',', ' ')
    except:
        return value

app.jinja_env.filters['comma'] = comma

# 4️⃣ ГЛОБАЛЬНЫЕ КОНСТАНТЫ v9.9
PLAYERS_EQUAL = True
ADMIN_LOGINS = ["Назар", "CatNap", "Admin"]
DB_PATH = 'players.db'  # ЕДИНАЯ БД!

# 🔥 АДМИНЫ С ПРАВАМИ БОГА
ADMIN_USERS = {
    "Назар": {"user_id": "admin_nazar_2026", "role": "superadmin", "permissions": ["all"]},
    "CatNap": {"user_id": "admin_catnap_2026", "role": "superadmin", "permissions": ["all"]},
    "Admin": {"user_id": "admin0001", "role": "superadmin", "permissions": ["all"]},
}

# ГЛОБАЛЬНЫЙ CONTEXT PROCESSOR для player во ВСЕХ шаблонах
@app.context_processor
def inject_realtime_data():
    from datetime import datetime as dt
    return {
        'now': dt.now(),  # ✅ ФИКС!
        'version': '2.6.0'
    }

    def get_live_gold():
        """Реальное золото из БД (сумма всех игроков)"""
        try:
            conn = sqlite3.connect('players.db')
            cursor = conn.cursor()
            cursor.execute("SELECT SUM(gold) FROM players")
            total = cursor.fetchone()[0] or 0
            conn.close()
            return int(total)
        except:
            return 0

    return {
        'get_player': get_player,
        'live_gold': get_live_gold,  # ← НАСТОЯЩЕЕ!
        'now': datetime.now(),
        'format_number': lambda x: f"{x:,}".replace(",", " ")
    }

def get_leaderboard(limit=50):
    conn = sqlite3.connect('players.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, username, silver, gold, wins, battles FROM players 
        ORDER BY wins DESC, silver DESC LIMIT ?
    """, (limit,))
    
    players = []
    for i, row in enumerate(cursor.fetchall(), 1):
        # ✅ Используем player ID, НЕ username
        tank_count = get_player_tanks(row[0])  # row[0] = id
        
        winrate = (row[4] / max(row[5], 1)) * 100 if row[5] > 0 else 0
        players.append({
            'rank': i,
            'username': row[1],
            'silver': row[2],
            'wins': row[4],
            'winrate': round(winrate, 1),
            'tank_count': tank_count  # ✅ int, НЕ len()
        })
    conn.close()
    return players

def get_player(user_id):
    try:
        conn = sqlite3.connect('players.db')
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, silver, gold, wins, battles, role, tank_id 
            FROM players WHERE id = ?
        """, (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row and len(row) >= 8:  # ✅ Проверяем длину tuple
            winrate = (row[4] / max(row[5], 1)) * 100 if row[5] > 0 else 0
            return {
                'id': row[0],
                'username': row[1],
                'silver': row[2],
                'gold': row[3],
                'wins': row[4],
                'battles': row[5],
                'winrate': round(winrate, 1),
                'role': row[6],
                'tank_id': row[7] or 'ms1'
            }
        return None
    except Exception as e:
        print(f"GET_PLAYER ERROR: {e}")
        return None

# 🔥 LIVE СТАТИСТИКА (строка ~740)
def get_live_gold():
    try:
        conn = sqlite3.connect('players.db')
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(gold) FROM players")
        total = cursor.fetchone()[0] or 0
        conn.close()
        return int(total)
    except:
        return 10000

def get_live_players():
    try:
        conn = sqlite3.connect('players.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM players")
        total = cursor.fetchone()[0]
        conn.close()
        return int(total)
    except:
        return 42

@app.route('/api/live-data')
def api_live_data():
    if 'user_id' not in session:
        return jsonify({'silver': 0, 'gold': 0, 'wins': 0, 'battles': 0})
    
    conn = get_db()
    cursor = conn.execute('SELECT silver, gold, wins, battles FROM players WHERE id=?', 
                         (session['user_id'],))
    player = cursor.fetchone()
    conn.close()
    
    return jsonify({
        'silver': player[0] if player else 0,
        'gold': player[1] if player else 0,
        'wins': player[2] if player else 0,
        'battles': player[3] if player else 0
    })

# 🔥 ГАРАЖ ФУНКЦИЯ
def get_player_tanks(player_id):
    try:
        conn = sqlite3.connect('garage.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM garage WHERE player_id = ?", (player_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except:
        return 0

@app.route('/leaderboard')
def leaderboard():
    conn = get_db()
    cursor = conn.cursor()
    
    # Топ 10 по победам
    cursor.execute('''SELECT username, wins, battles, silver 
                      FROM players ORDER BY wins DESC LIMIT 10''')
    top_players = cursor.fetchall()
    
    # Позиция текущего игрока
    if 'user_id' in session:
        cursor.execute('''SELECT username, wins FROM players WHERE id=?''', (session['user_id'],))
        player_data = cursor.fetchone()
        if player_data:
            cursor.execute('SELECT COUNT(*) + 1 FROM players WHERE wins > ?', (player_data[1],))
            player_rank = cursor.fetchone()[0]
        else:
            player_rank = None
    else:
        player_rank = None
    
    conn.close()
    return render_template('leaderboard.html', top_players=top_players, player_rank=player_rank)

@app.route('/api/leaderboard')
def api_leaderboard():
    """LIVE обновление лидерборда"""
    return jsonify(get_leaderboard())

# ========================================
# ✅ БАЗА ДАННЫХ - ИНИЦИАЛИЗАЦИЯ v9.9
# ========================================
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE,
        silver INTEGER DEFAULT 0,
        gold INTEGER DEFAULT 0,
        wins INTEGER DEFAULT 0,
        battles INTEGER DEFAULT 0,
        crystal INTEGER DEFAULT 0,  -- добавить эту строку
        bond INTEGER DEFAULT 0,
        created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

# Вызвать при старте
init_db()

def init_sample_data():
    """Инициализация БД с админами и тестовыми игроками"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 🎖️ АДМИНЫ (полные права)
    admins = [
        ('Назар', '120187', 5000, 0, 0, 0, 0, 1),  # Ветеран
        ('CatNap', '120187', 5000, 0, 0, 0, 0, 1),  # Топ-3
    ]
    # 1. Создать админов
    for username, password, silver, gold, wins, battles, crystal, level in admins:
        password_hash = generate_password_hash(password)
        cursor.execute('''INSERT OR REPLACE INTO players 
                         (username, password, silver, gold, wins, battles, crystal, level, 
                          is_admin, created, last_activity)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)''',
                      (username, password_hash, silver, gold, wins, battles, crystal, level,
                       datetime.now(), datetime.now()))
    
    # 2. Создать тестовых игроков  
    for username, password, silver, gold, wins, battles, crystal, level in test_players:
        password_hash = generate_password_hash(password)
        cursor.execute('''INSERT OR IGNORE INTO players 
                         (username, password, silver, gold, wins, battles, crystal, level,
                          created, last_activity)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (username, password_hash, silver, gold, wins, battles, crystal, level,
                       datetime.now(), datetime.now()))
    
    # 3. Установить стартовые значения для новых игроков
    cursor.execute('''UPDATE players SET 
                         silver = COALESCE(silver, 500),
                         gold = COALESCE(gold, 0),
                         wins = COALESCE(wins, 0),
                         battles = COALESCE(battles, 0),
                         crystal = COALESCE(crystal, 0),
                         level = COALESCE(level, 1)
                      WHERE silver IS NULL''')
    
    conn.commit()

    init_sample_data()  # ← Всё готово!
    
    # 4. Показать статистику
    cursor.execute('SELECT COUNT(*) FROM players')
    total_players = cursor.fetchone()[0]
    cursor.execute('SELECT SUM(battles) FROM players')
    total_battles = cursor.fetchone()[0] or 0
    
    print(f"✅ БД инициализирована!")
    print(f"👑 Админы: Назар/120187, CatNap/120187")
    print(f"📊 Игроков: {total_players} | Боёв: {total_battles}")
    print(f"🎮 Новички стартуют с 500 серебра")
    
    conn.close()

def get_player_stats(target_id):
    conn = get_db()
    cursor = conn.cursor()
    
    # Безопасный запрос только существующих колонок
    cursor.execute('PRAGMA table_info(players)')
    columns = [col[1] for col in cursor.fetchall()]
    
    select_cols = ['id', 'username', 'silver', 'gold', 'wins', 'battles', 'created', 'last_activity']
    if 'crystal' in columns: select_cols.append('crystal')
    if 'bond' in columns: select_cols.append('bond')
    
    query = f'SELECT {", ".join(select_cols)} FROM players WHERE id=?'
    cursor.execute(query, (target_id,))
    player = cursor.fetchone()
    conn.close()
    return player

def get_player_stats(player_id):
    """Полные статы игрока"""
    conn = sqlite3.connect('players.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT username, silver, gold, wins, battles, role 
        FROM players WHERE id = ?
    """, (player_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        winrate = (row[3] / max(row[4], 1)) * 100 if row[4] > 0 else 0
        return {
            'username': row[0],
            'silver': row[1],
            'gold': row[2],
            'wins': row[3],
            'battles': row[4],
            'winrate': round(winrate, 1),
            'tank_count': len(get_player_tanks(player_id))
        }
    return None

def update_player(player):
    try:
        conn = sqlite3.connect('players.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE players SET gold=?, silver=?, points=?, tanks=?, battles=?, wins=?, rank=?
            WHERE id=?
        ''', (
            player['gold'], player['silver'], player['points'],
            json.dumps(player['tanks']), player['battles'], player['wins'],
            player.get('rank', 'Солдат'), player['id']
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"UPDATE_PLAYER ERROR: {e}")
        return False

def validate_session():
    if 'user_id' not in session:
        return False
    player = get_player(session['user_id'])
    if not player:
        session.clear()
        return False
    return True

def is_superadmin(username):
    return username in ADMIN_LOGINS

queue_players = {}  # {tier: [player_ids]}

@app.route('/api/queue-status')
def api_queue_status():
    return jsonify({
        'tier1': len(queue_players.get(1, [])),
        'tier2': len(queue_players.get(2, [])),
        'tier3': len(queue_players.get(3, []))
    })

def give_reward(player_id, silver):
    conn = sqlite3.connect('players.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE players SET silver = silver + ? WHERE id = ?", (silver, player_id))
    cursor.execute("UPDATE players SET wins = wins + 1, battles = battles + 1 WHERE id = ?", (player_id,))
    conn.commit()
    conn.close()

# ========================================
# ✅ МАРШРУТЫ - АВТОРИЗАЦИЯ
# ========================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if len(username) < 3 or len(password) < 6:
            flash('❌ Имя >3 символов, пароль >6!')
            return render_template('register.html')
        
        try:
            conn = sqlite3.connect('players.db')
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM players")
            total_users = cursor.fetchone()[0]
            role = 'admin' if total_users < 3 else 'player'
            
            player_id = bcrypt.hashpw(username.encode(), bcrypt.gensalt()).decode()[:16]
            hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            
            cursor.execute('''
                INSERT INTO players (id, username, password, gold, silver, created_at, role)
                VALUES (?, ?, ?, 1500, 25000, ?, ?)
            ''', (player_id, username, hashed_pw, datetime.now().isoformat(), role))
            
            conn.commit()
            flash(f'✅ {username} зарегистрирован! Роль: {role}')
            return redirect(url_for('login'))
            
        except sqlite3.IntegrityError:
            flash('❌ Имя уже занято!')
        except Exception as e:
            logging.error(f"REGISTER ERROR: {e}")
            flash('❌ Ошибка регистрации!')
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/admin')
def admin_panel():
    if session.get('role') != 'superadmin':
        return redirect(url_for('login'))
    
    top_players = get_leaderboard(10)
    return render_template('admin.html', top_players=top_players)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        print(f"DEBUG LOGIN: username={username}")
        
        # 🔥 ГАРАНТИРОВАННОЕ создание БД ПЕРЕД запросом
        ensure_database()
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Проверяем существование таблицы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='players'")
        if not cursor.fetchone():
            ensure_database()
            conn = get_db()
            cursor = conn.cursor()
        
        cursor.execute("SELECT id, password, is_admin as role FROM players WHERE username = ?", (username,))
        player = cursor.fetchone()
        
        if player and check_password_hash(player[1], password):
            session['user_id'] = player[0]
            session['username'] = username
            session['role'] = player[2]
            conn.close()
            return redirect(url_for('index'))
        
        conn.close()
        flash('Неверный логин или пароль')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('👋 До новых боев!')
    return redirect(url_for('login'))

# ========================================
# ✅ ОСНОВНЫЕ МАРШРУТЫ ИГРЫ
# ========================================
@app.route('/')
def index():
    if not validate_session():
        return redirect(url_for('login'))
    
    player = get_player(session['user_id'])
    return render_template('index.html', player=player)

@app.route('/shop')
def shop():
    if not validate_session():
        return redirect(url_for('login'))
    
    player = get_player(session['user_id'])
    owned_ids = set(player.get('tanks', []))
    
    # ✅ СПИСОК ТАНКОВ С ID
    tanks_list = []
    for tank_id, tank_data in TANKS.items():
        tank_data_copy = tank_data.copy()
        tank_data_copy['id'] = tank_id
        tanks_list.append(tank_data_copy)
    
    return render_template('shop.html', player=player, tanks=tanks_list, owned_ids=owned_ids)

@app.route('/garage')
def garage():
    if not validate_session():
        return redirect(url_for('login'))
    
    player = get_player(session['user_id'])
    try:
        conn = sqlite3.connect('garage.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM garage WHERE player_id = ?", (player['id'],))
        garage_count = cursor.fetchone()[0]
        player['garage_count'] = garage_count
        conn.close()
    except:
        player['garage_count'] = 0
    
    return render_template('garage.html', player=player, TANKS=TANKS)

@app.route('/battle')
def battle():
    if not validate_session():
        return redirect(url_for('login'))
    
    player = get_player(session['user_id'])
    if not player:
        return redirect(url_for('login'))
    
    # Получаем танк из GET параметра или используем основной
    tank_id = request.args.get('tank', player.get('tank_id', 'ms1'))
    tier = TANKS.get(tank_id, {}).get('tier', 1)
    
    return render_template('battle.html', player=player, tank_id=tank_id, tier=tier)

@app.route('/api/battle-result', methods=['POST'])
def battle_result():
    """API для результата боя"""
    data = request.json
    player_id = data['player_id']
    tier = data['tier']
    is_win = data['win']
    
    reward = 15000 if is_win else 2000
    give_reward(player_id, reward)
    
    return jsonify({'reward': reward, 'status': 'ok'})

@app.route('/buy/<tank_id>', methods=['POST'])
def buy_tank(tank_id):
    if not validate_session():
        flash('🚫 Войдите в аккаунт!')
        return redirect(url_for('login'))
    
    player = get_player(session['user_id'])
    tank = TANKS.get(tank_id)
    
    if not tank or player['silver'] < tank['price']:
        flash('❌ Недостаточно серебра!')
        return redirect(url_for('shop'))
    
    # 🔥 ФИКС: Обновляем серебро напрямую в players.db
    conn = sqlite3.connect('players.db')
    cursor = conn.cursor()
    new_silver = player['silver'] - tank['price']
    cursor.execute("UPDATE players SET silver = ? WHERE id = ?", (new_silver, player['id']))
    
    # СОЗДАЁМ garage.db + добавляем танк
    conn_garage = sqlite3.connect('garage.db')
    cursor_garage = conn_garage.cursor()
    cursor_garage.execute('''CREATE TABLE IF NOT EXISTS garage 
                          (id INTEGER PRIMARY KEY, player_id TEXT, tank_id TEXT, 
                           bought_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor_garage.execute("INSERT INTO garage (player_id, tank_id) VALUES (?, ?)", 
                         (player['id'], tank_id))
    conn_garage.commit()
    conn_garage.close()
    
    conn.commit()
    conn.close()
    
    flash(f'✅ Купил {tank["name"]} за {tank["price"]:,} серебра! 🪙')
    return redirect(url_for('shop'))

# ========================================
# ✅ ДОПОЛНИТЕЛЬНЫЕ СТРАНИЦЫ
# ========================================
@app.route('/chat')
def chat():
    if not validate_session():
        return redirect(url_for('login'))
    return '''
    <!DOCTYPE html>
    <html><head><title>Чат</title>
    <meta charset="UTF-8">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>body{background:linear-gradient(135deg,#1e1e2e 0%,#2a2a3e 100%);color:white;font-family:'Segoe UI',sans-serif;padding:40px;text-align:center;min-height:100vh;display:flex;align-items:center;justify-content:center;}
    .chat-container{max-width:600px;width:100%;background:rgba(30,30,46,0.9);backdrop-filter:blur(20px);border-radius:24px;border:1px solid rgba(255,255,255,0.1);padding:40px;box-shadow:0 20px 40px rgba(0,0,0,0.3);}
    h1{font-size:3rem;font-weight:900;background:linear-gradient(135deg,#00d4ff,#7b42f6);background-clip:text;-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:2rem;}
    .status{font-size:1.2rem;color:#a0a0a0;margin-bottom:2rem;}
    .btn-home{display:inline-flex;items:center;gap:12px;background:linear-gradient(135deg,#16a34a,#15803d);color:white;padding:16px 32px;border-radius:16px;font-weight:700;font-size:1.1rem;text-decoration:none;transition:all 0.3s ease;box-shadow:0 8px 24px rgba(22,163,74,0.3);}
    .btn-home:hover{background:linear-gradient(135deg,#15803d,#166534);transform:translateY(-2px);box-shadow:0 12px 32px rgba(22,163,74,0.4);}
    </style></head>
    <body>
    <div class="chat-container">
        <h1><i class="fas fa-comments"></i> Глобальный Чат</h1>
        <div class="status">🔨 В разработке (Q1 2026)</div>
        <a href="/" class="btn-home"><i class="fas fa-home"></i> ← Вернуться в ангар</a>
    </div>
    </body></html>
    '''

@app.route('/tournaments')
def tournaments():
    if not validate_session():
        return redirect(url_for('login'))
    return '''
    <!DOCTYPE html>
    <html><head><title>Турниры</title>
    <meta charset="UTF-8">
    <style>body{background:linear-gradient(135deg,#1e1e2e 0%,#2a2a3e 100%);color:white;font-family:'Segoe UI',sans-serif;padding:40px;text-align:center;min-height:100vh;display:flex;align-items:center;justify-content:center;}
    .tour-container{max-width:600px;width:100%;background:rgba(30,30,46,0.9);backdrop-filter:blur(20px);border-radius:24px;border:1px solid rgba(255,255,255,0.1);padding:40px;box-shadow:0 20px 40px rgba(0,0,0,0.3);}
    h1{font-size:3rem;font-weight:900;background:linear-gradient(135deg,#fbbf24,#f59e0b);background-clip:text;-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:2rem;}
    </style></head>
    <body>
    <div class="tour-container">
        <h1><i class="fas fa-trophy"></i> Турниры</h1>
        <div style="font-size:1.2rem;color:#a0a0a0;margin-bottom:2rem;">🔨 В разработке (Q2 2026)</div>
        <a href="/" style="display:inline-flex;items:center;gap:12px;background:linear-gradient(135deg,#16a34a,#15803d);color:white;padding:16px 32px;border-radius:16px;font-weight:700;font-size:1.1rem;text-decoration:none;"><i class="fas fa-home"></i> ← Ангар</a>
    </div>
    </body></html>
    '''

@app.route('/achievements')
def achievements():
    if not validate_session():
        return redirect(url_for('login'))
    return '''
    <!DOCTYPE html>
    <html><head><title>Достижения</title>
    <meta charset="UTF-8">
    <style>body{background:linear-gradient(135deg,#1e1e2e 0%,#2a2a3e 100%);color:white;font-family:'Segoe UI',sans-serif;padding:40px;text-align:center;min-height:100vh;display:flex;align-items:center;justify-content:center;}
    .ach-container{max-width:600px;width:100%;background:rgba(30,30,46,0.9);backdrop-filter:blur(20px);border-radius:24px;border:1px solid rgba(255,255,255,0.1);padding:40px;box-shadow:0 20px 40px rgba(0,0,0,0.3);}
    h1{font-size:3rem;font-weight:900;background:linear-gradient(135deg,#8b5cf6,#7c3aed);background-clip:text;-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:2rem;}
    </style></head>
    <body>
    <div class="ach-container">
        <h1><i class="fas fa-medal"></i> Достижения</h1>
        <div style="font-size:1.2rem;color:#a0a0a0;margin-bottom:2rem;">🔨 В разработке</div>
        <a href="/" style="display:inline-flex;items:center;gap:12px;background:linear-gradient(135deg,#16a34a,#15803d);color:white;padding:16px 32px;border-radius:16px;font-weight:700;font-size:1.1rem;text-decoration:none;"><i class="fas fa-home"></i> ← Ангар</a>
    </div>
    </body></html>
    '''
import datetime
from datetime import datetime as dt

# 🔥 ФИЛЬТРЫ JINJA (один раз!)
@app.template_filter('datetimeformat')
def datetimeformat(value):
    try:
        return dt.fromtimestamp(float(value)).strftime('%d.%m.%Y')
    except:
        return str(value)

@app.template_filter('numberformat')
def numberformat(value):
    try:
        val = int(value)
        if val >= 1_000_000: return f'{val//1_000_000}M'
        if val >= 1_000: return f'{val//1_000}K'
        return f'{val:,}'
    except: return '0'

# 🔥 СИСТЕМА РАНГОВ
RANK_SYSTEM = {
    0: 'Рекрут 🪖', 100: 'Лейтенант ⭐', 500: 'Капитан ⚔️',
    1500: 'Майор 🛡️', 3500: 'Полковник 👑', 7000: 'Генерал 🌟', 15000: 'Легенда 🏆'
}

def get_rank_info(xp):
    for min_xp, rank in sorted(RANK_SYSTEM.items(), reverse=True):
        if xp >= min_xp: return rank, min_xp
    return RANK_SYSTEM[0], 0

def player_has_tank(player_id, tank_id):
    try:
        conn = sqlite3.connect('garage.db')
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM garage WHERE player_id=? AND tank_id=?", (player_id, tank_id))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    except: return False

# 🔥 ПРОФИЛЬ (свой + чужие!)
@app.route('/profile')
@app.route('/profile/<user_id>')
def profile(user_id=None):
    if not validate_session() and not user_id:
        return redirect(url_for('login'))
    
    # ID по умолчанию
    target_id = user_id or session.get('user_id', 120187)
    
    conn = sqlite3.connect('players.db')
    cursor = conn.cursor()
    
    # 🔥 БЕЗОПАСНЫЙ SELECT - только существующие колонки!
    cursor.execute('''SELECT id, username, silver, gold, wins, battles, crystal, bond, created, last_activity 
                      FROM players WHERE id=?''', (target_id,))
    row = cursor.fetchone()
    
    if not row:
        flash('Игрок не найден!')
        return redirect(url_for('index'))
    
    # 🔥 XP = wins * 10 если нет колонки
    wins, battles = row[4] or 0, row[5] or 0
    xp = wins * 10  # Автоматический XP
    
    player = {
        'id': row[0], 'username': row[1], 'silver': row[2] or 0, 'gold': row[3] or 0,
        'wins': wins, 'battles': battles, 'winrate': round((wins/max(battles,1))*100, 1),
        'xp': xp, 'crystal': row[6] or 0, 'bond': row[7] or 0, 'created': row[8] or 0
    }
    
    # 🔥 РАНГ
    rank_system = {0: 'Рекрут 🪖', 100: 'Лейтенант ⭐', 500: 'Капитан ⚔️', 
                   1500: 'Майор 🛡️', 3500: 'Полковник 👑', 7000: 'Генерал 🌟'}
    current_rank = 'Рекрут 🪖'
    for min_xp, rank in sorted(rank_system.items(), reverse=True):
        if xp >= min_xp: 
            current_rank = rank
            break
    
    player.update({
        'rank': current_rank, 'progress': min(100, (xp/7000)*100), 'xp_to_next': 7000
    })
    
    # 🔥 ГАРАЖ
    try:
        cursor.execute("SELECT COUNT(*) FROM garage WHERE player_id=?", (target_id,))
        player['garage_count'] = cursor.fetchone()[0]
    except: 
        player['garage_count'] = 0
    
    conn.close()
    return render_template('profile.html', player=player)

# ========================================
# ✅ ИНИЦИАЛИЗАЦИЯ
# ========================================
if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
else:
    init_db()








