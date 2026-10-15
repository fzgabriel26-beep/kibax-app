import calendar
import datetime as _dt
from datetime import date, datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, abort
from flask_login import login_required, current_user

from extensions import db
from models import (
    Appointment, Patient, User, WorkSchedule, ScheduleException,
    WaitingListEntry, WAITLIST_SHIFTS,
)

bp = Blueprint('agenda', __name__, url_prefix='/agenda')

APPOINTMENT_STATUSES = {
    'pendiente': 'Pendiente',
    'confirmado': 'Confirmado',
    'presente': 'Paciente presente',
    'atendido': 'Atendido',
    'ausente_aviso': 'Ausente con aviso',
    'ausente_sin_aviso': 'Ausente sin aviso',
    'cancelado': 'Cancelado',
}

# Estados que indican que el paciente no cumplió el turno. Se pintan en rojo
# claro y al asignarlos el turno corre 1 minuto para conservar el registro.
# (El genérico 'ausente' se eliminó: ahora hay que aclarar si avisó o no.)
NO_SHOW_STATUSES = {'ausente_aviso', 'ausente_sin_aviso', 'cancelado'}

# Clase CSS que colorea cada estado en los <select> y en las etiquetas.
# El mapeo va aparte de APPOINTMENT_STATUSES para poder nombrar las clases
# con guiones (ausente_sin_aviso -> st-ausente-sin-aviso).
STATUS_CLASSES = {
    'pendiente': '',
    'confirmado': 'st-confirmado',
    'presente': 'st-presente',
    'atendido': 'st-atendido',
    'ausente_aviso': 'st-ausente-aviso',
    'ausente_sin_aviso': 'st-ausente-sin-aviso',
    'cancelado': 'st-cancelado',
}


def status_class(status):
    """Clase CSS de un estado de turno ('' si es pendiente o desconocido)."""
    return STATUS_CLASSES.get(status, '')


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


def _parse_hora(raw):
    """Valida y normaliza una hora a 'HH:MM'. Devuelve None si no es válida."""
    raw = (raw or '').strip()
    if len(raw) != 5 or raw[2] != ':':
        return None
    try:
        hh, mm = int(raw[:2]), int(raw[3:])
    except ValueError:
        return None
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        return None
    return '%02d:%02d' % (hh, mm)


def _parse_fecha_ar(raw):
    """Parsea una fecha en formato argentino dd/mm/aaaa, ISO aaaa-mm-dd o
    aaaa-día-mes (formato erróneo que enviaba una versión vieja del JS del
    modal de turnos y terminaba en 'Fecha inválida')."""
    raw = (raw or '').strip()
    for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(raw, fmt).date()
        except (ValueError, TypeError):
            continue
    try:
        y, d, m = raw.split('-')
        return date(int(y), int(m), int(d))
    except (ValueError, AttributeError):
        return None

DAY_NAMES = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
MESES_ES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
            'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']


def fecha_larga(d):
    """'Lunes, 13 de octubre de 2026' — en español (el strftime del sistema
    devuelve los nombres en inglés)."""
    return f'{DAY_NAMES[d.weekday()]}, {d.day:02d} de {MESES_ES[d.month - 1].lower()} de {d.year}'


def fecha_lista(d):
    """'Lunes 13/10/2026' — en español."""
    return f'{DAY_NAMES[d.weekday()]} {d.strftime("%d/%m/%Y")}'


def _safe_next(default):
    """Devuelve la URL de retorno (post/redirect) si es interna y segura."""
    nxt = request.form.get('next') or request.args.get('next')
    if nxt and nxt.startswith('/') and not nxt.startswith('//'):
        return nxt
    return default


def _volver_a(fecha, profesional):
    """URL de la agenda integrada para ese día y profesional."""
    return url_for(
        'agenda.index',
        fecha=fecha.isoformat(),
        mes=f'{fecha.year:04d}-{fecha.month:02d}',
        profesional=profesional.id,
    )


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


def _exc_cubre(e, t):
    """¿La suspensión/permiso e cubre la hora t (HH:MM)?

    `start_time is None` significa que suspende el día completo. Si hay
    `start_time` sin `end_time`, se toma como "desde esa hora en adelante".
    """
    if e.start_time is None:
        return True
    if e.end_time is None:
        return e.start_time <= t
    return e.start_time <= t < e.end_time


def _exc_que_cubre(exceptions, t):
    """Primera suspensión de la lista que cubre la hora t (o None)."""
    return next((e for e in exceptions if _exc_cubre(e, t)), None)


def _is_available(prof, d, t):
    """True si se puede agendar con prof el día d a la hora t (HH:MM).

    Si el profesional tiene horario cargado para ese día se respeta el rango
    laboral. Si no tiene ninguno, la agenda queda abierta de 8:00 a 20:00
    (antes devolvía False y no dejaba agendar ningún turno). Las
    suspensiones cargadas se respetan siempre.
    """
    rows = _schedule_rows(prof, d)
    if rows and not any(r.start_time <= t < r.end_time for r in rows):
        return False
    if _exc_que_cubre(_exceptions_for(prof, d), t) is not None:
        return False
    if not rows:
        # Sin horario cargado: rango genérico de la consulta
        return '08:00' <= t < '20:00'
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
                dias = exc_by_key.get((u.id, d), [])
                avail.setdefault(iso, {})[u.id] = {
                    'start': min(r.start_time for r in rows),
                    'end': max(r.end_time for r in rows),
                    # 'suspended' significa "el día entero": una franja
                    # parcial (o un "no citar" de media hora) no tacha
                    # el día en el calendario.
                    'suspended': any(e.start_time is None for e in dias),
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

    # Lista de espera del panel lateral: lo más viejo primero.
    waitlist = (WaitingListEntry.query
                .order_by(WaitingListEntry.created_at.asc())
                .all())

    # La agenda siempre es de UN profesional: si no eligieron, mostramos el
    # primero de la lista y caemos en el día de hoy (redirigimos para que la
    # URL quede compartible).
    if profesional is None and profesionales:
        params = {k: v for k, v in request.args.to_dict().items() if v}
        # Sobrescribimos siempre: si el id venía vacío o era inválido
        # (profesional eliminado), evitamos un redirect loop.
        params['profesional'] = str(profesionales[0].id)
        params.setdefault('fecha', today.isoformat())
        params.setdefault('mes', f'{today.year:04d}-{today.month:02d}')
        return redirect(url_for('agenda.index', **params))

    availability = _month_availability(year, month, profesionales)

    # Conteo de turnos por día para el mini calendario
    counts = {}
    for a in _agenda_in_month(year, month):
        counts[a.planned_date.isoformat()] = counts.get(a.planned_date.isoformat(), 0) + 1

    base_q = Appointment.query
    if profesional:
        base_q = base_q.filter(Appointment.professional_id == profesional.id)

    if fecha:
        list_appts = base_q.filter_by(planned_date=fecha).order_by(Appointment.time).all()
    else:
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

    # Slots del día: si hay profesional, mostrar todos los slots de su horario.
    # Si no, mostrar slots genéricos 8:00-20:00 cada 30 min.
    day_slots = []
    if fecha:
        appts_by_time = {a.time[:5]: a for a in list_appts}

        schedule = _schedule_rows(profesional, fecha) if profesional else []
        exceptions = _exceptions_for(profesional, fecha) if profesional else []

        if schedule:
            # Generar slots desde el inicio hasta el fin del horario
            earliest = min(r.start_time for r in schedule)
            latest = max(r.end_time for r in schedule)
            sh, sm = int(earliest[:2]), int(earliest[3:5])
            eh, em = int(latest[:2]), int(latest[3:5])
        else:
            # Sin horario configurado: slots genéricos
            sh, sm, eh, em = 8, 0, 20, 0

        h, m = sh, sm
        while (h, m) < (eh, em):
            t = f'{h:02d}:{m:02d}'
            # Un "no citar" suspende ese horario aunque el profesional no
            # tenga horario cargado (franja genérica 8:00-20:00).
            exc = _exc_que_cubre(exceptions, t)
            if schedule:
                is_work = any(r.start_time <= t < r.end_time for r in schedule)
                available = is_work and exc is None
            else:
                available = exc is None
            day_slots.append({
                'time': t,
                'available': available,
                'appointment': appts_by_time.get(t),
                'suspension': exc,
            })
            m += 30
            if m >= 60:
                h += 1
                m = 0

        # Si por algún motivo quedó fuera un turno (hora fuera del rango),
        # lo agregamos al final para que nunca se pierda de vista.
        placed = {s['time'] for s in day_slots}
        for t, a in sorted(appts_by_time.items()):
            if t in placed:
                continue
            # Un turno anulado cuyo horario quedó marcado como NO CITAR no
            # se muestra aparte: la fila del bloque ya lo representa y una
            # fila extra (09:31) solo enredaría la vista.
            if a.status in NO_SHOW_STATUSES and \
                    _exc_que_cubre(exceptions, display_time(a)) is not None:
                continue
            day_slots.append({'time': t, 'available': False, 'appointment': a})
        day_slots.sort(key=lambda s: s['time'])

    # Contar turnos y disponibles para el header
    total_turnos = len(list_appts)
    disponibles = sum(1 for s in day_slots if s['available'] and not s['appointment'])

    prev_month, next_month = _prev_next(year, month)

    # Día de referencia para la barra de navegación (flechas ‹ ›)
    day_ref = fecha or today
    prev_day = day_ref - timedelta(days=1)
    next_day = day_ref + timedelta(days=1)

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
        no_show_statuses=NO_SHOW_STATUSES,
        prev_month=prev_month,
        next_month=next_month,
        fecha=fecha,
        month_name=MESES_ES[month - 1],
        profesionales=profesionales,
        profesional=profesional,
        availability=availability,
        day_slots=day_slots,
        total_turnos=total_turnos,
        disponibles=disponibles,
        prev_day=prev_day,
        next_day=next_day,
        waitlist=waitlist,
        waitlist_shifts=WAITLIST_SHIFTS,
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
        no_show_statuses=NO_SHOW_STATUSES,
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
        usuarios = [u for u in [db.session.get(User, prof_raw)] if u]
    else:
        usuarios = User.query.all()
    availability = _month_availability(year, month, usuarios)
    return jsonify({'ok': True, 'availability': availability})


@bp.route('/nuevo', methods=['POST'])
@login_required
def nuevo():
    patient_id = request.form.get('patient_id')
    fecha_raw = request.form.get('fecha')
    reason = request.form.get('reason', '').strip()
    status = request.form.get('status', 'confirmado')
    prof_raw = request.form.get('professional_id')
    # Un sobreturno elige el horario a mano (ej. 09:15 dentro del bloque de
    # 09:00 a 09:30) y puede caer fuera del horario del profesional.
    es_sobreturno = request.form.get('sobreturno') in ('1', 'true', 'on', 'si', 'sí')
    hora = _parse_hora(request.form.get('hora'))

    if not patient_id or not fecha_raw or not prof_raw:
        flash('Paciente, profesional y fecha son obligatorios.', 'danger')
        return redirect(url_for('agenda.index'))

    if not hora:
        flash('La hora debe tener formato HH:MM (ej. 09:15).', 'danger')
        return redirect(_safe_next(url_for('agenda.index')))

    fecha = _parse_fecha_ar(fecha_raw)
    if not fecha:
        flash('Fecha inválida.', 'danger')
        return redirect(url_for('agenda.index'))

    profesional = db.session.get(User, prof_raw)
    if not profesional:
        flash('Profesional inválido.', 'danger')
        return redirect(url_for('agenda.index'))

    # Un "NO CITAR" es una decisión explícita: se respeta aunque el turno
    # se cargue como sobreturno (el sobreturno solo saltea el horario del
    # profesional, no un horario que se mandó a anular).
    marcado = _exc_que_cubre(_exceptions_for(profesional, fecha), hora)
    if marcado is not None:
        detalle = marcado.reason or 'horario bloqueado'
        flash(f'Las {hora} están marcadas como NO CITAR ({detalle}). '
              f'Para agendar ahí, habilitalas desde el menú del horario '
              f'o desde Suspensiones.', 'danger')
        return redirect(_volver_a(fecha, profesional))

    fuera_de_horario = not _is_available(profesional, fecha, hora)
    if fuera_de_horario and not es_sobreturno:
        flash(f'{profesional.full_name} no atiende {fecha.strftime("%d/%m/%Y")} a las {hora} '
              f'(fuera de su horario o suspendido). Si es un sobreturno, cargalo como tal.', 'warning')
        return redirect(_volver_a(fecha, profesional))

    choque = (Appointment.query
              .filter_by(planned_date=fecha, time=hora, professional_id=profesional.id)
              .filter(Appointment.status != 'cancelado')
              .first())
    if choque:
        flash(f'Advertencia: {profesional.full_name} ya tiene un turno a las {hora} con '
              f'{choque.patient.full_name}. No se puede agendar 2 pacientes en el mismo horario.', 'danger')
        return redirect(_volver_a(fecha, profesional))

    turno = Appointment(
        patient_id=int(patient_id),
        professional_id=profesional.id,
        planned_date=fecha,
        time=hora,
        reason=reason or None,
        status=status if status in APPOINTMENT_STATUSES else 'confirmado',
        created_by_id=current_user.id,
    )
    db.session.add(turno)
    db.session.commit()
    if fuera_de_horario:
        flash(f'Sobreturno agendado a las {hora}, fuera del horario habitual de '
              f'{profesional.full_name}.', 'success')
    else:
        flash('Sobreturno agendado.' if es_sobreturno else 'Turno agendado.', 'success')

    # Si el turno salió de la lista de espera, sacamos la fila para que no
    # siga figurando como pendiente de agenda.
    wait_id = request.form.get('waitlist_id', type=int)
    if wait_id:
        entrada = db.session.get(WaitingListEntry, wait_id)
        if entrada:
            db.session.delete(entrada)
            db.session.commit()
            flash('Paciente quitado de la lista de espera.', 'info')

    return redirect(_volver_a(fecha, profesional))


@bp.route('/lista-espera', methods=['POST'])
@login_required
def lista_espera_nueva():
    """Agrega un paciente a la lista de espera del panel lateral."""
    patient_id = request.form.get('patient_id', type=int)
    prof_raw = request.form.get('professional_id', type=int)
    shift = request.form.get('shift', 'manana')
    note = (request.form.get('note') or '').strip()

    if not patient_id:
        flash('Elegí un paciente de la lista.', 'danger')
        return redirect(_safe_next(url_for('agenda.index')))

    paciente = db.session.get(Patient, patient_id)
    if not paciente:
        flash('Paciente inválido.', 'danger')
        return redirect(_safe_next(url_for('agenda.index')))

    if shift not in WAITLIST_SHIFTS:
        shift = 'manana'

    profesional = db.session.get(User, prof_raw) if prof_raw else None

    repetida = (WaitingListEntry.query
                .filter_by(patient_id=paciente.id)
                .first())
    if repetida:
        flash(f'{paciente.full_name} ya está en la lista de espera.', 'warning')
        return redirect(_safe_next(url_for('agenda.index')))

    db.session.add(WaitingListEntry(
        patient_id=paciente.id,
        professional_id=profesional.id if profesional else None,
        shift=shift,
        note=note or None,
        created_by_id=current_user.id,
    ))
    db.session.commit()
    flash(f'{paciente.full_name} agregado a la lista de espera.', 'success')
    return redirect(_safe_next(url_for('agenda.index')))


@bp.route('/lista-espera/<int:entry_id>/eliminar', methods=['POST'])
@login_required
def lista_espera_eliminar(entry_id):
    """Quita un paciente de la lista de espera."""
    entrada = db.session.get(WaitingListEntry, entry_id)
    if not entrada:
        abort(404)
    nombre = entrada.patient.full_name
    db.session.delete(entrada)
    db.session.commit()
    flash(f'{nombre} quitado de la lista de espera.', 'success')
    return redirect(_safe_next(url_for('agenda.index')))


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


@bp.route('/no-citar', methods=['POST'])
@login_required
def no_citar():
    """"Anular turno" desde el menú de la agenda.

    Marca un horario como NO CITAR, haya turno cargado o no:

    * con turno  -> da de baja el turno y bloquea el horario
    * sin turno  -> bloquea directamente el horario

    Si el horario ya estaba bloqueado se elimina el permiso y vuelve a
    quedar disponible (así el mismo menú sirve para deshacer).
    """
    fecha = _parse_fecha_ar(request.form.get('fecha'))
    hora = _parse_hora(request.form.get('hora'))
    prof_raw = request.form.get('professional_id', type=int)
    appt_id = request.form.get('appt_id', type=int)
    exc_id = request.form.get('exc_id', type=int)

    if not fecha:
        flash('Fecha inválida para anular un horario.', 'danger')
        return redirect(_safe_next(url_for('agenda.index')))

    profesional = db.session.get(User, prof_raw) if prof_raw else None
    if not profesional:
        flash('Seleccioná un profesional para anular un horario.', 'danger')
        return redirect(_safe_next(url_for('agenda.index')))

    volver = _safe_next(_volver_a(fecha, profesional))

    if exc_id:
        # Ya estaba marcado como NO CITAR: lo habilitamos de nuevo.
        exc = db.session.get(ScheduleException, exc_id)
        if exc and exc.user_id == profesional.id:
            db.session.delete(exc)
            db.session.commit()
            flash(f'Horario de las {exc.start_time or "--:--"} habilitado.',
                  'info')
        return redirect(volver)

    if not hora:
        flash('Horario inválido para anular.', 'danger')
        return redirect(volver)

    # Si en ese horario había un turno cargado, lo damos de baja.
    cancelado = None
    turno = db.session.get(Appointment, appt_id) if appt_id else None
    if turno is None:
        # Por si el menú no mandó el id: buscamos el turno de ese horario.
        turno = (Appointment.query
                 .filter_by(planned_date=fecha, time=hora,
                            professional_id=profesional.id)
                 .filter(Appointment.status.notin_(NO_SHOW_STATUSES))
                 .first())
    if turno and turno.professional_id == profesional.id \
            and turno.status not in NO_SHOW_STATUSES:
        turno.status = 'cancelado'
        turno.time = _bump_minute(turno.time)
        cancelado = turno

    # Bloqueamos la media hora siguiente ("NO CITAR ESTE TURNO").
    fin = _bump_minute(hora, 30)
    existente = (ScheduleException.query
                 .filter_by(user_id=profesional.id, date=fecha,
                            start_time=hora, end_time=fin)
                 .first())
    if not existente:
        db.session.add(ScheduleException(
            user_id=profesional.id,
            date=fecha,
            start_time=hora,
            end_time=fin,
            reason='No citar',
        ))
    db.session.commit()

    nombre = cancelado.patient.full_name if cancelado and cancelado.patient else ''
    if nombre:
        flash(f'Turno de {nombre} anulado y horario de las {hora} '
              f'marcado como NO CITAR.', 'success')
    else:
        flash(f'Horario de las {hora} marcado como NO CITAR.', 'success')

    return redirect(_safe_next(
        url_for('agenda.index', fecha=fecha.isoformat(),
                profesional=profesional.id)))


@bp.route('/<int:appt_id>/reprogramar', methods=['POST'])
@login_required
def reprogramar(appt_id):
    turno = Appointment.query.get_or_404(appt_id)
    fecha_raw = request.form.get('fecha', '')
    hora = (request.form.get('hora') or '').strip() or '10:00'
    prof_raw = request.form.get('professional_id') or turno.professional_id

    fecha = _parse_fecha_ar(fecha_raw)
    if not fecha:
        flash('Fecha inválida.', 'danger')
        return redirect(url_for('agenda.index'))

    profesional = db.session.get(User, prof_raw)
    if not profesional:
        flash('Profesional inválido.', 'danger')
        return redirect(url_for('agenda.index', fecha=fecha.isoformat()))

    back = _volver_a(fecha, profesional)

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

    profesional = db.session.get(User, prof_raw) if prof_raw else None
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

    profesional = db.session.get(User, prof_raw) if prof_raw else None
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


# ---------------------------------------------------------------------
# CRUD de profesionales
# ---------------------------------------------------------------------

@bp.route('/profesionales')
@login_required
def list_profesionales():
    """Listado de profesionales/odontólogos."""
    from models import User
    profesionales = User.query.order_by(User.full_name).all()
    return render_template('agenda/profesionales.html', profesionales=profesionales)


@bp.route('/profesionales/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_profesional():
    """Crear un nuevo profesional."""
    from models import User
    from auth import _password_strength, _validate_email

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        license_number = request.form.get('license_number', '').strip()
        password = request.form.get('password', '')

        if not full_name or not email:
            flash('Nombre y email son obligatorios.', 'danger')
            return render_template('agenda/profesional_form.html', form=request.form, action='create')

        email_err = _validate_email(email)
        if email_err:
            flash(email_err, 'danger')
            return render_template('agenda/profesional_form.html', form=request.form, action='create')

        if User.query.filter_by(email=email).first():
            flash('Ya existe un profesional con ese email.', 'danger')
            return render_template('agenda/profesional_form.html', form=request.form, action='create')

        if not password:
            flash('La contraseña es obligatoria para nuevos profesionales.', 'danger')
            return render_template('agenda/profesional_form.html', form=request.form, action='create')

        pw_err = _password_strength(password)
        if pw_err:
            flash(pw_err, 'danger')
            return render_template('agenda/profesional_form.html', form=request.form, action='create')

        u = User(full_name=full_name, email=email, license_number=license_number)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        flash(f'Profesional {full_name} creado correctamente.', 'success')
        return redirect(url_for('agenda.list_profesionales'))

    return render_template('agenda/profesional_form.html', form={}, action='create')


@bp.route('/profesionales/<int:user_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_profesional(user_id):
    """Editar un profesional existente."""
    from models import User
    from auth import _validate_email

    user = db.session.get(User, user_id)
    if not user:
        abort(404)

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        license_number = request.form.get('license_number', '').strip()

        if not full_name or not email:
            flash('Nombre y email son obligatorios.', 'danger')
            return render_template('agenda/profesional_form.html', form=request.form, action='edit', user=user)

        email_err = _validate_email(email)
        if email_err:
            flash(email_err, 'danger')
            return render_template('agenda/profesional_form.html', form=request.form, action='edit', user=user)

        existing = User.query.filter(User.email == email, User.id != user_id).first()
        if existing:
            flash('Ya existe otro profesional con ese email.', 'danger')
            return render_template('agenda/profesional_form.html', form=request.form, action='edit', user=user)

        user.full_name = full_name
        user.email = email
        user.license_number = license_number

        # Actualizar contraseña solo si se proporcionó una nueva
        new_password = request.form.get('password', '').strip()
        if new_password:
            from auth import _password_strength
            pw_err = _password_strength(new_password)
            if pw_err:
                flash(pw_err, 'danger')
                return render_template('agenda/profesional_form.html', form=request.form, action='edit', user=user)
            user.set_password(new_password)

        db.session.commit()
        flash(f'Profesional {full_name} actualizado.', 'success')
        return redirect(url_for('agenda.list_profesionales'))

    form = {
        'full_name': user.full_name or '',
        'email': user.email or '',
        'license_number': user.license_number or '',
    }
    return render_template('agenda/profesional_form.html', form=form, action='edit', user=user)


@bp.route('/profesionales/<int:user_id>/eliminar', methods=['POST'])
@login_required
def eliminar_profesional(user_id):
    """Eliminar un profesional."""
    from models import User
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    if user.id == current_user.id:
        flash('No podés eliminar tu propia cuenta.', 'danger')
        return redirect(url_for('agenda.list_profesionales'))

    # Verificar si tiene turnos activos
    from datetime import date as _date
    turnos_activos = Appointment.query.filter(
        Appointment.professional_id == user_id,
        Appointment.planned_date >= _date.today(),
        Appointment.status.notin_(['cancelado', 'atendido']),
    ).count()
    if turnos_activos:
        flash(f'{user.full_name} tiene {turnos_activos} turno(s) activo(s). Reasignalos antes de eliminar.', 'danger')
        return redirect(url_for('agenda.list_profesionales'))

    db.session.delete(user)
    db.session.commit()
    flash(f'Profesional {user.full_name} eliminado.', 'info')
    return redirect(url_for('agenda.list_profesionales'))


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
        dtstamp = _dt.datetime.now(_dt.UTC).strftime('%Y%m%dT%H%M%SZ')

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
