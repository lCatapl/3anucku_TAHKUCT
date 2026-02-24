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
    def get_player(user_id):
        if not user_id: return None
        try:
            conn = sqlite3.connect('players.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, silver, gold, role, tank_id FROM players WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                return {
                    'id': row[0], 'username': row[1], 'silver': row[2], 
                    'gold': row[3], 'role': row[4], 'tank_id': row[5]
                }
            return None
        except:
            return None

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
    if 'user_id' in session:
        player = get_player(session['user_id'])
        if player:
            return jsonify({
                'silver': player['silver'],
                'gold': player['gold'],
                'wins': player['wins'],
                'total_players': get_live_players(),
                'total_gold': get_live_gold()
            })
    return jsonify({'silver': 0, 'gold': 0, 'wins': 0, 'total_players': 42, 'total_gold': 10000})

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
    top_players = get_leaderboard()
    player = get_player(session.get('user_id')) if validate_session() else None
    player_rank = None
    if player:
        all_players = get_leaderboard(limit=100)
        player_rank = next((p for p in all_players if p['username'] == player['username']), None)
    return render_template('leaderboard.html', top_players=top_players, player_rank=player_rank)

@app.route('/api/leaderboard')
def api_leaderboard():
    """LIVE обновление лидерборда"""
    return jsonify(get_leaderboard())

# ========================================
# ✅ БАЗА ДАННЫХ - ИНИЦИАЛИЗАЦИЯ v9.9
# ========================================
def init_db():
    conn = sqlite3.connect('players.db')
    cursor = conn.cursor()
    
    # 1. Создаём структуру БД
    cursor.execute('''CREATE TABLE IF NOT EXISTS players (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        silver INTEGER DEFAULT 0,
        gold INTEGER DEFAULT 0,
        role TEXT DEFAULT 'player',
        wins INTEGER DEFAULT 0,
        battles INTEGER DEFAULT 0,
        tank_id TEXT DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 2. Проверяем/добавляем колонки
    cursor.execute("PRAGMA table_info(players)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'tank_id' not in columns:
        cursor.execute("ALTER TABLE players ADD COLUMN tank_id TEXT DEFAULT NULL")
    if 'wins' not in columns:
        cursor.execute("ALTER TABLE players ADD COLUMN wins INTEGER DEFAULT 0")
    if 'battles' not in columns:
        cursor.execute("ALTER TABLE players ADD COLUMN battles INTEGER DEFAULT 0")
    
    # 3. 🔥 СОЗДАЁМ АДМИНОВ (ВНУТРИ init_db!)
    admins = [
        {'id': 'admin0001', 'username': 'Админ', 'password': '120187', 'silver': 1000000},
        {'id': 'nazar_2026', 'username': 'Назар', 'password': '120187', 'silver': 1000000}
    ]
    
    for admin in admins:
        cursor.execute("SELECT id FROM players WHERE username = ?", (admin['username'],))
        if not cursor.fetchone():
            password_hash = bcrypt.hashpw(admin['password'].encode(), bcrypt.gensalt())
            cursor.execute("""
                INSERT INTO players (id, username, password, silver, gold, role, tank_id, wins, battles) 
                VALUES (?, ?, ?, ?, 10000, 'superadmin', 'ms1', 0, 0)
            """, (admin['id'], admin['username'], password_hash, admin['silver']))
    
    # 4. Стартовый танк всем новичкам
    cursor.execute("""
        UPDATE players SET silver = 50000, tank_id = 'ms1' 
        WHERE silver < 10000 AND role = 'player'
    """)
    
    # 5. garage.db + battles.db
    cursor.execute('''CREATE TABLE IF NOT EXISTS garage (
        id INTEGER PRIMARY KEY, player_id TEXT, tank_id TEXT, 
        bought_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS battles (
        id INTEGER PRIMARY KEY, player_id TEXT, opponent_type TEXT, 
        player_tier INTEGER, result TEXT, silver_reward INTEGER, battle_time TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()
    print("✅ БД готова! Назар/120187 + Админ/120187")

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
        
        conn = sqlite3.connect('players.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, password, role FROM players WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            stored_hash = row[1]  # Уже bytes!
            
            # ✅ ПРОВЕРЯЕМ БЕЗ .encode() если уже bytes
            try:
                if isinstance(stored_hash, bytes) and bcrypt.checkpw(password.encode(), stored_hash):
                    session['user_id'] = row[0]
                    session['role'] = row[2]
                    print(f"✅ LOGIN OK: {username}")
                    return redirect(url_for('profile'))
            except:
                pass
            
            # Fallback для строковых хэшей
            if isinstance(stored_hash, str):
                stored_hash = stored_hash.encode()
                if bcrypt.checkpw(password.encode(), stored_hash):
                    session['user_id'] = row[0]
                    session['role'] = row[2]
                    return redirect(url_for('profile'))
        
        print("LOGIN ERROR: неверный пароль")
        return render_template('login.html', error="Неверный логин/пароль")
    
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
    conn = sqlite3.connect('garage.db')
    cursor = conn.cursor()
    
    # ✅ ГАРАНТИРУЕМ MS-1 для новичков
    cursor.execute("SELECT COUNT(*) FROM garage WHERE player_id = ?", (player['id'],))
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO garage (player_id, tank_id) VALUES (?, 'ms1')", (player['id'],))
        conn.commit()
    
    cursor.execute("SELECT tank_id FROM garage WHERE player_id = ?", (player['id'],))
    player_tanks = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    return render_template('garage.html', player=player, player_tanks=player_tanks, tanks=TANKS)

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

@app.route('/profile')
@app.route('/profile/<user_id>')
def profile(user_id=None):
    if not validate_session():
        return redirect(url_for('login'))
    
    player = get_player(session['user_id'])
    return render_template('profile.html', player=player)

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

# ========================================
# ✅ ИНИЦИАЛИЗАЦИЯ
# ========================================
if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
else:
    init_db()


