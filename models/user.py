from datetime import datetime
from flask_login import UserMixin
from models import db


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    currency = db.Column(db.String(10), default='₹')
    monthly_budget = db.Column(db.Float, default=0.0)
    savings_goal = db.Column(db.Float, default=0.0)
    dark_mode = db.Column(db.Boolean, default=False)
    accent_color = db.Column(db.String(20), default='#2563EB')
    font_size = db.Column(db.String(20), default='medium')
    notif_budget = db.Column(db.Boolean, default=True)
    notif_monthly = db.Column(db.Boolean, default=True)
    notif_daily = db.Column(db.Boolean, default=False)
    profile_picture = db.Column(db.String(500), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    transactions = db.relationship('Transaction', backref='user', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.email}>'
