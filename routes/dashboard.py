from flask import Blueprint, render_template
from flask_login import login_required, current_user
from datetime import date
from models.transaction import Transaction
from services.calculations import (
    get_monthly_summary, get_yearly_summary,
    get_category_breakdown, get_financial_insights
)

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    today = date.today()
    currency = current_user.currency or '₹'
    return render_template('dashboard.html', today=today, currency=currency)
