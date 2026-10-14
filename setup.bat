@echo off
REM setup.bat — Inicializacion del proyecto Odontograma (Windows)
REM Ejecutar la primera vez despues de clonar el repositorio.

echo === Odontograma — Setup ===

REM Crear virtualenv si no existe
if not exist "venv" (
    echo Creando entorno virtual...
    python -m venv venv
)

REM Activar virtualenv
echo Activando entorno virtual...
call venv\Scripts\activate.bat

REM Instalar dependencias
echo Instalando dependencias...
pip install -r requirements.txt

REM Crear archivo .env si no existe (con SECRET_KEY aleatoria generada por Python)
if not exist ".env" (
    echo Creando archivo .env con SECRET_KEY aleatoria...
    python -c "import secrets; open('.env','w').write('# Generado por setup.bat - NO subir a git\nSECRET_KEY=%s\nREGISTRATION_CODE=mi-codigo-seguro\n' % secrets.token_hex(32))"
    echo   Editá el archivo .env y cambia REGISTRATION_CODE por uno seguro.
)

REM Inicializar base de datos
echo Configurando base de datos...
if not exist "migrations" (
    flask db init
)

REM Las migraciones ya vienen commiteadas en el repo: solo aplicarlas.
REM (NO usar "flask db migrate" acá: crearía una migración duplicada.)
flask db upgrade

echo.
echo ===========================================
echo   Odontograma listo en http://localhost:5000
echo ===========================================
echo.
python app.py
pause
