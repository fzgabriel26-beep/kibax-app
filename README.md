# Odontograma — app web para consultorio odontológico

Aplicación web (Flask + SQLite) para gestionar pacientes con un odontograma
interactivo: se hace clic en un diente, se ve su historial y se agregan
anotaciones (arreglos, diagnósticos). También permite subir imágenes y PDF
de estudios por paciente. Todo el sistema requiere haber iniciado sesión
como odontólogo/a — como invitado no se puede ver ni modificar nada.

## Estructura del proyecto

```
odontograma_app/
├── app.py              # Application factory, arranca la app
├── config.py           # Configuración (clave secreta, DB, uploads)
├── extensions.py       # Instancias de SQLAlchemy y Flask-Login
├── models.py            # User, Patient, ToothStatus, ProcedureLog, Attachment
├── auth.py              # Blueprint: registro / login / logout
├── patients.py           # Blueprint: pacientes, odontograma, adjuntos
├── templates/
│   ├── base.html
│   ├── auth/login.html, register.html
│   └── patients/list.html, new.html, detail.html
├── static/
│   ├── css/style.css
│   └── js/odontogram.js
├── requirements.txt
├── .flaskenv            # FLASK_APP=app.py, para que el comando `flask` funcione
├── migrations/          # (se crea con `flask db init`, no viene en el zip)
└── instance/            # (se crea sola) DB SQLite + archivos subidos
```

## Cómo correrlo localmente (primera vez)

```bash
cd odontograma_app
python3 -m venv venv
source venv/bin/activate          # en Windows: venv\Scripts\activate

pip install -r requirements.txt

# Variables de entorno (ver .env.example) — al menos definí estas dos:
export SECRET_KEY="una-clave-larga-y-aleatoria"
export REGISTRATION_CODE="un-codigo-que-solo-vos-conozcas"
```

Este proyecto usa **Flask-Migrate** (Alembic) para crear y actualizar las
tablas de la base de datos — ya no se crean solas al arrancar `app.py`.
La primera vez que instalás el proyecto (o si borraste `instance/`),
tenés que inicializar y aplicar las migraciones:

```bash
flask db init                              # solo la primera vez: crea la carpeta migrations/
flask db migrate -m "estado inicial"
flask db upgrade                           # crea las tablas en instance/odontograma.db
```

Recién ahí corrés la app normalmente:

```bash
python app.py
```

Abrí `http://localhost:5000`. La primera vez vas a tener que registrarte
como odontólogo/a en `/auth/register`, usando el `REGISTRATION_CODE` que
definiste. Una vez creada la cuenta, iniciá sesión y empezá a dar de alta
pacientes.

## Cómo actualizar la base cuando cambia un modelo

Antes, cada cambio en `models.py` (agregar una columna, por ejemplo)
requería borrar `instance/odontograma.db` y perder todo lo cargado. Con
Flask-Migrate ya no: el flujo pasa a ser siempre estos dos comandos,
cada vez que se modifique algo en `models.py`:

```bash
flask db migrate -m "una descripción corta del cambio"   # genera el script de migración
flask db upgrade                                          # lo aplica a la base real
```

El primer comando **revisa tus modelos, los compara contra el estado
actual de la base y genera automáticamente** el script con los `ALTER
TABLE` (u otros cambios) necesarios, en `migrations/versions/`. Conviene
siempre abrir ese archivo generado y darle una revisada antes de aplicar
el `upgrade`, sobre todo en cambios más grandes (por ejemplo, borrar una
columna con datos).

Si en algún momento un cambio sale mal, se puede volver atrás un paso:
```bash
flask db downgrade
```

## Si ya tenías una base de datos con datos reales (migración inicial)

Si ya veías la app funcionando y tenés `instance/odontograma.db` con
pacientes cargados que **no** querés perder, en vez de `flask db upgrade`
en el paso inicial usá:

```bash
flask db init
flask db migrate -m "estado inicial"
flask db stamp head    # en vez de "upgrade": le dice a Alembic
                        # "la base ya está en este estado", sin tocarla
```

Eso registra el esquema actual como punto de partida sin ejecutar ningún
cambio, ya que tu base ya tiene esas columnas. De ahí en adelante, los
próximos cambios de modelo sí se aplican con `flask db upgrade` como
cualquier otro caso.


## Cómo funciona el odontograma

- Los dientes se numeran del 1 al 32 (numeración universal). Cada botón
  también muestra el número FDI equivalente como referencia, ya que es el
  sistema más usado en Argentina.
- Al hacer clic en un diente se abre un modal con:
  - El **historial completo** de anotaciones de ese diente (fecha,
    odontólogo, estado, nota).
  - Un formulario para **agregar una anotación nueva** (estado + texto
    libre describiendo el arreglo o diagnóstico).
- El color del diente en el odontograma refleja su **estado actual**
  (sano, caries, obturado, corona, endodoncia, extraído, implante,
  ausente), que se actualiza automáticamente con cada anotación nueva.
- Se puede adjuntar una imagen o PDF asociado opcionalmente a un diente
  puntual (por ejemplo, una radiografía de la pieza 14).

## Privacidad de los datos

- **Todas** las rutas de pacientes (`/pacientes/...`) están protegidas con
  `@login_required` de Flask-Login: sin sesión iniciada, se redirige al
  login.
- Los archivos subidos (imágenes/PDF) **no** se guardan dentro de
  `/static`, sino en `instance/uploads/<id_paciente>/`, una carpeta fuera
  del árbol público. Solo se pueden descargar a través de una ruta
  protegida (`download_attachment`), nunca por URL directa adivinada.
- El registro de nuevas cuentas requiere conocer el `REGISTRATION_CODE`
  del consultorio, para que no cualquier visitante pueda crearse una
  cuenta.
- Las contraseñas se guardan con hash (`werkzeug.security`), nunca en
  texto plano.

## Antes de llevarlo a producción

Esto es una base sólida y funcional, pero para producción real conviene:

1. Servir por **HTTPS** (obligatorio si vas a manejar datos de salud).
2. Reemplazar SQLite por **PostgreSQL** si vas a tener uso concurrente.
3. Agregar protección **CSRF** (por ejemplo con `Flask-WTF`).
4. Definir `SECRET_KEY` y `REGISTRATION_CODE` como variables de entorno
   reales (no los valores por defecto del código).
5. Hacer **backups periódicos** de `instance/` (base de datos + archivos).
6. Si va a haber más de un odontólogo, pensar si cada uno debe ver solo
   sus propios pacientes o todos comparten la base (hoy comparten todo).
7. Revisar la normativa local de protección de datos de salud (en
   Argentina, Ley 25.326 de Protección de Datos Personales) para el
   almacenamiento y retención de historias clínicas.

## Posibles próximos pasos

- Exportar la ficha del paciente a PDF.
- Permitir varios odontólogos con distintos niveles de permiso.
- Búsqueda y filtro de pacientes por estado de tratamiento.
- Notificaciones/recordatorios de turnos.
