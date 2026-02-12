from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import json, sqlite3, hashlib, time, os, random, threading
from datetime import datetime, timedelta
from collections import defaultdict
import bcrypt
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import Length, Regexp, EqualTo, DataRequired
from flask_wtf.csrf import CSRFProtect
import secrets

app = Flask(__name__)
app.secret_key = 'tankist_v9.6_super_secret_key_2026'

WTF_CSRF_ENABLED = False  # ← ГЛАВНЫЙ ФИКС
app.config['WTF_CSRF_ENABLED'] = False

# ✅ ГЛОБАЛЬНЫЕ КОНСТАНТЫ v9.6
PLAYERS_EQUAL = True
ADMIN_LOGINS = ["Назар", "CatNap"]
MODERATORS = set()
MUTED_PLAYERS_TIME = {}
chat_messages = []
DB_PATH = 'tankist.db'

# ========================================
# 🔥 АДМИНЫ С ПРАВАМИ БОГА
# ========================================
ADMIN_USERS = {
    "Назар": {"user_id": "admin_nazar_2026", "role": "superadmin", "permissions": ["all"]},
    "CatNap": {"user_id": "admin_catnap_2026", "role": "superadmin", "permissions": ["all"]},
}

def is_superadmin(username):
    return username in ["Назар", "CatNap"]

def has_permission(username, permission):
    player = get_player(session.get('user_id')) if session.get('user_id') else None
    if player and player.get('username') in ADMIN_USERS:
        perms = ADMIN_USERS[player['username']].get('permissions', [])
        return "all" in perms or permission in perms
    return False

# Глобальная проверка сессии
def validate_session(admin_required=False):
    if not session.get('logged_in') or not session.get('user_id'):
        return False
    player = get_player(session['user_id'])
    if not player or player.get('username') != session.get('username'):
        session.clear()
        return False
    # Проверка токена
    if player.get('session_token') != session.get('session_token'):
        session.clear()
        return False
    if admin_required and not is_superadmin(player.get('username', '')):
        return False
    return True

# ========================================
# ✅ 1.1 ПОЛНЫЙ СПИСОК 60+ ТАНКОВ v9.4
# ========================================
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

ALL_TANKS_LIST = list(TANKS.values())

# ========================================
# ✅ 1.2 25 ЗВАНИЙ v9.3 - ПОЛНЫЙ СПИСОК (ПРОДОЛЖЕНИЕ)
# ========================================
RANKS_FULL = [
    # 🔥 НОВИЧКИ (0-4 ранг)
    {
        "id": 0, 
        "name": "Новобранец", 
        "icon": "👶", 
        "color": "#cccccc",
        "min_points": 0
    },
    {
        "id": 1, 
        "name": "Рядовой", 
        "icon": "🪖", 
        "color": "#aaaaaa",
        "min_points": 250
    },
    {
        "id": 2, 
        "name": "Рядовой 1-й статьи", 
        "icon": "🪖", 
        "color": "#999999",
        "min_points": 750
    },
    {
        "id": 3, 
        "name": "Ефрейтор", 
        "icon": "⭐", 
        "color": "#88aa88",
        "min_points": 1500
    },
    {
        "id": 4, 
        "name": "Младший сержант", 
        "icon": "⭐⭐", 
        "color": "#88aa88",
        "min_points": 3000
    },
    
    # 🛡️ СЕРЖАНТЫ (5-7 ранг)
    {
        "id": 5, 
        "name": "Сержант", 
        "icon": "⭐⭐⭐", 
        "color": "#88cc88",
        "min_points": 5500
    },
    {
        "id": 6, 
        "name": "Старший сержант", 
        "icon": "⭐⭐⭐⭐", 
        "color": "#88cc88",
        "min_points": 9000
    },
    {
        "id": 7, 
        "name": "Старшина", 
        "icon": "⭐⭐⭐⭐⭐", 
        "color": "#aadd88",
        "min_points": 14000
    },
    
    # ⚔️ ОФИЦЕРЫ (8-14 ранг)
    {
        "id": 8, 
        "name": "Мл. лейтенант", 
        "icon": "⚔️", 
        "color": "#ffcc00",
        "min_points": 20000
    },
    {
        "id": 9, 
        "name": "Лейтенант", 
        "icon": "⚔️", 
        "color": "#ffcc00",
        "min_points": 28000
    },
    {
        "id": 10, 
        "name": "Ст. лейтенант", 
        "icon": "⚔️⚔️", 
        "color": "#ffaa00",
        "min_points": 38000
    },
    {
        "id": 11, 
        "name": "Капитан", 
        "icon": "⚔️⚔️⚔️", 
        "color": "#ffaa00",
        "min_points": 50000
    },
    {
        "id": 12, 
        "name": "Майор", 
        "icon": "🌟", 
        "color": "#ff8800",
        "min_points": 65000
    },
    {
        "id": 13, 
        "name": "Подполковник", 
        "icon": "🌟🌟", 
        "color": "#ff8800",
        "min_points": 85000
    },
    {
        "id": 14, 
        "name": "Полковник", 
        "icon": "🌟🌟🌟", 
        "color": "#ff6600",
        "min_points": 110000
    },
    
    # 🏆 ГЕНЕРАЛЫ (15-19 ранг)
    {
        "id": 15, 
        "name": "Бригадный генерал", 
        "icon": "👑", 
        "color": "#ff4400",
        "min_points": 140000
    },
    {
        "id": 16, 
        "name": "Генерал-майор", 
        "icon": "👑👑", 
        "color": "#ff2200",
        "min_points": 180000
    },
    {
        "id": 17, 
        "name": "Генерал-лейтенант", 
        "icon": "👑👑👑", 
        "color": "#dd0000",
        "min_points": 230000
    },
    {
        "id": 18, 
        "name": "Генерал", 
        "icon": "🔥", 
        "color": "#cc0000",
        "min_points": 290000
    },
    {
        "id": 19, 
        "name": "Маршал", 
        "icon": "💎", 
        "color": "#aa0000",
        "min_points": 370000
    },
    
    # 🔥 ЛЕГЕНДЫ (20-23 ранг)
    {
        "id": 20, 
        "name": "Боевой Маршал", 
        "icon": "⚡", 
        "color": "#880000",
        "min_points": 470000
    },
    {
        "id": 21, 
        "name": "Полевой Маршал", 
        "icon": "🌌", 
        "color": "#660000",
        "min_points": 600000
    },
    {
        "id": 22, 
        "name": "Легенда Танков", 
        "icon": "⭐🌟⭐", 
        "color": "#440000",
        "min_points": 760000
    },
    {
        "id": 23, 
        "name": "Ветеран", 
        "icon": "🏆", 
        "color": "#ff0000",
        "min_points": 970000
    }
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
        "current": "👶 Новобранец",
        "current_id": 0,
        "color": "#cccccc",
        "progress": 0,
        "points": points,
        "next": "🪖 Рядовой",
        "next_points": 250,
        "rank_emoji": "👶"
    }
    
# ========================================
# ✅ 1.4 БАЗА ДАННЫХ И ИГРОКИ
# ========================================
def init_db():
    conn = sqlite3.connect('players.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT,
            gold INTEGER DEFAULT 5000,
            silver INTEGER DEFAULT 100000,
            points INTEGER DEFAULT 0,
            tanks TEXT DEFAULT '[]',
            battles INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            created_at TEXT,
            role TEXT DEFAULT 'player'
        )
    ''')
    conn.commit()
    conn.close()

# Вызвать при запуске
init_db()

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

@app.route('/garage')
def garage():
    player = get_player(session['user_id'])
    owned_tanks = [t for t in ALL_TANKS_LIST if t['id'] in player.get('tanks', [])]
    return render_template('garage.html', player=player, owned_tanks=owned_tanks)

# ========================================
# ✅ 1.8 МАГАЗИН ТАНКОВ
# ========================================
@app.route('/shop', methods=['GET', 'POST'])
def shop():
    if not validate_session():
        return redirect(url_for('login'))
    
    player = get_player(session['user_id'])
    owned_ids = set(t for t in player.get('tanks', []))
    
    # Фильтры
    nation_filter = request.args.get('nation', 'all')
    tier_filter = request.args.get('tier', 'all')
    type_filter = request.args.get('type', 'all')
    
    filtered_tanks = ALL_TANKS_LIST
    if nation_filter != 'all':
        filtered_tanks = [t for t in filtered_tanks if t['nation'] == nation_filter]
    if tier_filter != 'all':
        filtered_tanks = [t for t in filtered_tanks if t['tier'] == int(tier_filter)]
    if type_filter != 'all':
        filtered_tanks = [t for t in filtered_tanks if t['type'] == type_filter]
    
    if request.method == 'POST':
        tank_id = request.form.get('tank_id')
        payment = request.form.get('payment_method', 'silver')
        
        tank = next((t for t in ALL_TANKS_LIST if t['id'] == tank_id), None)
        if tank and tank['id'] not in owned_ids:
            price = tank['price']
            balance = player['gold'] if payment == 'gold' else player['silver']
            
            if balance >= price:
                player['tanks'].append(tank['id'])
                if payment == 'gold':
                    player['gold'] -= price
                else:
                    player['silver'] -= price
                player['purchases'] = player.get('purchases', 0) + 1
                update_player(player)
                
                # Админ лог
                if is_superadmin(player['username']):
                    log_admin_action(player['username'], f"Купил {tank['name']}")
                
                flash(f'✅ Куплен {tank["name"]} за {price:,} {payment}!')
                return redirect(url_for('shop', nation=nation_filter, tier=tier_filter, type=type_filter))
        
        flash('❌ Недостаточно средств или танк уже куплен!')
        return redirect(url_for('shop'))
    
    return render_template('shop.html', 
                         player=player, 
                         tanks=filtered_tanks,
                         owned_ids=owned_ids,
                         filters={'nation': nation_filter, 'tier': tier_filter, 'type': type_filter})

# ========================================
# ✅ 1.9 БОИ И ТУРНИРЫ (ПРОСТЫЕ)
# ========================================
@app.route('/battle', methods=['POST'])
def battle():
    if not validate_session():
        return jsonify({'error': 'Unauthorized!'}), 401
    
    player = get_player(session['user_id'])
    if not player.get('tanks'):
        return jsonify({'error': 'Нет танков для боя!'}), 400
    
    # Выбор танков
    player_tank_id = request.json.get('tank_id') or random.choice(player['tanks'])
    player_tank = next(t for t in ALL_TANKS_LIST if t['id'] == player_tank_id)
    enemy_tank = random.choice(ALL_TANKS_LIST)
    
    # Симуляция боя (15 раундов макс)
    player_hp, enemy_hp = player_tank['hp'], enemy_tank['hp']
    battle_log = []
    
    for round_num in range(15):
        if player_hp <= 0 or enemy_hp <= 0:
            break
        
        # Атака игрока (учет пробития)
        penetration_chance = player_tank['pen'] / enemy_tank['hp'] * 100
        if random.randint(1, 100) <= penetration_chance:
            damage = random.randint(player_tank['damage']//2, player_tank['damage'])
            enemy_hp = max(0, enemy_hp - damage)
            battle_log.append(f"💥 {damage} урона врагу!")
        else:
            battle_log.append("🛡️ Рикошет!")
        
        if enemy_hp <= 0:
            break
        
        # Контратака врага
        enemy_penetration = enemy_tank['pen'] / player_tank['hp'] * 100
        if random.randint(1, 100) <= enemy_penetration:
            damage = random.randint(enemy_tank['damage']//2, enemy_tank['damage'])
            player_hp = max(0, player_hp - damage)
            battle_log.append(f"💥 Враг нанес {damage} урона!")
        else:
            battle_log.append("🛡️ Ваш рикошет!")
    
    # Награды
    win = player_hp > 0
    tier_diff = player_tank['tier'] - enemy_tank['tier']
    multiplier = max(1.0, 1 + tier_diff * 0.2)
    
    rewards = {
        'gold': int(random.randint(800, 2500) * multiplier) if win else random.randint(150, 600),
        'silver': int(random.randint(4000, 12000) * multiplier) if win else random.randint(800, 2500),
        'points': int(random.randint(400, 1200) * multiplier) if win else random.randint(80, 250)
    }
    
    # Обновление статистики
    player['gold'] += rewards['gold']
    player['silver'] += rewards['silver']
    player['points'] += rewards['points']
    player['battles'] += 1
    if win:
        player['wins'] += 1
    
    update_player(player)
    
    return jsonify({
        'win': win,
        'player_tank': player_tank['name'],
        'enemy_tank': enemy_tank['name'],
        'player_hp_left': max(0, player_hp),
        'enemy_hp_left': max(0, enemy_hp),
        'rewards': rewards,
        'battle_log': battle_log[-8:],
        'winrate': round(player['wins']/player['battles']*100, 1) if player['battles'] else 0
    })

# ========================================
# ✅ 1.10 ЛИДЕРБОРДЫ И ПРОФИЛИ
# ========================================
@app.route('/leaderboard')
def leaderboard():
    conn = sqlite3.connect('players.db')
    cursor = conn.cursor()
    cursor.execute("SELECT username, points, wins, battles FROM players ORDER BY points DESC LIMIT 50")
    top_players = cursor.fetchall()
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
    if not validate_session(admin_required=True):
        flash('🚫 Доступ только для Назар & CatNap!')
        return redirect(url_for('index'))
    
    player = get_player(session['user_id'])
    action = request.form.get('action') if request.method == 'POST' else None
    
    if action == 'give_gold':
        target = request.form.get('target_username')
        amount = int(request.form.get('amount', 0))
        target_player = get_player(generate_user_id(target))
        if target_player:
            target_player['gold'] += amount
            update_player(target_player)
            log_admin_action(player['username'], f"Выдал {amount} золота {target}")
            flash(f'✅ {amount} золота выдано {target}!')
    
    elif action == 'mute':
        target = request.form.get('target_username')
        duration = float(request.form.get('duration', 0))  # часы
        target_player = get_player(generate_user_id(target))
        if target_player:
            target_player['is_muted'] = True
            target_player['mute_until'] = time.time() + (duration * 3600)
            update_player(target_player)
            flash(f'✅ {target} замучен на {duration}ч!')
    
    elif action == 'reset_stats':
        target = request.form.get('target_username')
        target_player = get_player(generate_user_id(target))
        if target_player:
            target_player.update({
                'gold': 5000, 'silver': 25000, 'points': 0,
                'wins': 0, 'battles': 0, 'tanks': []
            })
            update_player(target_player)
            flash(f'✅ Статистика {target} сброшена!')
    
    # Статистика сервера
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*), SUM(points), AVG(points) FROM players')
    server_stats = c.fetchone()
    c.execute('SELECT username, gold, points FROM players ORDER BY points DESC LIMIT 10')
    top_players = c.fetchall()
    conn.close()
    
    return render_template('admin.html', 
                         player=player,
                         server_stats=server_stats,
                         top_players=top_players)

# ========================================
# ✅ 1.12 ГЛАВНЫЕ РОУТЫ
# ========================================
@app.route('/')
def index():
    if not validate_session():
        return redirect(url_for('login'))
    
    player = get_player(session['user_id'])
    return render_template('index.html', player=player)

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo
import sqlite3
from datetime import datetime, timedelta

class RegisterForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired(), Length(min=3, max=20)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Зарегистрироваться')

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = ""
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if len(username) < 3 or len(password) < 6:
            error = "Логин ≥3, пароль ≥6 символов!"
        else:
            try:
                import sqlite3, bcrypt, hashlib
                from datetime import datetime
                
                conn = sqlite3.connect('players.db')
                cursor = conn.cursor()
                
                cursor.execute("SELECT id FROM players WHERE username=?", (username,))
                if cursor.fetchone():
                    error = "❌ Логин занят!"
                else:
                    user_id = hashlib.md5(username.encode()).hexdigest()[:8]
                    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
                    
                    cursor.execute("""
                        INSERT INTO players (id, username, password, gold, silver, created_at, role) 
                        VALUES (?, ?, ?, 5000, 100000, ?, 'player')
                    """, (user_id, username, hashed_pw, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                    
                    conn.commit()
                    conn.close()
                    return redirect(url_for('login'))
                
                conn.close()
            except Exception as e:
                error = f"Ошибка: {str(e)}"
    
    return render_template('register.html', error=error)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ""
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        try:
            import sqlite3, bcrypt
            conn = sqlite3.connect('players.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, password FROM players WHERE username=?", (username,))
            player = cursor.fetchone()
            conn.close()
            
            if player and bcrypt.checkpw(password.encode(), player[1].encode()):
                session['user_id'] = player[0]
                session['username'] = username
                return redirect(url_for('index'))  # или 'shop'
            else:
                error = "❌ Неверный логин/пароль!"
                
        except:
            error = "❌ Ошибка сервера!"
    
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    # Очистка всех попыток входа
    for key in list(session.keys()):
        if key.startswith('login_attempts_'):
            session.pop(key, None)
    flash('👋 До свидания!')
    return redirect(url_for('index'))

# ========================================
# ✅ 1.13 УТИЛЬНЫЕ ФУНКЦИИ
# ========================================
def generate_user_id(username):
    return hashlib.md5(username.encode()).hexdigest()

@app.route('/daily', methods=['GET'])
def daily():
    if not validate_session():
        return jsonify({'error': 'Авторизация!'}), 401
    
    player = get_player(session['user_id'])
    now = time.time()
    
    if now - player.get('last_daily', 0) < 86400:
        return jsonify({'error': '⏰ Только раз в сутки!'})
    
    streak = player.get('daily_streak', 0) + 1
    if streak > 7: streak = 1
    
    rewards = DAILY_REWARDS[str(streak)]
    player.update({
        'gold': player['gold'] + rewards['gold'],
        'silver': player['silver'] + rewards['silver'],
        'points': player['points'] + rewards['points'],
        'daily_streak': streak,
        'last_daily': now
    })
    
    if streak == 7:
        bonus_tank = random.choice([t for t in ALL_TANKS_LIST if t['tier'] <= 5])
        player['tanks'].append(bonus_tank['id'])
        rewards['bonus_tank'] = bonus_tank['name']
    
    update_player(player)
    return jsonify({'success': True, 'rewards': rewards, 'streak': streak})

@app.route('/api/stats')
def api_stats():
    if not validate_session():
        return jsonify({'error': 'Unauthorized'}), 401
    player = get_player(session['user_id'])
    return jsonify(player)

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
    init_db()  # Обязательно!
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)











