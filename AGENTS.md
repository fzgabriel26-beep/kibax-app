# AGENTS.md

App Flask + SQLite para un consultorio odontológico: fichas de pacientes,
odontograma interactivo (numeración FDI, estados por cara del diente, historial,
adjuntos) y agenda de turnos. Jinja renderizado en el servidor + Bootstrap y JS
vanilla (sin paso de build, sin framework de frontend). Un único proceso
desplegable, SQLite por defecto.

Todo —rutas, campos de los modelos, mensajes flash, plantillas, documentación,
mensajes de commit— está escrito en **castellano**. Mantené esa convención al
agregar código.

## Comandos

| Tarea | Comando |
| --- | --- |
| Setup inicial (todo en uno) | `./setup.sh` (crea `venv/`, instala dependencias, escribe `.env`, hace `flask db upgrade` y arranca el servidor en :5000) |
| Setup sin arrancar el servidor | `./setup.sh --no-run` |
| Arrancar la app | `./run.sh` (`HOST=0.0.0.0 ./run.sh`, `PORT=5055 ./run.sh` para cambiar host/puerto) |
| Correr toda la suite de tests | `./venv/bin/python -m pytest tests/ -q` |
| Correr un solo test | `./venv/bin/python -m pytest tests/test_agenda.py -k test_create_appointment -q` |
| Aplicar migraciones pendientes | `./venv/bin/python -m flask --app app.py db upgrade` (o `make db-upgrade`) |
| Setup inicial en Windows | `setup.bat` (hace lo mismo que `./setup.sh` y después arranca) |
| Scripts utilitarios | `./venv/bin/python create_user.py`, `reset_password.py`, `set_registration_code.py`, `seed_demo_patients.py 50`, `clear_all_patients.py` |

Targets del Makefile: `make setup | install | run | test | db-upgrade | usuario | clean`.
`make clean` borra `venv/`, los cachés y `__pycache__` — **no** toca la base de datos.

- Los tests tienen que correrse con `./venv/bin/python` (el `python3` del sistema
  no tiene las dependencias instaladas).
- Los tests usan SQLite en memoria y desactivan CSRF y el rate limiting. Las
  variables de entorno (`DATABASE_URL=sqlite:///:memory:`, `RATELIMIT_ENABLED=false`)
  se definen en `tests/conftest.py` **antes** de importar `app`/`config`: respetá
  ese orden si tocás cómo se carga la configuración.
- En este repo **no** hay linter, formateador, typechecker, CI ni pre-commit
  configurado. No inventes uno ni digas que corriste checks que no corriste.
- `.flaskenv` define `FLASK_APP=app.py`, así que `flask db ...` funciona desde la
  raíz del repo una vez activado `venv/`.
- La app requiere Python ≥ 3.11 (`models.py` usa `datetime.UTC`); el `venv/` del
  repo corre 3.12.

## Base de datos y migraciones

- Archivo SQLite: `instance/odontograma.db`. Archivos subidos:
  `instance/uploads/<patient_id>/`. `instance/` está en `.gitignore`, así que un
  clon nuevo no tiene base ni secretos: corré `./setup.sh` / `./setup.sh --no-run`
  (o `flask db upgrade`) antes de arrancar la app.
- `migrations/` **sí está commiteado**. En un clon nuevo nunca ejecutes
  `flask db init`; alcanza con `flask db upgrade`. (`setup.sh` solo hace el init si
  la carpeta no existe.)
- Después de cambiar `models.py`: `flask db migrate -m "..."` → revisá el archivo
  generado en `migrations/versions/` → `flask db upgrade`. Si la base viene copiada
  de otra máquina, usá `flask db stamp head` en lugar de `upgrade`.
- `Appointment.time` es un **string** `HH:MM`, no una columna `TIME`.

## Arquitectura (cómo está armada)

- `app.py`: factory `create_app()` **y** además `app = create_app()` a nivel de
  módulo, en el momento de la importación. `wsgi.py` lo re-exporta como
  `application` para gunicorn/PythonAnywhere.
- `extensions.py` es el dueño de las instancias `db`, `login_manager`, `migrate`,
  `csrf` y `limiter`: importalas desde ahí, nunca crees instancias nuevas.
- Tres blueprints: `auth` (`/auth`), `patients` (`/pacientes`) y `agenda`
  (`/agenda`). Modelos en `models.py`, configuración por variables de entorno en
  `config.py`. Modelos: `User` (rol `odontologo` o `secretario`),
  `Patient`, `ToothStatus`, `ProcedureLog`, `Attachment`,
  `TreatmentEvolutionPhoto`, `ConsultationNote`, `Appointment`, `WorkSchedule`,
  `ScheduleException`, `AuditLog`.
- Todas las rutas de pacientes y agenda están protegidas con `@login_required`; las
  rutas nuevas también deben estarlo (no hay capa de permisos: todos comparten la
  misma base).
- Solo los usuarios con `role='odontologo'` son profesionales de la agenda: tienen
  horarios y reciben turnos. Los `role='secretario'` pueden gestionar pacientes y
  turnos, pero no tienen horarios propios ni se asignan como profesional. Filtrá
  siempre con `User.role == 'odontologo'` al listar profesionales.
- La gestión de cuentas (`/agenda/profesionales...`) está reservada a odontólogos
  con el helper `_solo_odontologo()`; un secretario no puede cambiarse el rol solo.
- El alta, la edición y la eliminación de pacientes registran auditoría con
  `patients._audit(...)` (→ `AuditLog`). Los cambios en turnos/agenda **no** se
  auditan, aunque el docstring de `AuditLog` diga lo contrario: agregá las llamadas
  si extendés la agenda.
- Los filtros de Jinja `turno_hora`, `fecha_larga`, `fecha_lista` y `estado_clase`
  vienen de `agenda.py` (se registran en `create_app`). Los nombres de meses y días
  deben seguir en castellano: hay tests que verifican que no se filtren nombres en
  inglés en las páginas.

## Convenciones que te pueden morder

- **Los números de diente son FDI** (`11-18`, `21-28`, `31-38`, `41-48`, más la
  dentición temporaria `51-55, 61-65, 71-75, 81-85`). Las constantes de cuadrante
  `Q1..Q8`, `UPPER_ROW`, `LOWER_ROW` y `TOOTH_LAYOUTS` están arriba de todo en
  `patients.py`. El README todavía dice "1 a 32 (numeración universal)": quedó
  desactualizado, la verdad es `patients.py`.
- `ToothStatus.surface`: `''` = todo el diente, o `V/P/M/D/O` para una cara, único
  por `(patient_id, tooth_number, surface)`.
- **El minuto de más en los turnos no cumplidos es intencional.** Al poner el
  estado `ausente_aviso`, `ausente_sin_aviso` o `cancelado` se corre `time` un
  minuto para liberar el horario; el filtro `turno_hora` lo resta de nuevo para
  mostrarlo en pantalla. No "arregles" ese off-by-one (ver `agenda._bump_minute` y
  `display_time`).
- `agenda._parse_fecha_ar` acepta `dd/mm/aaaa`, ISO y el formato viejo `yyyy-dd-mm`
  que mandaba el JS anterior del modal de turnos. Mantenelo si tocás el manejo de
  fechas.
- **CSRF está activado globalmente** (`Flask-WTF`). Toda plantilla con formulario
  necesita `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`; los
  POST por JS/AJAX deben pasar por `csrfFetch()` en `static/js/odontogram.js`, que
  lee el tag `meta[name="csrf-token"]` de `templates/base.html`.
- **El rate limiting está activo** a nivel global (`200/day`, `50/hour` por IP,
  almacenamiento en memoria) y por ruta en auth (`register` 5/min, `login` 10/min,
  `olvide-password` 5/min, `restablecer` 10/min).
  Se prende/apaga con la variable de entorno `RATELIMIT_ENABLED`; un 429 muestra el
  mensaje "esperá unos minutos".
- **Restablecer contraseña** (`auth.forgot_password` → `auth.reset_password`): el
  token es un `itsdangerous.URLSafeTimedSerializer` firmado con `SECRET_KEY` (salt
  `restablecer-password`) que vence según `PASSWORD_RESET_MAX_AGE` (1 h por defecto)
  y además lleva una huella del hash: si la contraseña cambia, el enlace viejo deja
  de servir. El POST responde **siempre el mismo mensaje** exista o no la cuenta, a
  propósito, para no filtrar qué emails están registrados. El correo sale por SMTP
  (`MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_USE_TLS`,
  `MAIL_DEFAULT_SENDER`); si `MAIL_SERVER` está vacío o el envío falla, el enlace se
  escribe en `instance/enlaces-restablecer.log` — **nunca** en
  `logs/consultorio.log`, que sí está trackeado en git.
- La política de contraseñas (≥8 caracteres, mayúscula, número y carácter especial)
  está duplicada en `auth._password_strength` y `create_user.password_error`: si la
  cambiás, cambiá las dos.
- Para crear una cuenta hace falta el `REGISTRATION_CODE`; vive en `.env` y se lee
  solo al importar, así que hay que reiniciar el servidor después de usar
  `set_registration_code.py`.
- Los archivos subidos se limitan a 15 MB (`MAX_CONTENT_LENGTH`) y a
  `png/jpg/jpeg/webp/pdf` (`ALLOWED_EXTENSIONS` en `config.py`). Se guardan fuera de
  `/static` y solo son alcanzables por `download_attachment`: nunca los muevas a
  `static/`.
- Al correr la app se escribe `logs/consultorio.log`, que **está trackeado en git**
  (nivel WARNING, rotación de 5 archivos de 5 MB): esperate un working tree sucio
  después de correrla en local.
- La exportación a PDF usa WeasyPrint si está instalado y, si no, hace un fallback
  silencioso a una vista HTML imprimible (`patients.export_patient`). WeasyPrint es
  opcional y no está en `requirements.txt`.
- La agenda siempre muestra un solo odontólogo: `/agenda/` sin `?profesional=<id>`
  redirige al primero disponible. No existe la vista "todos los profesionales".
- Los tests comparan strings literales de la interfaz en castellano (por ejemplo
  `'Todavía no hay pacientes'`, `'incorrectos'`). Si reformulás los mensajes flash,
  se rompen.

## Deploy

`DEPLOY.md` documenta el flujo (gratis) en PythonAnywhere: `.env` con
`python-dotenv` para los secretos, `wsgi.py` como entrada WSGI, `static/` servido
desde la pestaña Web, y base + archivos subidos bajo `instance/`. En el servidor
usá siempre `./setup.sh --no-run` (el `./setup.sh` sin argumentos arranca un
servidor de desarrollo). Después de un `git push`, corré `./update_deploy.sh` en el
servidor (reinstala dependencias y aplica migraciones si hace falta) y apretá
**Reload** en la pestaña Web.

## El README quedó desactualizado

`README.md` sigue siendo bastante fiel para el setup y los comandos, pero se quedó
atrás en detalles: el árbol de archivos, la numeración de dientes y el TODO de
"agregar CSRF" ya no corresponden (CSRF, rate limiting, log de auditoría, agenda y
migraciones ya existen). Ante la duda, mandan el código y este archivo.
