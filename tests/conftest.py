import os
import sys
import pytest
from sqlalchemy.pool import StaticPool

# Ensure root dir is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force in-memory database AND disable rate limiting BEFORE anything imports app/config
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['RATELIMIT_ENABLED'] = 'false'
os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-testing-only')


@pytest.fixture(scope='session')
def app():
    """Create app with test config. Session-scoped = shared across all tests."""
    from app import create_app

    app = create_app()

    # Override config BEFORE any DB access (engine is lazy in Flask-SQLAlchemy 3.x)
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['RATELIMIT_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': {'check_same_thread': False},
        'poolclass': StaticPool,
    }

    return app


@pytest.fixture(autouse=True)
def reset_db(app):
    """Reset database state between tests."""
    from extensions import db
    with app.app_context():
        db.session.rollback()
        db.session.remove()
        db.drop_all()
        db.create_all()
    yield
    with app.app_context():
        db.session.rollback()
        db.session.remove()
        db.drop_all()


def _make_client(app):
    """Create a fresh test client."""
    return app.test_client()


def _create_and_login(app, email='test@consultorio.com', password='TestPass1!'):
    """Create a user, log them in, and return the authenticated client."""
    from extensions import db
    from models import User

    with app.app_context():
        u = User(full_name='Dr. Test', email=email)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()

    c = _make_client(app)
    c.post('/auth/login', data={'email': email, 'password': password})
    return c


def _create_patient(app, **kwargs):
    """Create a patient and return their ID."""
    from extensions import db
    from models import Patient

    defaults = dict(full_name='Juan Pérez', document_id='12345678')
    defaults.update(kwargs)
    with app.app_context():
        p = Patient(**defaults)
        db.session.add(p)
        db.session.commit()
        return p.id


def _create_professional(app):
    """Create a professional with Mon-Fri 8-16 schedule and return their ID."""
    from extensions import db
    from models import User, WorkSchedule
    from datetime import date, timedelta

    with app.app_context():
        u = User(full_name='Dr. Agenda', email='agenda@test.com')
        u.set_password('TestPass1!')
        db.session.add(u)
        db.session.commit()
        hoy = date.today()
        # Lunes a Viernes (0-4) para que siempre haya disponibilidad
        for day in range(5):
            ws = WorkSchedule(
                user_id=u.id, day_of_week=day,
                start_time='08:00', end_time='16:00',
                valid_from=hoy, valid_to=hoy + timedelta(days=365),
            )
            db.session.add(ws)
        db.session.commit()
        return u.id
