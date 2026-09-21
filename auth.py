import re

from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db, limiter
from models import User

bp = Blueprint('auth', __name__, url_prefix='/auth')


def _password_strength(password):
    """Valida que la contraseña tenga al menos 8 caracteres, una mayúscula,
    un número y un carácter especial. Devuelve None si es válida, o un
    mensaje de error descriptivo."""
    if len(password) < 8:
        return 'La contraseña debe tener al menos 8 caracteres.'
    if not re.search(r'[A-Z]', password):
        return 'La contraseña debe contener al menos una letra mayúscula.'
    if not re.search(r'[0-9]', password):
        return 'La contraseña debe contener al menos un número.'
    if not re.search(r'[!@#$%^&*(),.?\":{}|<>\-_=+\[\]\\;\'`~]', password):
        return 'La contraseña debe contener al menos un carácter especial (!@#$%^&*...).'
    return None


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('patients.list_patients'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')
        license_number = request.form.get('license_number', '').strip()
        code = request.form.get('registration_code', '')

        # El código de registro evita que cualquier visitante anónimo pueda
        # crearse una cuenta y acceder a los datos de los pacientes.
        if code != current_app.config['REGISTRATION_CODE']:
            flash('Código de registro inválido. Consultá con quien administra el consultorio.', 'danger')
            return render_template('auth/register.html', form=request.form)

        if not full_name or not email or not password:
            flash('Completá todos los campos obligatorios.', 'danger')
            return render_template('auth/register.html', form=request.form)

        if password != password2:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('auth/register.html', form=request.form)

        error = _password_strength(password)
        if error:
            flash(error, 'danger')
            return render_template('auth/register.html', form=request.form)

        if User.query.filter_by(email=email).first():
            flash('Ya existe una cuenta con ese email.', 'danger')
            return render_template('auth/register.html', form=request.form)

        user = User(full_name=full_name, email=email, license_number=license_number)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Cuenta creada correctamente. Ya podés iniciar sesión.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form={})


@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    """Rate limited: máximo 10 intentos de login por minuto por IP."""
    if current_user.is_authenticated:
        return redirect(url_for('patients.list_patients'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('patients.list_patients'))

        flash('Email o contraseña incorrectos.', 'danger')

    return render_template('auth/login.html')


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada.', 'info')
    return redirect(url_for('auth.login'))
