import os
import re
import smtplib
from datetime import UTC, datetime
from email.message import EmailMessage

from email_validator import validate_email, EmailNotValidError
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from extensions import db, limiter
from models import User, ROLES

bp = Blueprint('auth', __name__, url_prefix='/auth')

MSG_REGISTRO_GENERICO = 'No se pudo crear la cuenta, datos faltantes o erróneos.'
MSG_REGISTRO_CODIGO_INVALIDO = (
    'Código de registro inválido. Consultá con quien administra el consultorio.'
)
MSG_REGISTRO_EMAIL_EXISTENTE = 'Ya existe una cuenta con ese email asociado.'
MSG_REGISTRO_PASSWORD_DISTINTA = 'Las contraseñas no coinciden.'

# Se muestra siempre el mismo texto, exista o no la cuenta: así nadie puede
# usar este formulario para averiguar qué emails están registrados.
MSG_RESET_ENVIADO = (
    'Si ese email está asociado a una cuenta, te enviamos un enlace para '
    'restablecer la contraseña. Revisá también la carpeta de spam.'
)
MSG_RESET_ENLACE_INVALIDO = (
    'El enlace no es válido o ya venció. Pedí uno nuevo desde "¿Olvidaste tu contraseña?".'
)
MSG_RESET_SIN_CORREO = (
    'Este equipo todavía no tiene el correo configurado, así que el mensaje no '
    'salió: el enlace quedó guardado en el registro del servidor.'
)


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


def _validate_email(email):
    """Valida formato de email. Devuelve None si es válido, o un mensaje de error."""
    try:
        validate_email(email, check_deliverability=False)
        return None
    except EmailNotValidError:
        return 'El formato del email no es válido.'


# --- Restablecer contraseña -------------------------------------------------

def _reset_serializer():
    """Firmador de los enlaces de restablecimiento (usa SECRET_KEY)."""
    return URLSafeTimedSerializer(
        current_app.config['SECRET_KEY'], salt='restablecer-password')


def _huella_password(user):
    """Últimos caracteres del hash de la contraseña.

    Se guardan dentro del token: si la contraseña cambia, cualquier enlace
    viejo que haya quedado dando vueltas deja de servir.
    """
    return (user.password_hash or '')[-16:]


def generar_token_reset(user):
    """Token firmado y con vencimiento para restablecer la contraseña."""
    return _reset_serializer().dumps({
        'uid': user.id,
        'pw': _huella_password(user),
    })


def leer_token_reset(token):
    """Devuelve el User del token, o None si es inválido, venció o la
    contraseña ya cambió."""
    try:
        datos = _reset_serializer().loads(
            token, max_age=current_app.config['PASSWORD_RESET_MAX_AGE'])
    except (BadSignature, SignatureExpired):
        return None

    if not isinstance(datos, dict) or not isinstance(datos.get('uid'), int):
        return None

    user = db.session.get(User, datos['uid'])
    if user is None or _huella_password(user) != datos.get('pw'):
        return None
    return user


def _cuerpo_email_reset(nombre, enlace, minutos):
    """Devuelve (texto plano, html) del correo de restablecimiento."""
    texto = (
        f'Hola {nombre}:\n\n'
        'Recibimos un pedido para restablecer la contraseña de tu cuenta '
        'en Kiba X.\n\n'
        f'Abrí este enlace para elegir una contraseña nueva (vence en {minutos} minutos):\n\n'
        f'{enlace}\n\n'
        'Si no fuiste vos, ignorá este mensaje: tu contraseña actual sigue '
        'funcionando.\n'
    )
    html = (
        '<div style="font-family:Segoe UI,Arial,sans-serif;color:#3A4543;'
        'max-width:520px;line-height:1.55">'
        f'<p>Hola <strong>{nombre}</strong>:</p>'
        '<p>Recibimos un pedido para restablecer la contraseña de tu cuenta '
        'en <strong>Kiba X</strong>.</p>'
        '<p>Elegí una contraseña nueva desde este enlace '
        f'(vence en {minutos} minutos):</p>'
        f'<p><a href="{enlace}" style="display:inline-block;background:#5A9E94;'
        'color:#FFFFFF;text-decoration:none;padding:10px 18px;border-radius:8px;'
        'font-weight:600">Elegir contraseña nueva</a></p>'
        f'<p style="font-size:13px;color:#6B7A77;word-break:break-all">{enlace}</p>'
        '<p style="font-size:13px;color:#6B7A77">Si no fuiste vos, ignorá este '
        'mensaje: tu contraseña actual sigue funcionando.</p>'
        '</div>'
    )
    return texto, html


def _guardar_enlace_en_archivo(destinatario, enlace):
    """Deja el enlace en instance/ (ignorado por git).

    No se usa logs/consultorio.log a propósito: ese archivo sí está trackeado
    y un `git add -A` subiría un enlace de restablecimiento vivo.
    """
    ruta = os.path.join(current_app.instance_path, 'enlaces-restablecer.log')
    try:
        os.makedirs(current_app.instance_path, exist_ok=True)
        with open(ruta, 'a', encoding='utf-8') as fh:
            fh.write('%s  %s  %s\n' % (
                datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S'),
                destinatario, enlace))
    except OSError:
        current_app.logger.exception(
            'No se pudo escribir el enlace de restablecimiento en %s', ruta)
        return
    current_app.logger.warning(
        'Enlace de restablecimiento para %s guardado en %s', destinatario, ruta)


def _enviar_email_reset(destinatario, enlace, nombre):
    """Manda el enlace por correo. Devuelve True si salió.

    Si no hay servidor de correo configurado —o el envío falla— deja el enlace
    en instance/enlaces-restablecer.log y devuelve False, para poder probar el
    circuito en un equipo de desarrollo.
    """
    if not current_app.config.get('MAIL_SERVER'):
        _guardar_enlace_en_archivo(destinatario, enlace)
        return False

    minutos = max(1, current_app.config['PASSWORD_RESET_MAX_AGE'] // 60)
    texto, html = _cuerpo_email_reset(nombre, enlace, minutos)

    mensaje = EmailMessage()
    mensaje['Subject'] = 'Restablecer tu contraseña · Kiba X'
    mensaje['From'] = current_app.config['MAIL_DEFAULT_SENDER']
    mensaje['To'] = destinatario
    mensaje.set_content(texto)
    mensaje.add_alternative(html, subtype='html')

    try:
        with smtplib.SMTP(
                current_app.config['MAIL_SERVER'],
                current_app.config['MAIL_PORT'],
                timeout=current_app.config['MAIL_TIMEOUT']) as smtp:
            if current_app.config.get('MAIL_USE_TLS'):
                smtp.starttls()
            usuario = current_app.config.get('MAIL_USERNAME')
            if usuario:
                smtp.login(usuario, current_app.config.get('MAIL_PASSWORD', ''))
            smtp.send_message(mensaje)
        return True
    except (OSError, smtplib.SMTPException):
        current_app.logger.exception(
            'No se pudo enviar el correo de restablecimiento a %s', destinatario)
        _guardar_enlace_en_archivo(destinatario, enlace)
        return False


@bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def register():
    """Rate limited: máximo 5 registros por minuto por IP."""
    if current_user.is_authenticated:
        return redirect(url_for('patients.list_patients'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')
        license_number = request.form.get('license_number', '').strip()
        role = (request.form.get('role') or 'odontologo').strip().lower()
        code = request.form.get('registration_code', '')

        # Los datos faltantes se informan de forma genérica antes de revisar
        # el código, para que un código incorrecto no oculte el problema real.
        if not full_name or not email or not password or not password2:
            flash(MSG_REGISTRO_GENERICO, 'danger')
            return render_template('auth/register.html', form=request.form)

        if password != password2:
            flash(MSG_REGISTRO_PASSWORD_DISTINTA, 'danger')
            return render_template('auth/register.html', form=request.form)

        # El email duplicado se informa aunque el código no sea válido: la
        # persona necesita saber que ya tiene una cuenta asociada.
        if User.query.filter_by(email=email).first():
            flash(MSG_REGISTRO_EMAIL_EXISTENTE, 'danger')
            return render_template('auth/register.html', form=request.form)

        # El código de registro evita que cualquier visitante anónimo pueda
        # crearse una cuenta y acceder a los datos de los pacientes.
        if code != current_app.config['REGISTRATION_CODE']:
            flash(MSG_REGISTRO_CODIGO_INVALIDO, 'danger')
            return render_template('auth/register.html', form=request.form)

        if role not in ROLES:
            flash(MSG_REGISTRO_GENERICO, 'danger')
            return render_template('auth/register.html', form=request.form)

        # El secretario/a no tiene matrícula profesional: si el campo llegó
        # con algo, se ignora.
        if role == 'secretario':
            license_number = ''

        if _validate_email(email):
            flash(MSG_REGISTRO_GENERICO, 'danger')
            return render_template('auth/register.html', form=request.form)

        if _password_strength(password):
            flash(MSG_REGISTRO_GENERICO, 'danger')
            return render_template('auth/register.html', form=request.form)

        user = User(full_name=full_name, email=email,
                    license_number=license_number, role=role)
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


@bp.route('/olvide-password', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def forgot_password():
    """Pide el email y, si hay una cuenta, manda el enlace para restablecer."""
    if current_user.is_authenticated:
        return redirect(url_for('patients.list_patients'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first() if email else None

        if user:
            token = generar_token_reset(user)
            enlace = url_for('auth.reset_password', token=token, _external=True)
            if not _enviar_email_reset(user.email, enlace, user.full_name):
                flash(MSG_RESET_SIN_CORREO, 'warning')

        flash(MSG_RESET_ENVIADO, 'info')
        return redirect(url_for('auth.forgot_password'))

    return render_template('auth/olvide_password.html')


@bp.route('/restablecer/<token>', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def reset_password(token):
    """Formulario para elegir la contraseña nueva desde el enlace del correo."""
    user = leer_token_reset(token)
    if user is None:
        flash(MSG_RESET_ENLACE_INVALIDO, 'danger')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')

        if not password or not password2:
            flash('Completá las dos contraseñas.', 'danger')
            return render_template('auth/restablecer_password.html', token=token)

        if password != password2:
            flash(MSG_REGISTRO_PASSWORD_DISTINTA, 'danger')
            return render_template('auth/restablecer_password.html', token=token)

        error = _password_strength(password)
        if error:
            flash(error, 'danger')
            return render_template('auth/restablecer_password.html', token=token)

        user.set_password(password)
        db.session.commit()

        flash('Contraseña actualizada. Ya podés iniciar sesión.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/restablecer_password.html', token=token)


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada.', 'info')
    return redirect(url_for('auth.login'))
