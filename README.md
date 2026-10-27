# MagnetPlace Studio — versión web

La misma aplicación de escritorio, en una página web estática: se abre con una
URL, no hay que instalar nada y **no necesita servidor propio**. Cualquier
hosting de archivos estáticos sirve (GitHub Pages, Netlify, Cloudflare Pages…).

## Cómo funciona

- La lógica es **la misma de la app de escritorio**, no una reescritura: los
  módulos de `py/gcode_magnets/` y `py/magnet_app/` son copias sin tocar de los
  originales (análisis del G-code, detección de agujeros, distancia mínima,
  alcance del colocador, avisos, generación del bloque de imanes, exportación a
  `.gcode` y `.gcode.3mf`, proyectos `.mip`).
- Ese Python corre **dentro del navegador** con [Pyodide](https://pyodide.org)
  (Python compilado a WebAssembly), en un *Web Worker* para que analizar un
  archivo grande no congele la página.
- `py/webapi.py` hace el papel que en escritorio hace `main_window.py` (el estado
  de la sesión y los avisos), sin Qt.
- La interfaz es HTML/JS: `js/bed2d.js` es el visor 2D (port de
  `bed_canvas.py`) y `viewer3d/` es el visor 3D de siempre (three.js), con las
  rutas cambiadas para servirse como página normal.
- **Los archivos del usuario no salen de su ordenador**: se leen, se procesan y
  se descargan dentro del propio navegador. No hay ningún servidor que los reciba.

La primera visita descarga el motor de Python desde el CDN de jsDelivr
(~10 MB); después queda en la caché del navegador.

## Probarla en tu ordenador

Haz doble clic en **`Probar en local.bat`**: arranca un servidor local con
Python y abre `http://localhost:8000/`. Para cerrarlo, cierra la ventana negra.

> No sirve abrir `index.html` con doble clic: los navegadores no dejan cargar
> módulos ni *workers* desde `file://`. Hace falta servirla por `http://`, ya
> sea en local o publicada.

## Publicarla (URL pública, sin servidor)

Sube **el contenido de esta carpeta** tal cual. Tres opciones gratuitas:

### Opción A — GitHub Pages

1. Crea un repositorio nuevo en GitHub (por ejemplo `magnetplace-web`).
2. Sube todos los archivos de esta carpeta a la raíz del repositorio
   (*Add file → Upload files*, arrastrando la carpeta entera). Incluye el
   archivo oculto **`.nojekyll`**: sin él, GitHub descarta los `__init__.py` y
   la app no arranca.
3. En el repositorio: *Settings → Pages → Build and deployment → Source:
   Deploy from a branch*, rama `main`, carpeta `/ (root)` → *Save*.
4. En un par de minutos queda en `https://<tu-usuario>.github.io/magnetplace-web/`.

### Opción B — Netlify Drop (la más rápida)

1. Entra en <https://app.netlify.com/drop>.
2. Arrastra esta carpeta entera a la página.
3. Te da una URL al momento; creando una cuenta gratuita puedes cambiarle el
   nombre o ponerle tu dominio.

### Opción C — Cloudflare Pages

*Workers & Pages → Create → Pages → Upload assets*, y sube la carpeta.

Con cualquiera de las tres puedes apuntar después tu propio dominio (por
ejemplo `app.magnetplace.app`) desde el panel del hosting.

## Estructura

```
index.html            la página
css/app.css           estilos (temas claro y oscuro de theme.py)
js/app.js             la "ventana": botones, pestañas, diálogos, avisos
js/bed2d.js           visor 2D de la placa
js/api.js, worker.js  puente con Python (Pyodide en un Web Worker)
py/webapi.py          estado de la sesión y avisos, sin Qt
py/gcode_magnets/     copia sin tocar del paquete original
py/magnet_app/        copia sin tocar de los módulos sin Qt (settings, pipeline,
                      limits, project, features, magnetics, i18n)
viewer3d/             visor 3D (three.js + modelo de la A1)
assets/               logo, icono y la prueba de calibración (vídeos y .3mf)
Probar en local.bat   servidor local para probarla
.nojekyll             necesario para GitHub Pages
```

## Actualizarla cuando cambie la app de escritorio

1. Vuelve a copiar los `.py` de `gcode_magnets/` y los de `magnet_app/` que
   aparecen en `py/magnet_app/` (son los que no usan Qt).
2. Si has añadido un módulo nuevo, añádelo también a la lista `PY_FILES` de
   `js/worker.js`.
3. Sube el número de `ASSET_VERSION` en `js/worker.js` (por ejemplo
   `1.1.3-web1`): así los navegadores no siguen usando los `.py` viejos de su
   caché.
4. Vuelve a subir la carpeta al hosting.

## Qué tiene y qué no, frente a la de escritorio

Tiene todo el flujo de trabajo: abrir `.gcode.3mf` / `.3mf` / `.gcode` (también
arrastrándolos a la ventana), visor 2D con colocar / mover / apilar
(Ctrl + clic) / borrar (clic derecho; en táctil, mantener pulsado), varias
pausas, pestañas Imanes, Parámetros (con *Avanzado*), Secuencias, Puntos y
Vista previa, todos los avisos (bloqueantes y de riesgo, con la casilla de
responsabilidad al exportar), exportación a `.gcode` y `.gcode.3mf`, secuencia
de prueba, proyectos `.mip` (compatibles con los de escritorio), vista 3D,
asistente de calibración, ocho idiomas y tema claro/oscuro. Los ajustes se
recuerdan en el navegador de cada usuario.

No incluye, por ahora:

- los dos **gráficos** de *Parámetros → Avanzado* y los **dibujos** que van
  debajo de cada aviso (los textos y las tablas sí están);
- el aviso de **actualizaciones** y el sistema de **licencias** (en una web no
  tienen sentido: todos usan siempre la última versión publicada).

## Antes de publicar, ten en cuenta

- En una web **el código Python queda a la vista** de cualquiera que abra las
  herramientas del navegador, más expuesto que dentro del `.exe`.
- `viewer3d/printer_a1.glb` es el modelo de la impresora Bambu Lab A1 que ya
  usaba la app de escritorio. Si no es tuyo, revisa su licencia antes de
  publicarlo en abierto.
