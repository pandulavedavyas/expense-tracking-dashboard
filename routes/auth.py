import os
import re
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth
from models import db
from models.user import User

auth_bp = Blueprint('auth', __name__)
oauth = OAuth(app=None)

oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID', ''),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET', ''),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)


def _init_oauth(app):
    oauth.init_app(app)


def _is_phone(value):
    return bool(re.match(r'^[\d\+\-\s\(\)]{7,20}$', value))


def _find_user(identifier):
    if _is_phone(identifier):
        return User.query.filter_by(phone=identifier).first()
    return User.query.filter_by(email=identifier.lower().strip()).first()


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        errors = []
        if not name:
            errors.append('Name is required.')
        if not email and not phone:
            errors.append('Either email or phone number is required.')
        if email and not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            errors.append('Please enter a valid email address.')
        if phone and not _is_phone(phone):
            errors.append('Please enter a valid phone number.')
        if not password:
            errors.append('Password is required.')
        elif len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        if password != confirm_password:
            errors.append('Passwords do not match.')
        if email and User.query.filter_by(email=email).first():
            errors.append('An account with this email already exists.')
        if phone and User.query.filter_by(phone=phone).first():
            errors.append('An account with this phone number already exists.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('register.html')

        user = User(
            name=name,
            email=email if email else None,
            phone=phone if phone else None,
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
        identifier = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        user = _find_user(identifier)

        if user and user.password and check_password_hash(user.password, password):
            session.permanent = True
            login_user(user, remember=True)
            next_page = request.args.get('next')
            resp = redirect(next_page or url_for('dashboard.index'))
            resp.set_cookie('remembered_email', identifier, max_age=30*24*60*60)
            flash('Welcome back, {}!'.format(user.name), 'success')
            return resp
        else:
            flash('Invalid credentials. Please try again.', 'error')

    return render_template('login.html')


@auth_bp.route('/login/google')
def google_login():
    redirect_uri = url_for('auth.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route('/login/google/callback')
def google_callback():
    token = oauth.google.authorize_access_token()
    user_info = token.get('userinfo') or oauth.google.parse_id_token(token)

    google_id = user_info.get('sub')
    email = user_info.get('email', '').lower()
    name = user_info.get('name', '')
    picture = user_info.get('picture', '')

    user = User.query.filter_by(google_id=google_id).first()
    if not user:
        user = User.query.filter_by(email=email).first()
        if user:
            user.google_id = google_id
            if picture and not user.profile_picture:
                user.profile_picture = picture
            db.session.commit()
        else:
            user = User(
                name=name,
                email=email,
                google_id=google_id,
                profile_picture=picture,
                password=None
            )
            db.session.add(user)
            db.session.commit()

    session.permanent = True
    login_user(user, remember=True)
    flash('Welcome, {}!'.format(user.name), 'success')
    return redirect(url_for('dashboard.index'))


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    identifier = request.form.get('email', '').strip()
    if not identifier:
        flash('Please enter your email address or phone number.', 'error')
        return redirect(url_for('auth.login'))

    user = _find_user(identifier)
    if user:
        flash('A password reset link has been sent to {}. (Demo: check your email client)'.format(identifier), 'success')
    else:
        flash('No account found with that email or phone number.', 'error')

    return redirect(url_for('auth.login'))


@auth_bp.route('/api/check-email')
def check_email():
    email = request.args.get('email', '').strip().lower()
    exists = User.query.filter_by(email=email).first() is not None
    return jsonify({'exists': exists})


@auth_bp.route('/api/check-phone')
def check_phone():
    phone = request.args.get('phone', '').strip()
    exists = User.query.filter_by(phone=phone).first() is not None
    return jsonify({'exists': exists})


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    resp = redirect(url_for('auth.login'))
    resp.delete_cookie('remembered_email')
    return resp
