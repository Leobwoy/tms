# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
from flask_login import LoginManager
from flask_mail import Mail

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'tms.login'  # Redirect unauthorized users to login
mail = Mail()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    
    # Register the TMS module blueprint
    from app.tms.routes import tms_bp
    app.register_blueprint(tms_bp, url_prefix='/tms')

    # Register the Fleet module blueprint
    from app.fleet.routes import fleet_bp
    app.register_blueprint(fleet_bp, url_prefix='/fleet')

    return app

# User loader function for Flask-Login
from app.tms.models import User
@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
