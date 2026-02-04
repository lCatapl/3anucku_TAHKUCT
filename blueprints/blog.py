from flask import Blueprint, render_template
from models import Post

blog_bp = Blueprint('blog', __name__)

@blog_bp.route('/blog')
def blog():
    posts = Post.query.all()
    return render_template('blog/index.html', posts=posts)
