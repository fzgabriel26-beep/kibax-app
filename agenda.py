import calendar
from datetime import date, datetime

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user

from extensions import db
from models import Appointment, Patient

bp = Blueprint('agenda', __name__, url_prefix='/agenda')

APPOINTMENT_STATUSES = {
    'pendiente': 'Pendiente',
    'confirmado': 'Confirmado',
    'realizado': 'Realizado',
    'cancelado': 'Cancelado',
}


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

    cal = calendar.Calendar(firstweekday=0)
    weeks = cal.monthdayscalendar(year, month)

    month_start = date(year, month, 1)
    if month == 12:
        month_end = date(year + 1, 1, 1)
    else:
        month_end = date(year, month + 1, 1)

    month_appts = (Appointment.query
                   .filter(Appointment.planned_date >= month_start,
                           Appointment.planned_date < month_end)
                   .order_by(Appointment.planned_date, Appointment.time)
                   .all())

    counts = {}
    for a in month_appts:
        counts[a.planned_date.isoformat()] = counts.get(a.planned_date.isoformat(), 0) + 1

    if fecha:
        list_appts = (Appointment.query
                      .filter_by(planned_date=fecha)
                      .order_by(Appointment.time)
                      .all())
    else:
        list_appts = (Appointment.query
                      .filter(Appointment.planned_date >= today)
                      .order_by(Appointment.planned_date, Appointment.time)
                      .limit(60)
                      .all())

    todos_hoy = (Appointment.query
                 .filter_by(planned_date=today)
                 .filter(Appointment.status != 'cancelado')
                 .order_by(Appointment.time)
                 .all())

    pacientes = Patient.query.order_by(Patient.full_name).all()
    prev_month, next_month = _prev_next(year, month)

    return render_template(
        'agenda.html',
        weeks=weeks,
        month=month,
        year=year,
        today=today,
        counts=counts,
        list_appts=list_appts,
        todos_hoy=todos_hoy,
        pacientes=pacientes,
        statuses=APPOINTMENT_STATUSES,
        prev_month=prev_month,
        next_month=next_month,
        fecha=fecha,
        month_name=calendar.month_name[month].capitalize(),
    )


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


@bp.route('/nuevo', methods=['POST'])
@login_required
def nuevo():
    patient_id = request.form.get('patient_id')
    fecha_raw = request.form.get('fecha')
    hora = request.form.get('hora', '10:00')
    reason = request.form.get('reason', '').strip()
    status = request.form.get('status', 'confirmado')

    if not patient_id or not fecha_raw:
        flash('Paciente y fecha son obligatorios.', 'danger')
        return redirect(url_for('agenda.index'))

    try:
        fecha = datetime.strptime(fecha_raw, '%Y-%m-%d').date()
    except ValueError:
        try:
            fecha = datetime.strptime(fecha_raw, '%d/%m/%Y').date()
        except ValueError:
            flash('Fecha inválida.', 'danger')
            return redirect(url_for('agenda.index'))

    turno = Appointment(
        patient_id=int(patient_id),
        planned_date=fecha,
        time=hora or '10:00',
        reason=reason or None,
        status=status if status in APPOINTMENT_STATUSES else 'confirmado',
        created_by_id=current_user.id,
    )
    db.session.add(turno)
    db.session.commit()
    flash('Turno agendado.', 'success')
    return redirect(url_for('agenda.index', fecha=fecha_raw, mes=fecha_raw[:7]))


@bp.route('/<int:appt_id>/eliminar', methods=['POST'])
@login_required
def eliminar(appt_id):
    turno = Appointment.query.get_or_404(appt_id)
    db.session.delete(turno)
    db.session.commit()
    flash('Turno eliminado.', 'info')
    return redirect(url_for('agenda.index'))


@bp.route('/<int:appt_id>/estado', methods=['POST'])
@login_required
def estado(appt_id):
    turno = Appointment.query.get_or_404(appt_id)
    nuevo = request.form.get('status')
    if nuevo in APPOINTMENT_STATUSES:
        turno.status = nuevo
        db.session.commit()
        flash('Estado del turno actualizado.', 'success')
    return redirect(url_for('agenda.index'))