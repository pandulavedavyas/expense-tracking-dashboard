import os
from flask import Flask
from flask_login import LoginManager
from config import Config
from models import db
from models.user import User

login_manager = LoginManager()


def create_app():
    base_dir = os.path.abspath(os.path.dirname(__file__))
    app = Flask(__name__,
                static_folder=os.path.join(base_dir, 'static'),
                template_folder=os.path.join(base_dir, 'templates'))
    app.config.from_object(Config)

    from whitenoise import WhiteNoise
    app.wsgi_app = WhiteNoise(app.wsgi_app, root=os.path.join(base_dir, 'static'), prefix='static/')

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'error'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.context_processor
    def inject_user_settings():
        from flask_login import current_user
        if current_user.is_authenticated:
            return {
                'currency': current_user.currency,
                'dark_mode': current_user.dark_mode,
                'accent_color': current_user.accent_color
            }
        return {'currency': '₹', 'dark_mode': False, 'accent_color': '#2563EB'}

    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.transactions import transactions_bp
    from routes.analytics import analytics_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(analytics_bp)

    with app.app_context():
        db.create_all()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
