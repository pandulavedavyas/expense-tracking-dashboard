import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'expense-tracker-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///{}'.format(
        os.path.join('/tmp', 'database.db')
        if os.environ.get('VERCEL')
        else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'database.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_SECURE = bool(os.environ.get('VERCEL'))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    REMEMBER_COOKIE_SECURE = bool(os.environ.get('VERCEL'))
    REMEMBER_COOKIE_HTTPONLY = True
