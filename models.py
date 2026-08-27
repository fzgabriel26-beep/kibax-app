from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db


class User(UserMixin, db.Model):
    """El odontólogo/a. Es el único tipo de usuario que puede registrarse
    y es requisito estar logueado para ver o modificar cualquier dato
    de pacientes (ver decorador @login_required en patients.py)."""

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    license_number = db.Column(db.String(60))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    document_id = db.Column(db.String(60))
    birth_date = db.Column(db.Date)
    phone = db.Column(db.String(40))
    email = db.Column(db.String(120))
    address = db.Column(db.String(200))
    medical_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
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
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
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
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
