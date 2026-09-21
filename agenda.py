import calendar
from datetime import date, datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user

from extensions import db
from models import Appointment, Patient, User, WorkSchedule, ScheduleException

bp = Blueprint('agenda', __name__, url_prefix='/agenda')

APPOINTMENT_STATUSES = {
    'pendiente': 'Pendiente',
    'confirmado': 'Confirmado',
    'presente': 'Paciente presente',
    'atendido': 'Atendido',
    'ausente': 'Ausente',
    'ausente_aviso': 'Ausente con aviso',
    'cancelado': 'Cancelado',
}

# Estados que indican que el paciente no cumplió el turno. Se pintan en rojo
# claro y al asignarlos el turno corre 1 minuto para conservar el registro.
NO_SHOW_STATUSES = {'ausente', 'ausente_aviso', 'cancelado'}


def _bump_minute(t, delta=1):
    """Suma (o resta, con delta negativo) minutos a una hora HH:MM."""
    try:
        hh, mm = (int(x) for x in t.split(':'))
    except (ValueError, AttributeError):
        return t
    total = (hh * 60 + mm + delta) % (24 * 60)
    return '%02d:%02d' % (divmod(total, 60))


def display_time(appt):
    """Hora a mostrar en pantalla para un turno. Si está cancelado/ausente,
    se le resta el minuto que se le sumó automáticamente al marcarlo (ver
    _bump_minute), para no mostrar una hora rara que parezca un error de
    carga."""
    if appt.status in NO_SHOW_STATUSES:
        return _bump_minute(appt.time, -1)
    return appt.time

def _parse_fecha_ar(raw):
    """Parsea una fecha en formato argentino dd/mm/aaaa (con fallback a aaaa-mm-dd
    por si llega en formato ISO, ej. desde un link generado por la propia app)."""
    for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime((raw or '').strip(), fmt).date()
        except (ValueError, TypeError):
            continue
    return None

DAY_NAMES = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']


def _safe_next(default):
    """Devuelve la URL de retorno (post/redirect) si es interna y segura."""
    nxt = request.form.get('next') or request.args.get('next')
    if nxt and nxt.startswith('/') and not nxt.startswith('//'):
        return nxt
    return default


def _schedule_rows(prof, d):
    """Filas del horario semanal de un profesional vigentes para la fecha d."""
    rows = (WorkSchedule.query
            .filter_by(user_id=prof.id, day_of_week=d.weekday())
            .all())
    return [r for r in rows if r.valid_from <= d <= r.valid_to]


def _exceptions_for(prof, d):
    return (ScheduleException.query
            .filter_by(user_id=prof.id, date=d)
            .all())


def _is_available(prof, d, t):
    """True si el profesional trabaja el día d a la hora t (HH:MM)."""
    rows = _schedule_rows(prof, d)
    if not rows:
        return False
    if not any(r.start_time <= t < r.end_time for r in rows):
        return False
    for e in _exceptions_for(prof, d):
        if e.start_time is None:
            return False
        if e.start_time <= t < e.end_time:
            return False
    return True


def _month_availability(year, month, profesionales):
    """Disponibilidad por día de cada profesional para el mes mostrado.
    Retorna { 'YYYY-MM-DD': { prof_id: {'start','end','suspended'} } }."""
    if month == 12:
        month_end = date(year + 1, 1, 1)
    else:
        month_end = date(year, month + 1, 1)
    month_start = date(year, month, 1)

    exceptions = (ScheduleException.query
                  .filter(ScheduleException.date >= month_start,
                          ScheduleException.date < month_end)
                  .all())
    exc_by_key = {}
    for e in exceptions:
        exc_by_key.setdefault((e.user_id, e.date), []).append(e)

    avail = {}
    weeks = calendar.Calendar(firstweekday=0).monthdayscalendar(year, month)
    for week in weeks:
        for day in week:
            if not day:
                continue
            d = date(year, month, day)
            iso = d.isoformat()
            for u in profesionales:
                rows = _schedule_rows(u, d)
                if not rows:
                    continue
                avail.setdefault(iso, {})[u.id] = {
                    'start': min(r.start_time for r in rows),
                    'end': max(r.end_time for r in rows),
                    'suspended': bool(exc_by_key.get((u.id, d))),
                }
    return avail


def _prev_next(year, month):
    if month == 1:
        return (year - 1, 12), (year, 2)
    if month == 12:
        return (year, 11), (year + 1, 1)
    return (year, month - 1), (year, month + 1)


@bp.route('/')
@login_required
def index():
    today = date.today()
    mes_raw = request.args.get('mes')
    try:
        year, month = (int(mes_raw[:4]), int(mes_raw[5:7])) if mes_raw else (today.year, today.month)
    except (ValueError, TypeError):
        year, month = today.year, today.month

    if month < 1 or month > 12:
        year, month = today.year, today.month

    fecha = None
    fecha_raw = request.args.get('fecha')
    if fecha_raw:
        try:
            fecha = datetime.strptime(fecha_raw, '%Y-%m-%d').date()
        except ValueError:
            fecha = None

    profesionales = User.query.order_by(User.full_name).all()
    profesional_raw = request.args.get('profesional', type=int)
    profesional = next((u for u in profesionales if u.id == profesional_raw), None)

    availability = _month_availability(year, month, profesionales)

    counts = {}
    for a in _agenda_in_month(year, month):
        counts[a.planned_date.isoformat()] = counts.get(a.planned_date.isoformat(), 0) + 1

    base_q = Appointment.query
    if profesional:
        base_q = base_q.filter(Appointment.professional_id == profesional.id)

    if fecha:
        # Vista de un día puntual: mostramos todo, incluidos cancelados o
        # ausentes, para tener el panorama completo de ese día.
        list_appts = base_q.filter_by(planned_date=fecha).order_by(Appointment.time).all()
    else:
        # "Próximos turnos": solo los que siguen activos, para no mezclar
        # cancelados/ausentes con lo que realmente hay que atender.
        list_appts = (base_q
                      .filter(Appointment.planned_date >= today)
                      .filter(~Appointment.status.in_(NO_SHOW_STATUSES))
                      .order_by(Appointment.planned_date, Appointment.time)
                      .limit(60)
                      .all())

    todos_hoy = (Appointment.query
                 .filter_by(planned_date=today)
                 .filter(~Appointment.status.in_(NO_SHOW_STATUSES))
                 .order_by(Appointment.time)
                 .all())

    prev_month, next_month = _prev_next(year, month)

    return render_template(
        'agenda.html',
        weeks=calendar.Calendar(firstweekday=0).monthdayscalendar(year, month),
        month=month,
        year=year,
        today=today,
        counts=counts,
        list_appts=list_appts,
        todos_hoy=todos_hoy,
        statuses=APPOINTMENT_STATUSES,
        prev_month=prev_month,
        next_month=next_month,
        fecha=fecha,
        month_name=calendar.month_name[month].capitalize(),
        profesionales=profesionales,
        profesional=profesional,
        availability=availability,
    )


@bp.route('/turnos')
@login_required
def turnos():
    """Listado de turnos de todos los profesionales, con filtros."""
    profesionales = User.query.order_by(User.full_name).all()
    profesional_raw = request.args.get('profesional', type=int)
    profesional = next((u for u in profesionales if u.id == profesional_raw), None)

    estado_raw = request.args.get('estado', '')
    estado = estado_raw if estado_raw in APPOINTMENT_STATUSES else ''

    rango = request.args.get('rango', 'proximos')
    if rango not in ('proximos', 'pasados', 'todos'):
        rango = 'proximos'

    fecha_raw = request.args.get('fecha', '').strip()
    fecha = None
    if fecha_raw:
        try:
            fecha = datetime.strptime(fecha_raw, '%Y-%m-%d').date()
        except ValueError:
            fecha = None

    q = request.args.get('q', '').strip()
    hoy = date.today()

    query = Appointment.query
    if profesional:
        query = query.filter(Appointment.professional_id == profesional.id)
    if estado:
        query = query.filter(Appointment.status == estado)
    if q:
        query = query.join(Patient).filter(db.or_(
            Patient.full_name.ilike(f'%{q}%'),
            Patient.document_id.ilike(f'%{q}%'),
        ))

    if fecha:
        query = query.filter(Appointment.planned_date == fecha)
        query = query.order_by(Appointment.time)
    elif rango == 'proximos':
        query = query.filter(Appointment.planned_date >= hoy)
        query = query.order_by(Appointment.planned_date, Appointment.time)
    elif rango == 'pasados':
        query = query.filter(Appointment.planned_date < hoy)
        query = query.order_by(Appointment.planned_date.desc(), Appointment.time.desc())
    else:
        query = query.order_by(Appointment.planned_date.desc(), Appointment.time.desc())

    lista = query.limit(1000).all()

    grupos = []
    for t in lista:
        if not grupos or grupos[-1]['date'] != t.planned_date:
            grupos.append({'date': t.planned_date, 'items': []})
        grupos[-1]['items'].append(t)

    return render_template(
        'agenda_turnos.html',
        grupos=grupos,
        total=len(lista),
        profesionales=profesionales,
        profesional=profesional,
        estado=estado,
        rango=rango,
        fecha=fecha,
        q=q,
        statuses=APPOINTMENT_STATUSES,
        hoy=hoy,
    )


def _agenda_in_month(year, month):
    if month == 12:
        month_end = date(year + 1, 1, 1)
    else:
        month_end = date(year, month + 1, 1)
    month_start = date(year, month, 1)
    return (Appointment.query
            .filter(Appointment.planned_date >= month_start,
                    Appointment.planned_date < month_end)
            .order_by(Appointment.planned_date, Appointment.time)
            .all())


@bp.route('/pacientes')
@login_required
def pacientes_json():
    """Búsqueda de pacientes por nombre o DNI para el autocompletado de turnos."""
    q = request.args.get('q', '').strip()
    query = Patient.query
    if q:
        query = query.filter(db.or_(
            Patient.full_name.ilike(f'%{q}%'),
            Patient.document_id.ilike(f'%{q}%'),
        ))
    results = query.order_by(Patient.full_name).limit(20).all()
    return jsonify({
        'ok': True,
        'results': [
            {
                'id': p.id,
                'full_name': p.full_name,
                'document_id': p.document_id or '',
            } for p in results
        ],
    })


@bp.route('/disponibilidad')
@login_required
def disponibilidad_json():
    """Disponibilidad de un profesional (o de todos) para un mes. Se usa
    para pintar el mini calendario del formulario de turnos."""
    mes_raw = request.args.get('mes')
    prof_raw = request.args.get('profesional', type=int)
    try:
        year, month = int(mes_raw[:4]), int(mes_raw[5:7])
    except (ValueError, TypeError):
        return jsonify({'ok': False, 'error': 'Mes inválido.'}), 400
    if month < 1 or month > 12:
        return jsonify({'ok': False, 'error': 'Mes inválido.'}), 400

    if prof_raw:
        usuarios = [u for u in [User.query.get(prof_raw)] if u]
    else:
        usuarios = User.query.all()
    availability = _month_availability(year, month, usuarios)
    return jsonify({'ok': True, 'availability': availability})


@bp.route('/nuevo', methods=['POST'])
@login_required
def nuevo():
    patient_id = request.form.get('patient_id')
    fecha_raw = request.form.get('fecha')
    hora = request.form.get('hora', '10:00')
    reason = request.form.get('reason', '').strip()
    status = request.form.get('status', 'confirmado')
    prof_raw = request.form.get('professional_id')

    if not patient_id or not fecha_raw or not prof_raw:
        flash('Paciente, profesional y fecha son obligatorios.', 'danger')
        return redirect(url_for('agenda.index'))

    try:
        fecha = datetime.strptime(fecha_raw, '%Y-%m-%d').date()
    except ValueError:
        try:
            fecha = datetime.strptime(fecha_raw, '%d/%m/%Y').date()
        except ValueError:
            flash('Fecha inválida.', 'danger')
            return redirect(url_for('agenda.index'))

    profesional = User.query.get(prof_raw)
    if not profesional:
        flash('Profesional inválido.', 'danger')
        return redirect(url_for('agenda.index'))

    if not _is_available(profesional, fecha, hora):
        flash(f'{profesional.full_name} no trabaja {fecha.strftime("%d/%m/%Y")} a las {hora} '
              f'(fuera de su horario o suspendido).', 'warning')
        return redirect(url_for('agenda.index', fecha=fecha_raw, mes=fecha_raw[:7], profesional=prof_raw))

    choque = (Appointment.query
              .filter_by(planned_date=fecha, time=hora, professional_id=profesional.id)
              .filter(Appointment.status != 'cancelado')
              .first())
    if choque:
        flash(f'Advertencia: {profesional.full_name} ya tiene un turno a las {hora} con '
              f'{choque.patient.full_name}. No se puede agendar 2 pacientes en el mismo horario.', 'danger')
        return redirect(url_for('agenda.index', fecha=fecha_raw, mes=fecha_raw[:7], profesional=prof_raw))

    turno = Appointment(
        patient_id=int(patient_id),
        professional_id=profesional.id,
        planned_date=fecha,
        time=hora or '10:00',
        reason=reason or None,
        status=status if status in APPOINTMENT_STATUSES else 'confirmado',
        created_by_id=current_user.id,
    )
    db.session.add(turno)
    db.session.commit()
    flash('Turno agendado.', 'success')
    return redirect(url_for('agenda.index', fecha=fecha_raw, mes=fecha_raw[:7], profesional=prof_raw))


@bp.route('/<int:appt_id>/eliminar', methods=['POST'])
@login_required
def eliminar(appt_id):
    turno = Appointment.query.get_or_404(appt_id)
    prof = turno.professional_id
    db.session.delete(turno)
    db.session.commit()
    flash('Turno eliminado.', 'info')
    return redirect(_safe_next(url_for('agenda.index', profesional=prof)))


@bp.route('/<int:appt_id>/estado', methods=['POST'])
@login_required
def estado(appt_id):
    turno = Appointment.query.get_or_404(appt_id)
    prof = turno.professional_id
    nuevo = request.form.get('status')
    if nuevo in APPOINTMENT_STATUSES:
        anterior = turno.status
        turno.status = nuevo
        # Al marcar ausencia/cancelación corremos 1 minuto el turno para
        # conservar el registro sin ocupar el horario original.
        if nuevo in NO_SHOW_STATUSES and anterior not in NO_SHOW_STATUSES:
            turno.time = _bump_minute(turno.time)
        db.session.commit()
        flash('Estado del turno actualizado.', 'success')
    return redirect(_safe_next(url_for('agenda.index', profesional=prof)))


@bp.route('/<int:appt_id>/reprogramar', methods=['POST'])
@login_required
def reprogramar(appt_id):
    turno = Appointment.query.get_or_404(appt_id)
    fecha_raw = request.form.get('fecha', '')
    hora = (request.form.get('hora') or '').strip() or '10:00'
    prof_raw = request.form.get('professional_id') or turno.professional_id

    back = url_for('agenda.turnos', profesional=request.form.get('filtro_profesional') or '')

    try:
        try:
            fecha = datetime.strptime(fecha_raw, '%Y-%m-%d').date()
        except ValueError:
            fecha = datetime.strptime(fecha_raw, '%d/%m/%Y').date()
    except (ValueError, TypeError):
        flash('Fecha inválida.', 'danger')
        return redirect(back)

    profesional = User.query.get(prof_raw)
    if not profesional:
        flash('Profesional inválido.', 'danger')
        return redirect(back)

    if not _is_available(profesional, fecha, hora):
        flash(f'{profesional.full_name} no trabaja {fecha.strftime("%d/%m/%Y")} a las {hora} '
              f'(fuera de su horario o suspendido).', 'warning')
        return redirect(back)

    choque = (Appointment.query
              .filter(Appointment.id != turno.id)
              .filter_by(planned_date=fecha, time=hora, professional_id=profesional.id)
              .filter(Appointment.status != 'cancelado')
              .first())
    if choque:
        flash(f'{profesional.full_name} ya tiene un turno a las {hora} con '
              f'{choque.patient.full_name}.', 'danger')
        return redirect(back)

    turno.planned_date = fecha
    turno.time = hora
    turno.professional_id = profesional.id
    db.session.commit()
    flash('Turno reprogramado.', 'success')
    return redirect(back)


# ---------------------------------------------------------------------
# Horarios de trabajo y suspensiones de los profesionales
# ---------------------------------------------------------------------

@bp.route('/horarios')
@login_required
def horarios():
    profesionales = User.query.order_by(User.full_name).all()
    schedules = (WorkSchedule.query
                 .order_by(WorkSchedule.user_id, WorkSchedule.day_of_week)
                 .all())
    exceptions = (ScheduleException.query
                  .order_by(ScheduleException.date.desc())
                  .all())
    hoy = date.today()
    return render_template(
        'agenda_horarios.html',
        profesionales=profesionales,
        schedules=schedules,
        exceptions=exceptions,
        hoy=hoy,
        default_valid_to=hoy + timedelta(days=364),
        day_names=DAY_NAMES,
    )

@bp.route('/horarios/nuevo', methods=['POST'])
@login_required
def horario_nuevo():
    prof_raw = request.form.get('user_id')
    days = [d for d in request.form.getlist('days') if d.isdigit()]
    start = (request.form.get('start_time') or '').strip()
    end = (request.form.get('end_time') or '').strip()
    valid_from_raw = request.form.get('valid_from')
    valid_to_raw = request.form.get('valid_to')

    def _bad(msg):
        flash(msg, 'danger')
        return redirect(url_for('agenda.horarios'))

    profesional = User.query.get(prof_raw) if prof_raw else None
    if not profesional:
        return _bad('Seleccioná un profesional.')
    if not days:
        return _bad('Marcá al menos un día de la semana.')
    if not start or not end or start >= end:
        return _bad('Franja horaria inválida (inicio y fin obligatorios, inicio < fin).')

    valid_from = _parse_fecha_ar(valid_from_raw)
    valid_to = _parse_fecha_ar(valid_to_raw)
    if not valid_from or not valid_to:
        return _bad('Las fechas de vigencia son obligatorias (dd/mm/aaaa).')
    if valid_to < valid_from:
        return _bad('La fecha de fin no puede ser anterior a la de inicio.')

    for day in sorted(set(int(d) for d in days)):
        db.session.add(WorkSchedule(
            user_id=profesional.id,
            day_of_week=day,
            start_time=start,
            end_time=end,
            valid_from=valid_from,
            valid_to=valid_to,
        ))
    db.session.commit()
    flash(f'Horario asignado a {profesional.full_name}.', 'success')
    return redirect(url_for('agenda.horarios'))


@bp.route('/horarios/<int:sched_id>/eliminar', methods=['POST'])
@login_required
def horario_eliminar(sched_id):
    sched = WorkSchedule.query.get_or_404(sched_id)
    db.session.delete(sched)
    db.session.commit()
    flash('Horario eliminado.', 'info')
    return redirect(url_for('agenda.horarios'))

@bp.route('/suspensiones/nuevo', methods=['POST'])
@login_required
def suspension_nueva():
    prof_raw = request.form.get('user_id')
    fecha_raw = request.form.get('fecha')
    start = (request.form.get('start_time') or '').strip() or None
    end = (request.form.get('end_time') or '').strip() or None
    reason = (request.form.get('reason') or '').strip()

    def _bad(msg):
        flash(msg, 'danger')
        return redirect(url_for('agenda.horarios'))

    profesional = User.query.get(prof_raw) if prof_raw else None
    if not profesional:
        return _bad('Seleccioná un profesional.')

    fecha = _parse_fecha_ar(fecha_raw)
    if not fecha:
        return _bad('Fecha inválida (formato dd/mm/aaaa).')
    if start and end and start >= end:
        return _bad('Franja de suspensión inválida (inicio < fin).')

    db.session.add(ScheduleException(
        user_id=profesional.id,
        date=fecha,
        start_time=start,
        end_time=end,
        reason=reason or None,
    ))
    db.session.commit()
    flash('Suspensión registrada.', 'success')
    return redirect(url_for('agenda.horarios'))


@bp.route('/suspensiones/<int:exc_id>/eliminar', methods=['POST'])
@login_required
def suspension_eliminar(exc_id):
    exc = ScheduleException.query.get_or_404(exc_id)
    db.session.delete(exc)
    db.session.commit()
    flash('Suspensión eliminada.', 'info')
    return redirect(url_for('agenda.horarios'))


@bp.route('/exportar/ics')
@login_required
def export_ics():
    """Genera un archivo .ics con los turnos filtrados."""
    profesional_raw = request.args.get('profesional', type=int)
    rango = request.args.get('rango', 'proximos')
    hoy = date.today()

    query = Appointment.query.filter(Appointment.status != 'cancelado')
    if profesional_raw:
        query = query.filter(Appointment.professional_id == profesional_raw)
    if rango == 'proximos':
        query = query.filter(Appointment.planned_date >= hoy)
    elif rango == 'pasados':
        query = query.filter(Appointment.planned_date < hoy)
    query = query.order_by(Appointment.planned_date, Appointment.time)

    appointments = query.all()

    from flask import Response
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//Consultorio Odontologico//Agenda//ES',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        'X-WR-CALNAME:Agenda Consultorio',
    ]

    for appt in appointments:
        try:
            hh, mm = (int(x) for x in (appt.time or '10:00').split(':'))
        except (ValueError, AttributeError):
            hh, mm = 10, 0

        dt_start = datetime.combine(appt.planned_date, datetime.min.time().replace(hour=hh, minute=mm))
        dt_end = dt_start + timedelta(minutes=60)
        dtstamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')

        summary_parts = []
        if appt.patient:
            summary_parts.append(appt.patient.full_name)
        if appt.professional:
            summary_parts.append(appt.professional.full_name)
        summary = ' - '.join(summary_parts) if summary_parts else 'Turno'

        desc_parts = []
        if appt.reason:
            desc_parts.append(f'Motivo: {appt.reason}')
        desc_parts.append(f'Estado: {APPOINTMENT_STATUSES.get(appt.status, appt.status)}')
        description = '\\n'.join(desc_parts)

        uid = f'appt-{appt.id}@consultorio'

        lines.extend([
            'BEGIN:VEVENT',
            f'UID:{uid}',
            f'DTSTAMP:{dtstamp}',
            f'DTSTART:{dt_start.strftime("%Y%m%dT%H%M%S")}',
            f'DTEND:{dt_end.strftime("%Y%m%dT%H%M%S")}',
            f'SUMMARY:{summary}',
            f'DESCRIPTION:{description}',
            'END:VEVENT',
        ])

    lines.append('END:VCALENDAR')

    ics_content = '\r\n'.join(lines)
    return Response(
        ics_content,
        mimetype='text/calendar',
        headers={'Content-Disposition': 'attachment;filename=agenda.ics'},
    )
