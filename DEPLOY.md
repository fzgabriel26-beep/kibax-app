# Deploy de prueba en PythonAnywhere (gratis)

Objetivo: que otras personas (de confianza) puedan entrar desde internet,
cargar datos y que **persistan**, sin necesidad de que tu PC esté prendida.
PythonAnywhere gratis alcanza de sobra para esto: HTTPS incluido, filesystem
persistente (tu SQLite y los archivos subidos quedan en su disco) y un
subdominio propio `https://<tu-usuario>.pythonanywhere.com`.

> Los datos son de prueba / ficticios. Si en algún momento pasás a datos
> clínicos reales, revisá la sección "Endurecer para producción".

## Requisitos previos

- Cuenta gratis en https://www.pythonanywhere.com (no pide tarjeta).
- El repo subido a GitHub (ya lo está: `fzgabriel26-beep/kibax-app`).

---

## Paso 1 — Crear la cuenta

Entrá a https://www.pythonanywhere.com/registration/register/beginner/
y creá la cuenta gratuita ("Create a Beginner account"). Anotá tu **usuario**
(va a ser parte de la URL).

## Paso 2 — Traer el código

En PythonAnywhere abrí una consola: pestaña **Consoles** → **Bash**.

```bash
# Clonar el repo (público)
git clone https://github.com/fzgabriel26-beep/kibax-app.git
cd kibax-app
```

Si más adelante hacés cambios y querés actualizar el deploy:

```bash
cd ~/kibax-app && git pull
# y después Reload de la web (paso 6)
```

## Paso 3 — Entorno virtual con Python 3.11+

El código usa `datetime.UTC`, que requiere Python 3.11 o superior.

```bash
python3.11 -m venv venv          # si esa versión no existe, probá python3.12
source venv/bin/activate
pip install -r requirements.txt
```

Verificá la versión: `python --version` → debe decir 3.11.x o 3.12.x.

## Paso 4 — Variables de entorno (secretos)

Creá el archivo `.env` (no se sube a git, queda solo en tu cuenta de PA):

```bash
cd ~/kibax-app
python -c "import secrets; open('.env','w').write('SECRET_KEY=%s\nREGISTRATION_CODE=%s\n' % (secrets.token_hex(32), secrets.token_urlsafe(12)))"
cat .env       # copiate el REGISTRATION_CODE: es el código para registrar cuentas
```

`SECRET_KEY` queda aleatoria. El `REGISTRATION_CODE` es el que les vas a pasar
a la gente para que se registre (o les creás cuentas vos con
`python create_user.py`, ver paso 5).

## Paso 5 — Crear la base de datos

```bash
cd ~/kibax-app
source venv/bin/activate
export FLASK_APP=app.py
flask db upgrade          # crea instance/odontograma.db con todas las tablas
```

Verificación rápida de que la base quedó bien:

```bash
python - <<'EOF'
from app import create_app
from models import User
with create_app().app_context():
    print("usuarios en la base:", User.query.count())
EOF
```

(Opcional) Crear cuentas sin que la gente se registre:

```bash
python create_user.py amigo@mail.com --nombre "Amigo Uno" --password "Clave123!"
```

## Paso 6 — Configurar la app web

Pestaña **Web** → **Add a new web app**:

1. Dominio: ya viene `​<tu-usuario>.pythonanywhere.com` → Next.
2. **Manual configuration** (NO elijas Flask) → Python **3.11** (o la que usaste) → Next.

Después, en la misma pestaña **Web**, en la sección **Code**:

- **Source code**: `/home/<tu-usuario>/kibax-app`
- **Working directory**: `/home/<tu-usuario>/kibax-app`
- **WSGI configuration file**: hacé clic en el link del archivo
  (`/var/www/<tu-usuario>_pythonanywhere_com_wsgi.py`), borrá TODO su contenido
  y pegá esto:

```python
import os
import sys

sys.path.insert(0, '/home/<TU-USUARIO>/kibax-app')

from app import app as application
```

(reemplazá `<TU-USUARIO>` por tu usuario real de PythonAnywhere)

## Paso 7 — Archivos estáticos

En la misma pestaña **Web**, sección **Static files**, agregá una entrada:

| URL | Directory |
|-----|-----------|
| `/static/` | `/home/<tu-usuario>/kibax-app/static` |

Así el CSS/JS se sirve rápido (la app también podría servirlos, pero conviene
que los sirva el servidor web).

## Paso 8 — Encender

Arriba de todo en la pestaña **Web**, botón verde **Reload**.

Después entrá a:

```
https://<tu-usuario>.pythonanywhere.com
```

Debería llevarte a `/auth/login`. Si no carga, revisá el **Error log** y el
**Server log** en la misma pestaña (ahí aparece el traceback real).

---

## Dar acceso a la gente

Dos opciones:

1. **Les pasás el `REGISTRATION_CODE`** (el del paso 4) y se registran solos en
   `/auth/register`.
2. **Les creás la cuenta vos** (recomendado, no exponés el código):

```bash
cd ~/kibax-app && source venv/bin/activate
python create_user.py mail@ejemplo.com --nombre "Nombre" --password "Clave123!"
```

Después de crear cada cuenta: botón **Reload** en la pestaña Web (o directamente
no hace falta, la base se lee en cada request — solo hace falta Reload si
cambiaste código).

## Persistencia

- La base vive en `/home/<tu-usuario>/kibax-app/instance/odontograma.db`.
- Los archivos subidos, en `/home/<tu-usuario>/kibax-app/instance/uploads/`.
- Ninguno se borra al reiniciar la app. Los backups automáticos de
  PythonAnywhere (plan pago) no aplican en la cuenta gratis: hacé backup
  propio cada tanto con **Files** → descargar la carpeta `instance/`, o usá el
  botón de backup dentro de la app (`/admin/backup`, deja copias en
  `instance/backups/`).
- Si alguna vez necesitás bajar la base a tu PC: **Files** → navegar a
  `kibax-app/instance/` → descargar `odontograma.db`.

## Límites del plan gratis (suficientes para una prueba)

- 1 sola aplicación web.
- El subdominio es `<tu-usuario>.pythonanywhere.com`.
- La app se "duerme" si nadie la usa un tiempo? **No**: la app gratis se
  mantiene corriendo siempre (lo que está limitado es la CPU diaria).
- HTTPS incluido.

## Endurecer para producción (cuando ya no sea "de prueba")

1. `SESSION_COOKIE_SECURE = True` y `WTF_CSRF_SSL_STRICT = True` en
   `config.py` (la app ya corre bajo HTTPS).
2. Revisar que `FLASK_DEBUG` no esté en `1` (en PythonAnywhere no se usa
   `app.run()`, así que el debugger de Werkzeug no se activa).
3. Si crece el uso concurrente, migrar de SQLite a PostgreSQL
   (`DATABASE_URL=postgresql://...`) — las migraciones de Flask-Migrate
   siguen funcionando igual.
4. Backups programas de `instance/`.
5. Revisar la Ley 25.326 (datos personales) antes de cargar datos reales.

---

## Alternativa rápida: desde tu PC (sin PythonAnywhere)

Si solo es una demo corta y tu PC puede quedar prendida:

```bash
HOST=0.0.0.0 ./run.sh        # y les pasás http://<tu-ip>:5000 (hostname -I)
```

Pero eso solo funciona dentro de tu WiFi. Para internet sin subirla a un
servidor, se puede usar un túnel de Cloudflare (`cloudflared`), que te da una
URL pública apuntando a tu PC.
