"""Tests para las nuevas funcionalidades: editar paciente, ICS, paginación."""
from datetime import date, timedelta
from models import Patient, Appointment
from extensions import db as _db
from tests.conftest import _create_and_login, _create_patient, _create_professional, _make_client


class TestEditPatient:
    def test_edit_page_loads(self, app):
        c = _create_and_login(app)
        pid = _create_patient(app)
        r = c.get(f'/pacientes/{pid}/editar')
        assert r.status_code == 200
        assert 'Editar paciente' in r.data.decode()
        assert 'Juan Pérez' in r.data.decode()

    def test_edit_patient(self, app):
        c = _create_and_login(app)
        pid = _create_patient(app)
        r = c.post(f'/pacientes/{pid}/editar', data={
            'full_name': 'Juan Carlos Pérez',
            'document_id': '87654321',
            'phone': '11-9999-0000',
            'email': 'juancarlos@test.com',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert 'Juan Carlos Pérez' in r.data.decode()
        with app.app_context():
            p = Patient.query.get(pid)
            assert p.full_name == 'Juan Carlos Pérez'
            assert p.phone == '11-9999-0000'

    def test_edit_without_name_fails(self, app):
        c = _create_and_login(app)
        pid = _create_patient(app)
        r = c.post(f'/pacientes/{pid}/editar', data={
            'full_name': '',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert 'obligatorio' in r.data.decode()

    def test_edit_nonexistent(self, app):
        c = _create_and_login(app)
        r = c.get('/pacientes/99999/editar')
        assert r.status_code == 404


class TestPagination:
    def test_pagination_controls(self, app):
        c = _create_and_login(app)
        # Create 55 patients to trigger pagination
        for i in range(55):
            _create_patient(app, full_name=f'Paciente {i:03d}', document_id=f'{10000000 + i}')
        r = c.get('/pacientes/')
        assert r.status_code == 200
        body = r.data.decode()
        assert 'página 1 de 2' in body
        assert 'Siguiente' in body

    def test_pagination_page_2(self, app):
        c = _create_and_login(app)
        for i in range(55):
            _create_patient(app, full_name=f'Paciente {i:03d}', document_id=f'{10000000 + i}')
        r = c.get('/pacientes/?page=2')
        assert r.status_code == 200
        assert 'página 2 de 2' in r.data.decode()

    def test_server_side_search(self, app):
        c = _create_and_login(app)
        _create_patient(app, full_name='María García', document_id='11111111')
        _create_patient(app, full_name='Juan López', document_id='22222222')
        r = c.get('/pacientes/?q=María')
        assert r.status_code == 200
        assert 'María García' in r.data.decode()


class TestICSExport:
    def test_ics_export(self, app):
        c = _create_and_login(app)
        pid = _create_patient(app)
        prof_id = _create_professional(app)

        with app.app_context():
            appt = Appointment(
                patient_id=pid, professional_id=prof_id,
                planned_date=date.today() + timedelta(days=1),
                time='10:00', status='confirmado', reason='Control',
            )
            _db.session.add(appt)
            _db.session.commit()

        r = c.get('/agenda/exportar/ics')
        assert r.status_code == 200
        assert 'text/calendar' in r.content_type
        body = r.data.decode()
        assert 'BEGIN:VCALENDAR' in body
        assert 'END:VCALENDAR' in body

    def test_ics_export_with_professional_filter(self, app):
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        r = c.get(f'/agenda/exportar/ics?profesional={prof_id}')
        assert r.status_code == 200
        assert 'BEGIN:VCALENDAR' in r.data.decode()
