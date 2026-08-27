import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # IMPORTANTE: en producción, definí SECRET_KEY como variable de entorno.
    SECRET_KEY = os.environ.get('SECRET_KEY', 'cambia-esta-clave-en-produccion')

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'odontograma.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Los archivos de pacientes se guardan FUERA de /static para que no se
    # puedan acceder por URL directa: solo se sirven mediante una ruta
    # protegida con @login_required (ver patients.py -> download_attachment).
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'instance', 'uploads')
    MAX_CONTENT_LENGTH = 15 * 1024 * 1024  # 15 MB por archivo
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'pdf'}

    # Código que se debe conocer para poder crear una cuenta de odontólogo.
    # Cambialo por variable de entorno en producción y compartilo solo con
    # las personas que vayan a trabajar en el consultorio.
    REGISTRATION_CODE = os.environ.get('REGISTRATION_CODE', 'changeme')
