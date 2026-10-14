#!/usr/bin/env bash
# run.sh — Arranque rápido de la app (la instalación ya está hecha).
# Si es la primera vez, ejecutá primero: ./setup.sh

set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
  echo "✗ Falta el entorno virtual. Ejecutá primero:  ./setup.sh"
  exit 1
fi

# shellcheck disable=SC1091
source venv/bin/activate
export FLASK_APP=app.py

echo "→ Odontograma en http://localhost:5000  (Ctrl+C para detener)"
exec python app.py
