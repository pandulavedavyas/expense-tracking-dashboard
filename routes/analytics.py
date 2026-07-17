import csv
import io
import json
from flask import Blueprint, render_template, request, jsonify, make_response, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import date
from models import db
from models.transaction import Transaction
from services.calculations import (
    get_monthly_summary, get_yearly_summary, get_category_breakdown,
    get_all_time_stats, get_financial_insights, get_payment_method_breakdown,
    get_daily_spending, get_weekly_spending, get_top_categories,
    get_highest_transaction, get_savings_rate, get_avg_daily_spending,
    get_avg_monthly_spending, get_budget_used_pct, get_transaction_count,
    calculate_budget_remaining, calculate_expense, calculate_income
)

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/analytics')
@login_required
def analytics():
    today = date.today()
    year = request.args.get('year', today.year, type=int)
    month = request.args.get('month', today.month, type=int)

    monthly = get_monthly_summary(current_user.id, year, month)
    yearly = get_yearly_summary(current_user.id, year)
    categories = get_category_breakdown(current_user.id, year, month)
    stats = get_all_time_stats(current_user.id)
    insights = get_financial_insights(current_user.id)
    payment_methods = get_payment_method_breakdown(current_user.id, year, month)
    daily = get_daily_spending(current_user.id, year, month)
    weekly = get_weekly_spending(current_user.id, year, month)
    top_cats = get_top_categories(current_user.id, year, month)
    highest_tx = get_highest_transaction(current_user.id, year, month)
    savings_rate = get_savings_rate(current_user.id, year, month)
    avg_daily = get_avg_daily_spending(current_user.id, year, month)
    avg_monthly = get_avg_monthly_spending(current_user.id, year)
    budget_used = get_budget_used_pct(current_user.id, year, month)
    budget_remaining = calculate_budget_remaining(current_user.id, year, month)
    tx_count = get_transaction_count(current_user.id, year, month)

    return render_template('analytics.html',
        monthly=monthly, yearly=yearly, categories=categories,
        stats=stats, insights=insights, payment_methods=payment_methods,
        daily_spending=daily, weekly_spending=weekly,
        top_categories=top_cats, highest_tx=highest_tx,
        savings_rate=savings_rate, avg_daily=avg_daily, avg_monthly=avg_monthly,
        budget_used=budget_used, budget_remaining=budget_remaining,
        tx_count=tx_count,
        selected_year=year, selected_month=month,
        current_year=today.year, currency=current_user.currency,
        monthly_budget=current_user.monthly_budget,
        savings_goal=current_user.savings_goal
    )


@analytics_bp.route('/reports')
@login_required
def reports():
    today = date.today()
    year = request.args.get('year', today.year, type=int)
    month = request.args.get('month', type=int)
    category = request.args.get('category', '')
    payment = request.args.get('payment', '')
    tx_type = request.args.get('type', '')
    report_type = request.args.get('report_type', 'yearly')

    query = Transaction.query.filter_by(user_id=current_user.id)

    if report_type == 'monthly' and month:
        query = query.filter(
            db.and_(Transaction.user_id == current_user.id,
                    db.extract('year', Transaction.date) == year,
                    db.extract('month', Transaction.date) == month)
        )
    elif report_type == 'yearly':
        query = query.filter(db.extract('year', Transaction.date) == year)

    if category:
        query = query.filter_by(category=category)
    if payment:
        query = query.filter_by(payment_method=payment)
    if tx_type:
        query = query.filter_by(type=tx_type)

    transactions = query.order_by(Transaction.date.desc()).all()

    total_income = sum(t.amount for t in transactions if t.type == 'income')
    total_expense = sum(t.amount for t in transactions if t.type == 'expense')
    amounts = [t.amount for t in transactions]

    yearly = get_yearly_summary(current_user.id, year)
    stats = get_all_time_stats(current_user.id)

    return render_template('reports.html',
        transactions=transactions, yearly=yearly, stats=stats,
        total_income=total_income, total_expense=total_expense,
        savings=total_income - total_expense,
        avg_transaction=round(sum(amounts) / len(amounts), 2) if amounts else 0,
        highest_expense=max(amounts, default=0),
        lowest_expense=min(amounts, default=0),
        tx_count=len(transactions),
        selected_year=year, selected_month=month,
        selected_category=category, selected_payment=payment,
        selected_type=tx_type, report_type=report_type,
        current_year=today.year, currency=current_user.currency,
        categories=Transaction.CATEGORIES, payment_methods=Transaction.PAYMENT_METHODS
    )


@analytics_bp.route('/reports/export/csv')
@login_required
def export_csv():
    from sqlalchemy import extract as sa_extract
    today = date.today()
    year = request.args.get('year', today.year, type=int)
    month = request.args.get('month', type=int)
    query = Transaction.query.filter_by(user_id=current_user.id)
    query = query.filter(sa_extract('year', Transaction.date) == year)
    if month:
        query = query.filter(sa_extract('month', Transaction.date) == month)
    transactions = query.order_by(Transaction.date.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Title', 'Category', 'Type', 'Amount', 'Payment Method', 'Description'])
    for t in transactions:
        writer.writerow([t.date.strftime('%Y-%m-%d'), t.title, t.category, t.type, t.amount, t.payment_method, t.description])
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=expense_report_{year}.csv'
    return response


@analytics_bp.route('/reports/export/pdf')
@login_required
def export_pdf():
    from fpdf import FPDF
    from sqlalchemy import extract as sa_extract
    today = date.today()
    year = request.args.get('year', today.year, type=int)
    month = request.args.get('month', type=int)
    query = Transaction.query.filter_by(user_id=current_user.id)
    query = query.filter(sa_extract('year', Transaction.date) == year)
    if month:
        query = query.filter(sa_extract('month', Transaction.date) == month)
    transactions = query.order_by(Transaction.date.desc()).all()
    total_income = sum(t.amount for t in transactions if t.type == 'income')
    total_expense = sum(t.amount for t in transactions if t.type == 'expense')

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 12, 'Expense Report', ln=True, align='C')
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 8, f'User: {current_user.name} | Date: {today.strftime("%d %B %Y")}', ln=True, align='C')
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(60, 8, f'Total Income:  Rs.{total_income:,.2f}')
    pdf.cell(60, 8, f'Total Expense: Rs.{total_expense:,.2f}')
    pdf.cell(60, 8, f'Savings:       Rs.{total_income - total_expense:,.2f}')
    pdf.ln(12)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_fill_color(230, 230, 230)
    for w, h in [(25, 'Date'), (50, 'Title'), (30, 'Category'), (20, 'Type'), (30, 'Amount'), (30, 'Payment')]:
        pdf.cell(w, 8, h, border=1, fill=True)
    pdf.ln()
    pdf.set_font('Helvetica', '', 9)
    for t in transactions:
        pdf.cell(25, 7, t.date.strftime('%Y-%m-%d'), border=1)
        pdf.cell(50, 7, t.title[:22], border=1)
        pdf.cell(30, 7, t.category, border=1)
        pdf.cell(20, 7, t.type.capitalize(), border=1)
        pdf.cell(30, 7, f'Rs.{t.amount:,.2f}', border=1)
        pdf.cell(30, 7, t.payment_method, border=1)
        pdf.ln()
    response = make_response(bytes(pdf.output()))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=expense_report_{year}.pdf'
    return response


@analytics_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        action = request.form.get('action', 'update')

        if action == 'reset':
            Transaction.query.filter_by(user_id=current_user.id).delete()
            current_user.monthly_budget = 0
            current_user.savings_goal = 0
            db.session.commit()
            flash('All data has been reset.', 'success')
            return redirect(url_for('analytics.settings'))

        name = request.form.get('name', '').strip()
        currency = request.form.get('currency', '₹')
        budget = request.form.get('monthly_budget', 0, type=float)
        savings_goal = request.form.get('savings_goal', 0, type=float)
        accent_color = request.form.get('accent_color', '#2563EB')
        font_size = request.form.get('font_size', 'medium')
        dark_mode = 'dark_mode' in request.form
        notif_budget = 'notif_budget' in request.form
        notif_monthly = 'notif_monthly' in request.form
        notif_daily = 'notif_daily' in request.form

        if name:
            current_user.name = name
        current_user.currency = currency
        current_user.monthly_budget = budget
        current_user.savings_goal = savings_goal
        current_user.accent_color = accent_color
        current_user.font_size = font_size
        current_user.dark_mode = dark_mode
        current_user.notif_budget = notif_budget
        current_user.notif_monthly = notif_monthly
        current_user.notif_daily = notif_daily
        current_user.profile_picture = request.form.get('profile_picture', '').strip()
        db.session.commit()
        flash('Settings updated successfully!', 'success')

    from datetime import datetime
    return render_template('settings.html', user=current_user, current_year=datetime.now().year)
