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
login.login_view = 'routes.login'  # Redirect unauthorized users to login
mail = Mail()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    
    from app.tms.routes import bp as routes_bp
    app.register_blueprint(routes_bp)
    
    return app

# User loader function for Flask-Login
from app.tms.models import User
@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
