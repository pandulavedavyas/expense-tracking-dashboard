from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import re
from models import db
from models.user import User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        errors = []
        if not name:
            errors.append('Name is required.')
        if not email:
            errors.append('Email is required.')
        elif not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            errors.append('Please enter a valid email address.')
        if not password:
            errors.append('Password is required.')
        elif len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        if password != confirm_password:
            errors.append('Passwords do not match.')
        if User.query.filter_by(email=email).first():
            errors.append('An account with this email already exists. Please login.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('register.html')

        user = User(
            name=name,
            email=email,
            password=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()

        flash('Account created successfully! Welcome, {}!'.format(name), 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember') in ('on', '1', 'true', 'yes')

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            resp = redirect(next_page or url_for('dashboard.index'))
            if remember:
                resp.set_cookie('remembered_email', email, max_age=30*24*60*60)
            else:
                resp.delete_cookie('remembered_email')
            flash('Welcome back, {}!'.format(user.name), 'success')
            return resp
        else:
            flash('Invalid email or password.', 'error')

    return render_template('login.html')


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    email = request.form.get('email', '').strip().lower()
    if not email:
        flash('Please enter your email address.', 'error')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(email=email).first()
    if user:
        flash('A password reset link has been sent to {}. (Demo: check your email client)'.format(email), 'success')
    else:
        flash('No account found with that email address.', 'error')

    return redirect(url_for('auth.login'))


@auth_bp.route('/api/check-email')
def check_email():
    email = request.args.get('email', '').strip().lower()
    exists = User.query.filter_by(email=email).first() is not None
    return jsonify({'exists': exists})


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    resp = redirect(url_for('auth.login'))
    resp.delete_cookie('remembered_email')
    return resp
