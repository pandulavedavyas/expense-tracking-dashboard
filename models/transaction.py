from datetime import datetime
from models import db


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' or 'expense'
    payment_method = db.Column(db.String(50), default='Cash')
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    description = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    CATEGORIES = [
        'Food', 'Shopping', 'Bills', 'Medical', 'Travel',
        'Fuel', 'Education', 'Investment', 'Salary',
        'Entertainment', 'Others'
    ]

    PAYMENT_METHODS = [
        'Cash', 'UPI', 'Credit Card', 'Debit Card', 'Net Banking', 'Wallet'
    ]

    def __repr__(self):
        return f'<Transaction {self.title} - {self.amount}>'
