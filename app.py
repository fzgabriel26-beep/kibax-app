import logging
import os
import shutil
from datetime import date
from logging.handlers import RotatingFileHandler

from flask import Flask, redirect, url_for, request, flash, send_file, jsonify
from flask_login import current_user, login_required

from config import Config
from extensions import db, login_manager, migrate, csrf, limiter


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # --- Logging estructurado con rotación ---
    if not app.debug and not app.testing:
        os.makedirs('logs', exist_ok=True)
        file_handler = RotatingFileHandler(
            'logs/consultorio.log', maxBytes=5_000_000, backupCount=5
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.WARNING)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.WARNING)
        app.logger.info('Consultorio arrancado.')

    # Hacemos que la sesión sea permanente para que PERMANENT_SESSION_LIFETIME
    # tenga efecto. Sin esto, la sesión se borra al cerrar el navegador.
    @app.before_request
    def make_session_permanent():
        from flask import session
        session.permanent = True

    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    import auth
    import patients
    import agenda
    app.register_blueprint(auth.bp)
    app.register_blueprint(patients.bp)
    app.register_blueprint(agenda.bp)

    # Exponer csrf_token() en todas las plantillas Jinja
    from flask_wtf.csrf import generate_csrf
    app.jinja_env.globals['csrf_token'] = generate_csrf

    # Filtro de Jinja para mostrar la hora "real" de un turno cancelado o
    # ausente: internamente se corre 1 minuto para no perder el registro
    # sin ocupar el horario original, pero en pantalla mostramos la hora
    # original para no confundir con un error de carga.
    app.jinja_env.filters['turno_hora'] = agenda.display_time

    @app.context_processor
    def inject_agenda():
        """Inyecta contadores para las insignias del navbar: turnos de hoy
        y turnos pendientes de confirmar (en cualquier fecha)."""
        from models import Appointment
        if current_user.is_authenticated:
            hoy = date.today()
            conteo = Appointment.query.filter_by(planned_date=hoy).filter(
                Appointment.status != 'cancelado'
            ).count()
            pendientes = Appointment.query.filter_by(status='pendiente').count()
            return {'agenda_hoy': conteo, 'hoy': hoy, 'turnos_pendientes': pendientes}
        return {}

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('patients.list_patients'))
        return redirect(url_for('auth.login'))

    # --- Backup de la base de datos ---
    @app.route('/admin/backup')
    @login_required
    def backup_database():
        """Genera una copia de seguridad de la base de datos."""
        from flask_login import login_required as lr
        db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        if not os.path.exists(db_path):
            flash('No se encontró la base de datos.', 'danger')
            return redirect(url_for('patients.list_patients'))

        backup_dir = os.path.join(app.instance_path, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_dir, f'odontograma_{timestamp}.db')
        shutil.copy2(db_path, backup_path)

        # Mantener solo los últimos 10 backups
        backups = sorted([
            f for f in os.listdir(backup_dir) if f.endswith('.db')
        ])
        while len(backups) > 10:
            os.remove(os.path.join(backup_dir, backups.pop(0)))

        flash(f'Backup creado: {os.path.basename(backup_path)}', 'success')
        return redirect(url_for('patients.list_patients'))

    @app.errorhandler(404)
    def not_found(_e):
        return render_error('Página no encontrada', 404)

    @app.errorhandler(500)
    def server_error(_e):
        return render_error('Error interno del servidor', 500)

    def render_error(message, code):
        from flask import render_template
        return render_template('errors/error.html', message=message, code=code), code

    @app.errorhandler(413)
    def too_large(_e):
        flash('El archivo supera el tamaño máximo permitido (15 MB).', 'danger')
        return redirect(request.referrer or url_for('patients.list_patients'))

    @app.errorhandler(429)
    def rate_limit_exceeded(_e):
        flash('Demasiadas solicitudes. Esperá unos minutos y volvé a intentar.', 'danger')
        return redirect(request.referrer or url_for('auth.login'))

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
