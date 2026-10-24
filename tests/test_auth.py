"""Tests para el blueprint de autenticación."""
from models import User
from extensions import db as _db
from tests.conftest import _make_client, _create_and_login


class TestLogin:
    def test_login_page_loads(self, app):
        r = _make_client(app).get('/auth/login')
        assert r.status_code == 200
        assert 'Iniciar sesión' in r.data.decode()

    def test_login_with_valid_credentials(self, app):
        _create_and_login(app)
        r = _make_client(app).post('/auth/login', data={
            'email': 'test@consultorio.com', 'password': 'TestPass1!',
        })
        assert r.status_code == 302
        assert '/pacientes' in r.headers['Location']

    def test_login_with_wrong_password(self, app):
        _create_and_login(app)
        r = _make_client(app).post('/auth/login', data={
            'email': 'test@consultorio.com', 'password': 'WrongPass1!',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert 'incorrectos' in r.data.decode()

    def test_login_with_nonexistent_user(self, app):
        r = _make_client(app).post('/auth/login', data={
            'email': 'noexiste@test.com', 'password': 'TestPass1!',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert 'incorrectos' in r.data.decode()


class TestRegister:
    def test_register_page_loads(self, app):
        r = _make_client(app).get('/auth/register')
        assert r.status_code == 200
        html = r.data.decode()
        assert 'Crear cuenta' in html
        assert 'Tipo de usuario' in html
        assert 'Odontólogo/a' in html
        assert 'Secretario/a' in html

    def test_register_success(self, app):
        with app.app_context():
            app.config['REGISTRATION_CODE'] = 'testcode'
        r = _make_client(app).post('/auth/register', data={
            'full_name': 'Dr. Nuevo', 'email': 'nuevo@test.com',
            'password': 'NewPass1!', 'password2': 'NewPass1!',
            'registration_code': 'testcode',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert 'correctamente' in r.data.decode()
        with app.app_context():
            u = User.query.filter_by(email='nuevo@test.com').first()
            assert u is not None
            assert u.role == 'odontologo'

    def test_register_secretary_has_no_license(self, app):
        with app.app_context():
            app.config['REGISTRATION_CODE'] = 'testcode'
        r = _make_client(app).post('/auth/register', data={
            'full_name': 'Secretaria Nueva', 'email': 'secre@test.com',
            'license_number': 'MAT-999',
            'role': 'secretario',
            'password': 'NewPass1!', 'password2': 'NewPass1!',
            'registration_code': 'testcode',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert 'correctamente' in r.data.decode()
        with app.app_context():
            u = User.query.filter_by(email='secre@test.com').first()
            assert u is not None
            assert u.role == 'secretario'
            assert not u.license_number

    def test_register_invalid_role_fails(self, app):
        with app.app_context():
            app.config['REGISTRATION_CODE'] = 'testcode'
        r = _make_client(app).post('/auth/register', data={
            'full_name': 'Rol Inválido', 'email': 'rol@test.com',
            'role': 'administrador',
            'password': 'NewPass1!', 'password2': 'NewPass1!',
            'registration_code': 'testcode',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert 'No se pudo crear la cuenta, datos faltantes o erróneos.' in r.data.decode()
        with app.app_context():
            assert User.query.filter_by(email='rol@test.com').first() is None

    def test_register_wrong_code(self, app):
        r = _make_client(app).post('/auth/register', data={
            'full_name': 'Dr. Test', 'email': 'test@test.com',
            'password': 'TestPass1!', 'password2': 'TestPass1!',
            'registration_code': 'wrongcode',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert ('Código de registro inválido. Consultá con quien administra el consultorio.'
                in r.data.decode())
        with app.app_context():
            assert User.query.filter_by(email='test@test.com').first() is None

    def test_register_password_mismatch(self, app):
        with app.app_context():
            app.config['REGISTRATION_CODE'] = 'testcode'
        r = _make_client(app).post('/auth/register', data={
            'full_name': 'Dr. Test', 'email': 'test@test.com',
            'password': 'TestPass1!', 'password2': 'DifferentPass1!',
            'registration_code': 'testcode',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert 'Las contraseñas no coinciden.' in r.data.decode()
        with app.app_context():
            assert User.query.filter_by(email='test@test.com').first() is None

    def test_register_password_mismatch_wins_over_wrong_code(self, app):
        r = _make_client(app).post('/auth/register', data={
            'full_name': 'Dr. Test', 'email': 'test@test.com',
            'password': 'TestPass1!', 'password2': 'DifferentPass1!',
            'registration_code': 'wrongcode',
        }, follow_redirects=True)
        assert r.status_code == 200
        body = r.data.decode()
        assert 'Las contraseñas no coinciden.' in body
        assert 'Código de registro inválido' not in body

    def test_register_weak_password(self, app):
        with app.app_context():
            app.config['REGISTRATION_CODE'] = 'testcode'
        r = _make_client(app).post('/auth/register', data={
            'full_name': 'Dr. Test', 'email': 'test@test.com',
            'password': 'weak', 'password2': 'weak',
            'registration_code': 'testcode',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert 'No se pudo crear la cuenta, datos faltantes o erróneos.' in r.data.decode()
        with app.app_context():
            assert User.query.filter_by(email='test@test.com').first() is None

    def test_register_empty_fields_uses_generic_error(self, app):
        r = _make_client(app).post('/auth/register', data={
            'registration_code': 'wrongcode',
        }, follow_redirects=True)
        assert r.status_code == 200
        body = r.data.decode()
        assert 'No se pudo crear la cuenta, datos faltantes o erróneos.' in body
        assert 'Código de registro inválido' not in body

    def test_register_invalid_email_uses_generic_error(self, app):
        with app.app_context():
            app.config['REGISTRATION_CODE'] = 'testcode'
        r = _make_client(app).post('/auth/register', data={
            'full_name': 'Dr. Test', 'email': 'no-es-un-email',
            'password': 'TestPass1!', 'password2': 'TestPass1!',
            'registration_code': 'testcode',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert 'No se pudo crear la cuenta, datos faltantes o erróneos.' in r.data.decode()

    def test_register_duplicate_email(self, app):
        with app.app_context():
            app.config['REGISTRATION_CODE'] = 'testcode'
            u = User(full_name='Existente', email='dup@test.com')
            u.set_password('TestPass1!')
            _db.session.add(u)
            _db.session.commit()
        r = _make_client(app).post('/auth/register', data={
            'full_name': 'Otro', 'email': 'dup@test.com',
            'password': 'TestPass1!', 'password2': 'TestPass1!',
            'registration_code': 'testcode',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert 'Ya existe una cuenta con ese email asociado.' in r.data.decode()
        with app.app_context():
            assert User.query.filter_by(email='dup@test.com').count() == 1

    def test_register_duplicate_email_wins_over_wrong_code(self, app):
        with app.app_context():
            app.config['REGISTRATION_CODE'] = 'testcode'
            u = User(full_name='Existente', email='dup2@test.com')
            u.set_password('TestPass1!')
            _db.session.add(u)
            _db.session.commit()
        r = _make_client(app).post('/auth/register', data={
            'full_name': 'Otro', 'email': 'dup2@test.com',
            'password': 'TestPass1!', 'password2': 'TestPass1!',
            'registration_code': 'wrongcode',
        }, follow_redirects=True)
        assert r.status_code == 200
        body = r.data.decode()
        assert 'Ya existe una cuenta con ese email asociado.' in body
        assert 'Código de registro inválido' not in body
        with app.app_context():
            assert User.query.filter_by(email='dup2@test.com').count() == 1


class TestLogout:
    def test_logout(self, app):
        c = _create_and_login(app)
        r = c.get('/auth/logout', follow_redirects=True)
        assert r.status_code == 200
        assert 'Sesión cerrada' in r.data.decode()


def _crear_usuario(app, email='reset@test.com', password='TestPass1!'):
    """Crea un usuario suelto (sin loguearse) y devuelve su id."""
    with app.app_context():
        u = User(full_name='Dr. Reset', email=email)
        u.set_password(password)
        _db.session.add(u)
        _db.session.commit()
        return u.id


def _token_para(app, email='reset@test.com'):
    import auth as auth_module
    with app.app_context():
        u = User.query.filter_by(email=email).first()
        return auth_module.generar_token_reset(u)


class TestPasswordReset:
    """Circuito de "¿Olvidaste tu contraseña?"."""

    def test_forgot_page_loads(self, app):
        r = _make_client(app).get('/auth/olvide-password')
        assert r.status_code == 200
        html = r.data.decode()
        assert 'Restablecer contraseña' in html
        assert 'Enviarme el enlace' in html

    def test_login_page_has_forgot_link(self, app):
        html = _make_client(app).get('/auth/login').data.decode()
        assert '¿Olvidaste tu contraseña?' in html
        assert '/auth/olvide-password' in html

    def test_register_page_has_forgot_link(self, app):
        html = _make_client(app).get('/auth/register').data.decode()
        assert '¿Olvidaste tu contraseña?' in html
        assert '/auth/olvide-password' in html

    def test_forgot_existing_email_sends_link(self, app, monkeypatch):
        _crear_usuario(app)
        import auth as auth_module
        enviados = []

        def falso(destinatario, enlace, nombre):
            enviados.append((destinatario, enlace))
            return True

        monkeypatch.setattr(auth_module, '_enviar_email_reset', falso)

        r = _make_client(app).post(
            '/auth/olvide-password',
            data={'email': 'reset@test.com'}, follow_redirects=True)

        assert r.status_code == 200
        assert 'Si ese email está asociado a una cuenta' in r.data.decode()
        assert len(enviados) == 1
        assert enviados[0][0] == 'reset@test.com'
        assert '/auth/restablecer/' in enviados[0][1]

    def test_forgot_unknown_email_same_message(self, app, monkeypatch):
        import auth as auth_module
        enviados = []
        monkeypatch.setattr(
            auth_module, '_enviar_email_reset',
            lambda d, e, n: enviados.append(d) or True)

        r = _make_client(app).post(
            '/auth/olvide-password',
            data={'email': 'noexiste@test.com'}, follow_redirects=True)

        assert r.status_code == 200
        assert 'Si ese email está asociado a una cuenta' in r.data.decode()
        assert enviados == []

    def test_forgot_without_mail_server_warns(self, app, tmp_path):
        with app.app_context():
            app.config['MAIL_SERVER'] = ''
            app.instance_path = str(tmp_path)
        _crear_usuario(app)

        r = _make_client(app).post(
            '/auth/olvide-password',
            data={'email': 'reset@test.com'}, follow_redirects=True)

        body = r.data.decode()
        assert 'el enlace quedó guardado en el registro del servidor' in body
        assert 'Si ese email está asociado a una cuenta' in body

        # El enlace queda en instance/ (ignorado por git), no en el log trackeado.
        archivo = tmp_path / 'enlaces-restablecer.log'
        assert archivo.exists()
        contenido = archivo.read_text(encoding='utf-8')
        assert 'reset@test.com' in contenido
        assert '/auth/restablecer/' in contenido

    def test_reset_changes_password(self, app):
        _crear_usuario(app)
        token = _token_para(app)

        c = _make_client(app)
        r = c.post(f'/auth/restablecer/{token}', data={
            'password': 'NuevaClave1!', 'password2': 'NuevaClave1!',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert 'Contraseña actualizada' in r.data.decode()

        r = _make_client(app).post('/auth/login', data={
            'email': 'reset@test.com', 'password': 'NuevaClave1!',
        })
        assert r.status_code == 302
        assert '/pacientes' in r.headers['Location']

    def test_reset_rejects_weak_password(self, app):
        _crear_usuario(app)
        token = _token_para(app)

        r = _make_client(app).post(f'/auth/restablecer/{token}', data={
            'password': 'debil', 'password2': 'debil',
        }, follow_redirects=True)
        assert 'al menos 8 caracteres' in r.data.decode()

        with app.app_context():
            assert User.query.filter_by(email='reset@test.com').first() \
                .check_password('TestPass1!')

    def test_reset_rejects_mismatch(self, app):
        _crear_usuario(app)
        token = _token_para(app)

        r = _make_client(app).post(f'/auth/restablecer/{token}', data={
            'password': 'NuevaClave1!', 'password2': 'OtraClave1!',
        }, follow_redirects=True)
        assert 'Las contraseñas no coinciden.' in r.data.decode()

    def test_reset_invalid_token(self, app):
        r = _make_client(app).get('/auth/restablecer/token-inventado',
                                  follow_redirects=True)
        assert r.status_code == 200
        assert 'El enlace no es válido o ya venció' in r.data.decode()

    def test_reset_token_dies_after_password_change(self, app):
        _crear_usuario(app)
        token = _token_para(app)

        with app.app_context():
            u = User.query.filter_by(email='reset@test.com').first()
            u.set_password('OtraClaveDistinta1!')
            _db.session.commit()

        r = _make_client(app).get(f'/auth/restablecer/{token}',
                                  follow_redirects=True)
        assert 'El enlace no es válido o ya venció' in r.data.decode()
