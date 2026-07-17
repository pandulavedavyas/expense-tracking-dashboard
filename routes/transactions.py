import csv
import io
from datetime import datetime, date, timedelta
from sqlalchemy import extract, and_
from flask import Blueprint, render_template, request, jsonify, make_response
from flask_login import login_required, current_user
from models import db
from models.transaction import Transaction
from services.calculations import (
    get_monthly_summary, get_yearly_summary, get_category_breakdown,
    get_financial_insights, calculate_monthly_expense
)

transactions_bp = Blueprint('transactions', __name__)


def _tx_json(tx):
    return {
        'id': tx.id,
        'title': tx.title,
        'amount': tx.amount,
        'category': tx.category,
        'type': tx.type,
        'payment_method': tx.payment_method,
        'date': tx.date.strftime('%Y-%m-%d'),
        'date_display': tx.date.strftime('%d %b %Y'),
        'description': tx.description or ''
    }


def _dashboard_data(user_id, filter_type='this_month'):
    today = date.today()
    year, month = today.year, today.month

    if filter_type == 'last_month':
        if month == 1:
            year, month = year - 1, 12
        else:
            month -= 1
    elif filter_type == 'this_year':
        pass
    elif filter_type == 'custom':
        pass

    summary = get_monthly_summary(user_id, year, month)
    yearly = get_yearly_summary(user_id, today.year)
    categories = get_category_breakdown(user_id, year, month)
    insights = get_financial_insights(user_id)
    monthly_expense = calculate_monthly_expense(user_id, today.year)

    recent = Transaction.query.filter_by(user_id=user_id)\
        .order_by(Transaction.date.desc(), Transaction.created_at.desc()).limit(10).all()

    user = __import__('models.user', fromlist=['User']).User.query.get(user_id)
    budget_progress = 0
    if user and user.monthly_budget > 0:
        budget_progress = min((summary['total_expense'] / user.monthly_budget) * 100, 100)

    return {
        'summary': summary,
        'yearly': yearly,
        'categories': categories,
        'insights': insights,
        'monthly_expense': monthly_expense,
        'recent_transactions': [_tx_json(tx) for tx in recent],
        'budget_progress': budget_progress,
        'monthly_budget': user.monthly_budget if user else 0,
        'currency': user.currency if user else '₹'
    }


@transactions_bp.route('/transactions')
@login_required
def transactions_page():
    today = date.today()
    return render_template('transactions.html',
        categories=Transaction.CATEGORIES,
        payment_methods=Transaction.PAYMENT_METHODS,
        current_year=today.year,
        currency=current_user.currency
    )


@transactions_bp.route('/api/dashboard-data')
@login_required
def api_dashboard_data():
    filter_type = request.args.get('filter', 'this_month')
    data = _dashboard_data(current_user.id, filter_type)
    return jsonify(data)


@transactions_bp.route('/api/transactions')
@login_required
def api_transactions():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    tx_type = request.args.get('type', '')
    category = request.args.get('category', '')
    payment = request.args.get('payment', '')
    filter_range = request.args.get('filter', 'this_month')
    custom_start = request.args.get('start_date', '')
    custom_end = request.args.get('end_date', '')
    sort = request.args.get('sort', 'date_desc')

    today = date.today()
    query = Transaction.query.filter_by(user_id=current_user.id)

    if filter_range == 'this_month':
        query = query.filter(
            extract('year', Transaction.date) == today.year,
            extract('month', Transaction.date) == today.month
        )
    elif filter_range == 'last_month':
        if today.month == 1:
            query = query.filter(extract('year', Transaction.date) == today.year - 1, extract('month', Transaction.date) == 12)
        else:
            query = query.filter(extract('year', Transaction.date) == today.year, extract('month', Transaction.date) == today.month - 1)
    elif filter_range == 'this_year':
        query = query.filter(extract('year', Transaction.date) == today.year)
    elif filter_range == 'custom' and custom_start and custom_end:
        start = datetime.strptime(custom_start, '%Y-%m-%d').date()
        end = datetime.strptime(custom_end, '%Y-%m-%d').date()
        query = query.filter(Transaction.date >= start, Transaction.date <= end)

    if category:
        query = query.filter_by(category=category)
    if tx_type:
        query = query.filter_by(type=tx_type)
    if payment:
        query = query.filter_by(payment_method=payment)
    if search:
        query = query.filter(
            db.or_(
                Transaction.title.ilike(f'%{search}%'),
                Transaction.description.ilike(f'%{search}%'),
                Transaction.category.ilike(f'%{search}%')
            )
        )

    if sort == 'date_asc':
        query = query.order_by(Transaction.date.asc())
    elif sort == 'amount_desc':
        query = query.order_by(Transaction.amount.desc())
    elif sort == 'amount_asc':
        query = query.order_by(Transaction.amount.asc())
    else:
        query = query.order_by(Transaction.date.desc())

    per_page = 15
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    total_income = sum(t.amount for t in pagination.items if t.type == 'income')
    total_expense = sum(t.amount for t in pagination.items if t.type == 'expense')

    return jsonify({
        'transactions': [_tx_json(tx) for tx in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': pagination.page,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev,
        'page_total_income': total_income,
        'page_total_expense': total_expense
    })


@transactions_bp.route('/api/transactions', methods=['POST'])
@login_required
def api_add_transaction():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    title = data.get('title', '').strip()
    amount = data.get('amount', 0)
    category = data.get('category', '')
    tx_type = data.get('type', '')
    payment_method = data.get('payment_method', 'Cash')
    date_str = data.get('date', '')
    description = data.get('description', '').strip()

    if not title or not amount or not category or not tx_type or not date_str:
        return jsonify({'error': 'All required fields must be filled'}), 400

    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid amount'}), 400

    if amount <= 0:
        return jsonify({'error': 'Amount must be positive'}), 400

    try:
        tx_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

    transaction = Transaction(
        user_id=current_user.id,
        title=title,
        amount=amount,
        category=category,
        type=tx_type,
        payment_method=payment_method,
        date=tx_date,
        description=description
    )
    db.session.add(transaction)
    db.session.commit()

    dash = _dashboard_data(current_user.id)
    return jsonify({
        'success': True,
        'message': f'{tx_type.capitalize()} of ₹{amount:,.2f} added!',
        'transaction': _tx_json(transaction),
        'dashboard': dash
    })


@transactions_bp.route('/api/transactions/<int:tx_id>', methods=['PUT'])
@login_required
def api_edit_transaction(tx_id):
    transaction = Transaction.query.filter_by(id=tx_id, user_id=current_user.id).first()
    if not transaction:
        return jsonify({'error': 'Transaction not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    transaction.title = data.get('title', transaction.title).strip()
    try:
        transaction.amount = float(data.get('amount', transaction.amount))
    except (ValueError, TypeError):
        pass
    transaction.category = data.get('category', transaction.category)
    transaction.type = data.get('type', transaction.type)
    transaction.payment_method = data.get('payment_method', transaction.payment_method)
    if data.get('date'):
        try:
            transaction.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        except ValueError:
            pass
    transaction.description = data.get('description', transaction.description).strip()

    db.session.commit()

    dash = _dashboard_data(current_user.id)
    return jsonify({
        'success': True,
        'message': 'Transaction updated!',
        'transaction': _tx_json(transaction),
        'dashboard': dash
    })


@transactions_bp.route('/api/transactions/<int:tx_id>', methods=['DELETE'])
@login_required
def api_delete_transaction(tx_id):
    transaction = Transaction.query.filter_by(id=tx_id, user_id=current_user.id).first()
    if not transaction:
        return jsonify({'error': 'Transaction not found'}), 404

    db.session.delete(transaction)
    db.session.commit()

    dash = _dashboard_data(current_user.id)
    return jsonify({
        'success': True,
        'message': 'Transaction deleted!',
        'dashboard': dash
    })


@transactions_bp.route('/reports/export/csv')
@login_required
def export_csv():
    filter_range = request.args.get('filter', 'this_year')
    today = date.today()
    query = Transaction.query.filter_by(user_id=current_user.id)

    if filter_range == 'this_month':
        query = query.filter(extract('year', Transaction.date) == today.year, extract('month', Transaction.date) == today.month)
    elif filter_range == 'last_month':
        m = today.month - 1 if today.month > 1 else 12
        y = today.year if today.month > 1 else today.year - 1
        query = query.filter(extract('year', Transaction.date) == y, extract('month', Transaction.date) == m)
    elif filter_range == 'this_year':
        query = query.filter(extract('year', Transaction.date) == today.year)

    transactions = query.order_by(Transaction.date.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Title', 'Category', 'Type', 'Amount', 'Payment Method', 'Description'])
    for t in transactions:
        writer.writerow([
            t.date.strftime('%Y-%m-%d'), t.title, t.category, t.type,
            t.amount, t.payment_method, t.description
        ])

    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=expense_report_{today.strftime("%Y_%m")}.csv'
    return response


@transactions_bp.route('/reports/export/pdf')
@login_required
def export_pdf():
    from fpdf import FPDF
    filter_range = request.args.get('filter', 'this_year')
    today = date.today()
    query = Transaction.query.filter_by(user_id=current_user.id)

    if filter_range == 'this_month':
        query = query.filter(extract('year', Transaction.date) == today.year, extract('month', Transaction.date) == today.month)
    elif filter_range == 'last_month':
        m = today.month - 1 if today.month > 1 else 12
        y = today.year if today.month > 1 else today.year - 1
        query = query.filter(extract('year', Transaction.date) == y, extract('month', Transaction.date) == m)
    elif filter_range == 'this_year':
        query = query.filter(extract('year', Transaction.date) == today.year)

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
    pdf.cell(25, 8, 'Date', border=1, fill=True)
    pdf.cell(50, 8, 'Title', border=1, fill=True)
    pdf.cell(30, 8, 'Category', border=1, fill=True)
    pdf.cell(20, 8, 'Type', border=1, fill=True)
    pdf.cell(30, 8, 'Amount', border=1, fill=True)
    pdf.cell(30, 8, 'Payment', border=1, fill=True)
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
    response.headers['Content-Disposition'] = f'attachment; filename=expense_report_{today.strftime("%Y_%m")}.pdf'
    return response
