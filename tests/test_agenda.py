"""Tests para el blueprint de agenda."""
from datetime import date, timedelta
from models import Appointment, Patient, WorkSchedule
from extensions import db as _db
from tests.conftest import _create_and_login, _create_patient, _create_professional, _make_client


def _logged_user_id(app):
    """ID del usuario creado y logueado por _create_and_login."""
    from models import User
    with app.app_context():
        return User.query.filter_by(email='test@consultorio.com').first().id


class TestAgendaIndex:
    def test_agenda_requires_login(self, app):
        r = _make_client(app).get('/agenda/')
        assert r.status_code == 302
        assert '/auth/login' in r.headers['Location']

    def test_agenda_loads(self, app):
        """Sin profesional elegido, la agenda redirige al primero disponible."""
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        r = c.get('/agenda/')
        assert r.status_code == 302
        assert f'profesional={prof_id}' in r.headers['Location']

        r = c.get(r.headers['Location'])
        assert r.status_code == 200
        html = r.data.decode()
        assert 'agenda-new-layout' in html
        assert 'Profesional' in html

    def test_agenda_day_view_shows_slots(self, app):
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        r = c.get(f'/agenda/?fecha=2026-10-13&profesional={prof_id}')
        assert r.status_code == 200
        html = r.data.decode()
        assert 'slots-table' in html
        assert '08:00' in html
        assert '15:30' in html

    def test_agenda_navbar_has_single_agenda_entry(self, app):
        """El navbar no debe separar Calendario y Turnos: hay un solo 'Agenda'."""
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        html = c.get(f'/agenda/?profesional={prof_id}').data.decode()
        assert 'nav-agenda-link' in html
        assert '>Calendario<' not in html
        assert '>Turnos<' not in html
        assert 'navAgendaDropdown' not in html

    def test_agenda_dates_are_in_spanish(self, app):
        """El sistema devuelve fechas en inglés; la UI debe mostrarlas en español."""
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        html = c.get(f'/agenda/?profesional={prof_id}').data.decode()
        assert 'October' not in html
        assert 'Octubre' in html
        assert 'Monday' not in html and 'Tuesday' not in html and 'Wednesday' not in html

    def test_agenda_has_no_all_professionals_option(self, app):
        """La agenda es siempre de un profesional: no existe 'Todos'."""
        c = _create_and_login(app)
        _create_professional(app)
        html = c.get('/agenda/').get_data(as_text=True)
        assert 'Todos los profesionales' not in html

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

    def test_create_appointment_without_schedule(self, app):
        """Un profesional sin horario cargado no debe bloquear el turno."""
        c = _create_and_login(app)
        pid = _create_patient(app, full_name='Paciente Sin Horario', document_id='44444444')
        tomorrow = date.today() + timedelta(days=1)
        r = c.post('/agenda/nuevo', data={
            'patient_id': pid,
            'professional_id': _logged_user_id(app),
            'fecha': tomorrow.strftime('%Y-%m-%d'),
            'hora': '09:30',
            'status': 'confirmado',
        }, follow_redirects=True)
        assert r.status_code == 200
        with app.app_context():
            assert Appointment.query.filter_by(patient_id=pid).count() == 1

    def test_create_appointment_accepts_argentine_date(self, app):
        """El input muestra dd/mm/aaaa: debe guardarse igual."""
        c = _create_and_login(app)
        pid = _create_patient(app, full_name='Paciente Fecha AR', document_id='55555555')
        tomorrow = date.today() + timedelta(days=1)
        r = c.post('/agenda/nuevo', data={
            'patient_id': pid,
            'professional_id': _logged_user_id(app),
            'fecha': tomorrow.strftime('%d/%m/%Y'),
            'hora': '11:00',
            'status': 'confirmado',
        }, follow_redirects=True)
        assert r.status_code == 200
        with app.app_context():
            appt = Appointment.query.filter_by(patient_id=pid).first()
            assert appt is not None
            assert appt.planned_date == tomorrow

    def test_create_appointment_fixes_swapped_date(self, app):
        """Una versión vieja del JS enviaba aaaa-día-mes; no debe rebotar."""
        c = _create_and_login(app)
        pid = _create_patient(app, full_name='Paciente Fecha Rota', document_id='66666666')
        r = c.post('/agenda/nuevo', data={
            'patient_id': pid,
            'professional_id': _logged_user_id(app),
            'fecha': '2026-27-10',  # año-día-mes
            'hora': '11:30',
            'status': 'confirmado',
        }, follow_redirects=True)
        assert r.status_code == 200
        with app.app_context():
            appt = Appointment.query.filter_by(patient_id=pid).first()
            assert appt is not None
            assert appt.planned_date == date(2026, 10, 27)

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
            from extensions import db as _db2
            assert _db2.session.get(Appointment, appt_id).status == 'atendido'

    def test_no_generic_ausente_status(self, app):
        """El estado genérico 'Ausente' fue eliminado: hay que distinguir si
        el paciente avisó o no, así que solo existen las dos variantes."""
        c = _create_and_login(app)
        pid = _create_patient(app, full_name='Paciente Sin Generico', document_id='99999999')
        prof_id = _create_professional(app)
        tomorrow = date.today() + timedelta(days=1)

        with app.app_context():
            appt = Appointment(
                patient_id=pid, professional_id=prof_id,
                planned_date=tomorrow, time='12:00', status='confirmado',
            )
            _db.session.add(appt)
            _db.session.commit()
            appt_id = appt.id

        html = c.get(f'/agenda/?fecha={tomorrow.isoformat()}&profesional={prof_id}').data.decode()
        assert 'value="ausente"' not in html
        assert 'value="ausente_aviso"' in html
        assert 'value="ausente_sin_aviso"' in html

        # La API rechaza el valor viejo en vez de guardarlo
        r = c.post(f'/agenda/{appt_id}/estado', data={'status': 'ausente'})
        with app.app_context():
            assert _db.session.get(Appointment, appt_id).status == 'confirmado'

    def test_status_select_carries_color_class(self, app):
        """Cada estado pinta su <select> con la clase st-... de CSS."""
        c = _create_and_login(app)
        pid = _create_patient(app, full_name='Paciente Colores', document_id='66666666')
        prof_id = _create_professional(app)
        tomorrow = date.today() + timedelta(days=1)

        with app.app_context():
            appt = Appointment(
                patient_id=pid, professional_id=prof_id,
                planned_date=tomorrow, time='12:30', status='atendido',
            )
            _db.session.add(appt)
            _db.session.commit()

        html = c.get(f'/agenda/?fecha={tomorrow.isoformat()}&profesional={prof_id}').data.decode()
        assert 'st-atendido' in html
        # Cada <option> también lleva su clase, para colorear el desplegable
        for cls in ('st-confirmado', 'st-presente', 'st-ausente-aviso',
                    'st-ausente-sin-aviso', 'st-cancelado'):
            assert f'class="{cls}"' in html
        # Pendiente no tiene color propio
        assert 'class=""' in html

    def test_ausente_sin_aviso_in_dropdown(self, app):
        """El estado 'Ausente sin aviso' debe figurar en los select de estado."""
        c = _create_and_login(app)
        pid = _create_patient(app, full_name='Paciente Estados', document_id='77777777')
        prof_id = _create_professional(app)
        tomorrow = date.today() + timedelta(days=1)

        with app.app_context():
            appt = Appointment(
                patient_id=pid, professional_id=prof_id,
                planned_date=tomorrow, time='12:00', status='confirmado',
            )
            _db.session.add(appt)
            _db.session.commit()
            appt_id = appt.id

        html = c.get(f'/agenda/?fecha={tomorrow.isoformat()}&profesional={prof_id}').data.decode()
        assert 'Ausente sin aviso' in html
        assert 'value="ausente_sin_aviso"' in html

    def test_ausente_sin_aviso_frees_the_slot(self, app):
        """Ausente sin aviso libera el horario (corre 1 min, como los demás)."""
        c = _create_and_login(app)
        pid = _create_patient(app, full_name='Paciente No Asistio', document_id='88888888')
        prof_id = _create_professional(app)
        tomorrow = date.today() + timedelta(days=1)

        with app.app_context():
            appt = Appointment(
                patient_id=pid, professional_id=prof_id,
                planned_date=tomorrow, time='12:00', status='confirmado',
            )
            _db.session.add(appt)
            _db.session.commit()
            appt_id = appt.id

        c.post(f'/agenda/{appt_id}/estado', data={'status': 'ausente_sin_aviso'})
        with app.app_context():
            turno = _db.session.get(Appointment, appt_id)
            assert turno.status == 'ausente_sin_aviso'
            assert turno.time == '12:01'

        # El slot vuelve a figurar como disponible en la tabla del día
        html = c.get(f'/agenda/?fecha={tomorrow.isoformat()}&profesional={prof_id}').data.decode()
        assert 'slot-book-btn' in html


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
            from extensions import db as _db2
            assert _db2.session.get(Appointment, appt_id) is None


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
