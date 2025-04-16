# app/models.py
from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class User(UserMixin, db.Model):
    __tablename__= "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True, nullable=False)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(64), default='user')  # "admin" for admin users, "user" otherwise

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'
    
class Carrier(db.Model):
    __tablename__= "carriers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    cost_factor = db.Column(db.Float, default=1.0)  # Lower is better for optimization

    def __repr__(self):
        return f'<Carrier {self.name}>'

class Shipment(db.Model):
    __tablename__= "shipments"
    id = db.Column(db.Integer, primary_key=True)
    origin = db.Column(db.String(128))
    destination = db.Column(db.String(128))
    weight = db.Column(db.Float)
    carrier_id = db.Column(db.Integer, db.ForeignKey('carrier.id'))
    status = db.Column(db.String(64), default='Pending')  # New field for shipment status
    
    def __repr__(self):
        return f'<Shipment {self.id} from {self.origin} to {self.destination}>'

class ActivityLog(db.Model):
    __tablename__= "activity_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Who performed the action
    action = db.Column(db.String(64))   # e.g., 'create', 'update', 'delete'
    model = db.Column(db.String(64))    # e.g., 'Shipment', 'Carrier'
    model_id = db.Column(db.Integer)    # The id of the affected record
    description = db.Column(db.String(256))  # Additional details
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ActivityLog {self.id} {self.action} on {self.model} {self.model_id}>'