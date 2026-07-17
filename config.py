import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'expense-tracker-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
