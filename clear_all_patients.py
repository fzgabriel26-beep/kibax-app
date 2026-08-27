"""
Borra TODOS los pacientes de la base (y en cascada su odontograma,
historial y adjuntos registrados en la base -- los archivos físicos en
instance/uploads/<id> no se borran solos, ver aviso abajo).

Uso:
    python clear_all_patients.py
Te va a pedir confirmación antes de borrar nada.
"""
import shutil
from pathlib import Path

from app import create_app
from extensions import db
from models import Patient


def main():
    app = create_app()
    with app.app_context():
        total = Patient.query.count()
        if total == 0:
            print("No hay pacientes cargados.")
            return

        confirm = input(f"Esto va a borrar los {total} pacientes cargados (y todo su historial). ¿Confirmás? (escribí 'si'): ")
        if confirm.strip().lower() != 'si':
            print("Cancelado, no se borró nada.")
            return

        Patient.query.delete()
        db.session.commit()

        uploads_dir = Path(app.config['UPLOAD_FOLDER'])
        if uploads_dir.exists():
            shutil.rmtree(uploads_dir)
            uploads_dir.mkdir(parents=True, exist_ok=True)

        print(f"Listo: se borraron {total} pacientes y sus archivos adjuntos.")


if __name__ == '__main__':
    main()
