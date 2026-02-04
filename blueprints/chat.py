from flask import Blueprint, render_template
from flask_socketio import emit, join_room

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/chat')
def chat():
    return render_template('chat/index.html')

@chat_bp.record_once
def init_state(state):
    global socketio
    socketio = state.app.extensions['socketio']
