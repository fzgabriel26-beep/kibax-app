"""Tests para el blueprint de agenda."""
from datetime import date, timedelta
from models import Appointment, Patient, WorkSchedule
from extensions import db as _db
from tests.conftest import _create_and_login, _create_patient, _create_professional, _make_client


class TestAgendaIndex:
    def test_agenda_requires_login(self, app):
        r = _make_client(app).get('/agenda/')
        assert r.status_code == 302
        assert '/auth/login' in r.headers['Location']

    def test_agenda_loads(self, app):
        c = _create_and_login(app)
        r = c.get('/agenda/')
        assert r.status_code == 200
        assert 'Agenda de turnos' in r.data.decode()

    def test_agenda_with_professional_filter(self, app):
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        r = c.get(f'/agenda/?profesional={prof_id}')
        assert r.status_code == 200
        assert 'Dr. Agenda' in r.data.decode()


class TestTurnos:
    def test_turnos_page(self, app):
        c = _create_and_login(app)
        r = c.get('/agenda/turnos')
        assert r.status_code == 200
        assert 'Turnos' in r.data.decode()


class TestNuevoTurno:
    def test_create_appointment(self, app):
        c = _create_and_login(app)
        pid = _create_patient(app, full_name='Paciente Agenda', document_id='11111111')
        prof_id = _create_professional(app)
        tomorrow = date.today() + timedelta(days=1)
        r = c.post('/agenda/nuevo', data={
            'patient_id': pid,
            'professional_id': prof_id,
            'fecha': tomorrow.strftime('%Y-%m-%d'),
            'hora': '10:00',
            'status': 'confirmado',
            'reason': 'Control general',
        }, follow_redirects=True)
        assert r.status_code == 200
        with app.app_context():
            appt = Appointment.query.filter_by(patient_id=pid).first()
            assert appt is not None
            assert appt.reason == 'Control general'

    def test_no_double_booking(self, app):
        c = _create_and_login(app)
        pid1 = _create_patient(app, full_name='Paciente A', document_id='11111111')
        pid2 = _create_patient(app, full_name='Paciente B', document_id='22222222')
        prof_id = _create_professional(app)
        tomorrow = date.today() + timedelta(days=1)

        # Primer turno
        c.post('/agenda/nuevo', data={
            'patient_id': pid1,
            'professional_id': prof_id,
            'fecha': tomorrow.strftime('%Y-%m-%d'),
            'hora': '10:00',
            'status': 'confirmado',
        }, follow_redirects=True)

        # Segundo turno en el mismo horario
        r = c.post('/agenda/nuevo', data={
            'patient_id': pid2,
            'professional_id': prof_id,
            'fecha': tomorrow.strftime('%Y-%m-%d'),
            'hora': '10:00',
            'status': 'confirmado',
        }, follow_redirects=True)
        assert r.status_code == 200
        body = r.data.decode()
        assert 'ya tiene un turno' in body.lower() or 'mismo horario' in body.lower()


class TestEstadoTurno:
    def test_change_status(self, app):
        c = _create_and_login(app)
        pid = _create_patient(app, full_name='Paciente Agenda', document_id='11111111')
        prof_id = _create_professional(app)
        tomorrow = date.today() + timedelta(days=1)

        with app.app_context():
            appt = Appointment(
                patient_id=pid, professional_id=prof_id,
                planned_date=tomorrow, time='10:00', status='confirmado',
            )
            _db.session.add(appt)
            _db.session.commit()
            appt_id = appt.id

        r = c.post(f'/agenda/{appt_id}/estado', data={'status': 'atendido'}, follow_redirects=True)
        assert r.status_code == 200
        assert 'actualizado' in r.data.decode()
        with app.app_context():
            assert Appointment.query.get(appt_id).status == 'atendido'


class TestEliminarTurno:
    def test_delete_appointment(self, app):
        c = _create_and_login(app)
        pid = _create_patient(app, full_name='Paciente Agenda', document_id='11111111')
        prof_id = _create_professional(app)
        tomorrow = date.today() + timedelta(days=1)

        with app.app_context():
            appt = Appointment(
                patient_id=pid, professional_id=prof_id,
                planned_date=tomorrow, time='11:00', status='confirmado',
            )
            _db.session.add(appt)
            _db.session.commit()
            appt_id = appt.id

        r = c.post(f'/agenda/{appt_id}/eliminar', follow_redirects=True)
        assert r.status_code == 200
        assert 'eliminado' in r.data.decode()
        with app.app_context():
            assert Appointment.query.get(appt_id) is None


class TestHorarios:
    def test_horarios_page(self, app):
        c = _create_and_login(app)
        r = c.get('/agenda/horarios')
        assert r.status_code == 200
        assert 'Horarios' in r.data.decode()

    def test_create_schedule(self, app):
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        hoy = date.today()
        r = c.post('/agenda/horarios/nuevo', data={
            'user_id': prof_id,
            'days': ['0', '1', '2'],
            'start_time': '09:00',
            'end_time': '17:00',
            'valid_from': hoy.strftime('%d/%m/%Y'),
            'valid_to': (hoy + timedelta(days=364)).strftime('%d/%m/%Y'),
        }, follow_redirects=True)
        assert r.status_code == 200
        assert 'asignado' in r.data.decode()
