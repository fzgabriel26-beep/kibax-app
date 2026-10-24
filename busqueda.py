"""Búsqueda de pacientes tolerante a acentos, mayúsculas y puntuación.

La idea: `fernandez` tiene que encontrar a "Fernández" y `21588825` a
"21.588.825". SQLite no trae esa comparación, así que registramos una función
propia (`normalizar`) en cada conexión y filtramos con ella. Si algún día se
migra a PostgreSQL, se cae al LIKE de siempre.
"""
import re
import unicodedata

from sqlalchemy import event, func, or_
from sqlalchemy.engine import Engine

from extensions import db


def normalizar(texto):
    """Minúsculas, sin acentos y sin nada que no sea letra o número."""
    if texto is None:
        return ''
    plano = unicodedata.normalize('NFD', str(texto))
    plano = ''.join(c for c in plano if unicodedata.category(c) != 'Mn')
    return ''.join(c for c in plano.lower() if c.isalnum())


@event.listens_for(Engine, 'connect')
def _registrar_normalizar(conexion, _registro):
    """Expone `normalizar()` dentro de SQLite (no hace nada en otros motores)."""
    if type(conexion).__module__.startswith('sqlite3'):
        conexion.create_function('normalizar', 1, normalizar, deterministic=True)


def _tokens(consulta):
    """Parte la búsqueda en palabras ya normalizadas."""
    return [t for t in (normalizar(p) for p in re.split(r'\s+', consulta or '')) if t]


def condiciones(consulta, columnas):
    """Devuelve una condición por cada palabra, para encadenar con `.filter()`.

    Cada palabra tiene que aparecer en alguna de las columnas, así que
    "silva julieta" encuentra a "Julieta Silva".
    """
    tokens = _tokens(consulta)
    if not tokens:
        return []

    es_sqlite = db.engine.dialect.name == 'sqlite'
    resultado = []
    for token in tokens:
        patron = '%' + token + '%'
        if es_sqlite:
            resultado.append(or_(*[
                func.normalizar(columna).like(patron) for columna in columnas
            ]))
        else:
            resultado.append(or_(*[
                columna.ilike(patron) for columna in columnas
            ]))
    return resultado
