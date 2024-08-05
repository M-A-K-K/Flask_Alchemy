# app/routes/__init__.py

from flask import Blueprint

users_bp = Blueprint('users', __name__)
subjects_bp = Blueprint('subjects', __name__)

# Import routes at the end to avoid circular imports


def register_blueprints(app):
    app.register_blueprint(users_bp)
    app.register_blueprint(subjects_bp)
