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

## Cómo correrlo localmente (primera vez) — un solo comando

```bash
git clone <url-del-repo> && cd kibax-app
./setup.sh
```

Eso hace **todo**: crea el entorno virtual, instala las dependencias,
genera el `.env` con una `SECRET_KEY` aleatoria, aplica las migraciones
(que ya vienen en el repo, no hace falta `flask db init`) y arranca el
servidor. Cuando termine, abrí **http://localhost:5000**.

Para los días siguientes:

```bash
./run.sh            # arranque rápido (las dependencias ya están instaladas)
```

Otras opciones útiles:

```bash
./setup.sh --no-run   # solo instala deps y prepara la base, sin arrancar
make setup            # equivalente (Makefile)
make run              # arranca la app
make test             # corre los tests
```

En Windows: ejecutá `setup.bat` con doble clic (hace lo mismo y arranca).

La primera vez que abras la web vas a tener que registrarte como
odontólogo/a en `/auth/register`, usando el `REGISTRATION_CODE` que
definiste en el `.env`. Una vez creada la cuenta, iniciá sesión y empezá
a dar de alta pacientes.

### Qué hace `setup.sh` paso a paso (por si algo falla)

| Paso | Comando que ejecuta por vos |
|------|------------------------------|
| Entorno virtual | `python3 -m venv venv` |
| Dependencias | `pip install -r requirements.txt` |
| Secretos | genera `.env` con `SECRET_KEY` aleatoria (si no existe) |
| Base de datos | `flask db upgrade` (aplica las migraciones del repo) |
| Servidor | `python app.py` |

Si preferís hacerlo a mano (modo tradicional), el orden es el mismo:

```bash
python3 -m venv venv
source venv/bin/activate          # en Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # y editar SECRET_KEY / REGISTRATION_CODE
export SECRET_KEY="una-clave-larga-y-aleatoria"
export REGISTRATION_CODE="un-codigo-que-solo-vos-conozcas"

flask db upgrade                  # crea las tablas en instance/odontograma.db
python app.py                     # http://localhost:5000
```

> **Nota:** las migraciones ya están commiteadas en `migrations/`, así que
> **no** necesitás `flask db init` ni `flask db migrate` en un clon nuevo;
> con `flask db upgrade` alcanza. `flask db migrate` se usa solo cuando
> cambiás `models.py` y querés generar una migración nueva.

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


## Cambiar el código de registro (para crear cuentas)

Para registrar una cuenta hace falta el `REGISTRATION_CODE`. Se guarda en el
archivo `.env` y podés verlo o cambiarlo con un comando, sin editar el
archivo a mano:

```bash
python3 set_registration_code.py                  # ver el código actual
python3 set_registration_code.py "mi-codigo-2026" # poner uno propio
python3 set_registration_code.py --generar        # generar uno aleatorio
```

Después de cambiarlo hay que **reiniciar el servidor** (`Ctrl+C` y `./run.sh`),
porque la app lee el `.env` solo al arrancar.

## Scripts utilitarios

| Script | Para qué sirve |
|--------|----------------|
| `reset_password.py` | resetear la contraseña de tu cuenta si te la olvidaste |
| `set_registration_code.py` | ver/cambiar el código de registro |
| `create_user.py` | crear una cuenta de odontólogo/a sin pasar por el registro web |
| `seed_demo_patients.py 50` | cargar pacientes de prueba (datos inventados) |
| `clear_all_patients.py` | borrar todos los pacientes (pide confirmación) |

Todos se ejecutan con el Python del entorno virtual activado, p. ej.:
`source venv/bin/activate && python reset_password.py`.

## Darle acceso a otra persona (ej. que el profesor pruebe la página)

### 1. Crearle la cuenta (una sola vez)

```bash
source venv/bin/activate
python create_user.py                      # te pregunta email, nombre y contraseña
# o directo:
./venv/bin/python create_user.py profe@mail.com --nombre "Ana Peres" --password "Clave123!"
```

Después le pasás el email y la contraseña, y entra en `/auth/login`. No necesita
saber el `REGISTRATION_CODE` ni registrarse.

### 2. Que entre sin instalar nada: exponer la app en tu red

```bash
HOST=0.0.0.0 ./run.sh        # escucha en todas las interfaces de tu red
```

Y le pasás **http://<tu-ip-local>:5000** (averiguás tu IP con `hostname -I`).
Para otro puerto: `PORT=5055 ./run.sh`.

- Solo funciona si las dos PCs están en la **misma red** (mismo WiFi/router).
- Cuando `HOST` no es localhost, el modo debug se desactiva solo (el debugger de
  Werkzeug permitiría ejecución remota de código). Para forzarlo: `FLASK_DEBUG=1 ./run.sh`.
- Es para una prueba informal. Para acceso desde internet o datos de salud hace
  falta HTTPS, un servidor de verdad (gunicorn + Nginx o un PaaS tipo
  Render/Railway/PythonAnywhere) y reemplazar SQLite por PostgreSQL.

### Sobre la persistencia de los datos

La base (`instance/odontograma.db`) **sí persiste** entre reinicios: los usuarios
y pacientes que crees siguen ahí mientras no borres la carpeta `instance/`. Lo
que NO persiste es un clon nuevo del repo, porque `instance/` está en
`.gitignore` (cada máquina tiene su propia base). Por eso:

- La cuenta del profesor se crea **en la PC donde corre la app** (la tuya, si
  entra por la red).
- Si en algún momento llevás la base a otra máquina, copiá la carpeta
  `instance/` completa (base + archivos subidos) o usá el backup de
  `/admin/backup` dentro de la app.

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
