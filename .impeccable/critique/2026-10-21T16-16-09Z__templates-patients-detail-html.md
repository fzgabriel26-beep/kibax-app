---
target: ficha del paciente (templates/patients/detail.html)
total_score: 22
max_score: 40
na_heuristics: 
p0_count: 1
p1_count: 4
target_identity: "file:/home/kuro/Proyectos/repos/test/kibax-app/templates/patients/detail.html"
target_fingerprint: "sha256:7eac296812ac361d76ba71195c153ec873cc9f505135e2c25527cc68b5ad8070"
target_path: /home/kuro/Proyectos/repos/test/kibax-app/templates/patients/detail.html
timestamp: 2026-10-21T16-16-09Z
slug: templates-patients-detail-html
---
## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|---|---|---|
| 1 | Visibility of System Status | 2 | Al entrar, ninguna pestaña está activa: estudios, evolución y notas quedan ocultos y parecen no existir |
| 2 | Match System / Real World | 3 | FDI, voseo y `dd/mm/aaaa` correctos; "Nace 17/04/1991", "Click" y dentición de leche visible en adultos |
| 3 | User Control and Freedom | 2 | Hay "Cancelar" y deep-link por hash, pero sin undo; borrar es definitivo y el reorden de fotos no persiste |
| 4 | Consistency and Standards | 2 | Dos `.btn-solid` en el mismo modal y tres patrones de borrado con confirms distintos |
| 5 | Error Prevention | 2 | El tipo de estudio arranca en "Panorámica": subir un archivo sin tocar el select reemplaza la radiografía principal |
| 6 | Recognition Rather Than Recall | 2 | El diente comunica estado solo por color; la leyenda no es focusable ni se anuncia |
| 7 | Flexibility and Efficiency | 2 | Atajos `n/p/a` que no cubren charting; sin acciones masivas ni recorrido por teclado entre dientes |
| 8 | Aesthetic and Minimalist Design | 3 | Limpio y aireado, pero compiten logout arena, 9 estados y 52 dientes |
| 9 | Error Recovery | 2 | Sesión vencida en el modal se reporta como "Error de conexión", no como "volvé a iniciar sesión" |
| 10 | Help and Documentation | 2 | Buena microcopia por panel; filtro de leyenda y atajos son indescubribles |
| **Total** | | **22/40** | **Acceptable** (55%) |

## Design Specificity Verdict

**Veredicto: la mitad superior está hecha para este producto; la mitad inferior es un CRUD con otro color.**

**LLM assessment.** Lo específico es real y no se transfiere a otro SaaS: el odontograma FDI con arcadas permanente y temporaria, la geometría de caras por cuadrante, el overlay para estados de diente completo, el filtro por leyenda, la panorámica contigua al chart y los antecedentes arriba del fold. La paleta menta/arena sostiene "El Gabinete de Menta" sin caer en el dashboard azul que `DESIGN.md` declara como anti-referencia.

Lo intercambiable empieza debajo de las pestañas: "Estudios y documentación" es un `<input type=file>` + select + lista; "Notas de consulta" son tres inputs de una línea; "Evolución" son cards con foto y ✕. Nada ahí habla de odontología. Y hay una oportunidad de carácter perdida que además rompe el Principio 1 de `PRODUCT.md` ("la ficha y la agenda son un solo producto"): **la ficha no muestra ni permite agendar el próximo turno**. No hay "próximo turno", no hay "agendar", no hay historial de visitas. El puente hallazgo → turno no existe.

**Deterministic scan.** La corrida CLI estática es casi ciega en este repo: `templates/patients/detail.html` devuelve 3 `broken-image` y 1 advisory `design-system-color`, pero los tres `broken-image` son falsos positivos (dos son `src=""` en contenedores ocultos que se rellenan al abrir modal/lightbox, uno es lazy-load con `data-src`) y la advisory es el negro por defecto del user-agent: el detector no resuelve `{% extends %}` ni `url_for()`, así que no carga `style.css`. Con `--no-design-system` quedan los mismos 3 warnings. La corrida en navegador sobre el HTML renderizado con el CSS real sí es concluyente: **46 hallazgos en desktop, 45 en mobile y 9 en el listado**, con `low-contrast` 18, `undersized-ui-text` 20 y `nested-cards` 3. El contraste medido confirma lo que la revisión de diseño sospechaba y va más allá: navbar **1.7:1**, etiquetas de arcada en arena **1.7:1**, enlaces **2.1:1**, texto secundario **3.1–3.5:1**, y el aviso de antecedentes **2.8:1**.

**Visual overlays.** No hay overlay inyectado en el navegador: el navegador del detector se usó sobre un snapshot renderizado servido en local, no sobre el servidor Flask autenticado, y no se inyectó `detect.js`.

## Overall Impression

La ficha tiene un centro de gravedad claro —el odontograma— y lo defiende bien. El problema no es el gusto: es que la pantalla **esconde su propio contenido** al cargar (pestañas sin activar), se rompe en mobile (814 px de ancho contra 390) y falla contraste en los lugares donde el dato es más delicado, incluido el antecedente de alergia. La mayor oportunidad no es cosmética: es cerrar el circuito clínico mostrando y creando el próximo turno desde la ficha.

## What's Working

1. **El odontograma como objeto propio.** FDI correcto por cuadrante, cinco caras, overlay para diente completo, hover con lift y filtro por leyenda. Es el activo de diseño del producto y justifica el proyecto.
2. **Orden clínico correcto.** Nombre, edad, antecedentes y las dos imágenes clínicas arriba: la primera pantalla responde "¿quién es y qué tiene?" antes de pedir cualquier acción.
3. **Sistema visual coherente y honesto.** Tokens en claro/oscuro, estados vacíos que explican cómo resolverlos, microcopia rioplatense y CSRF consistente en todos los POST.

## Priority Issues

### [P0] Las pestañas no muestran nada al cargar
- **What**: `#pane-estudios`, `#pane-evolucion` y `#pane-notas` son `tab-pane fade` sin `active`, y el JS solo activa una pestaña si hay hash en la URL (`detail.html:539-550`). En una visita limpia, todo el contenido inferior desaparece y "Eliminar paciente" queda pegado a la barra de pestañas.
- **Why it matters**: el usuario cree que el paciente no tiene estudios, evolución ni notas. Es una pérdida de información clínica percibida, no un detalle visual. Y el único botón visible en esa zona pasa a ser el destructivo.
- **Fix**: marcar la primera pestaña y su panel como `active show` con `aria-selected="true"`, o activar la primera en JS cuando no hay hash.
- **Suggested command**: `/impeccable harden`

### [P1] La ficha se desborda en mobile y el borrado es inalcanzable sin mouse
- **What**: a 390 px, `document.scrollWidth` mide **814 px**: 424 px de scroll lateral. `section.panel.odontogram-panel` mide 802 px y arrastra encabezado, leyenda y arcada; el `overflow-x: auto` de `.arch-row` no evita que el panel crezca (falta `min-width: 0` en los hijos del grid). Además `.tooth-file-del` solo aparece con `:hover`.
- **Why it matters**: en tablet o celular la ficha se vuelve incómoda y el borrado de un estudio no existe. El producto declara uso desde navegador en escritorio, tablet y celular.
- **Fix**: `min-width: 0` en los hijos del grid, scroll interno visible con indicador, y borrado siempre visible o dentro de un menú por archivo. Verificar a 390 px y a 200% de zoom.
- **Suggested command**: `/impeccable adapt`

### [P1] Contraste insuficiente en la navegación, los enlaces y el aviso de antecedentes
- **What**: navbar blanco sobre menta translúcida **1.7:1**; `#brand-x` **1.5:1**; `.arch-wrap-primary .arch-label` en arena **1.7:1**; `a` en menta sobre blanco **2.1:1**; `.notice-card` de antecedentes **2.8:1**; `.patient-meta` y `.panel-head p` **3.1–3.5:1**. Todos por debajo del 4.5:1 de WCAG AA.
- **Why it matters**: "Antecedentes: alergia a la penicilina" es el dato más crítico de la pantalla y es el que peor se lee. En un consultorio con luz ambiente y pantallas modestas, esto no es académico.
- **Fix**: oscurecer el texto de navbar y enlaces (menta profunda o grafito), llevar el aviso de antecedentes a grafito clínico sobre el tinte, y subir el texto secundario a un gris con ≥4.5:1. Revalidar ambos modos.
- **Suggested command**: `/impeccable colorize` (o `/impeccable audit` para el barrido completo)

### [P1] Editar o borrar una anotación desincroniza el color del diente
- **What**: `tooth_log_update` (`patients.py:518`) y `tooth_log_delete` (`patients.py:560`) tocan `ProcedureLog` pero no `ToothStatus`; la creación sí lo actualiza (`patients.py:489`). Tras recargar, el historial y el odontograma cuentan cosas distintas.
- **Why it matters**: es un registro clínico. Que el color sobreviva a la nota que lo justificaba —o que borrar el historial no revierta el estado— erosiona la confianza en todo el chart.
- **Fix**: sincronizar `ToothStatus` en update y recalcular desde el log más reciente (o volver a `sano`) en delete.
- **Suggested command**: `/impeccable harden`

### [P1] El default "Panorámica" puede reemplazar la radiografía principal sin aviso
- **What**: el select de categoría del upload arranca en `panoramica` y la ficha toma el adjunto panorámico más reciente. Subir cualquier archivo sin tocar el select cambia el estudio principal.
- **Why it matters**: un error de un clic sobrescribe la referencia visual del caso, y el usuario no recibe confirmación de que lo hizo.
- **Fix**: opción vacía `disabled selected` + `required`, o default "Otro"; confirmación explícita al reemplazar la panorámica.
- **Suggested command**: `/impeccable harden`

### [P2] Charting lento y con fricción clínica
- **What**: cada cambio exige diente → modal → cara → estado → **nota obligatoria** (`#toothNote` con `required`) → guardar. Sin acciones rápidas, sin "marcar sano", sin copiar al contralateral, sin navegación por teclado entre dientes.
- **Why it matters**: marcar una boca completa son 32 aperturas de modal. El flujo premia chartear poco, que es lo contrario de lo que el producto necesita.
- **Fix**: chips de estado rápido sobre el diente seleccionado, nota opcional con default ("Sin observaciones"), y `←/→` para recorrer dientes.
- **Suggested command**: `/impeccable polish`

## Persona Red Flags

**Sam (accesibilidad).** `a` en menta sobre blanco = 2.1:1 y navbar 1.7:1: no puede leer los nombres de adjuntos ni la marca. Los `.tooth-btn` no tienen `aria-label`: el lector anuncia "16, botón", sin estado. La leyenda son `<span>` clickeables sin `tabindex`, `role` ni `aria-pressed`. El estado se codifica solo por color. `main.container` anima `fadeUp` sin `prefers-reduced-motion` y los toasts no tienen `aria-live`. El modal no tiene `aria-labelledby`.

**Alex (odontólogo power user).** Para 32 dientes hace 32 aperturas de modal con 4 controles cada una. Los atajos `n/p/a` no incluyen la tarea real y `p` puede navegar fuera si el foco está en un botón del modal. El select "Sin diente asociado" lista 52 dientes planos. La leyenda filtra solo `.arch-wrap` (dentición permanente): los dientes de leche nunca se atenúan. Reordenar fotos con drag no guarda nada.

**Casey (mobile, un dedo).** A 390 px hay 424 px de scroll lateral y el odontograma se corta sin pista de scroll. El borrado de estudios vive en `:hover`, inalcanzable al tacto. El botón más fuerte de la pantalla, "Cerrar sesión", está arriba y es arena. Subir una foto desde el celular obliga a tipear una descripción.

## Minor Observations

- "Nace 17/04/1991" en la ficha vs "Nacimiento" en `export.html`; "Click para ver" vs el voseo del resto.
- "Ausente" cae solo en la segunda fila de la leyenda y rompe la lectura de los 9 estados.
- Cada pestaña repite su label como `<h2>` justo debajo de la pestaña.
- El sistema de toasts existe pero solo lo usa el atajo `?`.
- El límite de 15 MB y los formatos aceptados no se anuncian hasta que falla la subida.
- `body.dark .panel` aplica `backdrop-filter`, contra `La Regla del Vidrio Discreto`.
- La galería de evolución ordena descendente: una secuencia "Antes → Después" se lee al revés.
- `nested-cards` (3) y `skipped-heading` (h5 del modal Bootstrap) son ruido o nit de a11y, no defectos de diseño; `overused-font` (Inter 93%) es una decisión declarada del sistema.

## Questions to Consider

- Si la agenda es la otra mitad del producto, ¿por qué desde la ficha no puedo ver ni crear el próximo turno? ¿La ficha es una historia clínica o un visor de odontograma?
- Si esto va a ser un registro clínico, ¿por qué el color del diente sobrevive a la nota que lo justifica y borrar el historial no deja rastro?
- ¿Un odontólogo va a chartear una boca entera desde el celular? Si sí, el target real es una cara de 12 px; si no, la ficha móvil no necesita existir — y hoy está rota igual.
