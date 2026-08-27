"""
Genera pacientes de prueba con datos aleatorios, para ver cómo se
comporta la interfaz (lista de pacientes, búsqueda, etc.) con muchos
registros cargados.

Uso:
    python seed_demo_patients.py 200

Si no pasás ningún número, genera 50 por defecto.

IMPORTANTE: estos son datos 100% inventados (nombres y apellidos
combinados al azar, documentos y teléfonos ficticios). No usar en una
base con pacientes reales sin limpiar después.
"""
import random
import sys
from datetime import date, timedelta

from app import create_app
from extensions import db
from models import Patient, User

FIRST_NAMES = [
    "Mateo", "Sofía", "Bautista", "Emma", "Benjamín", "Isabella", "Santino",
    "Catalina", "Joaquín", "Valentina", "Thiago", "Martina", "Lautaro",
    "Mia", "Facundo", "Renata", "Dylan", "Guadalupe", "Ian", "Lucía",
    "Agustín", "Julieta", "Tomás", "Victoria", "Nicolás", "Delfina",
    "Franco", "Camila", "Bruno", "Antonella", "Gabriel", "Abril",
    "Ignacio", "Pilar", "Ciro", "Zoe", "Máximo", "Ámbar", "Valentino",
    "Malena",
]
LAST_NAMES = [
    "González", "Rodríguez", "Gómez", "Fernández", "López", "Díaz",
    "Martínez", "Pérez", "García", "Sánchez", "Romero", "Sosa",
    "Álvarez", "Torres", "Ruiz", "Ramírez", "Flores", "Acosta",
    "Benítez", "Medina", "Herrera", "Aguirre", "Ojeda", "Cabrera",
    "Ibáñez", "Peralta", "Molina", "Rojas", "Silva", "Núñez",
]
STREETS = [
    "Av. 9 de Julio", "Av. Sarmiento", "San Martín", "Belgrano",
    "Av. Alberdi", "Mitre", "Rivadavia", "Moreno", "Av. Alvear", "Necochea",
]


def random_patient(i):
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    full_name = f"{first} {last}"

    document_id = str(random.randint(20_000_000, 45_000_000))

    start = date(1945, 1, 1).toordinal()
    end = date(2022, 1, 1).toordinal()
    birth_date = date.fromordinal(random.randint(start, end))

    phone = f"362{random.randint(4000000, 5999999)}"
    email = f"{first.lower()}.{last.lower()}{i}@ejemplo.com"
    address = f"{random.choice(STREETS)} {random.randint(100, 4500)}"

    return Patient(
        full_name=full_name,
        document_id=document_id,
        birth_date=birth_date,
        phone=phone,
        email=email,
        address=address,
        medical_notes="",
    )


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 50

    app = create_app()
    with app.app_context():
        dentist = User.query.first()
        if not dentist:
            print("No hay ningún usuario (odontólogo) registrado todavía.")
            print("Registrate primero en /auth/register y volvé a correr este script.")
            return

        pacientes = [random_patient(i) for i in range(count)]
        for p in pacientes:
            p.created_by_id = dentist.id

        db.session.add_all(pacientes)
        db.session.commit()
        print(f"Listo: se crearon {count} pacientes de prueba.")


if __name__ == '__main__':
    main()
