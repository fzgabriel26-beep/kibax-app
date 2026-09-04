import os
import shutil
import uuid
from datetime import datetime

from flask import (
    Blueprint, render_template, redirect, url_for, request, flash,
    current_app, send_from_directory, abort, jsonify
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from extensions import db
from models import Patient, ToothStatus, ProcedureLog, Attachment, TreatmentEvolutionPhoto

bp = Blueprint('patients', __name__, url_prefix='/pacientes')

STATUS_LABELS = {
    'sano': 'Sano',
    'caries': 'Caries',
    'obturado': 'Obturado / restaurado',
    'corona': 'Corona',
    'endodoncia': 'Endodoncia',
    'extraido': 'Extraído',
    'implante': 'Implante',
    'ausente': 'Ausente',
}

# Numeración FDI (la que se usa en Argentina y la mayoría de Latinoamérica
# y Europa), organizada por cuadrantes.
# Dentición permanente:
#   Q1 = superior derecho (11-18)   Q2 = superior izquierdo (21-28)
#   Q4 = inferior derecho (41-48)   Q3 = inferior izquierdo (31-38)
# Dentición temporaria / de leche (pacientes pediátricos):
#   Q5 = superior derecho (51-55)   Q6 = superior izquierdo (61-65)
#   Q8 = inferior derecho (81-85)   Q7 = inferior izquierdo (71-75)
# El odontograma se dibuja tal como se ve parado frente al paciente:
# el cuadrante derecho del paciente queda del lado izquierdo de la pantalla.
Q1 = list(range(18, 10, -1))   # 18, 17, ..., 11
Q2 = list(range(21, 29))       # 21, 22, ..., 28
Q3 = list(range(31, 39))       # 31, 32, ..., 38
Q4 = list(range(48, 40, -1))   # 48, 47, ..., 41
Q5 = list(range(55, 50, -1))   # 55, 54, ..., 51
Q6 = list(range(61, 66))       # 61, 62, ..., 65
Q7 = list(range(71, 76))       # 71, 72, ..., 75
Q8 = list(range(85, 80, -1))   # 85, 84, ..., 81

UPPER_ROW = Q1 + Q2                   # permanentes, fila superior
LOWER_ROW = Q4 + Q3                   # permanentes, fila inferior
PRIMARY_UPPER_ROW = Q5 + Q6           # de leche, fila superior
PRIMARY_LOWER_ROW = Q8 + Q7           # de leche, fila inferior

ALL_TEETH_ORDERED = UPPER_ROW + LOWER_ROW + PRIMARY_UPPER_ROW + PRIMARY_LOWER_ROW
ALL_TEETH = set(ALL_TEETH_ORDERED)

# Caras de cada diente que se pueden marcar por separado.
SURFACE_LABELS = {
    '': 'General (todo el diente)',
    'V': 'Vestibular',
    'P': 'Palatino / lingual',
    'M': 'Mesial',
    'D': 'Distal',
    'O': 'Oclusal / incisal',
}

# Estados que aplican a una cara puntual vs. al diente completo (a modo de
# sugerencia visual en el formulario; el backend acepta cualquier
# combinación para no ser demasiado rígido).
WHOLE_TOOTH_STATUSES = {'ausente', 'extraido', 'corona', 'endodoncia', 'implante'}

UPPER_QUADS = {1, 2, 5, 6}
RIGHT_QUADS = {1, 4, 5, 8}   # cuadrantes del lado derecho del paciente


def _surface_layout(tooth_number):
    """Devuelve qué cara (V/P/M/D) va en cada posición visual (arriba,
    abajo, izquierda, derecha) del ícono de un diente, según su cuadrante
    FDI. El centro siempre es la cara oclusal/incisal."""
    quad = tooth_number // 10
    if quad in UPPER_QUADS:
        top, bottom = 'V', 'P'
    else:
        top, bottom = 'P', 'V'
    if quad in RIGHT_QUADS:
        left, right = 'D', 'M'
    else:
        left, right = 'M', 'D'
    return {'top': top, 'bottom': bottom, 'left': left, 'right': right, 'center': 'O'}


TOOTH_LAYOUTS = {n: _surface_layout(n) for n in ALL_TEETH_ORDERED}

ATTACHMENT_CATEGORIES = {
    'panoramica': 'Panorámica',
    'bitewing': 'Bitewing',
    'periapical': 'Periapical',
    'foto_intraoral': 'Foto intraoral',
    'foto_extraoral': 'Foto extraoral',
    'otro': 'Otro',
}
IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}


def allowed_file(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return ext in current_app.config['ALLOWED_EXTENSIONS']


def patient_folder_path(patient_id):
    return os.path.join(current_app.config['UPLOAD_FOLDER'], str(patient_id))


@bp.route('/')
@login_required
def list_patients():
    q = request.args.get('q', '').strip()
    query = Patient.query
    if q:
        query = query.filter(Patient.full_name.ilike(f'%{q}%'))
    pacientes = query.order_by(Patient.full_name).all()
    return render_template('patients/list.html', pacientes=pacientes, q=q)


@bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def new_patient():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        if not full_name:
            flash('El nombre del paciente es obligatorio.', 'danger')
            return render_template('patients/new.html', form=request.form)

        birth_date_raw = request.form.get('birth_date') or None
        birth_date = None
        if birth_date_raw:
            try:
                birth_date = datetime.strptime(birth_date_raw, '%Y-%m-%d').date()
            except ValueError:
                birth_date = None

        paciente = Patient(
            full_name=full_name,
            document_id=request.form.get('document_id', '').strip(),
            birth_date=birth_date,
            phone=request.form.get('phone', '').strip(),
            email=request.form.get('email', '').strip(),
            address=request.form.get('address', '').strip(),
            medical_notes=request.form.get('medical_notes', '').strip(),
            created_by_id=current_user.id,
        )
        db.session.add(paciente)
        db.session.commit()
        flash('Paciente dado de alta correctamente.', 'success')
        return redirect(url_for('patients.patient_detail', patient_id=paciente.id))

    return render_template('patients/new.html', form={})


@bp.route('/<int:patient_id>')
@login_required
def patient_detail(patient_id):
    paciente = Patient.query.get_or_404(patient_id)

    # statuses queda como: { numero_diente: { '' : 'ausente', 'V': 'caries', ... } }
    statuses = {}
    for ts in paciente.tooth_statuses:
        statuses.setdefault(ts.tooth_number, {})[ts.surface] = ts.status

    panoramic = (Attachment.query
                 .filter_by(patient_id=patient_id, category='panoramica')
                 .order_by(Attachment.uploaded_at.desc())
                 .first())

    return render_template(
        'patients/detail.html',
        paciente=paciente,
        statuses=statuses,
        status_labels=STATUS_LABELS,
        surface_labels=SURFACE_LABELS,
        upper_row=UPPER_ROW,
        lower_row=LOWER_ROW,
        primary_upper_row=PRIMARY_UPPER_ROW,
        primary_lower_row=PRIMARY_LOWER_ROW,
        layouts=TOOTH_LAYOUTS,
        all_teeth=ALL_TEETH_ORDERED,
        attachment_categories=ATTACHMENT_CATEGORIES,
        panoramic=panoramic,
        panoramic_is_image=(panoramic and panoramic.original_filename.rsplit('.', 1)[-1].lower() in IMAGE_EXTENSIONS),
    )


@bp.route('/<int:patient_id>/eliminar', methods=['POST'])
@login_required
def delete_patient(patient_id):
    paciente = Patient.query.get_or_404(patient_id)
    folder = patient_folder_path(patient_id)
    if os.path.isdir(folder):
        shutil.rmtree(folder)
    db.session.delete(paciente)
    db.session.commit()
    flash('Paciente y toda su información fueron eliminados.', 'info')
    return redirect(url_for('patients.list_patients'))


# ---------------------------------------------------------------------
# Odontograma: consulta y actualización del estado/historial de un diente
# ---------------------------------------------------------------------

@bp.route('/<int:patient_id>/diente/<int:tooth_number>', methods=['GET'])
@login_required
def tooth_info(patient_id, tooth_number):
    paciente = Patient.query.get_or_404(patient_id)
    if tooth_number not in ALL_TEETH:
        abort(404)

    rows = ToothStatus.query.filter_by(patient_id=paciente.id, tooth_number=tooth_number).all()
    statuses = {row.surface: row.status for row in rows}

    logs = (ProcedureLog.query
            .filter_by(patient_id=paciente.id, tooth_number=tooth_number)
            .order_by(ProcedureLog.created_at.desc()).all())

    return jsonify({
        'ok': True,
        'tooth_number': tooth_number,
        'statuses': statuses,
        'logs': [
            {
                'surface': log.surface,
                'surface_label': SURFACE_LABELS.get(log.surface, log.surface),
                'status_label': STATUS_LABELS.get(log.status, log.status or ''),
                'note': log.note,
                'dentist': log.dentist.full_name if log.dentist else '',
                'created_at': log.created_at.strftime('%d/%m/%Y %H:%M'),
            } for log in logs
        ],
    })


@bp.route('/<int:patient_id>/diente/<int:tooth_number>', methods=['POST'])
@login_required
def tooth_update(patient_id, tooth_number):
    paciente = Patient.query.get_or_404(patient_id)
    if tooth_number not in ALL_TEETH:
        abort(404)

    surface = request.form.get('surface', '')
    status = request.form.get('status', 'sano')
    note = request.form.get('note', '').strip()

    if surface not in SURFACE_LABELS:
        return jsonify({'ok': False, 'error': 'Cara inválida.'}), 400
    if status not in STATUS_LABELS:
        return jsonify({'ok': False, 'error': 'Estado inválido.'}), 400
    if not note:
        return jsonify({'ok': False, 'error': 'La anotación no puede estar vacía.'}), 400

    log = ProcedureLog(
        patient_id=paciente.id,
        tooth_number=tooth_number,
        surface=surface,
        status=status,
        note=note,
        created_by_id=current_user.id,
    )
    db.session.add(log)

    ts = ToothStatus.query.filter_by(patient_id=paciente.id, tooth_number=tooth_number, surface=surface).first()
    if not ts:
        ts = ToothStatus(patient_id=paciente.id, tooth_number=tooth_number, surface=surface, status=status)
        db.session.add(ts)
    else:
        ts.status = status

    db.session.commit()

    return jsonify({
        'ok': True,
        'surface': surface,
        'status': status,
        'status_label': STATUS_LABELS.get(status, status),
        'log': {
            'surface': surface,
            'surface_label': SURFACE_LABELS.get(surface, surface),
            'status_label': STATUS_LABELS.get(status, status),
            'note': log.note,
            'dentist': current_user.full_name,
            'created_at': log.created_at.strftime('%d/%m/%Y %H:%M'),
        }
    })


# ---------------------------------------------------------------------
# Adjuntos: imágenes / PDF de estudios, ligados al paciente (y opcional
# a un diente puntual). Se sirven SIEMPRE mediante ruta protegida.
# ---------------------------------------------------------------------

@bp.route('/<int:patient_id>/adjuntos', methods=['POST'])
@login_required
def upload_attachment(patient_id):
    paciente = Patient.query.get_or_404(patient_id)
    file = request.files.get('file')

    if not file or file.filename == '':
        flash('No se seleccionó ningún archivo.', 'danger')
        return redirect(url_for('patients.patient_detail', patient_id=patient_id))

    if not allowed_file(file.filename):
        flash('Tipo de archivo no permitido. Solo se aceptan imágenes (jpg, png, webp) o PDF.', 'danger')
        return redirect(url_for('patients.patient_detail', patient_id=patient_id))

    original_name = secure_filename(file.filename)
    ext = original_name.rsplit('.', 1)[-1].lower()
    stored_name = f"{uuid.uuid4().hex}.{ext}"

    folder = patient_folder_path(patient_id)
    os.makedirs(folder, exist_ok=True)
    file.save(os.path.join(folder, stored_name))

    tooth_raw = request.form.get('tooth_number')
    tooth_number = int(tooth_raw) if tooth_raw and tooth_raw.isdigit() else None

    category = request.form.get('category', 'otro')
    if category not in ATTACHMENT_CATEGORIES:
        category = 'otro'

    attachment = Attachment(
        patient_id=paciente.id,
        original_filename=original_name,
        stored_filename=stored_name,
        description=request.form.get('description', '').strip(),
        category=category,
        tooth_number=tooth_number,
        uploaded_by_id=current_user.id,
    )
    db.session.add(attachment)
    db.session.commit()
    flash('Archivo adjuntado correctamente.', 'success')
    return redirect(url_for('patients.patient_detail', patient_id=patient_id))


@bp.route('/<int:patient_id>/adjuntos/<int:attachment_id>')
@login_required
def download_attachment(patient_id, attachment_id):
    attachment = Attachment.query.filter_by(id=attachment_id, patient_id=patient_id).first_or_404()
    folder = patient_folder_path(patient_id)
    return send_from_directory(
        folder, attachment.stored_filename,
        as_attachment=False, download_name=attachment.original_filename
    )


@bp.route('/<int:patient_id>/adjuntos/<int:attachment_id>/eliminar', methods=['POST'])
@login_required
def delete_attachment(patient_id, attachment_id):
    attachment = Attachment.query.filter_by(id=attachment_id, patient_id=patient_id).first_or_404()
    folder = patient_folder_path(patient_id)
    filepath = os.path.join(folder, attachment.stored_filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    db.session.delete(attachment)
    db.session.commit()
    flash('Archivo eliminado.', 'info')
    return redirect(url_for('patients.patient_detail', patient_id=patient_id))

# ---------------------------------------------------------------------
# Evolución de Tratamientos: Gestión de fotografías históricas
# ---------------------------------------------------------------------

@bp.route('/<int:patient_id>/evolucion/subir', methods=['POST'])
@login_required
def upload_evolution_photo(patient_id):
    """Procesa la subida de una imagen de evolución médica (Antes/Durante/Después)
    para un tratamiento específico."""
    paciente = Patient.query.get_or_404(patient_id)
    
    if 'photo' not in request.files:
        flash('No se seleccionó ningún archivo de imagen.', 'danger')
        return redirect(url_for('patients.patient_detail', patient_id=patient_id))
        
    file = request.files['photo']
    treatment_type = request.form.get('treatment_type', '').strip()
    stage = request.form.get('stage', '').strip()
    notes = request.form.get('notes', '').strip()
    
    if not treatment_type or not stage:
        flash('El tipo de tratamiento y la etapa son obligatorios.', 'danger')
        return redirect(url_for('patients.patient_detail', patient_id=patient_id))

    if file and allowed_file(file.filename):
        original_filename = file.filename
        ext = original_filename.rsplit('.', 1)[-1].lower() if '.' in original_filename else 'jpg'
        
        # Generamos un nombre único y seguro utilizando UUID para evitar colisiones
        stored_filename = f"evo_{uuid.uuid4().hex}.{ext}"
        
        # Estructuramos la subcarpeta 'evolution' dentro del directorio del paciente
        folder = os.path.join(patient_folder_path(patient_id), 'evolution')
        os.makedirs(folder, exist_ok=True)
        
        # Guardamos físicamente el archivo
        file.save(os.path.join(folder, stored_filename))
        
        # Registramos los datos en la base de datos relacional
        photo = TreatmentEvolutionPhoto(
            patient_id=paciente.id,
            treatment_type=treatment_type,
            stage=stage,
            original_filename=original_filename,
            stored_filename=stored_filename,
            notes=notes if notes else None,
            uploaded_by_id=current_user.id
        )
        
        db.session.add(photo)
        db.session.commit()
        flash('Fotografía de evolución añadida correctamente.', 'success')
    else:
        flash('Archivo no permitido. Solo se aceptan formatos de imagen válidos.', 'danger')
        
    return redirect(url_for('patients.patient_detail', patient_id=patient_id))


@bp.route('/<int:patient_id>/evolucion/foto/<int:photo_id>')
@login_required
def serve_evolution_photo(patient_id, photo_id):
    """Sirve de manera segura las imágenes de evolución almacenadas
    fuera del árbol público, validando sesión activa."""
    photo = TreatmentEvolutionPhoto.query.filter_by(id=photo_id, patient_id=patient_id).first_or_404()
    
    folder = os.path.join(patient_folder_path(patient_id), 'evolution')
    return send_from_directory(folder, photo.stored_filename)
@bp.route('/<int:patient_id>/evolucion/eliminar/<int:photo_id>', methods=['POST'])
@login_required
def delete_evolution_photo(patient_id, photo_id):
    """Elimina de forma segura el registro de la base de datos 
    y el archivo físico del almacenamiento local."""
    photo = TreatmentEvolutionPhoto.query.filter_by(id=photo_id, patient_id=patient_id).first_or_404()
    
    # 1. Intentar borrar el archivo físico del disco para no acumular basura
    folder = os.path.join(patient_folder_path(patient_id), 'evolution')
    file_path = os.path.join(folder, photo.stored_filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass # Si el archivo no existía físicamente por alguna razón, permitimos que continúe el borrado
            
    # 2. Borrar el registro lógico en la base de datos
    db.session.delete(photo)
    db.session.commit()
    
    flash('Fotografía de evolución eliminada correctamente.', 'info')
    return redirect(url_for('patients.patient_detail', patient_id=patient_id))
