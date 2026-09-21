import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db


def _utcnow():
    """Función default para columnas datetime. Reemplaza datetime.utcnow()
    deprecado en Python 3.12+."""
    return datetime.datetime.now(datetime.UTC)


class User(UserMixin, db.Model):
    """El odontólogo/a. Es el único tipo de usuario que puede registrarse
    y es requisito estar logueado para ver o modificar cualquier dato
    de pacientes (ver decorador @login_required en patients.py)."""

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    license_number = db.Column(db.String(60))
    created_at = db.Column(db.DateTime, default=_utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False, index=True)
    document_id = db.Column(db.String(60), index=True)
    birth_date = db.Column(db.Date)
    phone = db.Column(db.String(40), index=True)
    email = db.Column(db.String(120), index=True)
    address = db.Column(db.String(200))
    medical_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=_utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    tooth_statuses = db.relationship(
        'ToothStatus', backref='patient', lazy=True,
        cascade='all, delete-orphan'
    )
    procedure_logs = db.relationship(
        'ProcedureLog', backref='patient', lazy=True,
        cascade='all, delete-orphan',
        order_by='ProcedureLog.created_at.desc()'
    )
    attachments = db.relationship(
        'Attachment', backref='patient', lazy=True,
        cascade='all, delete-orphan',
        order_by='Attachment.uploaded_at.desc()'
    )
    evolution_photos = db.relationship(
        'TreatmentEvolutionPhoto', backref='patient', lazy=True,
        cascade='all, delete-orphan',
        order_by='TreatmentEvolutionPhoto.created_at.desc()'
    )
    consultation_notes = db.relationship(
        'ConsultationNote', backref='patient', lazy=True,
        cascade='all, delete-orphan',
        order_by='ConsultationNote.visit_date.desc(), ConsultationNote.created_at.desc()'
    )


class ToothStatus(db.Model):
    """Estado ACTUAL de cada cara de cada diente (o del diente completo).
    Se usa para pintar el odontograma. El historial completo de
    anotaciones vive en ProcedureLog.

    surface: '' (vacío) = todo el diente (ausente, extraído, corona,
    endodoncia, implante); o una de 'V' (vestibular), 'P' (palatino/
    lingual), 'M' (mesial), 'D' (distal), 'O' (oclusal/incisal) para
    marcar una cara puntual (caries, obturado, etc.)."""

    __tablename__ = 'tooth_status'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    tooth_number = db.Column(db.Integer, nullable=False)  # numeración FDI
    surface = db.Column(db.String(1), nullable=False, default='')
    status = db.Column(db.String(30), default='sano')
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        db.UniqueConstraint('patient_id', 'tooth_number', 'surface', name='uix_patient_tooth_surface'),
    )


class ProcedureLog(db.Model):
    """Historial de anotaciones/tratamientos hechos sobre un diente
    (o una cara puntual de un diente)."""

    __tablename__ = 'procedure_log'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    tooth_number = db.Column(db.Integer, nullable=False)
    surface = db.Column(db.String(1), nullable=False, default='')
    status = db.Column(db.String(30))
    note = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    dentist = db.relationship('User')


class Attachment(db.Model):
    """Imagen o PDF (radiografías, estudios, etc.) asociado a un paciente
    y opcionalmente a un diente puntual."""

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255))
    category = db.Column(db.String(30), default='otro')  # panoramica, bitewing, periapical, foto_intraoral, foto_extraoral, otro
    tooth_number = db.Column(db.Integer, nullable=True)
    uploaded_at = db.Column(db.DateTime, default=_utcnow)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class TreatmentEvolutionPhoto(db.Model):
    """Registro fotográfico para el seguimiento evolutivo de tratamientos de un paciente
    organizado por etapas del tipo 'Antes', 'Durante' y 'Después'."""

    __tablename__ = 'treatment_evolution_photo'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    treatment_type = db.Column(db.String(100), nullable=False)  # Ortodoncia, Conducto, Blanqueamiento, etc.
    stage = db.Column(db.String(30), nullable=False)            # Antes, Durante, Después
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=_utcnow)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    dentist = db.relationship('User')


class ConsultationNote(db.Model):
    """Nota de consulta: registro diario de una visita del paciente
    (motivo de la consulta, tratamiento realizado e indicaciones)."""

    __tablename__ = 'consultation_note'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    visit_date = db.Column(db.Date, nullable=False, default=datetime.date.today)
    reason = db.Column(db.Text)
    treatment = db.Column(db.Text)
    indications = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=_utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    dentist = db.relationship('User')


class Appointment(db.Model):
    """Turno/agenda: cita de un paciente con un odontólogo en una fecha y hora."""

    __tablename__ = 'appointment'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    professional_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    planned_date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(5), nullable=False, default='10:00')  # formato HH:MM
    reason = db.Column(db.String(255))
    status = db.Column(db.String(20), default='confirmado')  # pendiente, confirmado, presente, atendido, ausente, ausente_aviso, cancelado
    created_at = db.Column(db.DateTime, default=_utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    patient = db.relationship('Patient', backref='appointments')
    professional = db.relationship('User', foreign_keys=[professional_id])
    dentist = db.relationship('User', foreign_keys=[created_by_id])


class WorkSchedule(db.Model):
    """Horario semanal de trabajo de un profesional dentro de una vigencia.
    Una fila por día de la semana (0 = lunes .. 6 = domingo) con su franja
    horaria. Ej.: lunes a jueves de 08:00 a 16:00 por un año = 4 filas."""

    __tablename__ = 'work_schedule'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.String(5), nullable=False)  # HH:MM
    end_time = db.Column(db.String(5), nullable=False)    # HH:MM
    valid_from = db.Column(db.Date, nullable=False)
    valid_to = db.Column(db.Date, nullable=False)

    dentist = db.relationship('User', foreign_keys=[user_id])


class ScheduleException(db.Model):
    """Suspensión puntual de la disponibilidad de un profesional
    (enfermedad, licencia, etc.). Sin horario = día completo."""

    __tablename__ = 'schedule_exception'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.String(5))  # None = todo el día
    end_time = db.Column(db.String(5))
    reason = db.Column(db.String(255))

    dentist = db.relationship('User', foreign_keys=[user_id])


class AuditLog(db.Model):
    """Registro de auditoría: cada cambio relevante en datos de pacientes
    o turnos queda registrado con quién, cuándo y qué cambió."""

    __tablename__ = 'audit_log'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False)
    action = db.Column(db.String(20), nullable=False)
    changes = db.Column(db.Text)  # JSON con los cambios
    timestamp = db.Column(db.DateTime, default=_utcnow, index=True)

    user = db.relationship('User')
