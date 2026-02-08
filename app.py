from flask import Flask, render_template, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(80), unique=True)
    rank = db.Column(db.Integer, default=1)  # 25 званий
    tank_id = db.Column(db.Integer)

# Роуты: лобби, бой, турниры
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/battle')
def battle():
    return render_template('battle.html')

@app.route('/api/tanks')
def get_tanks():
    return jsonify({'tanks': ['T-34', 'Tiger', 'IS-2'][:60]})  # 60+ танков

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
