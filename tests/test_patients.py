"""Tests para el blueprint de pacientes."""
from datetime import date

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
            'birth_date': '1990-05-15', 'gender': 'Femenino',
            'address': 'Av. Corrientes 1234, CABA',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert 'María García' in r.data.decode()
        with app.app_context():
            p = Patient.query.filter_by(full_name='María García').first()
            assert p is not None
            assert p.gender == 'Femenino'
            assert p.address == 'Av. Corrientes 1234, CABA'

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


class TestPatientExport:
    def test_export_includes_age_gender_and_address(self, app):
        c = _create_and_login(app)
        birth = date(1990, 5, 15)
        pid = _create_patient(
            app, full_name='María García', document_id='87654321',
            birth_date=birth, gender='Femenino',
            address='Av. Corrientes 1234, CABA',
        )
        r = c.get(f'/pacientes/{pid}/exportar')
        assert r.status_code == 200
        html = r.data.decode()
        today = date.today()
        age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
        assert f'Edad:</b> {age} años' in html
        assert 'Género:</b> Femenino' in html
        assert 'Domicilio:</b> Av. Corrientes 1234, CABA' in html

    def test_edit_patient_gender(self, app):
        c = _create_and_login(app)
        pid = _create_patient(app)
        r = c.post(f'/pacientes/{pid}/editar', data={
            'full_name': 'Juan Pérez', 'gender': 'Masculino',
        }, follow_redirects=True)
        assert r.status_code == 200
        with app.app_context():
            assert _db.session.get(Patient, pid).gender == 'Masculino'


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

class TestPatientSearch:
    """El buscador tiene que encontrar en TODA la base, sin acentos ni puntos."""

    def test_busca_nombre_sin_acentos(self, app):
        c = _create_and_login(app)
        _create_patient(app, full_name='María Fernández', document_id='30111222')
        html = c.get('/pacientes/?q=fernandez').data.decode()
        assert 'María Fernández' in html
        assert 'No se encontraron pacientes' not in html

    def test_busca_nombre_con_mayusculas(self, app):
        c = _create_and_login(app)
        _create_patient(app, full_name='Ciro Acosta', document_id='40315455')
        html = c.get('/pacientes/?q=CIRO').data.decode()
        assert 'Ciro Acosta' in html

    def test_busca_dni_sin_puntos(self, app):
        c = _create_and_login(app)
        _create_patient(app, full_name='Ciro Acosta', document_id='21.588.825')
        html = c.get('/pacientes/?q=21588825').data.decode()
        assert 'Ciro Acosta' in html

    def test_busca_por_palabras_en_otro_orden(self, app):
        c = _create_and_login(app)
        _create_patient(app, full_name='Julieta Silva', document_id='36617308')
        html = c.get('/pacientes/?q=silva julieta').data.decode()
        assert 'Julieta Silva' in html

    def test_busca_en_todas_las_paginas(self, app):
        """Antes solo filtraba las 50 tarjetas de la página actual."""
        c = _create_and_login(app)
        for i in range(55):
            _create_patient(app, full_name='Paciente %02d' % i,
                            document_id='90%06d' % i)

        html = c.get('/pacientes/?q=Paciente 54').data.decode()
        assert 'Paciente 54' in html

        html = c.get('/pacientes/?q=90000054').data.decode()
        assert 'Paciente 54' in html

    def test_sin_resultados_no_dice_que_no_hay_pacientes(self, app):
        c = _create_and_login(app)
        _create_patient(app, full_name='Juan Pérez', document_id='12345678')
        html = c.get('/pacientes/?q=zzzzzz').data.decode()
        assert 'No se encontraron pacientes' in html
        assert 'Todavía no hay pacientes' not in html

    def test_limpiar_busqueda_vuelve_al_listado(self, app):
        c = _create_and_login(app)
        _create_patient(app, full_name='Juan Pérez', document_id='12345678')
        html = c.get('/pacientes/?q=zzzzzz').data.decode()
        assert '/pacientes/' in html
        assert 'Limpiar búsqueda' in html


class TestAgendaPatientSearch:
    def test_autocompletado_sin_acentos(self, app):
        c = _create_and_login(app)
        _create_patient(app, full_name='María Fernández', document_id='30111222')
        r = c.get('/agenda/pacientes?q=fernandez')
        assert r.status_code == 200
        nombres = [p['full_name'] for p in r.get_json()['results']]
        assert 'María Fernández' in nombres

    def test_autocompletado_por_dni_sin_puntos(self, app):
        c = _create_and_login(app)
        _create_patient(app, full_name='Ciro Acosta', document_id='21.588.825')
        r = c.get('/agenda/pacientes?q=21588825')
        nombres = [p['full_name'] for p in r.get_json()['results']]
        assert 'Ciro Acosta' in nombres
