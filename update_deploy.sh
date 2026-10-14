#!/usr/bin/env bash
# update_deploy.sh — Actualiza el deploy después de un git push.
#
# Baja los cambios de GitHub, reinstala dependencias si cambió
# requirements.txt y aplica migraciones si cambió migrations/.
# Después SOLO hay que apretar "Reload" en la pestaña Web de
# PythonAnywhere (eso no se puede automatizar sin un token de API).
#
# Uso (en el servidor):
#     cd ~/kibax-app && ./update_deploy.sh
#
# NO toca: .env, venv/, instance/ (la base de datos y los secretos
# quedan intactos, porque no están en git).

set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d venv ]; then
  echo "✗ Falta el entorno virtual. En el servidor ejecutá primero: ./setup.sh --no-run"
  exit 1
fi

# shellcheck disable=SC1091
source venv/bin/activate
export FLASK_APP=app.py

ANTES=$(git rev-parse HEAD)
RAMA=$(git branch --show-current)

echo "→ Bajando cambios de GitHub (rama $RAMA)..."
git pull --ff-only origin "$RAMA"

if [ "$(git rev-parse HEAD)" = "$ANTES" ]; then
  echo "= No había cambios nuevos en GitHub."
else
  CAMBIOS=$(git diff --name-only "$ANTES" HEAD)
  echo "  Archivos actualizados:"
  echo "$CAMBIOS" | sed 's/^/    - /'

  if echo "$CAMBIOS" | grep -q '^requirements.txt$'; then
    echo "→ Cambió requirements.txt: reinstalando dependencias..."
    pip install --quiet -r requirements.txt
  fi

  if echo "$CAMBIOS" | grep -q '^migrations/'; then
    echo "→ Hay migraciones nuevas: aplicándolas a la base..."
    flask db upgrade
  fi
fi

echo ""
echo "✓ Código actualizado."
echo "⚠️  ÚLTIMO PASO: entrá a la pestaña Web de PythonAnywhere y apretá el"
echo "   botón verde 'Reload' para que la web use el código nuevo."
