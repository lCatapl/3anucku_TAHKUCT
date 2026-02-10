from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import json, sqlite3, hashlib, time, os, random, threading
from datetime import datetime, timedelta
from collections import defaultdict

app = Flask(__name__)
app.secret_key = 'tankist_v9.6_super_secret_key_2026'

# ✅ ГЛОБАЛЬНЫЕ КОНСТАНТЫ v9.6
PLAYERS_EQUAL = True
ADMIN_LOGINS = ["Назар", "CatNap"]
MODERATORS = set()
MUTED_PLAYERS_TIME = {}
chat_messages = []
DB_PATH = 'tankist.db'

# ========================================
# ✅ 1.1 ПОЛНЫЙ СПИСОК 60+ ТАНКОВ v9.4
# ========================================
TANKS = {
    # 🇷🇺 СССР - S-TIER META (НОВЫЕ ЦЕНЫ)
    "obj140": {"name": "Объект 140", "nation": "USSR", "tier": 10, "type": "MT", "price": 950000, "hp": 1940, "damage": 440, "pen": 258, "speed": 55, "premium": False},
    "t62a": {"name": "Т-62А", "nation": "USSR", "tier": 10, "type": "MT", "price": 920000, "hp": 2120, "damage": 360, "pen": 264, "speed": 50, "premium": False},
    "obj430u": {"name": "Объект 430У", "nation": "USSR", "tier": 9, "type": "MT", "price": 380000, "hp": 1860, "damage": 390, "pen": 252, "speed": 50, "premium": False},
    "obj268v4": {"name": "Объект 268 Вариант 4", "nation": "USSR", "tier": 10, "type": "TD", "price": 980000, "hp": 2120, "damage": 490, "pen": 299, "speed": 42, "premium": False},
    "obj432": {"name": "Объект 432", "nation": "USSR", "tier": 8, "type": "MT", "price": 145000, "hp": 1520, "damage": 320, "pen": 220, "speed": 52, "premium": False},
    "obj907": {"name": "Объект 907", "nation": "USSR", "tier": 10, "type": "MT", "price": 960000, "hp": 1960, "damage": 390, "pen": 270, "speed": 52, "premium": False},
    "obj258": {"name": "Объект 258", "nation": "USSR", "tier": 10, "type": "LT", "price": 880000, "hp": 1750, "damage": 360, "pen": 264, "speed": 68, "premium": False},
    "is7": {"name": "ИС-7", "nation": "USSR", "tier": 10, "type": "HT", "price": 990000, "hp": 2300, "damage": 490, "pen": 270, "speed": 30, "premium": False},
    "stii": {"name": "СТ-II", "nation": "USSR", "tier": 10, "type": "HT", "price": 940000, "hp": 2250, "damage": 440, "pen": 252, "speed": 28, "premium": False},
    "t44_100": {"name": "Т-44-100", "nation": "USSR", "tier": 8, "type": "MT", "price": 185000, "hp": 1620, "damage": 440, "pen": 259, "speed": 52, "premium": True},
    "obj263": {"name": "Объект 263", "nation": "USSR", "tier": 10, "type": "TD", "price": 1250000, "hp": 2120, "damage": 490, "pen": 299, "speed": 45, "premium": True},
    
    # 🇩🇪 ГЕРМАНИЯ
        # 🇩🇪 ГЕРМАНИЯ
    "e100": {"name": "E 100", "nation": "Germany", "tier": 10, "type": "HT", "price": 1050000, "hp": 2400, "damage": 490, "pen": 299, "speed": 25, "premium": False},
    "e75": {"name": "E 75", "nation": "Germany", "tier": 9, "type": "HT", "price": 390000, "hp": 2100, "damage": 490, "pen": 270, "speed": 28, "premium": False},
    "vte100": {"name": "VK 100.01 (P)", "nation": "Germany", "tier": 8, "type": "HT", "price": 155000, "hp": 1800, "damage": 440, "pen": 252, "speed": 22, "premium": False},
    "leopard1": {"name": "Leopard 1", "nation": "Germany", "tier": 10, "type": "LT", "price": 890000, "hp": 1850, "damage": 400, "pen": 264, "speed": 65, "premium": False},
    "obj268": {"name": "Объект 268", "nation": "Germany", "tier": 10, "type": "TD", "price": 970000, "hp": 1940, "damage": 490, "pen": 299, "speed": 38, "premium": False},
    "pro_art": {"name": "Progetto M35 mod. 46", "nation": "Germany", "tier": 8, "type": "MT", "price": 165000, "hp": 1580, "damage": 340, "pen": 234, "speed": 58, "premium": False},
    "e50m": {"name": "E 50 M", "nation": "Germany", "tier": 10, "type": "MT", "price": 1220000, "hp": 1960, "damage": 440, "pen": 270, "speed": 52, "premium": True},
    "vk7201": {"name": "VK 72.01 (K)", "nation": "Germany", "tier": 10, "type": "HT", "price": 1350000, "hp": 2350, "damage": 490, "pen": 299, "speed": 25, "premium": True},

    # 🇺🇸 США
    "sheridan": {"name": "M551 Sheridan", "nation": "USA", "tier": 10, "type": "LT", "price": 870000, "hp": 1620, "damage": 400, "pen": 268, "speed": 70, "premium": False},
    "t110e5": {"name": "T110E5", "nation": "USA", "tier": 10, "type": "HT", "price": 1020000, "hp": 2250, "damage": 400, "pen": 252, "speed": 32, "premium": False},
    "t95e6": {"name": "T95E6", "nation": "USA", "tier": 10, "type": "HT", "price": 1010000, "hp": 2250, "damage": 400, "pen": 252, "speed": 30, "premium": False},
    "t29": {"name": "T29", "nation": "USA", "tier": 7, "type": "HT", "price": 65000, "hp": 1650, "damage": 400, "pen": 224, "speed": 35, "premium": False},
    "t92htc": {"name": "T92 HMC", "nation": "USA", "tier": 8, "type": "ARTY", "price": 175000, "hp": 1650, "damage": 1100, "pen": 86, "speed": 40, "premium": False},
    "t34": {"name": "T34", "nation": "USA", "tier": 9, "type": "HT", "price": 450000, "hp": 2100, "damage": 400, "pen": 252, "speed": 35, "premium": True},
    "t110e3": {"name": "T110E3", "nation": "USA", "tier": 10, "type": "HT", "price": 1240000, "hp": 2250, "damage": 400, "pen": 252, "speed": 28, "premium": True},

    # 🇬🇧 БРИТАНИЯ
    "fv215b": {"name": "FV215b (183)", "nation": "UK", "tier": 10, "type": "HT", "price": 1030000, "hp": 2200, "damage": 400, "pen": 257, "speed": 34, "premium": False},
    "super_conqueror": {"name": "Super Conqueror", "nation": "UK", "tier": 10, "type": "HT", "price": 1080000, "hp": 2150, "damage": 400, "pen": 270, "speed": 36, "premium": False},
    "chieftain_mk6": {"name": "Chieftain Mk. 6", "nation": "UK", "tier": 10, "type": "HT", "price": 1060000, "hp": 2100, "damage": 400, "pen": 270, "speed": 38, "premium": False},
        "turtle_mk1": {"name": "Turtle Mk. I", "nation": "UK", "tier": 10, "type": "HT", "price": 1150000, "hp": 2400, "damage": 400, "pen": 257, "speed": 28, "premium": True},

    # 🇯🇵 ЯПОНИЯ
    "sta1": {"name": "STA-1", "nation": "Japan", "tier": 10, "type": "MT", "price": 910000, "hp": 1960, "damage": 360, "pen": 264, "speed": 53, "premium": False},
    "type71": {"name": "Type 71", "nation": "Japan", "tier": 10, "type": "HT", "price": 1040000, "hp": 2250, "damage": 490, "pen": 270, "speed": 32, "premium": False},
    "ho_ri_3": {"name": "Ho-Ri 3", "nation": "Japan", "tier": 10, "type": "TD", "price": 1090000, "hp": 2120, "damage": 490, "pen": 299, "speed": 38, "premium": True},

    # 🇨🇳 КИТАЙ
    "113": {"name": "113", "nation": "China", "tier": 10, "type": "MT", "price": 930000, "hp": 1960, "damage": 360, "pen": 264, "speed": 50, "premium": False},
    "wz111_5a": {"name": "WZ-113G FT", "nation": "China", "tier": 10, "type": "HT", "price": 1000000, "hp": 2250, "damage": 400, "pen": 252, "speed": 32, "premium": False},
    "114_sp2": {"name": "114 SP2", "nation": "China", "tier": 10, "type": "TD", "price": 1070000, "hp": 1940, "damage": 490, "pen": 299, "speed": 40, "premium": True},

    # 🇮🇹 ИТАЛИЯ
    "pro_getter": {"name": "Progetto 46", "nation": "Italy", "tier": 8, "type": "MT", "price": 135000, "hp": 1580, "damage": 340, "pen": 234, "speed": 58, "premium": False},
    "rhm_borsig": {"name": "Rhm.-Borsig Waffenträger", "nation": "Italy", "tier": 9, "type": "TD", "price": 360000, "hp": 1750, "damage": 490, "pen": 280, "speed": 45, "premium": False},

    # 🇵🇱 ПОЛЬША
    "cs63": {"name": "CS-63", "nation": "Poland", "tier": 10, "type": "MT", "price": 900000, "hp": 1960, "damage": 360, "pen": 264, "speed": 62, "premium": False},
    "60tp": {"name": "60TP Lewandowskiego", "nation": "Poland", "tier": 10, "type": "HT", "price": 1100000, "hp": 2250, "damage": 490, "pen": 270, "speed": 32, "premium": False},

    # 🇸🇪 ШВЕЦИЯ
    "kranvagn": {"name": "Kranvagn", "nation": "Sweden", "tier": 10, "type": "HT", "price": 1070000, "hp": 2150, "damage": 400, "pen": 257, "speed": 34, "premium": False},
    "strv103b": {"name": "Strv 103B", "nation": "Sweden", "tier": 10, "type": "TD", "price": 920000, "hp": 1940, "damage": 400, "pen": 270, "speed": 32, "premium": False},

    # 🇨🇿 ЧЕХОСЛОВАКИЯ
    "tvp_t50": {"name": "TVP T 50/51", "nation": "Czech", "tier": 10, "type": "MT", "price": 895000, "hp": 1960, "damage": 360, "pen": 264, "speed": 60, "premium": False},
    "skoda_t56": {"name": "Skoda T 56", "nation": "Czech", "tier": 10, "type": "HT", "price": 1200000, "hp": 2250, "damage": 490, "pen": 270, "speed": 32, "premium": True},
    "uim42": {"name": "U-Des. 42", "nation": "Sweden", "tier": 8, "type": "MT", "price": 195000, "hp": 1580, "damage": 360, "pen": 240, "speed": 55, "premium": True},
}

ALL_TANKS_LIST = list(TANKS.values())

# ========================================
# ✅ 1.2 25 ЗВАНИЙ v9.3 - ПОЛНЫЙ СПИСОК (ПРОДОЛЖЕНИЕ)
# ========================================
RANKS_FULL = [
    {"id": 1, "name": "Рядовой", "min_points": 0, "max_points": 999, "color": "#cccccc", "icon": "👶"},
    {"id": 2, "name": "Ефрейтор", "min_points": 1000, "max_points": 2999, "color": "#cccccc", "icon": "⚔️"},
    {"id": 3, "name": "Младший сержант", "min_points": 3000, "max_points": 5999, "color": "#cccccc", "icon": "⭐"},
    {"id": 4, "name": "Сержант", "min_points": 6000, "max_points": 9999, "color": "#cccccc", "icon": "⭐⭐"},
    {"id": 5, "name": "Старший сержант", "min_points": 10000, "max_points": 14999, "color": "#cccccc", "icon": "⭐⭐⭐"},
    {"id": 6, "name": "Старшина", "min_points": 15000, "max_points": 21999, "color": "#cccccc", "icon": "⭐⭐⭐⭐"},
    {"id": 7, "name": "Младший лейтенант", "min_points": 22000, "max_points": 29999, "color": "#87CEEB", "icon": "⚐"},
    {"id": 8, "name": "Лейтенант", "min_points": 30000, "max_points": 39999, "color": "#87CEEB", "icon": "⚐⚐"},
    {"id": 9, "name": "Ст. лейтенант", "min_points": 40000, "max_points": 54999, "color": "#87CEEB", "icon": "⚐⚐⚐"},
    {"id": 10, "name": "Капитан", "min_points": 55000, "max_points": 74999, "color": "#87CEEB", "icon": "⚑"},
    {"id": 11, "name": "Майор", "min_points": 75000, "max_points": 99999, "color": "#87CEEB", "icon": "⚑⚑"},
    {"id": 12, "name": "Подполковник", "min_points": 100000, "max_points": 129999, "color": "#87CEEB", "icon": "⚑⚑⚑"},
    {"id": 13, "name": "Полковник", "min_points": 130000, "max_points": 169999, "color": "#87CEEB", "icon": "👑"},
    {"id": 14, "name": "Генерал-майор", "min_points": 170000, "max_points": 229999, "color": "#FFD700", "icon": "⭐👑"},
    {"id": 15, "name": "Генерал-лейтенант", "min_points": 230000, "max_points": 299999, "color": "#FFD700", "icon": "⭐⭐👑"},
    {"id": 16, "name": "Генерал-полковник", "min_points": 300000, "max_points": 399999, "color": "#FFD700", "icon": "⭐⭐⭐👑"},
    {"id": 17, "name": "Генерал армии", "min_points": 400000, "max_points": 599999, "color": "#FFD700", "icon": "⭐⭐⭐⭐👑"},
    {"id": 18, "name": "Маршал", "min_points": 600000, "max_points": 999999, "color": "#FF4500", "icon": "🌟👑"},
    {"id": 19, "name": "Маршал БРонеТРОПЫ", "min_points": 1000000, "max_points": 1499999, "color": "#FF1493", "icon": "🔥👑"},
    {"id": 20, "name": "Герой Советского Союза", "min_points": 1500000, "max_points": 1999999, "color": "#FF69B4", "icon": "⭐🔥👑"},
    {"id": 21, "name": "Дважды Герой СССР", "min_points": 2000000, "max_points": 2999999, "color": "#FF1493", "icon": "⭐⭐🔥👑"},
    {"id": 22, "name": "Трижды Герой СССР", "min_points": 3000000, "max_points": 4999999, "color": "#DC143C", "icon": "⭐⭐⭐🔥👑"},
    {"id": 23, "name": "Легенда Танковых войск", "min_points": 5000000, "max_points": 9999999, "color": "#8A2BE2", "icon": "🌟🔥👑"},
    {"id": 24, "name": "Титан Стального Кулака", "min_points": 10000000, "max_points": 49999999, "color": "#FF00FF", "icon": "💎🔥👑"},
    {"id": 25, "name": "НЕПОБЕДИМЫЙ МАРШАЛ", "min_points": 50000000, "max_points": float('inf'), "color": "#FFD700", "icon": "🏆🔥👑🌟"}
]

# ========================================
# ✅ 1.3 ФУНКЦИИ ЗВАНИЙ И БАЗА ДАННЫХ
# ========================================
def get_rank_progress(points):
    """Возвращает текущее звание + прогресс до следующего"""
    for rank in RANKS_FULL:
        if points >= rank["min_points"]:
            current_rank = rank
            
            next_rank_idx = RANKS_FULL.index(rank) + 1
            if next_rank_idx < len(RANKS_FULL):
                next_rank = RANKS_FULL[next_rank_idx]
                progress = min(100, ((points - rank["min_points"]) / (next_rank["min_points"] - rank["min_points"])) * 100)
            else:
                progress = 100
                next_rank = {"name": "⚔️ ЛЕГЕНДА ⚔️", "min_points": float('inf')}
            
            return {
                "current": f'{current_rank["icon"]} {current_rank["name"]}',
                "current_id": current_rank["id"],
                "color": current_rank["color"],
                "progress": progress,
                "points": points,
                "next": next_rank["name"],
                "next_points": next_rank["min_points"],
                "rank_emoji": current_rank["icon"]
            }
    return {
        "current": "👶 Рядовой",
        "current_id": 1,
        "color": "#cccccc",
        "progress": 0,
        "points": points,
        "next": "⚔️ Ефрейтор",
        "next_points": 1000,
        "rank_emoji": "👶"
    }

# ========================================
# ✅ 1.4 БАЗА ДАННЫХ И ИГРОКИ
# ========================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS players (
        user_id TEXT PRIMARY KEY,
        username TEXT,
        gold INTEGER DEFAULT 5000,
        silver INTEGER DEFAULT 25000,
        points INTEGER DEFAULT 0,
        rank_id INTEGER DEFAULT 1,
        tanks TEXT DEFAULT '[]',
        wins INTEGER DEFAULT 0,
        battles INTEGER DEFAULT 0,
        daily_streak INTEGER DEFAULT 0,
        last_daily REAL DEFAULT 0,
        is_muted INTEGER DEFAULT 0,
        mute_until REAL DEFAULT 0,
        role TEXT DEFAULT 'player',
        join_date REAL DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS leaderboards (
        user_id TEXT PRIMARY KEY,
        points INTEGER,
        wins INTEGER,
        battles INTEGER,
        updated REAL
    )''')
    conn.commit()
    conn.close()

def create_player(username, user_id):
    """Все игроки с НУЛЯ - равенство!"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO players 
                 (user_id, username, gold, silver, points, rank_id, tanks, wins, battles, daily_streak, last_daily, role, join_date)
                 VALUES (?, ?, 5000, 25000, 0, 1, '[]', 0, 0, 0, 0, 'player', ?)''',
              (user_id, username, time.time()))
    conn.commit()
    conn.close()
    return True

def get_player(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM players WHERE user_id = ?', (user_id,))
    player = c.fetchone()
    conn.close()
    
    if player:
        return {
            "user_id": player[0],
            "username": player[1],
            "gold": player[2],
            "silver": player[3],
            "points": player[4],
            "rank_id": player[5],
            "tanks": json.loads(player[6]) if player[6] else [],
            "wins": player[7],
            "battles": player[8],
            "daily_streak": player[9],
            "last_daily": player[10],
            "is_muted": player[11] == 1,
            "mute_until": player[12],
            "role": player[13],
            "join_date": player[14]
        }
    return None

def update_player(player_data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''UPDATE players SET 
                 gold=?, silver=?, points=?, rank_id=?, tanks=?, wins=?, battles=?, 
                 daily_streak=?, last_daily=?, is_muted=?, mute_until=?, role=?
                 WHERE user_id=?''',
              (player_data['gold'], player_data['silver'], player_data['points'], player_data['rank_id'],
               json.dumps(player_data['tanks']), player_data['wins'], player_data['battles'],
               player_data['daily_streak'], player_data['last_daily'], 
               1 if player_data['is_muted'] else 0, player_data['mute_until'], player_data['role'],
               player_data['user_id']))
    conn.commit()
    conn.close()

# ========================================
# ✅ 1.5 АДМИН/МОДЕР ПРОВЕРКИ
# ========================================
def is_admin(username):
    return username in ADMIN_LOGINS

def is_moderator(username):
    return username in MODERATORS or is_admin(username)

def is_muted(username):
    player = get_player(session.get('user_id'))
    if player and player['is_muted'] and time.time() < player['mute_until']:
        return True
    return False

# ========================================
# ✅ 1.6 НАГРАДЫ - ПОЛНЫЙ СПИСОК
# ========================================
DAILY_REWARDS = {
    "1": {"gold": 2500, "silver": 5000, "points": 500, "msg": "🎁 Ежедневная награда (1 день)"},
    "2": {"gold": 3500, "silver": 7500, "points": 750, "msg": "🎁 Ежедневная награда (2 дня)"},
    "3": {"gold": 5000, "silver": 10000, "points": 1000, "msg": "🎁 Ежедневная награда (3 дня)"},
    "4": {"gold": 7500, "silver": 15000, "points": 1250, "msg": "🎁 Ежедневная награда (4 дня)"},
    "5": {"gold": 10000, "silver": 20000, "points": 1500, "msg": "🎁 🔥 Серия 5 дней! 🔥"},
    "6": {"gold": 12500, "silver": 25000, "points": 1750, "msg": "🎁 Ежедневная награда (6 дней)"},
    "7": {"gold": 15000, "silver": 30000, "points": 2000, "msg": "🏆 НЕДЕЛЬНАЯ НАГРАДА! + Бонусный танк!"}
}

# ========================================
# ✅ 1.7 ЕЖЕДНЕВНЫЕ НАГРАДЫ
# ========================================
def claim_daily(username):
    player = get_player(session.get('user_id'))
    if not player:
        return False, "❌ Профиль не найден!"
    
    now = time.time()
    if now - player['last_daily'] < 86400:  # 24 часа
        return False, "⏰ Подожди 24 часа до следующей награды!"
    
    streak = player['daily_streak']
    if streak >= 7:
        streak = 0  # Сброс после 7 дней
    
    reward = DAILY_REWARDS[str(streak + 1)]
    
    # Награда
    player['gold'] += reward['gold']
    player['silver'] += reward['silver']
    player['points'] += reward['points']
    player['daily_streak'] = streak + 1
    player['last_daily'] = now
    
    # Бонусный танк на 7-й день
    if streak + 1 == 7:
        bonus_tank = random.choice([t for t in ALL_TANKS_LIST if t['tier'] <= 5 and not t['premium']])
        player['tanks'].append(bonus_tank['id'])
        update_player(player)
        return True, f"{reward['msg']}\n🎁 +1 {bonus_tank['name']} (ID: {bonus_tank['id']})"
    
    update_player(player)
    return True, reward['msg']

# ========================================
# ✅ 1.8 МАГАЗИН ТАНКОВ
# ========================================
@app.route('/shop', methods=['GET', 'POST'])
def shop():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    player = get_player(session.get('user_id'))
    if not player:
        return "Профиль не найден!", 404
    
    owned_ids = [t['id'] for t in player['tanks']]
    
    if request.method == 'POST':
        tank_id = request.form.get('tank_id')
        use_gold = 'gold' in request.form
        
        tank = next((t for t in ALL_TANKS_LIST if t['id'] == tank_id), None)
        if not tank:
            flash('Танк не найден!')
            return redirect(url_for('shop'))
        
        if tank['id'] in owned_ids:
            flash('Танк уже куплен!')
            return redirect(url_for('shop'))
        
        price = tank['price']
        currency = player['gold'] if use_gold else player['silver']
        
        if currency < price:
            flash(f'Недостаточно { "золота 💰" if use_gold else "серебра 🪙" }!')
            return redirect(url_for('shop'))
        
        # Покупка
        player['tanks'].append(tank['id'])
        if use_gold:
            player['gold'] -= price
        else:
            player['silver'] -= price
        player['battles'] += 1  # Бонус за покупку
        
        update_player(player)
        flash(f'✅ Куплен {tank["name"]} за {price:,} { "золота 💰" if use_gold else "серебра 🪙" }!')
        return redirect(url_for('shop'))
    
    return render_template('shop.html', 
                         player=player, 
                         tanks=[t for t in ALL_TANKS_LIST if t['id'] not in owned_ids],
                         owned_ids=owned_ids)

# ========================================
# ✅ 1.9 БОИ И ТУРНИРЫ (ПРОСТЫЕ)
# ========================================
@app.route('/battle', methods=['POST'])
def battle():
    if not session.get('logged_in'):
        return jsonify({"error": "Не авторизован!"}), 401
    
    player = get_player(session.get('user_id'))
    if not player or not player['tanks']:
        return jsonify({"error": "Нет танков для боя!"}), 400
    
    enemy_tank = random.choice(player['tanks'])
    player_tank = random.choice(player['tanks'])
    
    # Простая боевая система
    player_hp = player_tank['hp']
    enemy_hp = enemy_tank['hp']
    
    while player_hp > 0 and enemy_hp > 0:
        # Урон игрока
        damage = random.randint(player_tank['damage']//2, player_tank['damage'])
        enemy_hp -= max(0, damage - random.randint(0, 50))  # Броня врага
        
        if enemy_hp <= 0:
            break
            
        # Урон врага
        damage = random.randint(enemy_tank['damage']//2, enemy_tank['damage'])
        player_hp -= max(0, damage - random.randint(0, 50))
    
    win = player_hp > 0
    reward_gold = random.randint(500, 2000) if win else random.randint(100, 500)
    reward_silver = random.randint(2000, 8000) if win else random.randint(500, 2000)
    reward_points = random.randint(300, 1000) if win else random.randint(50, 200)
    
    player['gold'] += reward_gold
    player['silver'] += reward_silver
    player['points'] += reward_points
    player['battles'] += 1
    if win:
        player['wins'] += 1
    
    update_player(player)
    
    return jsonify({
        "win": win,
        "reward_gold": reward_gold,
        "reward_silver": reward_silver,
        "reward_points": reward_points,
        "player_tank": player_tank['name'],
        "enemy_tank": enemy_tank['name']
    })
# ========================================
# ✅ 1.10 ЛИДЕРБОРДЫ И ПРОФИЛИ
# ========================================
@app.route('/leaderboard')
def leaderboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT user_id, points, wins, battles FROM leaderboards ORDER BY points DESC LIMIT 50')
    top_players = c.fetchall()
    conn.close()
    
    return render_template('leaderboard.html', top_players=top_players)

@app.route('/profile/<user_id>')
def profile(user_id):
    player = get_player(user_id)
    if not player:
        return "Игрок не найден!", 404
    
    rank_info = get_rank_progress(player['points'])
    owned_tanks = [t for t in ALL_TANKS_LIST if t['id'] in player['tanks']]
    
    return render_template('profile.html', 
                         player=player, 
                         rank_info=rank_info,
                         owned_tanks=owned_tanks)

# ========================================
# ✅ 1.11 АДМИН ПАНЕЛЬ
# ========================================
@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    username = session.get('username')
    if not is_admin(username):
        flash('Доступ запрещён!')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        target_user = request.form.get('target_user')
        
        if action == 'give_gold':
            amount = int(request.form.get('amount', 0))
            player = get_player(target_user)
            if player:
                player['gold'] += amount
                update_player(player)
                flash(f'✅ Выдано {amount:,} золота игроку {player["username"]}')
        
        elif action == 'mute':
            duration = float(request.form.get('duration', 0))  # часы
            player = get_player(target_user)
            if player:
                player['is_muted'] = True
                player['mute_until'] = time.time() + (duration * 3600)
                update_player(player)
                flash(f'✅ Игрок {player["username"]} замучен на {duration}ч')
    
    players = []
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT user_id, username, gold, points FROM players ORDER BY points DESC LIMIT 20')
    players = c.fetchall()
    conn.close()
    
    return render_template('admin.html', players=players)

# ========================================
# ✅ 1.12 ГЛАВНЫЕ РОУТЫ
# ========================================
@app.route('/')
def index():
    if session.get('logged_in'):
        player = get_player(session.get('user_id'))
        if player:
            rank_info = get_rank_progress(player['points'])
            return render_template('dashboard.html', player=player, rank_info=rank_info)
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if len(username) < 3:
            flash('Имя слишком короткое!')
            return render_template('register.html')
        
        if create_player(username, generate_user_id(username)):
            flash('✅ Регистрация успешна!')
            return redirect(url_for('login'))
        else:
            flash('Ошибка регистрации!')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']  # В реальности используй хеширование!
        
        user_id = generate_user_id(username)
        player = get_player(user_id)
        
        if player:  # Простая проверка (в продакшене используй bcrypt!)
            session['logged_in'] = True
            session['username'] = username
            session['user_id'] = user_id
            flash('✅ Вход выполнен!')
            return redirect(url_for('index'))
        else:
            flash('❌ Неверные данные!')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('👋 До свидания!')
    return redirect(url_for('index'))

# ========================================
# ✅ 1.13 УТИЛЬНЫЕ ФУНКЦИИ
# ========================================
def generate_user_id(username):
    return hashlib.md5(username.encode()).hexdigest()

@app.route('/daily')
def daily():
    if not session.get('logged_in'):
        return jsonify({"error": "Авторизуйтесь!"}), 401
    
    success, message = claim_daily(session.get('username'))
    return jsonify({"success": success, "message": message})

@app.errorhandler(404)
def not_found(error):
    return """
    <!DOCTYPE html>
    <html><head><title>404</title><style>body{font-family:Arial;background:#1a1a2e;color:white;text-align:center;padding:100px;}</style></head>
    <body><h1>❌ 404 - Страница не найдена</h1><a href="/" style="color:#667eea;">🏠 На главную</a></body></html>
    """, 404

# ========================================
# ✅ 1.14 ЗАПУСК СЕРВЕРА
# ========================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
