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

REM Crear archivo .env si no existe
if not exist ".env" (
    echo Creando archivo .env con valores por defecto...
    echo SECRET_KEY=cambia-esta-clave-secreta > .env
    echo REGISTRATION_CODE=cambiar-este-codigo >> .env
    echo   Editá el archivo .env y cambia REGISTRATION_CODE por uno seguro.
)

REM Cargar variables de entorno
for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    set "%%A=%%B"
)

REM Inicializar base de datos
echo Configurando base de datos...
if not exist "migrations" (
    flask db init
)

flask db migrate -m "estado inicial"
flask db upgrade

echo.
echo === ¡Listo! ===
echo Para arrancar la app:  python app.py
echo Abrí http://localhost:5000
echo.
pause
