# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

**Situación actual:** Kiba X es todavía un proyecto demo/académico en validación. La persona responsable (Gabriel) lo desarrolla y prueba; ningún consultorio lo usa aún con datos reales de pacientes.

**Usuarios previstos:** un equipo pequeño de consultorio odontológico (1 a 3 profesionales) que comparte una misma base.

- **Odontólogo/a:** atiende, tiene horarios propios y recibe turnos. Es quien carga el odontograma, los estudios y las notas clínicas.
- **Secretario/a:** gestiona pacientes, turnos y agenda, pero no tiene horarios propios ni se le asignan turnos. Puede administrar cuentas junto a un odontólogo.
- **Paciente:** no usa el sistema; el profesional carga su información.

## Product Purpose

Kiba X reúne la ficha del paciente, el odontograma interactivo, los estudios, la evolución fotográfica y las notas de consulta con la agenda del consultorio, para que un equipo pequeño sostenga el ciclo de atención en una sola aplicación y sin papel.

El éxito es que una persona nueva pueda registrarse, dar de alta un paciente, marcar su odontograma y agendar un turno sin leer un manual. Como proyecto demo, el éxito inmediato es validar ese flujo antes de un uso clínico real.

## Positioning

**Sin definir.** El responsable no identifica todavía una diferencia que otra app de consultorio no pueda copiar. La única base confirmada es la combinación de ficha clínica + agenda en un producto simple y de bajo costo. No inventar una afirmación de posicionamiento hasta que se decida.

## Operating Context

- Consultorio pequeño con 1 a 3 profesionales trabajando a la vez sobre una base compartida; hoy no hay separación de pacientes por profesional.
- Uso desde navegador en escritorio, tablet y celular. No hay app nativa ni instalación para el usuario.
- No es un portal de pacientes: los pacientes no se registran ni reservan turnos por su cuenta.
- No es un sistema de facturación ni una historia clínica legal completa.
- La agenda se organiza alrededor de un odontólogo por vista: horarios semanales, excepciones, turnos, sobreturnos, estados, lista de espera y exportación a `.ics`.
- Despliegue previsto en PythonAnywhere (plan gratuito): un solo proceso, SQLite, respaldo manual de la base desde `/admin/backup`, archivos subidos en `instance/uploads/`.
- Convenciones locales: castellano rioplatense, fechas `dd/mm/aaaa` y numeración dental FDI.

## Capabilities and Constraints

**Acceso y cuentas**

- Registro con código del consultorio, login, logout y contraseñas con hash (≥8 caracteres, mayúscula, número y carácter especial).
- Roles `odontologo` y `secretario`; solo los odontólogos son profesionales de la agenda.
- Toda ruta de pacientes y agenda exige sesión iniciada. CSRF global y rate limiting activos.

**Ficha clínica**

- Alta, edición y eliminación de pacientes con auditoría; búsqueda, paginación de 50 e importación desde CSV.
- Datos: nombre, documento, fecha de nacimiento, género, teléfono, email, domicilio y antecedentes médicos.
- Exportación de la ficha a PDF si el servidor tiene WeasyPrint; si no, vista HTML imprimible.

**Odontograma**

- Dentición permanente y temporaria con numeración FDI, diente completo o una cara (`V/P/M/D/O`).
- Estados: sano, caries, obturado/restaurado, corona, endodoncia, extraído, implante, prótesis y ausente.
- Historial por diente con fecha, profesional, estado y nota; edición y eliminación de anotaciones.
- Adjuntos por paciente y por diente: PNG, JPG, JPEG, WEBP y PDF de hasta 15 MB, guardados fuera de `static` y descargables solo con sesión.
- Fotos de evolución (antes/durante/después) y notas de consulta.

**Agenda**

- Horarios semanales por profesional, suspensiones por fecha y franja, turnos, sobreturnos y estados (pendiente, confirmado, presente, atendido, ausente con/sin aviso, cancelado).
- Lista de espera con conversión a turno; exportación de la agenda a `.ics`.
- La vista de agenda muestra un solo odontólogo a la vez, sin vista "todos".

**Plataforma y operación**

- Flask + SQLite, Jinja renderizado en el servidor, Bootstrap y JavaScript vanilla, sin paso de build.
- Un solo proceso desplegable; `migrations/` versionado con Flask-Migrate.
- Sin CI, sin métricas de uso y sin restauración de copias desde la interfaz (el respaldo solo cubre la base, no los archivos subidos).
- Suite de 99 tests con pytest.

**Decisiones abiertas**

- Posicionamiento del producto.
- Auditoría de accesibilidad WCAG 2.1 AA (hoy parcial).
- Restauración de copias de seguridad desde la app.
- Recordatorios automáticos de turnos.
- Consentimiento, retención y borrado según Ley 25.326.
- Tablero de indicadores de uso.
- Separación de datos por profesional, si el piloto la necesita.

## Brand Commitments

- Nombre **Kiba X**, con símbolo de diente y favicon propio.
- Kit de logo en `assets/logo/` (horizontal, apilado, símbolo, icono y monocromos negro/blanco) más la guía `logo_guia_uso.html`.
- Interfaz en castellano rioplatense (voseo), sin emojis; se usan iconos SVG.
- Bajo costo operativo: sin infraestructura paga obligatoria ni servicios externos imprescindibles.

## Evidence on Hand

- `docs/requisitos_y_casos_de_uso.md` (v1.0, 20/10/2026): 68 requisitos funcionales y 12 no funcionales con estado de implementación.
- `docs/objetivos_smart.md`: plan de 90 días y metas de piloto (3 profesionales, 30 pacientes, 60 turnos), todavía no medidas.
- `assets/logo/`: seis SVG de marca y `logo_guia_uso.html`.
- `AGENTS.md`, `README.md` y `DEPLOY.md`: arquitectura, comandos y despliegue.
- `seed_demo_patients.py` para datos de demostración y `tests/` como evidencia de comportamiento actual.
- **Ausencias que no deben inventarse:** no hay usuarios reales, clientes, testimonios, métricas de uso, resultados de auditoría de accesibilidad ni matriz formal de navegadores. La base local (`instance/`) no está versionada y las demos no deben usar datos reales de pacientes.

## Product Principles

1. **La ficha y la agenda son un solo producto.** Cada cambio debe acortar el camino entre registrar un hallazgo clínico y agendar el próximo turno, no crear módulos paralelos.
2. **Hablar el idioma del consultorio.** Castellano rioplatense, numeración FDI y fechas `dd/mm/aaaa` son parte de la función, no una traducción.
3. **Liviano por diseño.** Un proceso, SQLite y un respaldo que se pueda copiar como archivo; ninguna función nueva puede exigir infraestructura paga u operación dedicada.
4. **Dato clínico tratado como dato de salud.** Sesión obligatoria, archivos fuera de lo público y respaldo verificable, aunque el uso actual sea demo.
5. **Un profesional a la vez en la agenda.** No agregar vistas "todos" ni reasignaciones implícitas sin una decisión de producto explícita.

## Accessibility & Inclusion

El objetivo declarado es WCAG 2.1 AA: uso con teclado, lectores de pantalla y contraste mínimo 4.5:1 en modo claro y oscuro. Hay atajos de teclado y modo oscuro implementados, pero la auditoría de accesibilidad está pendiente y no debe darse por cumplida.
