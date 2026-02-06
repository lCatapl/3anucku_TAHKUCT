from flask import Blueprint, render_template, request, jsonify
from models import db
from datetime import datetime

chat_bp = Blueprint('chat', __name__)

# Временная таблица сообщений
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20))
    content = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@chat_bp.route('/chat')
def chat():
    messages = Message.query.order_by(Message.timestamp.desc()).limit(50).all()
    return render_template('chat.html', messages=messages[::-1])

@chat_bp.route('/api/chat/send', methods=['POST'])
def send_message():
    data = request.json
    msg = Message(username=data.get('username', 'Гость'), content=data.get('message'))
    db.session.add(msg)
    db.session.commit()
    return jsonify({'status': 'ok'})

@chat_bp.route('/api/chat/messages')
def get_messages():
    messages = Message.query.order_by(Message.timestamp.desc()).limit(50).all()
    return jsonify([{
        'username': m.username, 
        'content': m.content, 
        'time': m.timestamp.strftime('%H:%M')
    } for m in messages[::-1]])
