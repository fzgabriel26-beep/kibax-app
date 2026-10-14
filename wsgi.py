"""Punto de entrada WSGI (para deploy en PythonAnywhere, gunicorn, etc.).

PythonAnyhere pide un archivo WSGI que exponga la variable `application`.
Este archivo hace justo eso: garantiza que el directorio del proyecto esté
en el sys.path y expone la app creada por app.py.

En PythonAnywhere, en la pestaña "Web" → sección "Code", editá el archivo
WSGI (algo como /var/www/<tu-usuario>_pythonanywhere_com_wsgi.py) y poné
adentro el contenido de este archivo.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app as application  # noqa: E402

# Para gunicorn:  gunicorn --bind 0.0.0.0:8000 wsgi:application
