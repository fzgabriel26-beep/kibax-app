#!/bin/bash
# setup.sh — Inicialización del proyecto Odontograma
# Ejecutar la primera vez después de clonar el repositorio.

set -e

echo "=== Odontograma — Setup ==="

# Crear virtualenv si no existe
if [ ! -d "venv" ]; then
  echo "→ Creando entorno virtual..."
  python3 -m venv venv
fi

# Activar virtualenv
echo "→ Activando entorno virtual..."
source venv/bin/activate

# Instalar dependencias
echo "→ Instalando dependencias..."
pip install -r requirements.txt

# Crear archivo .env si no existe
if [ ! -f ".env" ]; then
  echo "→ Creando archivo .env con valores por defecto..."
  cat > .env <<'EOF'
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
REGISTRATION_CODE=cambiar-este-codigo
EOF
  echo "  ⚠️  Editá el archivo .env y cambiá REGISTRATION_CODE por uno seguro."
fi

# Cargar variables de entorno
export $(grep -v '^#' .env | xargs)

# Inicializar base de datos
echo "→ Configurando base de datos..."
if [ ! -d "migrations" ]; then
  flask db init
fi

flask db migrate -m "estado inicial" 2>/dev/null || true
flask db upgrade

echo ""
echo "=== ¡Listo! ==="
echo "Para arrancar la app:  python app.py"
echo "Abrí http://localhost:5000"
echo ""
