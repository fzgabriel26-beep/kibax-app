"""Tests para el blueprint de pacientes."""
from models import Patient, ToothStatus
from extensions import db as _db
from tests.conftest import _create_and_login, _create_patient


class TestPatientList:
    def test_list_requires_login(self, app):
        from tests.conftest import _make_client
        r = _make_client(app).get('/pacientes/')
        assert r.status_code == 302
        assert '/auth/login' in r.headers['Location']

    def test_list_empty(self, app):
        c = _create_and_login(app)
        r = c.get('/pacientes/')
        assert r.status_code == 200
        assert 'Todavía no hay pacientes' in r.data.decode()

    def test_list_with_patients(self, app):
        c = _create_and_login(app)
        _create_patient(app)
        r = c.get('/pacientes/')
        assert r.status_code == 200
        assert 'Juan Pérez' in r.data.decode()


class TestNewPatient:
    def test_new_patient_page(self, app):
        c = _create_and_login(app)
        r = c.get('/pacientes/nuevo')
        assert r.status_code == 200
        assert 'Dar de alta' in r.data.decode()

    def test_create_patient(self, app):
        c = _create_and_login(app)
        r = c.post('/pacientes/nuevo', data={
            'full_name': 'María García', 'document_id': '87654321',
            'phone': '11-5555-1234', 'email': 'maria@test.com',
            'birth_date': '1990-05-15',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert 'María García' in r.data.decode()
        with app.app_context():
            assert Patient.query.filter_by(full_name='María García').first() is not None

    def test_create_patient_without_name(self, app):
        c = _create_and_login(app)
        r = c.post('/pacientes/nuevo', data={
            'full_name': '', 'document_id': '12345678',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert 'obligatorio' in r.data.decode()


class TestPatientDetail:
    def test_detail_page(self, app):
        c = _create_and_login(app)
        pid = _create_patient(app)
        r = c.get(f'/pacientes/{pid}')
        assert r.status_code == 200
        assert 'Juan Pérez' in r.data.decode()
        assert 'Odontograma' in r.data.decode()

    def test_detail_nonexistent(self, app):
        c = _create_and_login(app)
        r = c.get('/pacientes/99999')
        assert r.status_code == 404


class TestDeletePatient:
    def test_delete_patient(self, app):
        c = _create_and_login(app)
        pid = _create_patient(app)
        r = c.post(f'/pacientes/{pid}/eliminar', follow_redirects=True)
        assert r.status_code == 200
        assert 'eliminados' in r.data.decode()
        with app.app_context():
            from extensions import db as _db2
            assert _db2.session.get(Patient, pid) is None


class TestToothOperations:
    def test_tooth_info(self, app):
        c = _create_and_login(app)
        pid = _create_patient(app)
        r = c.get(f'/pacientes/{pid}/diente/11')
        assert r.status_code == 200
        data = r.get_json()
        assert data['ok'] is True
        assert data['tooth_number'] == 11

    def test_tooth_invalid_number(self, app):
        c = _create_and_login(app)
        pid = _create_patient(app)
        r = c.get(f'/pacientes/{pid}/diente/99')
        assert r.status_code == 404

    def test_tooth_update(self, app):
        c = _create_and_login(app)
        pid = _create_patient(app)
        r = c.post(f'/pacientes/{pid}/diente/11', data={
            'surface': 'V', 'status': 'caries', 'note': 'Caries visible',
        })
        assert r.status_code == 200
        data = r.get_json()
        assert data['ok'] is True
        assert data['status'] == 'caries'
        with app.app_context():
            ts = ToothStatus.query.filter_by(
                patient_id=pid, tooth_number=11, surface='V'
            ).first()
            assert ts is not None
            assert ts.status == 'caries'

    def test_tooth_update_empty_note(self, app):
        c = _create_and_login(app)
        pid = _create_patient(app)
        r = c.post(f'/pacientes/{pid}/diente/11', data={
            'surface': 'V', 'status': 'caries', 'note': '',
        })
        assert r.status_code == 400
        assert r.get_json()['ok'] is False
