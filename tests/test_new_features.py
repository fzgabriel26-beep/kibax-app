"""Tests para las nuevas funcionalidades: editar paciente, ICS, paginación,
profesionales, CSV import, auditoría."""
from datetime import date, timedelta
from models import Patient, Appointment, User, AuditLog
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
            from extensions import db as _db2
            p = _db2.session.get(Patient, pid)
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

    def test_edit_invalid_email_fails(self, app):
        c = _create_and_login(app)
        pid = _create_patient(app)
        r = c.post(f'/pacientes/{pid}/editar', data={
            'full_name': 'Test',
            'email': 'not-an-email',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert 'email' in r.data.decode().lower()

    def test_edit_creates_audit_log(self, app):
        c = _create_and_login(app)
        pid = _create_patient(app)
        c.post(f'/pacientes/{pid}/editar', data={
            'full_name': 'Nombre Editado',
            'document_id': '11111111',
        }, follow_redirects=True)
        with app.app_context():
            logs = AuditLog.query.filter_by(
                entity_type='patient', entity_id=pid, action='update'
            ).count()
            assert logs >= 1

    def test_edit_nonexistent(self, app):
        c = _create_and_login(app)
        r = c.get('/pacientes/99999/editar')
        assert r.status_code == 404


class TestPagination:
    def test_pagination_controls(self, app):
        c = _create_and_login(app)
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


class TestProfessionalCRUD:
    def test_list_profesionales(self, app):
        c = _create_and_login(app)
        r = c.get('/agenda/profesionales')
        assert r.status_code == 200
        assert 'Profesionales' in r.data.decode()

    def test_create_profesional(self, app):
        c = _create_and_login(app)
        r = c.post('/agenda/profesionales/nuevo', data={
            'full_name': 'Dr. Nuevo',
            'email': 'nuevo@test.com',
            'license_number': 'MAT-123',
            'password': 'TestPass1!',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert 'Dr. Nuevo' in r.data.decode()
        with app.app_context():
            assert User.query.filter_by(email='nuevo@test.com').first() is not None

    def test_create_profesional_without_password_fails(self, app):
        c = _create_and_login(app)
        r = c.post('/agenda/profesionales/nuevo', data={
            'full_name': 'Dr. Sin Pass',
            'email': 'sinpass@test.com',
            'password': '',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert 'contraseña' in r.data.decode().lower()

    def test_edit_profesional(self, app):
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        r = c.post(f'/agenda/profesionales/{prof_id}/editar', data={
            'full_name': 'Dr. Editado',
            'email': 'editado@test.com',
            'license_number': 'MAT-456',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert 'Dr. Editado' in r.data.decode()

    def test_delete_profesional(self, app):
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        r = c.post(f'/agenda/profesionales/{prof_id}/eliminar', follow_redirects=True)
        assert r.status_code == 200
        with app.app_context():
            from extensions import db as _db2
            assert _db2.session.get(User, prof_id) is None

    def test_delete_self_fails(self, app):
        c = _create_and_login(app)
        with app.app_context():
            from models import User
            user = User.query.filter_by(email='test@consultorio.com').first()
            uid = user.id
        r = c.post(f'/agenda/profesionales/{uid}/eliminar', follow_redirects=True)
        assert r.status_code == 200
        assert 'propia cuenta' in r.data.decode()


class TestCSVImport:
    def test_import_page_loads(self, app):
        c = _create_and_login(app)
        r = c.get('/pacientes/importar')
        assert r.status_code == 200
        assert 'Importar' in r.data.decode()

    def test_import_csv(self, app):
        c = _create_and_login(app)
        csv_data = b'nombre,documento,telefono,email\nMaria Lopez,11111111,11-5555-0000,maria@test.com\nJuan Garcia,22222222,11-5555-1111,juan@test.com\n'
        import io
        r = c.post('/pacientes/importar', data={
            'csv_file': (io.BytesIO(csv_data), 'pacientes.csv'),
        }, content_type='multipart/form-data', follow_redirects=True)
        assert r.status_code == 200
        with app.app_context():
            assert Patient.query.filter_by(full_name='Maria Lopez').first() is not None
            assert Patient.query.filter_by(full_name='Juan Garcia').first() is not None

    def test_import_invalid_file(self, app):
        c = _create_and_login(app)
        import io
        r = c.post('/pacientes/importar', data={
            'csv_file': (io.BytesIO(b'not csv'), 'file.txt'),
        }, content_type='multipart/form-data', follow_redirects=True)
        assert r.status_code == 200
        assert 'CSV válido' in r.data.decode()


