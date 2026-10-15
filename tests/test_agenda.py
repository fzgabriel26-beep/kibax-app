"""Tests para el blueprint de agenda."""
import json
from datetime import date, timedelta
from models import (Appointment, AuditLog, Patient, ScheduleException,
                    WorkSchedule, WaitingListEntry)
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


def _lunes_siguiente():
    """Un lunes futuro, para caer siempre en día laborable del test."""
    d = date.today() + timedelta(days=7)
    while d.weekday() != 0:
        d += timedelta(days=1)
    return d


class TestWaitingList:
    """Lista de espera del panel lateral de la agenda."""

    def test_requires_login(self, app):
        r = _make_client(app).post('/agenda/lista-espera', data={'patient_id': 1})
        assert r.status_code == 302
        assert '/auth/login' in r.headers['Location']

    def test_section_renders_in_sidebar(self, app):
        """El panel aparece en el sidebar con el contador en cero."""
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        html = c.get(f'/agenda/?profesional={prof_id}').data.decode()
        assert 'Lista de espera' in html
        assert 'waitlist-section' in html
        assert 'Nadie espera turno' in html

    def test_add_entry(self, app):
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        pid = _create_patient(app, full_name='Paciente Lista', document_id='41111111')

        r = c.post('/agenda/lista-espera', data={
            'patient_id': pid,
            'professional_id': prof_id,
            'shift': 'tarde',
            'note': 'solo de tarde',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert 'agregado a la lista de espera' in r.data.decode()

        with app.app_context():
            e = WaitingListEntry.query.one()
            assert e.patient_id == pid
            assert e.professional_id == prof_id
            assert e.shift == 'tarde'
            assert e.note == 'solo de tarde'

        html = c.get(f'/agenda/?profesional={prof_id}').data.decode()
        assert 'Paciente Lista' in html
        assert 'solo de tarde' in html
        assert 'Tarde' in html

    def test_add_without_patient_is_rejected(self, app):
        c = _create_and_login(app)
        _create_professional(app)
        c.post('/agenda/lista-espera', data={'shift': 'manana'})
        with app.app_context():
            assert WaitingListEntry.query.count() == 0

    def test_invalid_shift_defaults_to_manana(self, app):
        c = _create_and_login(app)
        _create_professional(app)
        pid = _create_patient(app, full_name='Paciente Turno', document_id='42222222')
        c.post('/agenda/lista-espera', data={'patient_id': pid, 'shift': 'medianoche'})
        with app.app_context():
            assert WaitingListEntry.query.one().shift == 'manana'

    def test_duplicate_patient_is_not_added_twice(self, app):
        c = _create_and_login(app)
        _create_professional(app)
        pid = _create_patient(app, full_name='Paciente Repetido', document_id='43333333')
        c.post('/agenda/lista-espera', data={'patient_id': pid})
        r = c.post('/agenda/lista-espera', data={'patient_id': pid}, follow_redirects=True)
        assert 'ya está en la lista de espera' in r.data.decode()
        with app.app_context():
            assert WaitingListEntry.query.count() == 1

    def test_delete_entry(self, app):
        c = _create_and_login(app)
        _create_professional(app)
        pid = _create_patient(app, full_name='Paciente Sale', document_id='44444444')
        c.post('/agenda/lista-espera', data={'patient_id': pid})
        with app.app_context():
            entry_id = WaitingListEntry.query.one().id

        r = c.post(f'/agenda/lista-espera/{entry_id}/eliminar', follow_redirects=True)
        assert r.status_code == 200
        assert 'quitado de la lista de espera' in r.data.decode()
        with app.app_context():
            assert WaitingListEntry.query.count() == 0

    def test_delete_unknown_entry_is_404(self, app):
        c = _create_and_login(app)
        _create_professional(app)
        assert c.post('/agenda/lista-espera/999999/eliminar').status_code == 404

    def test_assigning_turn_removes_from_list(self, app):
        """Al agendar el turno con waitlist_id, la fila se da de baja sola."""
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        pid = _create_patient(app, full_name='Paciente Asignado', document_id='45555555')
        c.post('/agenda/lista-espera', data={
            'patient_id': pid, 'professional_id': prof_id, 'shift': 'manana',
        })
        with app.app_context():
            entry_id = WaitingListEntry.query.one().id

        lunes = _lunes_siguiente()
        r = c.post('/agenda/nuevo', data={
            'patient_id': pid,
            'professional_id': prof_id,
            'fecha': lunes.strftime('%Y-%m-%d'),
            'hora': '10:00',
            'status': 'confirmado',
            'waitlist_id': entry_id,
        }, follow_redirects=True)
        assert r.status_code == 200

        with app.app_context():
            assert WaitingListEntry.query.count() == 0
            assert Appointment.query.count() == 1

    def test_creating_turn_without_waitlist_id_keeps_list(self, app):
        """Un turno normal no debe tocar la lista de espera."""
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        pid = _create_patient(app, full_name='Paciente Queda', document_id='46666666')
        c.post('/agenda/lista-espera', data={'patient_id': pid})

        c.post('/agenda/nuevo', data={
            'patient_id': pid,
            'professional_id': prof_id,
            'fecha': _lunes_siguiente().strftime('%Y-%m-%d'),
            'hora': '11:00',
            'status': 'confirmado',
        })
        with app.app_context():
            assert WaitingListEntry.query.count() == 1
            assert Appointment.query.count() == 1


class TestSlotMenu:
    """Menú contextual (Nuevo turno / Nuevo sobreturno / Anular turno)."""

    def _agendar(self, c, app, prof_id, hora, **extra):
        pid = _create_patient(app, full_name='Paciente Menú', document_id='47777777')
        data = {
            'patient_id': pid,
            'professional_id': prof_id,
            'fecha': _lunes_siguiente().strftime('%Y-%m-%d'),
            'hora': hora,
            'status': 'confirmado',
        }
        data.update(extra)
        return c.post('/agenda/nuevo', data=data, follow_redirects=True)

    def test_menu_is_rendered_in_day_view(self, app):
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        html = c.get(f'/agenda/?profesional={prof_id}'
                     f'&fecha={_lunes_siguiente().strftime("%Y-%m-%d")}').data.decode()
        assert 'id="slotMenu"' in html
        assert 'Nuevo turno' in html
        assert 'Nuevo sobreturno' in html
        assert 'Anular turno' in html
        # el modal sabe cuándo es sobreturno
        assert 'name="sobreturno"' in html

    def test_rows_carry_slot_data(self, app):
        """Cada fila expone la hora y la fecha para poder abrir el menú."""
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        self._agendar(c, app, prof_id, '09:00')
        html = c.get(f'/agenda/?profesional={prof_id}'
                     f'&fecha={_lunes_siguiente().strftime("%Y-%m-%d")}').data.decode()
        assert 'data-hora="09:00"' in html
        assert 'data-fecha="' in html
        assert 'data-appt-id="' in html

    def test_regular_turno_outside_schedule_is_blocked(self, app):
        """07:00 está fuera del horario L-V 08:00-16:00."""
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        r = self._agendar(c, app, prof_id, '07:00')
        assert r.status_code == 200
        assert 'no atiende' in r.data.decode()
        with app.app_context():
            assert Appointment.query.count() == 0

    def test_sobreturno_outside_schedule_is_allowed(self, app):
        """El mismo horario sí entra si se marca como sobreturno."""
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        r = self._agendar(c, app, prof_id, '07:00', sobreturno='1')
        assert r.status_code == 200
        assert 'Sobreturno agendado' in r.data.decode()
        with app.app_context():
            appt = Appointment.query.one()
            assert appt.time == '07:00'

    def test_sobreturno_at_intermediate_time(self, app):
        """09:15 dentro del bloque 09:00-09:30 convive con el turno de 09:00."""
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        self._agendar(c, app, prof_id, '09:00')
        r = self._agendar(c, app, prof_id, '09:15', sobreturno='1')
        assert 'Sobreturno agendado' in r.data.decode()
        with app.app_context():
            assert Appointment.query.count() == 2
            times = sorted(a.time for a in Appointment.query.all())
            assert times == ['09:00', '09:15']

    def test_exact_time_double_booking_is_still_rejected(self, app):
        """Un sobreturno no debe pisar un turno en la misma hora exacta."""
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        self._agendar(c, app, prof_id, '10:00')
        r = self._agendar(c, app, prof_id, '10:00', sobreturno='1')
        assert 'ya tiene un turno' in r.data.decode()
        with app.app_context():
            assert Appointment.query.count() == 1

    def test_invalid_time_format_is_rejected(self, app):
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        for mala in ('25:99', '9:15', 'ab:cd', '1000'):
            self._agendar(c, app, prof_id, mala, sobreturno='1')
            with app.app_context():
                assert Appointment.query.count() == 0, f'aceptó hora {mala!r}'

    def test_anular_turno_frees_the_slot(self, app):
        """Anular marca cancelado, corre la hora 1 min y libera la celda."""
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        self._agendar(c, app, prof_id, '09:30')
        with app.app_context():
            appt_id = Appointment.query.one().id

        r = c.post(f'/agenda/{appt_id}/estado', data={
            'status': 'cancelado',
            'next': f'/agenda/?fecha={_lunes_siguiente().strftime("%Y-%m-%d")}'
                    f'&profesional={prof_id}',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert 'Estado del turno actualizado' in r.data.decode()

        with app.app_context():
            appt = Appointment.query.first()
            assert appt.status == 'cancelado'
            # la hora se corre para que esa celda vuelva a estar libre
            assert appt.time == '09:31'

        html = c.get(f'/agenda/?profesional={prof_id}'
                     f'&fecha={_lunes_siguiente().strftime("%Y-%m-%d")}').data.decode()
        # la fila 09:30 existe y ya no tiene turno encima
        i = html.find('data-hora="09:30"')
        assert i != -1
        assert 'slot-book-btn' in html
        assert 'status-cancelado' in html


class TestNoCitar:
    """"Anular turno" marca un horario como NO CITAR, con turno o sin él."""

    def _url(self):
        return f'/agenda/?fecha={_lunes_siguiente().strftime("%Y-%m-%d")}'

    def _anular(self, c, prof_id, hora, **extra):
        data = {
            'fecha': _lunes_siguiente().strftime('%Y-%m-%d'),
            'hora': hora,
            'professional_id': prof_id,
            'next': self._url(),
        }
        data.update(extra)
        return c.post('/agenda/no-citar', data=data, follow_redirects=True)

    def _agendar(self, c, app, prof_id, hora):
        pid = _create_patient(app, full_name='Ana Paciente', document_id='51111111')
        return c.post('/agenda/nuevo', data={
            'patient_id': pid,
            'professional_id': prof_id,
            'fecha': _lunes_siguiente().strftime('%Y-%m-%d'),
            'hora': hora,
            'status': 'confirmado',
        }, follow_redirects=True)

    def test_anular_empty_slot_marks_it_no_citar(self, app):
        """Sin turno cargado, el horario queda bloqueado igual."""
        from models import ScheduleException
        c = _create_and_login(app)
        prof_id = _create_professional(app)

        r = self._anular(c, prof_id, '11:00')
        assert r.status_code == 200
        assert 'NO CITAR' in r.data.decode()

        with app.app_context():
            exc = ScheduleException.query.one()
            assert exc.start_time == '11:00'
            assert exc.end_time == '11:30'
            assert exc.reason == 'No citar'

        html = c.get(f'/agenda/?profesional={prof_id}'
                     f'&fecha={_lunes_siguiente().strftime("%Y-%m-%d")}').data.decode()
        assert 'slot-row blocked' in html
        assert 'data-hora="11:00"' in html
        # la fila expone el permiso para poder deshacerlo desde el menú
        assert f'data-exc-id="{exc.id}"' in html

    def test_available_rows_carry_empty_exc_id(self, app):
        """Las filas libres avisan con exc_id vacío que no hay nada que habilitar."""
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        html = c.get(f'/agenda/?profesional={prof_id}'
                     f'&fecha={_lunes_siguiente().strftime("%Y-%m-%d")}').data.decode()
        assert 'data-exc-id=""' in html

    def test_anular_slot_with_appointment_cancels_and_blocks(self, app):
        """Con turno: se da de baja el turno y además queda NO CITAR."""
        from models import ScheduleException
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        self._agendar(c, app, prof_id, '09:30')

        r = self._anular(c, prof_id, '09:30')
        assert 'NO CITAR' in r.data.decode()

        with app.app_context():
            appt = Appointment.query.one()
            assert appt.status == 'cancelado'
            assert ScheduleException.query.count() == 1

        html = c.get(f'/agenda/?profesional={prof_id}'
                     f'&fecha={_lunes_siguiente().strftime("%Y-%m-%d")}').data.decode()
        i = html.find('data-hora="09:30"')
        assert i != -1
        # la fila que sigue siendo la de 09:30 es la de NO CITAR, no una
        # fila extra con la hora corrida (09:31)
        assert 'slot-row blocked' in html
        assert 'status-cancelado' not in html

    def test_no_citar_slot_cannot_be_booked(self, app):
        """Ni normal ni como sobreturno: un NO CITAR se respeta."""
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        self._anular(c, prof_id, '11:00')

        pid = _create_patient(app, full_name='Paciente Bloqueado',
                              document_id='53333333')
        base = {
            'patient_id': pid,
            'professional_id': prof_id,
            'fecha': _lunes_siguiente().strftime('%Y-%m-%d'),
            'hora': '11:00',
            'status': 'confirmado',
        }
        for extra in ({}, {'sobreturno': '1'}):
            data = dict(base, **extra)
            r = c.post('/agenda/nuevo', data=data, follow_redirects=True)
            assert 'NO CITAR' in r.data.decode()

        with app.app_context():
            assert Appointment.query.count() == 0

    def test_no_citar_blocks_intermediate_sobreturno(self, app):
        """Un sobreturno de 11:15 tampoco entra dentro de un NO CITAR 11:00."""
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        self._anular(c, prof_id, '11:00')
        pid = _create_patient(app, full_name='Rosa Diaz', document_id='52222222')
        c.post('/agenda/nuevo', data={
            'patient_id': pid,
            'professional_id': prof_id,
            'fecha': _lunes_siguiente().strftime('%Y-%m-%d'),
            'hora': '11:15',
            'sobreturno': '1',
            'status': 'confirmado',
        }, follow_redirects=True)
        with app.app_context():
            assert Appointment.query.count() == 0

    def test_enabling_a_blocked_slot_frees_it(self, app):
        """El mismo menú sirve para deshacer: habilita el horario."""
        from models import ScheduleException
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        self._anular(c, prof_id, '11:00')
        with app.app_context():
            exc_id = ScheduleException.query.one().id

        r = self._anular(c, prof_id, '11:00', exc_id=exc_id)
        assert 'habilitado' in r.data.decode()
        with app.app_context():
            assert ScheduleException.query.count() == 0

        html = c.get(f'/agenda/?profesional={prof_id}'
                     f'&fecha={_lunes_siguiente().strftime("%Y-%m-%d")}').data.decode()
        assert 'slot-row blocked' not in html
        assert 'data-exc-id=""' in html

    def test_no_citar_requires_professional(self, app):
        c = _create_and_login(app)
        _create_professional(app)
        r = c.post('/agenda/no-citar', data={
            'fecha': _lunes_siguiente().strftime('%Y-%m-%d'),
            'hora': '11:00',
        }, follow_redirects=True)
        assert 'Seleccioná un profesional' in r.data.decode()

    def test_menu_shows_habilitar_when_slot_is_blocked(self, app):
        """El menú alterna el rótulo según si el horario está bloqueado."""
        from models import ScheduleException
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        self._anular(c, prof_id, '11:00')
        with app.app_context():
            exc_id = ScheduleException.query.one().id

        html = c.get(f'/agenda/?profesional={prof_id}'
                     f'&fecha={_lunes_siguiente().strftime("%Y-%m-%d")}').data.decode()
        assert 'Habilitar turno' in html
        assert f'data-exc-id="{exc_id}"' in html
        assert 'anularLabel' in html


class TestAgendaAudit:
    """El registro de auditoría (AuditLog) también cubre la agenda."""

    def _fecha(self):
        return _lunes_siguiente().strftime('%Y-%m-%d')

    def _agendar(self, c, app, prof_id, hora='09:00', **extra):
        pid = _create_patient(app, full_name='Laura Testeo',
                              document_id='61111111')
        data = {
            'patient_id': pid,
            'professional_id': prof_id,
            'fecha': self._fecha(),
            'hora': hora,
            'status': 'confirmado',
        }
        data.update(extra)
        return c.post('/agenda/nuevo', data=data, follow_redirects=True)

    def _anular(self, c, prof_id, hora, **extra):
        data = {'fecha': self._fecha(), 'hora': hora,
                'professional_id': prof_id}
        data.update(extra)
        return c.post('/agenda/no-citar', data=data, follow_redirects=True)

    def _logs(self, app, **filtros):
        with app.app_context():
            return [(l.entity_type, l.action, l.entity_id, l.user_id,
                     json.loads(l.changes) if l.changes else None)
                    for l in AuditLog.query.filter_by(**filtros)
                    .order_by(AuditLog.id).all()]

    def test_crear_turno_registra_auditoria(self, app):
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        self._agendar(c, app, prof_id, '09:00')

        with app.app_context():
            assert Appointment.query.count() == 1
        logs = self._logs(app, entity_type='appointment', action='create')
        assert len(logs) == 1
        _, _, entity_id, user_id, datos = logs[0]
        assert user_id == _logged_user_id(app)
        assert datos['hora'] == '09:00'
        assert datos['paciente'] == 'Laura Testeo'
        assert datos['sobreturno'] is False

    def test_cambiar_estado_registra_antes_y_despues(self, app):
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        self._agendar(c, app, prof_id, '10:00')
        with app.app_context():
            appt_id = Appointment.query.one().id

        c.post(f'/agenda/{appt_id}/estado', data={'status': 'ausente_aviso'},
               follow_redirects=True)
        logs = self._logs(app, entity_type='appointment', action='update')
        assert len(logs) == 1
        datos = logs[0][4]
        assert datos['status'] == {'antes': 'confirmado',
                                   'después': 'ausente_aviso'}
        assert datos['paciente'] == 'Laura Testeo'

    def test_eliminar_turno_registra_el_borrado(self, app):
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        self._agendar(c, app, prof_id, '10:30')
        with app.app_context():
            appt_id = Appointment.query.one().id

        c.post(f'/agenda/{appt_id}/eliminar', follow_redirects=True)
        logs = self._logs(app, entity_type='appointment', action='delete')
        assert len(logs) == 1
        assert logs[0][2] == appt_id
        assert logs[0][4]['paciente'] == 'Laura Testeo'

    def test_reprogramar_registra_el_cambio(self, app):
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        self._agendar(c, app, prof_id, '11:00')
        with app.app_context():
            appt_id = Appointment.query.one().id

        c.post(f'/agenda/{appt_id}/reprogramar', data={
            'fecha': self._fecha(), 'hora': '14:00',
            'professional_id': prof_id,
        }, follow_redirects=True)
        datos = self._logs(app, entity_type='appointment',
                           action='update')[0][4]
        assert datos['hora'] == {'antes': '11:00', 'después': '14:00'}

    def test_no_citar_registra_el_bloqueo(self, app):
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        self._anular(c, prof_id, '15:00')

        logs = self._logs(app, entity_type='schedule_exception',
                          action='create')
        assert len(logs) == 1
        assert logs[0][3] == _logged_user_id(app)
        datos = logs[0][4]
        assert datos['fecha'] == self._fecha()
        assert datos['de'] == '15:00'
        assert datos['a'] == '15:30'
        assert datos['motivo'] == 'No citar'
        assert datos['profesional']  # nombre del profesional

    def test_anular_turno_con_paciente_registra_ambas_cosas(self, app):
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        self._agendar(c, app, prof_id, '15:30')
        self._anular(c, prof_id, '15:30')

        exc = self._logs(app, entity_type='schedule_exception',
                         action='create')
        assert len(exc) == 1
        cancel = self._logs(app, entity_type='appointment', action='update')
        assert len(cancel) == 1
        assert cancel[0][4]['status'] == {'antes': 'confirmado',
                                         'después': 'cancelado'}
        assert cancel[0][4]['accion'] == 'anulado desde el menú de la agenda'

    def test_habilitar_registra_el_borrado_del_bloqueo(self, app):
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        self._anular(c, prof_id, '15:00')
        with app.app_context():
            exc_id = ScheduleException.query.one().id

        self._anular(c, prof_id, '15:00', exc_id=exc_id)
        borrado = self._logs(app, entity_type='schedule_exception',
                             action='delete')
        assert len(borrado) == 1
        assert borrado[0][2] == exc_id

    def test_suspension_tambien_queda_registrada(self, app):
        c = _create_and_login(app)
        prof_id = _create_professional(app)
        c.post('/agenda/suspensiones/nuevo', data={
            'user_id': prof_id, 'fecha': self._fecha(),
            'start_time': '12:00', 'end_time': '13:00',
            'reason': 'Almuerzo',
        }, follow_redirects=True)
        datos = self._logs(app, entity_type='schedule_exception',
                           action='create')[0][4]
        assert datos['de'] == '12:00'
        assert datos['a'] == '13:00'
        assert datos['motivo'] == 'Almuerzo'
