# app/__init__.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import logging

# Initialize Flask extensions
db = SQLAlchemy()
ma = Marshmallow()

# Set up logging
logger = logging.getLogger(__name__)

# Configuration class
class Config:
    SQLALCHEMY_DATABASE_URI = 'mysql://root:@localhost/alchemy'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'kabirhere'

# Function to create the Flask application
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions with the app context
    db.init_app(app)
    ma.init_app(app)

    # Register blueprints
    from app.routes import users_bp, subjects_bp  # Import blueprints
    app.register_blueprint(users_bp)
    app.register_blueprint(subjects_bp)

    return app
