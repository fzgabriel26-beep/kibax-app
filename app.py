import os

from flask import Flask, redirect, url_for, request, flash
from flask_login import current_user

from config import Config
from extensions import db, login_manager, migrate


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    import auth
    import patients
    app.register_blueprint(auth.bp)
    app.register_blueprint(patients.bp)

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('patients.list_patients'))
        return redirect(url_for('auth.login'))

    @app.errorhandler(413)
    def too_large(_e):
        flash('El archivo supera el tamaño máximo permitido (15 MB).', 'danger')
        return redirect(request.referrer or url_for('patients.list_patients'))

    # OJO: ya NO se llama a db.create_all() acá. Las tablas se crean y
    # actualizan con Flask-Migrate ("flask db upgrade"), no automáticamente
    # al arrancar la app. Ver README para el setup inicial.

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
