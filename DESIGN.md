---
name: Kiba X
description: "Sistema visual del consultorio odontológico: menta clínica, vidrio suave y acento arena."
colors:
  menta-clinica: "#7EBFB5"
  menta-profunda: "#5A9E94"
  menta-en-reposo: "#EDF7F5"
  arena-calida: "#E8B87A"
  arena-encendida: "#F0CB9A"
  marron-de-sobre: "#5A4530"
  lienzo-consultorio: "#F4F6F5"
  vidrio-claro: "#FFFFFF"
  vidrio-con-sol: "#FAFCFB"
  grafito-clinico: "#3A4543"
  grafito-suave: "#7E8C88"
  borde-instrumental: "#E4EAE7"
  borde-tenue: "#EDF1EF"
  terracota-alerta: "#B06060"
  terracota-reposo: "#FDF0EE"
  consultorio-nocturno: "#1A2020"
  vidrio-nocturno: "#222C2A"
  vidrio-nocturno-iluminado: "#2A3532"
  grafito-claro: "#D8E2DF"
  grafito-medio: "#9AA8A4"
  borde-nocturno: "#303E3A"
  menta-nocturna: "#223532"
  caries-lavada: "#E8A0A0"
  azul-obturacion: "#A0C4DE"
  oro-corona: "#E0CC8A"
  lila-endodoncia: "#C4A8D4"
  gris-extraccion: "#B8C4C0"
  verde-implante: "#8ED4BC"
  arcilla-protesis: "#D4B098"
  gris-ausencia: "#A8B4B0"
  turno-confirmado: "#2E9E6B"
  turno-confirmado-suave: "#E3F4EB"
  turno-presente: "#2F7FE0"
  turno-presente-suave: "#E4EDFB"
  turno-atendido: "#8B5CF6"
  turno-atendido-suave: "#EDE6FE"
  turno-ausente-aviso: "#D9891F"
  turno-ausente-aviso-suave: "#FCF0DB"
  turno-ausente-sin-aviso: "#D64545"
  turno-ausente-sin-aviso-suave: "#FBE4E4"
  turno-cancelado: "#59636F"
  turno-cancelado-suave: "#E8EBEF"
typography:
  display:
    fontFamily: "Space Grotesk, Inter, sans-serif"
    fontSize: "2.5rem"
    fontWeight: 500
    lineHeight: 1.2
  headline:
    fontFamily: "Space Grotesk, Inter, sans-serif"
    fontSize: "1.6rem"
    fontWeight: 500
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Space Grotesk, Inter, sans-serif"
    fontSize: "1.15rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  body:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  body-small:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "0.85rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "0.83rem"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "-0.01em"
  eyebrow:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "0.72rem"
    fontWeight: 700
    lineHeight: 1.4
    letterSpacing: "0.08em"
rounded:
  micro: "6px"
  sm: "10px"
  md: "14px"
  lg: "20px"
  xl: "24px"
  pill: "999px"
spacing:
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "20px"
  xl: "24px"
  2xl: "32px"
  3xl: "40px"
components:
  button-primary:
    backgroundColor: "{colors.arena-calida}"
    textColor: "{colors.marron-de-sobre}"
    rounded: "{rounded.sm}"
    padding: "0.5rem 1rem"
  button-primary-hover:
    backgroundColor: "{colors.arena-encendida}"
    textColor: "{colors.marron-de-sobre}"
    rounded: "{rounded.sm}"
    padding: "0.5rem 1rem"
  button-outline:
    backgroundColor: "{colors.vidrio-claro}"
    textColor: "{colors.grafito-clinico}"
    rounded: "{rounded.sm}"
    padding: "0.5rem 1rem"
  button-outline-hover:
    backgroundColor: "{colors.menta-en-reposo}"
    textColor: "{colors.menta-clinica}"
    rounded: "{rounded.sm}"
    padding: "0.5rem 1rem"
  button-nav-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.vidrio-claro}"
    rounded: "{rounded.sm}"
    padding: "0.5rem 1rem"
  button-danger-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.terracota-alerta}"
    rounded: "{rounded.sm}"
    padding: "0.5rem 1rem"
  input-field:
    backgroundColor: "{colors.vidrio-claro}"
    textColor: "{colors.grafito-clinico}"
    rounded: "{rounded.sm}"
    padding: "0.375rem 0.75rem"
  input-search:
    backgroundColor: "{colors.vidrio-claro}"
    textColor: "{colors.grafito-clinico}"
    rounded: "{rounded.sm}"
    padding: "0.375rem 0.75rem 0.375rem 2.2rem"
  panel:
    backgroundColor: "{colors.vidrio-claro}"
    textColor: "{colors.grafito-clinico}"
    rounded: "{rounded.lg}"
    padding: "1.5rem 1.5rem 1.75rem"
  patient-card:
    backgroundColor: "{colors.vidrio-claro}"
    textColor: "{colors.grafito-clinico}"
    rounded: "{rounded.md}"
    padding: "1.1rem 1.2rem"
  badge-role:
    backgroundColor: "{colors.menta-en-reposo}"
    textColor: "{colors.menta-profunda}"
    rounded: "{rounded.pill}"
    padding: "0.12rem 0.45rem"
  tab-active:
    backgroundColor: "{colors.vidrio-claro}"
    textColor: "{colors.menta-profunda}"
    rounded: "10px 10px 0 0"
    padding: "0.55rem 1.1rem"
  status-select:
    backgroundColor: "{colors.turno-confirmado-suave}"
    textColor: "{colors.turno-confirmado}"
    rounded: "{rounded.micro}"
    padding: "0.25rem 0.5rem"
---

# Design System: Kiba X

## Overview

**Creative North Star: "El Gabinete de Menta"**

Kiba X se ve como el gabinete de un consultorio ordenado: superficies de vidrio apenas lechoso, instrumentos alineados, una menta clínica que tiñe la navegación y un acento arena que marca lo que hay que tocar. La interfaz es **clínica y aireada**: mucho blanco entre bloques, bordes de un píxel, radios generosos y jerarquía tipográfica corta. Nada compite con el dato del paciente, y el odontograma —con sus nueve colores de estado— es el único lugar donde la paleta se permite saturación.

El sistema es una capa propia sobre Bootstrap 5.3.3, sin paso de build: un único `style.css` define tokens, componentes y modo oscuro. Esa restricción es una decisión de producto, no una deuda: cualquier pantalla nueva debe resolverse con tokens existentes, HTML de Jinja y JS vanilla, sin introducir un framework de estilos.

El modo oscuro es un ciudadano de primera, no un afterthought: no invierte colores, redefine la misma familia de tokens sobre un grafito verdoso y mantiene el acento arena intacto.

**Anti-referencia confirmada:** el dashboard SaaS azul genérico. Nada de azul corporativo saturado como color de marca, degradados fríos de fondo ni tablas densas tipo panel de administración.

**Key Characteristics:**
- Vidrio suave: superficies blancas translúcidas con desenfoque de fondo (8–20 px) y sombras ambientales muy bajas.
- Menta clínica como color de estructura (navbar, enlaces, foco) y arena cálida como color de acción.
- Aire: densidad baja, padding generoso, separación por espacio antes que por líneas.
- Semántica cromática reservada: estados de diente y de turno tienen su propia escala, ajena a la marca.
- Tipografía en dos voces: Space Grotesk para títulos y marca, Inter para todo lo demás.

## Colors

Paleta de consultorio: una menta desaturada que estructura, una arena cálida que invita a la acción y un grafito verdoso que sostiene la lectura.

### Primary
- **Menta Clínica**: color de la barra de navegación, de los enlaces y del anillo de foco. Es estructura, no decoración.
- **Menta Profunda**: texto y bordes sobre fondos de menta en reposo; también el estado activo de pestañas y selectores.
- **Menta en Reposo**: relleno de hover, fondos de badges de rol y tarjetas de aviso. Es el tinte que aparece cuando algo se toca.
- **Menta Nocturna**: el mismo rol en modo oscuro, sobre el vidrio nocturno.

### Secondary
- **Arena Cálida**: color de la acción principal (dar de alta, guardar, cerrar sesión) y de los avatares. Aparece en gradiente hacia **Arena Encendida** en botones y paginación activa.
- **Marrón de Sobre**: texto sobre arena. Nunca blanco puro sobre el acento: el contraste y el tono cálido se pierden.

### Neutral
- **Lienzo de Consultorio**: fondo general, con un degradado diagonal apenas perceptible entre tres grises verdosos.
- **Vidrio Claro** / **Vidrio con Sol**: superficies de tarjetas, paneles y campos; el segundo es el hover de filas y listas.
- **Grafito Clínico** / **Grafito Suave**: texto principal y texto secundario (metadatos, ayudas, pies).
- **Borde de Instrumental** / **Borde Tenue**: bordes de 1 px; el tenue se usa en superficies flotantes y separadores internos.
- **Terracota de Alerta** / **Terracota en Reposo**: acciones destructivas, textos de error y estados bloqueados.
- **Consultorio Nocturno**, **Vidrio Nocturno**, **Grafito Claro**, **Grafito Medio**, **Borde Nocturno**: la contraparte oscura de la misma familia. El modo oscuro no reutiliza los grises claros con opacidad: define valores propios.

### Semántica del odontograma
Nueve rellenos por estado, lavados y de saturación media, pensados para leerse como caras de un mismo diente: caries, obturado, corona, endodoncia, extraído, implante, prótesis y ausente. El estado sano es el vidrio claro con borde de instrumental, de modo que un diente sano se lea como ausencia de marca.

### Semántica de turnos
Cada estado de turno es un par: color de tinta y su tinte suave de fondo. Confirmado (verde), presente (azul), atendido (violeta), ausente con aviso (ámbar), ausente sin aviso (rojo) y cancelado (gris azulado). El par se usa junto, nunca el color solo.

### Named Rules
**La Regla del Diente Manda.** Los colores de estado del odontograma y de los turnos no se reutilizan como color de marca, fondo de página ni decoración. Si un tono ya significa "caries" o "cancelado", no puede significar otra cosa.

**La Regla del Acento Escaso.** La arena ocupa menos del 10% de cualquier pantalla: una acción principal, los avatares y los contadores. Su rareza es lo que la vuelve una señal.

**La Regla del Par de Estado.** Todo estado se comunica con tinta + tinte de fondo + texto, nunca con color solo. Si se imprime en blanco y negro o se mira con daltonismo, la etiqueta tiene que seguir siendo legible.

## Typography

**Display Font:** Space Grotesk (con Inter, sans-serif)
**Body Font:** Inter (con system-ui, sans-serif)

**Character:** Space Grotesk aporta el filo geométrico justo para títulos cortos y la marca; Inter hace todo el trabajo de lectura, formularios y datos clínicos. La mezcla se siente instrumento, no editorial.

### Hierarchy
- **Display** (500, 2.5 rem, 1.2): título de página (`h1`). Una sola vez por pantalla, siempre acompañado de un `eyebrow` cuando la página pertenece a un módulo.
- **Headline** (500, 1.6 rem, 1.2, tracking negativo): títulos de tarjetas de autenticación y encabezados de sección amplios.
- **Title** (700, 1.15 rem, tracking negativo): marca, nombre del profesional en la agenda y títulos de panel (`h2`, 1.2 rem).
- **Body** (400, 1 rem, 1.5): texto corriente y valores de formulario. Los metadatos bajan a 0.8–0.9 rem y usan Grafito Suave.
- **Label** (600, 0.83 rem, tracking negativo): etiquetas de formulario y botones. Los botones usan 0.85 rem.
- **Eyebrow** (700, 0.72 rem, mayúsculas, tracking 0.08 em): módulo sobre el título ("Consultorio", "Pacientes"). Es el único texto en mayúsculas además de las etiquetas de tabla y los badges.

### Named Rules
**La Regla de las Dos Voces.** Space Grotesk solo en `h1`, `h2`, `h3` y la marca. Inter en todo lo demás, incluidos los números FDI del odontograma, las horas de turno y los contadores: son datos, no titulares.

**La Regla del Título Corto.** Los títulos no pasan de dos líneas. Si hace falta más contexto, va en el párrafo de apoyo del panel con Grafito Suave, no en el título.

## Layout

Un contenedor único de hasta 1600 px con `padding` vertical de 1.5 rem. Cada página abre con un encabezado flex (título a la izquierda, acciones a la derecha, `margin-bottom` 1.5 rem) que envuelve en pantallas chicas.

- **Listado de pacientes:** grilla `auto-fill` con mínimo 240 px y separación de 1 rem; la tarjeta es el único elemento con hover elevado.
- **Ficha del paciente:** grilla de 2 columnas (2fr odontograma / 1fr panorámica) con 1.25 rem de separación; colapsa a una columna en 860 px. Debajo, pestañas de sección con paneles de radio inferior.
- **Agenda:** sidebar fijo de 260 px + área principal, sin separación entre columnas; la sidebar es sticky a 60 px del borde superior. Colapsa a una columna en 960 px y la sidebar pasa a ser una banda superior.
- **Formularios:** tarjeta centrada de 780 px como máximo, con 2 rem de padding. Autenticación: tarjeta de 440 px.
- **Ritmo:** múltiplos de 4 px derivados de rem; los bloques internos usan 0.5 / 0.75 / 1 / 1.25 / 1.5 rem y los saltos de sección 2 / 2.5 rem.

### Breakpoints
- 576 px: odontograma y uploads se compactan; toasts ocupan el ancho.
- 768 px: la navbar colapsa a hamburguesa; el detalle del diente pasa de dos columnas a apilado.
- 860 px: la ficha pasa de dos columnas a una.
- 960 px: la agenda pasa de sidebar + main a una sola columna.

### Named Rules
**La Regla del Aire Antes que la Línea.** Para separar bloques, primero espacio; después borde tenue; el borde fuerte queda para tablas y encabezados de columna.

## Elevation & Depth

El sistema usa **capas translúcidas**: las superficies flotan sobre el lienzo con `backdrop-filter` y sombras ambientales de baja opacidad. La profundidad es atmosférica, no estructural: no hay bordes duros ni planos apilados con contraste fuerte. En modo oscuro las mismas sombras se vuelven más densas y el vidrio se oscurece, pero la lógica no cambia.

### Shadow Vocabulary
- **Reposo** (`0 1px 2px rgba(0,0,0,.03)`): tarjetas y alertas en estado normal.
- **Superficie** (`0 2px 8px rgba(0,0,0,.05)`): paneles y tarjetas de formulario.
- **Hover** (`0 4px 16px rgba(0,0,0,.06)`): tarjeta de paciente al pasar el mouse, sumado al halo menta.
- **Flotante** (`0 8px 32px rgba(0,0,0,.08)`): menús desplegables, autocompletado, datepicker, modales y menú contextual de la agenda.
- **Halo menta** (`0 0 20px rgba(126,191,181,.1)`): refuerzo de hover sobre superficies menta; nunca se usa solo.

### Named Rules
**La Regla del Vidrio Discreto.** El desenfoque de fondo se reserva para lo que flota o cubre: navbar, modales, menús, autocompletado, toasts y tarjetas de autenticación. Un panel de contenido quieto no lleva `backdrop-filter`.

**La Regla de una Sola Elevación.** Una tarjeta en reposo tiene una sombra; en hover puede sumar halo, pero no cambia de nivel dos veces. Los menús y modales son los únicos que llegan al nivel flotante.

## Shapes

Lenguaje de esquinas generosas y bordes finos. La escala principal es 10 / 14 / 20 / 24 px, con radios menores (6–12 px) para controles pequeños: selectores de estado, botones de icono, miniaturas y filas de historial.

- Bordes de 1 px en superficies y separadores; 1.5 px en campos de formulario y estados vacíos (estos últimos, además, punteados).
- Píldoras completas (`999px`) para badges de rol, contadores, chips de estado y puntos de leyenda.
- El odontograma es la única silueta cuadrada dura: cada cara es un polígono de 40×40 con esquinas vivas, porque representa anatomía, no interfaz.
- Los paneles de pestañas usan radio superior en las pestañas y radio inferior en el panel, para leerse como una sola pieza.

### Named Rules
**La Regla de la Esquina Suave.** Ningún contenedor nuevo baja de 10 px de radio, salvo controles en línea de menos de 32 px de alto, que usan 6 px. Nada de esquinas rectas en superficies.

## Components

### Buttons
- **Shape:** rectángulo de radio 10 px, padding 0.5 rem × 1 rem, tipografía Inter 600 a 0.85 rem.
- **Primary:** gradiente arena, texto marrón de sobre, sombra cálida baja. Es la única acción principal por pantalla.
- **Hover / Focus:** la primaria sube 1 px y profundiza la sombra; contorno y fantasma cambian a menta en reposo con texto menta. El foco es un anillo de 3 px con el halo menta, nunca `outline` por defecto.
- **Secondary / Ghost:** contorno con borde de instrumental sobre vidrio claro; fantasma con borde blanco translúcido sobre la navbar; peligro en terracota con borde propio.
- **Tamaños:** existe una variante compacta (`btn-sm`, 0.35 × 0.75 rem) para acciones dentro de tablas y una extra compacta (`btn-xs`, 0.28 × 0.6 rem) para filas de agenda.

### Inputs / Fields
- **Style:** borde de 1.5 px, radio 10 px, fondo vidrio claro, texto grafito. Las etiquetas van arriba, en 0.83 rem y peso 600.
- **Focus:** borde menta y anillo de 3 px con el halo, sin mover el layout.
- **Error / Disabled:** el error se escribe en terracota debajo del campo; no se pinta el campo de rojo. El deshabilitado baja la opacidad y conserva el borde.
- **Búsqueda:** el campo de búsqueda lleva una lupa SVG embebida como `background-image` y padding izquierdo de 2.2 rem.

### Cards / Containers
- **Corner Style:** 14 px en tarjetas de paciente y avisos; 20 px en paneles, tarjetas de formulario y estados vacíos; 24 px en autenticación.
- **Background:** vidrio claro translúcido (opacidad 0.75–0.85) sobre el degradado del lienzo.
- **Shadow Strategy:** reposo o superficie según el peso; el hover suma halo menta y sube 3 px solo en la tarjeta de paciente.
- **Border:** borde tenue de 1 px; el borde instrumental aparece en hover y en tablas.
- **Internal Padding:** 1.5 rem en paneles, 2 rem en formularios, 1.1 × 1.2 rem en tarjetas de paciente.

### Chips & Badges
- **Style:** píldora completa, tipografía 0.68–0.7 rem en mayúsculas con tracking leve.
- **Role:** menta en reposo con texto menta profunda para odontólogos; gris de superficie para secretarios.
- **Counters:** arena con texto blanco (o marrón de sobre en la lista de espera); gris cuando el contador está en cero.

### Navigation
- **Style:** barra menta translúcida con desenfoque de 20 px, texto blanco, marca con isotipo de diente y la "X" atenuada.
- **Default / Hover:** los enlaces son píldoras fantasma con borde blanco translúcido; el hover sube la opacidad del fondo, no cambia el color del texto.
- **Active:** no hay estado activo pintado en la navbar; la ubicación se comunica con el título y el `eyebrow` de la página.
- **Mobile:** por debajo de 768 px colapsa a hamburguesa; los enlaces pasan a ancho completo y el desplegable se vuelve estático y oscuro.
- **Theme toggle:** icono sol/luna en el mismo lenguaje fantasma; el modo oscuro se guarda en `localStorage` y respeta `prefers-color-scheme` la primera vez.

### Section Tabs
Pestañas de ficha clínica: borde de instrumental, radio superior de 10 px, inactivas en grafito suave y activas en vidrio claro con texto menta profunda y peso 700. El panel debajo pierde el borde superior y toma radio inferior de 16 px.

### Agenda Slot Menu
Menú contextual flotante que se abre al tocar una fila de horario: radio 14 px, sombra flotante + halo, animación de entrada de 130 ms con desplazamiento y escala leve. Los ítems son filas de 0.5 × 0.6 rem con icono a la izquierda; la acción destructiva va en terracota y su hover usa el tinte de ausencia.

### Tooth Button (signature)
El diente es un SVG de 40×40 con cinco caras (superior, derecha, inferior, izquierda y oclusal) y un número FDI debajo en Inter 700. Cada cara se pinta con un color de estado; los estados que afectan el diente completo se resuelven con un overlay semitransparente o un trazo punteado. En hover el diente sube 3 px y gana una sombra proyectada; al tocar baja a 0.95. Los dientes temporarios usan la variante `size-small` (34×46 px, 30×42 px en mobile). La leyenda es interactiva: al elegir un estado, los dientes que no coinciden bajan a 25% de opacidad y pierden saturación.

### Empty States
Bloque punteado con radio 20 px, fondo translúcido y texto centrado en Grafito Suave, con un título en Space Grotesk y una acción primaria. Es el patrón para "Todavía no hay pacientes", listas de espera vacías y galerías sin fotos.

## Do's and Don'ts

### Do:
- **Do** usar los tokens de `:root` y su contraparte `body.dark` para todo color, radio y sombra nuevos; si falta un valor, agregalo a ambos bloques.
- **Do** reservar la arena para una sola acción principal por pantalla y para los avatares.
- **Do** acompañar cada estado de turno con su par tinta + tinte suave y con texto legible.
- **Do** mantener Space Grotesk en títulos y marca, e Inter en datos, horas y números FDI.
- **Do** usar el halo menta como anillo de foco de 3 px en todo control interactivo.
- **Do** verificar cada pantalla nueva en modo claro y oscuro antes de darla por terminada.
- **Do** preferir espacio y borde tenue antes que líneas divisorias fuertes.

### Don't:
- **Don't** introducir azul corporativo, violeta de marca o degradados fríos: es la anti-referencia confirmada del sistema.
- **Don't** reutilizar los colores de estado del odontograma o de los turnos como decoración o color de marca.
- **Don't** poner texto blanco sobre la arena; usá marrón de sobre.
- **Don't** aplicar `backdrop-filter` a paneles de contenido quietos ni apilar más de un nivel de elevación en una tarjeta.
- **Don't** crear esquinas rectas en superficies ni radios menores a 10 px fuera de controles en línea.
- **Don't** agregar un framework CSS, un paso de build o una fuente nueva: el sistema se resuelve con Bootstrap, este stylesheet y JS vanilla.
- **Don't** dar por cumplida la accesibilidad: el objetivo es WCAG 2.1 AA y la auditoría sigue pendiente.
