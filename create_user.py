"""
Crea (o actualiza) una cuenta de odontólogo/a o secretario/a desde la terminal.

Sirve para darle acceso a alguien (por ejemplo, que el profesor pueda probar
la página) sin que tenga que registrarse ni conocer el REGISTRATION_CODE.

La cuenta se guarda en la base de datos del proyecto (instance/odontograma.db),
así que una vez creada sigue existiendo mientras no borres esa base.

Uso:
    python create_user.py                                  # te pregunta los datos
    python create_user.py profe@mail.com                   # email por argumento
    python create_user.py profe@mail.com --nombre "Ana Peres" --password "Clave123!"
    python create_user.py secretaria@mail.com --rol secretario
    ./venv/bin/python create_user.py profe@mail.com --si   # --si: pisa la contraseña
                                                           #  si el usuario ya existe,
                                                           #  sin preguntar

Requiere el entorno virtual:
    source venv/bin/activate && python create_user.py
"""
import argparse
import getpass
import re
import sys

from app import create_app
from extensions import db
from models import User, ROLES, Appointment, WorkSchedule, WaitingListEntry


def password_error(password):
    """Misma política de contraseñas que el registro web (auth.py)."""
    if len(password) < 8:
        return 'La contraseña debe tener al menos 8 caracteres.'
    if not re.search(r'[A-Z]', password):
        return 'Debe tener al menos una letra mayúscula.'
    if not re.search(r'[0-9]', password):
        return 'Debe tener al menos un número.'
    if not re.search(r'[!@#$%^&*(),.?":{}|<>\-_=+\[\]\\;\'`~]', password):
        return 'Debe tener al menos un carácter especial (!@#$%^&*...).'
    return None


def pedir_password():
    while True:
        password = getpass('Contraseña para la cuenta (mínimo 8, con mayúscula, número y símbolo): ')
        error = password_error(password)
        if error:
            print(f'  ✗ {error}')
            continue
        if getpass('Repetí la contraseña: ') != password:
            print('  ✗ Las contraseñas no coinciden.')
            continue
        return password


def main():
    parser = argparse.ArgumentParser(
        description='Crea o actualiza una cuenta de odontólogo/a o secretario/a.'
    )
    parser.add_argument('email', nargs='?', help='email de la cuenta')
    parser.add_argument('--nombre', help='nombre y apellido')
    parser.add_argument('--matricula', help='matrícula profesional (solo odontólogos)')
    parser.add_argument('--rol', choices=tuple(ROLES.keys()),
                        help='rol de la cuenta: odontologo o secretario (por defecto odontologo)')
    parser.add_argument('--password', help='contraseña (si la omitís, se pide sin mostrarla)')
    parser.add_argument('--si', action='store_true',
                        help='si el usuario ya existe, actualiza la contraseña sin preguntar')
    args = parser.parse_args()

    email = (args.email or input('Email de la cuenta: ')).strip().lower()
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        print('✗ Ese email no tiene formato válido.')
        return 1

    app = create_app()
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        existe = user is not None
        rol = (args.rol or (user.role if existe else 'odontologo') or 'odontologo').strip().lower()

        if existe:
            print(f'= Ya existe una cuenta con el email {email} ({user.full_name}).')
            if not args.si:
                respuesta = input('¿Actualizar la contraseña? [s/N]: ').strip().lower()
                if respuesta != 's':
                    print('Cancelado, no se cambió nada.')
                    return 0
            if args.rol == 'secretario' and user.role != 'secretario':
                from datetime import date as _date
                turnos = Appointment.query.filter(
                    Appointment.professional_id == user.id,
                    Appointment.planned_date >= _date.today(),
                    Appointment.status.notin_(['cancelado', 'atendido']),
                ).count()
                horarios = WorkSchedule.query.filter_by(user_id=user.id).count()
                espera = WaitingListEntry.query.filter_by(professional_id=user.id).count()
                if turnos or horarios or espera:
                    print('✗ No se puede pasar a secretario/a: todavía tiene '
                          f'{turnos} turno(s) activo(s), {horarios} horario(s) '
                          f'y {espera} paciente(s) en lista de espera.')
                    print('  Reasigná los turnos, eliminá los horarios y la lista '
                          'de espera desde la web, y volvé a intentar.')
                    return 1
            if args.rol:
                user.role = rol
                if rol == 'secretario':
                    user.license_number = None
                elif args.matricula:
                    user.license_number = args.matricula
        else:
            nombre = args.nombre or input('Nombre y apellido: ').strip()
            if not nombre:
                print('✗ El nombre no puede estar vacío.')
                return 1
            user = User(full_name=nombre, email=email, role=rol,
                        license_number=(args.matricula or None) if rol == 'odontologo' else None)

        if args.password:
            password = args.password
            error = password_error(password)
            if error:
                print(f'✗ {error}')
                return 1
        else:
            password = pedir_password()

        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        verbo = 'actualizada' if existe else 'creada'
        print(f'\n✓ Cuenta {verbo} en {app.config["SQLALCHEMY_DATABASE_URI"]}')
        print(f'   Usuario:    {email}')
        print(f'   Contraseña: la que acabas de poner (no se muestra ni se guarda en texto)')
        print(f'   Nombre:     {user.full_name}')
        print(f'   Rol:        {ROLES.get(user.role, ROLES["odontologo"])}')
        print('\nCon estos datos puede entrar en /auth/login.')
        print('   - En tu PC:          la app ya está corriendo, entrá nomás.')
        print('   - En PythonAnywhere: si el servidor ya estaba levantado, apretá')
        print('     "Reload" en la pestaña Web (aunque para una cuenta nueva no')
        print('     hace falta: la base se lee en cada request).')


if __name__ == '__main__':
    sys.exit(main())
