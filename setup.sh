#!/usr/bin/env bash
# setup.sh — Instalación y arranque en UN solo comando (Linux/macOS).
#
#   ./setup.sh              # primera vez: instala todo y arranca la web
#   ./setup.sh              # siguientes veces: verifica y arranca
#   ./setup.sh --no-run     # solo instala deps y prepara la base, sin arrancar
#   ./run.sh                # arranque rápido (ya instalado)
#
# Requisito: Python 3.10+ en el sistema.

set -euo pipefail
cd "$(dirname "$0")"

NO_RUN=0
for arg in "$@"; do
  case "$arg" in
    --no-run) NO_RUN=1 ;;
    -h|--help)
      echo "Uso: ./setup.sh [--no-run]"
      exit 0
      ;;
    *)
      echo "✗ Opción desconocida: $arg  (usá ./setup.sh --help)"
      exit 1
      ;;
  esac
done

echo "=== Odontograma — Setup ==="

# --- 1. Comprobar Python -----------------------------------------------------
if ! command -v python3 >/dev/null 2>&1; then
  echo "✗ No se encontró python3. Instalalo (p. ej. 'sudo apt install python3 python3-venv python3-pip')."
  exit 1
fi
echo "→ Python: $(python3 --version 2>&1)"

# --- 2. Entorno virtual ------------------------------------------------------
# Guardamos el Python del sistema: si el venv se crea "sin pip" (plan B),
# lo necesitamos para instalar pip dentro del venv.
SYSTEM_PYTHON=$(command -v python3)

if [ ! -d "venv" ]; then
  echo "→ Creando entorno virtual..."
  if ! "$SYSTEM_PYTHON" -m venv venv 2>/dev/null; then
    echo "  ⚠️  Este sistema no trae python3-venv (falta ensurepip). Plan B:"
    echo "     venv sin pip + pip del sistema apuntando al venv."
    echo "     Para el modo normal: sudo apt install python3.12-venv"
    echo "     y después: rm -rf venv && ./setup.sh"
    rm -rf venv
    "$SYSTEM_PYTHON" -m venv --without-pip venv
  fi
fi
# shellcheck disable=SC1091
source venv/bin/activate

# Asegurar que haya pip dentro del venv (necesario en el plan B)
if ! python -m pip --version >/dev/null 2>&1; then
  echo "→ Instalando pip dentro del entorno virtual..."
  "$SYSTEM_PYTHON" -m pip --python "$(pwd)/venv/bin/python" install --upgrade pip
fi

# --- 3. Dependencias ---------------------------------------------------------
echo "→ Instalando dependencias..."
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

# --- 4. Variables de entorno (.env) ------------------------------------------
if [ ! -f ".env" ]; then
  echo "→ Generando .env con SECRET_KEY aleatoria..."
  SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
  cat > .env <<EOF
# Generado por setup.sh — NO subir a git (ya está en .gitignore)
SECRET_KEY=${SECRET_KEY}
REGISTRATION_CODE=mi-codigo-seguro
EOF
  echo "  ⚠️  Editá .env y cambiá REGISTRATION_CODE por uno seguro (es el código"
  echo "     que te piden al registrar una cuenta de odontólogo/a)."
else
  echo "→ .env ya existe, se respeta."
fi

# --- 5. Base de datos (migraciones ya commiteadas en el repo) ---------------
export FLASK_APP=app.py
echo "→ Aplicando migraciones..."
if [ ! -d "migrations" ]; then
  flask db init
fi

DB_PREVIA=0
[ -f "instance/odontograma.db" ] && DB_PREVIA=1

if ! flask db upgrade; then
  echo ""
  echo "✗ Falló la migración de la base de datos."
  if [ "$DB_PREVIA" -eq 1 ]; then
    echo "  Ya existía una base de datos (copiada de otra PC). Si tiene datos"
    echo "  reales que no querés perder, marcala como ya migrada SIN tocarla:"
    echo "      source venv/bin/activate && flask db stamp head"
  fi
  exit 1
fi
echo "  ✓ Base de datos lista (instance/odontograma.db)"

if [ "$NO_RUN" -eq 1 ]; then
  echo ""
  echo "=== Instalación completa ==="
  echo "Arrancá la app con:  ./run.sh"
  exit 0
fi

# --- 6. Arranque -------------------------------------------------------------
echo ""
echo "==========================================="
echo "  Odontograma listo en http://localhost:5000"
echo "  (Ctrl+C para detener el servidor)"
echo "==========================================="
exec python app.py
