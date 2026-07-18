import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'expense-tracker-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///{}'.format(
        os.path.join('/tmp', 'database.db')
        if os.environ.get('VERCEL')
        else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'database.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
