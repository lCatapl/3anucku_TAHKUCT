from flask import Blueprint, render_template
from flask_socketio import emit

game_bp = Blueprint('game', __name__)

@game_bp.route('/arena')
def arena():
    return render_template('game/arena.html')

@game_bp.route('/api/tanks')
def get_tanks():
    from models import Tank
    return {'tanks': [{'id': t.id, 'name': t.name} for t in Tank.query.all()]}
