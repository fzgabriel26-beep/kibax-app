import os
from datetime import date

from flask import Flask, redirect, url_for, request, flash
from flask_login import current_user

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

    # Hacemos que la sesión sea permanente para que PERMANENT_SESSION_LIFETIME
    # tenga efecto. Sin esto, la sesión se borra al cerrar el navegador.
    @app.before_request
    def make_session_permanent():
        from flask import session
        session.permanent = True

    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

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

    @app.errorhandler(413)
    def too_large(_e):
        flash('El archivo supera el tamaño máximo permitido (15 MB).', 'danger')
        return redirect(request.referrer or url_for('patients.list_patients'))

    @app.errorhandler(429)
    def rate_limit_exceeded(_e):
        flash('Demasiadas solicitudes. Esperá unos minutos y volvé a intentar.', 'danger')
        return redirect(request.referrer or url_for('auth.login'))

    # OJO: ya NO se llama a db.create_all() acá. Las tablas se crean y
    # actualizan con Flask-Migrate ("flask db upgrade"), no automáticamente
    # al arrancar la app. Ver README para el setup inicial.

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
