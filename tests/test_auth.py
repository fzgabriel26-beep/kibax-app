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
        assert 'Crear cuenta' in r.data.decode()

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
            assert User.query.filter_by(email='nuevo@test.com').first() is not None

    def test_register_wrong_code(self, app):
        r = _make_client(app).post('/auth/register', data={
            'full_name': 'Dr. Test', 'email': 'test@test.com',
            'password': 'TestPass1!', 'password2': 'TestPass1!',
            'registration_code': 'wrongcode',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert 'inválido' in r.data.decode()

    def test_register_password_mismatch(self, app):
        with app.app_context():
            app.config['REGISTRATION_CODE'] = 'testcode'
        r = _make_client(app).post('/auth/register', data={
            'full_name': 'Dr. Test', 'email': 'test@test.com',
            'password': 'TestPass1!', 'password2': 'DifferentPass1!',
            'registration_code': 'testcode',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert 'no coinciden' in r.data.decode()

    def test_register_weak_password(self, app):
        with app.app_context():
            app.config['REGISTRATION_CODE'] = 'testcode'
        r = _make_client(app).post('/auth/register', data={
            'full_name': 'Dr. Test', 'email': 'test@test.com',
            'password': 'weak', 'password2': 'weak',
            'registration_code': 'testcode',
        }, follow_redirects=True)
        assert r.status_code == 200
        body = r.data.decode()
        assert 'caracteres' in body or 'mayúscula' in body or 'número' in body

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
        assert 'Ya existe' in r.data.decode()


class TestLogout:
    def test_logout(self, app):
        c = _create_and_login(app)
        r = c.get('/auth/logout', follow_redirects=True)
        assert r.status_code == 200
        assert 'Sesión cerrada' in r.data.decode()
