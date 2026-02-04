from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models import User

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/profile')
@login_required
def profile():
    user = User.query.get(current_user.id)
    return render_template('profile/index.html', user=user)
