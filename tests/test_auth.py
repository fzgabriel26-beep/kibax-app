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
