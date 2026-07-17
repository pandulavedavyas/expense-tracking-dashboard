from datetime import datetime, date, timedelta
from collections import defaultdict
from sqlalchemy import extract, and_, func
from models.transaction import Transaction


def _date_filter(user_id, year, month=None, tx_type=None):
    conditions = [Transaction.user_id == user_id, extract('year', Transaction.date) == year]
    if month:
        conditions.append(extract('month', Transaction.date) == month)
    if tx_type:
        conditions.append(Transaction.type == tx_type)
    return Transaction.query.filter(and_(*conditions)).all()


def calculate_income(user_id, year=None, month=None):
    if not year or not month:
        today = date.today()
        year, month = today.year, today.month
    return sum(t.amount for t in _date_filter(user_id, year, month, 'income'))


def calculate_expense(user_id, year=None, month=None):
    if not year or not month:
        today = date.today()
        year, month = today.year, today.month
    return sum(t.amount for t in _date_filter(user_id, year, month, 'expense'))


def calculate_balance(user_id, year=None, month=None):
    return calculate_income(user_id, year, month) - calculate_expense(user_id, year, month)


def get_monthly_summary(user_id, year=None, month=None):
    income = calculate_income(user_id, year, month)
    expense = calculate_expense(user_id, year, month)
    return {'total_income': income, 'total_expense': expense, 'savings': income - expense, 'balance': income - expense}


def calculate_monthly_expense(user_id, year=None):
    if not year:
        year = date.today().year
    return {datetime(year, m, 1).strftime('%b'): calculate_expense(user_id, year, m) for m in range(1, 13)}


def calculate_category_totals(user_id, year=None, month=None):
    if not year or not month:
        today = date.today()
        year, month = today.year, today.month
    txs = _date_filter(user_id, year, month, 'expense')
    cats = defaultdict(float)
    for t in txs:
        cats[t.category] += t.amount
    total = sum(cats.values()) if cats else 1
    return {'categories': dict(cats), 'percentages': {c: round((a / total) * 100, 1) for c, a in cats.items()}}


def get_daily_spending(user_id, year=None, month=None):
    if not year or not month:
        today = date.today()
        year, month = today.year, today.month
    txs = _date_filter(user_id, year, month, 'expense')
    daily = defaultdict(float)
    for t in txs:
        daily[t.date.day] += t.amount
    days_in_month = (date(year, month + 1, 1) - date(year, month, 1)).days if month < 12 else 31
    return {d: daily.get(d, 0) for d in range(1, days_in_month + 1)}


def get_weekly_spending(user_id, year=None, month=None):
    if not year or not month:
        today = date.today()
        year, month = today.year, today.month
    txs = _date_filter(user_id, year, month, 'expense')
    weekly = defaultdict(float)
    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    for t in txs:
        weekly[day_names[t.date.weekday()]] += t.amount
    return {d: weekly.get(d, 0) for d in day_names}


def get_top_categories(user_id, year=None, month=None, limit=5):
    cats = calculate_category_totals(user_id, year, month)['categories']
    sorted_cats = sorted(cats.items(), key=lambda x: x[1], reverse=True)[:limit]
    return [{'name': c, 'amount': a} for c, a in sorted_cats]


def get_highest_transaction(user_id, year=None, month=None):
    if not year or not month:
        today = date.today()
        year, month = today.year, today.month
    txs = _date_filter(user_id, year, month, 'expense')
    if not txs:
        return None
    top = max(txs, key=lambda t: t.amount)
    return {'title': top.title, 'amount': top.amount, 'category': top.category, 'date': top.date.strftime('%d %b %Y')}


def get_savings_rate(user_id, year=None, month=None):
    inc = calculate_income(user_id, year, month)
    sav = calculate_balance(user_id, year, month)
    return round((sav / inc) * 100, 1) if inc > 0 else 0


def get_avg_daily_spending(user_id, year=None, month=None):
    if not year or not month:
        today = date.today()
        year, month = today.year, today.month
    expense = calculate_expense(user_id, year, month)
    days_in_month = (date(year, month + 1, 1) - date(year, month, 1)).days if month < 12 else 31
    return round(expense / days_in_month, 2) if days_in_month > 0 else 0


def get_avg_monthly_spending(user_id, year=None):
    if not year:
        year = date.today().year
    total = sum(calculate_expense(user_id, year, m) for m in range(1, 13))
    active_months = sum(1 for m in range(1, 13) if calculate_expense(user_id, year, m) > 0)
    return round(total / active_months, 2) if active_months > 0 else 0


def calculate_budget_remaining(user_id, year=None, month=None):
    from models.user import User
    user = User.query.get(user_id)
    expense = calculate_expense(user_id, year, month)
    if user and user.monthly_budget > 0:
        return max(user.monthly_budget - expense, 0)
    return 0


def get_budget_used_pct(user_id, year=None, month=None):
    from models.user import User
    user = User.query.get(user_id)
    if not user or user.monthly_budget <= 0:
        return 0
    expense = calculate_expense(user_id, year, month)
    return min(round((expense / user.monthly_budget) * 100, 1), 100)


def get_transaction_count(user_id, year=None, month=None):
    if not year or not month:
        today = date.today()
        year, month = today.year, today.month
    return len(_date_filter(user_id, year, month))


def get_yearly_summary(user_id, year=None):
    if not year:
        year = date.today().year
    return [{'month': datetime(year, m, 1).strftime('%b'), 'income': calculate_income(user_id, year, m),
             'expense': calculate_expense(user_id, year, m), 'savings': calculate_balance(user_id, year, m)} for m in range(1, 13)]


def get_category_breakdown(user_id, year=None, month=None):
    return calculate_category_totals(user_id, year, month)


def get_payment_method_breakdown(user_id, year=None, month=None):
    if not year or not month:
        today = date.today()
        year, month = today.year, today.month
    txs = _date_filter(user_id, year, month)
    methods = defaultdict(float)
    for t in txs:
        methods[t.payment_method] += t.amount
    return dict(methods)


def get_financial_insights(user_id):
    today = date.today()
    cur = get_monthly_summary(user_id, today.year, today.month)
    prev = get_monthly_summary(user_id, today.year - 1, 12) if today.month == 1 else get_monthly_summary(user_id, today.year, today.month - 1)
    insights = []
    if prev['total_expense'] > 0:
        diff = cur['total_expense'] - prev['total_expense']
        pct = (diff / prev['total_expense']) * 100
        if diff > 0:
            insights.append(f"You spent Rs.{diff:,.0f} ({abs(pct):.0f}%) more than last month.")
        elif diff < 0:
            insights.append(f"You spent Rs.{abs(diff):,.0f} ({abs(pct):.0f}%) less than last month.")
    if cur['total_income'] > 0:
        rate = (cur['savings'] / cur['total_income']) * 100
        if rate > 20:
            insights.append(f"Excellent! You saved {rate:.0f}% of your income.")
        elif rate > 0:
            insights.append(f"You saved {rate:.0f}% of your income this month.")
        else:
            insights.append("You are spending more than you earn this month.")
    cat_data = get_category_breakdown(user_id, today.year, today.month)
    if cat_data['categories']:
        top = max(cat_data['categories'], key=cat_data['categories'].get)
        insights.append(f"{top} is your highest expense category.")
    if cur['savings'] > 0:
        insights.append(f"You saved Rs.{cur['savings']:,.0f} this month.")
    return insights


def get_all_time_stats(user_id):
    txs = Transaction.query.filter_by(user_id=user_id).all()
    total_income = sum(t.amount for t in txs if t.type == 'income')
    total_expense = sum(t.amount for t in txs if t.type == 'expense')
    expenses = [t for t in txs if t.type == 'expense']
    avg_expense = total_expense / len(expenses) if expenses else 0
    highest_expense = max((t.amount for t in expenses), default=0)
    most_used_category = 'N/A'
    highest_month = 'N/A'
    if expenses:
        cats = defaultdict(float)
        for t in expenses:
            cats[t.category] += t.amount
        most_used_category = max(cats, key=cats.get)
        monthly = defaultdict(float)
        for t in expenses:
            monthly[f'{t.date.year}-{t.date.month:02d}'] += t.amount
        if monthly:
            hm = max(monthly, key=monthly.get)
            y, m = hm.split('-')
            highest_month = datetime(int(y), int(m), 1).strftime('%B %Y')
    return {
        'total_income': total_income, 'total_expense': total_expense,
        'savings': total_income - total_expense, 'avg_expense': avg_expense,
        'highest_expense': highest_expense, 'highest_month': highest_month,
        'most_used_category': most_used_category, 'transaction_count': len(txs)
    }
