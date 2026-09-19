"""
Resetea la contraseña de un usuario (odontólogo/a) existente, por si te
olvidaste la clave y no hay pantalla de "olvidé mi contraseña" en la app.

Uso:
    python reset_password.py

Te va a pedir el email de la cuenta y la nueva contraseña.
"""
from getpass import getpass

from app import create_app
from extensions import db
from models import User


def main():
    app = create_app()
    with app.app_context():
        users = User.query.order_by(User.full_name).all()
        if not users:
            print("No hay ningún usuario registrado todavía.")
            return

        print("Usuarios existentes:")
        for u in users:
            print(f"  - {u.email}  ({u.full_name})")

        email = input("\nEmail de la cuenta a resetear: ").strip().lower()
        user = User.query.filter_by(email=email).first()
        if not user:
            print("No existe ningún usuario con ese email.")
            return

        password = getpass("Nueva contraseña (mínimo 8 caracteres): ")
        password2 = getpass("Repetí la nueva contraseña: ")

        if password != password2:
            print("Las contraseñas no coinciden. Cancelado.")
            return
        if len(password) < 8:
            print("La contraseña debe tener al menos 8 caracteres. Cancelado.")
            return

        user.set_password(password)
        db.session.commit()
        print(f"Listo: se actualizó la contraseña de {user.email}.")


if __name__ == '__main__':
    main()
