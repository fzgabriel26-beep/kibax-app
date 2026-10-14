"""Cambia el REGISTRATION_CODE (el código que se pide al registrar una cuenta).

No toca la base de datos: el código vive en el archivo .env de la raíz del
proyecto (ver config.py -> REGISTRATION_CODE).

Uso:
    python3 set_registration_code.py                 # muestra el código actual
    python3 set_registration_code.py mi-codigo-2026  # lo cambia por ese
    python3 set_registration_code.py --generar       # genera uno aleatorio y lo guarda

Después de cambiarlo hay que REINICIAR el servidor (Ctrl+C y ./run.sh),
porque la app lee el .env solo al arrancar.
"""
import argparse
import re
import secrets
import sys
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent / '.env'
VARIABLE = 'REGISTRATION_CODE'


def leer_codigo_actual():
    """Devuelve el valor actual del REGISTRATION_CODE en el .env, o None."""
    if not ENV_PATH.exists():
        return None
    for linea in ENV_PATH.read_text(encoding='utf-8').splitlines():
        linea = linea.strip()
        if linea.startswith(f'{VARIABLE}='):
            return linea.split('=', 1)[1].strip()
    return None


def guardar_codigo(nuevo_codigo):
    """Escribe (o actualiza) la línea REGISTRATION_CODE en el .env."""
    linea = f'{VARIABLE}={nuevo_codigo}'
    if ENV_PATH.exists():
        contenido = ENV_PATH.read_text(encoding='utf-8')
        if re.search(rf'^{VARIABLE}=', contenido, flags=re.MULTILINE):
            contenido = re.sub(
                rf'^{VARIABLE}=.*$', linea, contenido, flags=re.MULTILINE
            )
        elif contenido and not contenido.endswith('\n'):
            contenido += '\n'
        if not re.search(rf'^{VARIABLE}=', contenido, flags=re.MULTILINE):
            contenido += linea + '\n'
    else:
        # Si no hay .env (raro, lo crea setup.sh), lo creamos con todo lo mínimo.
        contenido = (
            '# Generado por set_registration_code.py - NO subir a git\n'
            f'SECRET_KEY={secrets.token_hex(32)}\n'
            f'{linea}\n'
        )
    ENV_PATH.write_text(contenido, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(
        description='Ver o cambiar el REGISTRATION_CODE (código para registrar cuentas).'
    )
    parser.add_argument(
        'codigo', nargs='?',
        help='el nuevo código de registro (si lo omitís, solo muestra el actual)'
    )
    parser.add_argument(
        '--generar', action='store_true',
        help='genera un código aleatorio y lo guarda en el .env'
    )
    args = parser.parse_args()

    actual = leer_codigo_actual()

    if args.generar:
        nuevo = secrets.token_urlsafe(12)
        guardar_codigo(nuevo)
        print(f'✓ Código generado y guardado en {ENV_PATH.name}:')
        print(f'  {nuevo}')
    elif args.codigo:
        if args.codigo == actual:
            print(f'= El código ya era ese. Nada que cambiar ({actual})')
            return
        guardar_codigo(args.codigo)
        print(f'✓ Código actualizado en {ENV_PATH.name}: {args.codigo}')
        if actual:
            print(f'  (antes era: {actual})')
    else:
        if actual is None:
            print(f'No se encontró {VARIABLE} en {ENV_PATH} (¿existe el archivo?).')
            print('Usá:  python3 set_registration_code.py --generar')
            return
        print(f'Código actual: {actual}')
        print('Para cambiarlo:  python3 set_registration_code.py "el-nuevo-codigo"')
        return

    print('\n⚠️  La app leyó el código al arrancar: para que tome el valor nuevo')
    print('   hay que reiniciarla.')
    print('   - En tu PC:            Ctrl+C y ./run.sh')
    print('   - En PythonAnywhere:   botón "Reload" en la pestaña Web')


if __name__ == '__main__':
    sys.exit(main())
