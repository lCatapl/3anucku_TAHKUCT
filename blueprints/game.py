from flask import Blueprint, render_template

game_bp = Blueprint('game', __name__)

@game_bp.route('/arena')
def arena():
    return render_template('game.html')

@game_bp.route('/api/tanks')
def get_tanks():
    from models import Tank
    tanks = Tank.query.all()
    return {'tanks': [{'name': t.name, 'hp': t.hp} for t in tanks]}
