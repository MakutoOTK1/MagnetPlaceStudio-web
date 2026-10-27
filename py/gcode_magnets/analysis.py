"""Analysis routines that operate on parsed G-code data."""
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import bisect
import math
import re
from . import geometry
from .parser import GCodeMove, parse_float
from .config import PAUSE_TOKEN, Z_TOL

_FEATURE_RE = re.compile(r"; FEATURE:\s*(.+)")

# Categorías de FEATURE que se consideran "relleno" y se pueden ocultar en el
# visor (no aportan a la geometría de paredes/agujeros, solo ensucian la vista).
INFILL_FEATURE_KEYWORDS = ("infill", "surface", "prime tower", "brim", "skirt")


def is_infill_feature(name: str) -> bool:
    """True si el nombre de FEATURE corresponde a relleno/ruido visual."""
    lowered = (name or "").lower()
    return any(kw in lowered for kw in INFILL_FEATURE_KEYWORDS)


def find_pause_indices(lines: List[str], pause_token: str = PAUSE_TOKEN) -> List[int]:
    """Índices de **todas** las pausas reales, en el orden en que se imprimen.

    Una pausa real es el token precedido de su marca ``; PAUSE_PRINTING``: el
    mismo ``M400 U1`` aparece también dentro de las secuencias del laminador
    (y de las nuestras), donde no significa "para aquí y espera al usuario".

    Un archivo puede traer varias —una por cada tanda de imanes—, así que quien
    llama elige con cuál trabaja; el resto del análisis se ancla en el índice
    elegido para que la geometría, la Z, la temperatura y el punto de inserción
    se refieran siempre a la MISMA pausa.
    """
    # El rango arranca en 1 porque hace falta poder mirar la línea anterior
    # (con i = 0, lines[i-1] sería la última línea del archivo).
    return [
        i for i in range(1, len(lines))
        if pause_token in lines[i] and "; PAUSE_PRINTING" in lines[i - 1]
    ]


def find_pause_index(lines: List[str], pause_token: str = PAUSE_TOKEN) -> int:
    """Índice de la última pausa real (ver :func:`find_pause_indices`)."""
    indices = find_pause_indices(lines, pause_token)
    if not indices:
        raise ValueError(f"No se encontró la pausa '{pause_token}' en el G-code")
    return indices[-1]


def z_before_pause(lines: List[str], pause_index: int) -> Optional[float]:
    """Z de la capa en la que ocurre la pausa de ``pause_index``, o ``None``.

    Solo movimientos reales y sin comentarios: un comentario del laminador puede
    contener "Z" seguido de números (p. ej. ``; Z_HEIGHT: 3``) y daba una altura
    de capa equivocada.
    """
    return _last_move_z_before(lines, pause_index)


def find_pause_line_and_z(lines: List[str], pause_token: str = PAUSE_TOKEN) -> Tuple[int, float]:
    """Return (pause_index, last_z_before_pause) using the last real pause."""
    pause_index = find_pause_index(lines, pause_token)
    last_z = z_before_pause(lines, pause_index)
    if last_z is None:
        raise ValueError("No se encontró ningún Z antes de la pausa real")
    return pause_index, last_z


def _last_move_z_before(lines: List[str], index: int) -> Optional[float]:
    """Último Z de un movimiento real anterior a ``index`` (ignora comentarios)."""
    for line in reversed(lines[:index]):
        code = line.split(";")[0].strip()
        if not code or code.split()[0] not in ("G0", "G1", "G2", "G3"):
            continue
        z = parse_float(code, "Z")
        if z is not None:
            return z
    return None


def find_layer_height(lines: List[str], pause_index: int) -> Optional[float]:
    """Altura de capa medida alrededor de la pausa, en mm.

    Se compara la Z de la capa que se está mirando —la expuesta al pausar, la
    que delimita :func:`find_layer_region`— con la de la capa de antes. Sirve
    para deducir el ancho del cordón a partir del caudal de E (ver
    :func:`gcode_magnets.geometry.extrusion_width`), donde la altura entra como
    divisor.

    Se ancla en la región y no directamente en la pausa: cuando el laminador
    pone la pausa justo al empezar una capa, la Z de antes del ``M400 U1`` es ya
    la de la capa anterior, y la resta daba 0 (valor descartado, ancho por
    defecto).

    Devuelve ``None`` si no hay marcadores suficientes o si el valor obtenido
    no es plausible (fuera de 0.04–1.5 mm), para que el llamante use su valor
    por defecto en vez de un ancho absurdo.
    """
    layer_start_index, layer_end_index = find_layer_region(lines, pause_index)
    if layer_start_index < 0:
        return None

    z_current = _last_move_z_before(lines, layer_end_index)
    # La Z de la capa anterior es la que había justo antes de que empezara la
    # capa actual, es decir, antes de su propio marcador.
    z_previous = _last_move_z_before(lines, layer_start_index)
    if z_current is None or z_previous is None:
        return None

    height = z_current - z_previous
    if not (0.04 <= height <= 1.5):
        return None
    return height


_MAX_Z_HEIGHT_RE = re.compile(r";\s*max_z_height:\s*([\d.]+)")


def find_print_height(lines: List[str], moves: Optional[List[GCodeMove]] = None) -> Optional[float]:
    """Altura total de la pieza, en mm, o ``None`` si no se puede saber.

    Bambu Studio la deja escrita en la cabecera del G-code
    (``; max_z_height: 5.00``), que es la fuente buena: es la altura del modelo,
    ya sin los movimientos de servicio.

    Si no está esa línea se recurre a la Z más alta de un movimiento **con
    extrusión**. Lo de la extrusión importa: el G-code final aparca el cabezal
    muy arriba (``G1 Z240``) y tomar la Z máxima a secas daría una pieza
    imposible en cualquier archivo.
    """
    # La cabecera va al principio; no hace falta recorrer un archivo de 60 000
    # líneas para encontrarla.
    for line in lines[:200]:
        match = _MAX_Z_HEIGHT_RE.search(line)
        if match:
            return float(match.group(1))

    if not moves:
        return None
    alturas = [m.z for m in moves if m.z is not None and m.e is not None and m.e > 0]
    return max(alturas) if alturas else None


_FILAMENT_TYPE_RE = re.compile(r";\s*filament_type\s*=\s*(.+)")


def find_filament_type(lines: List[str]) -> Optional[str]:
    """Material del filamento (``PLA``, ``PETG``...), o ``None`` si no lo dice.

    Lo escriben todos los laminadores de la familia Slic3r —Bambu Studio, Orca,
    Prusa— como ``; filament_type = PLA``, pero **no siempre en el mismo sitio**:
    unos lo ponen en la cabecera y otros en el bloque de ajustes del final, así
    que se miran los dos extremos del archivo.

    Con varios extrusores viene la lista entera (``PLA;PETG``) y se devuelve el
    primero, que es con el que se imprime la primera capa y por tanto el que
    decide cómo agarra la pieza (ver :func:`~gcode_magnets.adhesion.bed_adhesion`).
    """
    for tramo in (lines[:200], lines[-500:]):
        for line in tramo:
            match = _FILAMENT_TYPE_RE.search(line)
            if match:
                valor = match.group(1).split(";")[0].strip().strip('"')
                if valor:
                    return valor
    return None


def get_hotend_temperature_before_pause(lines: List[str], pause_index: int) -> Optional[float]:
    """Return the temperature value from the last M109 command before pause_index."""
    for i in range(pause_index - 1, -1, -1):
        line = lines[i]
        if "M109" in line:
            # Extract the temperature value (usually after M109 S or M109 with space)
            match = re.search(r'M109\s+S?(\d+)', line)
            if match:
                return float(match.group(1))
    return None


def get_fan_speed_before_pause(lines: List[str], pause_index: int) -> Optional[float]:
    """Velocidad del ventilador de pieza vigente justo antes de la pausa (0-255).

    La secuencia *Final* apaga el ventilador para purgar, así que necesita saber
    a qué valor devolverlo. Dejarlo en un número fijo imprime la capa de la
    reanudación con una refrigeración distinta a la del resto de la pieza, y el
    siguiente ``M106`` del laminador puede tardar miles de líneas en llegar: esa
    capa se queda entera con el valor equivocado.

    Solo cuenta el ventilador de pieza: ``M106 S...`` (sin ``P``, que es como lo
    escribe Bambu Studio) y ``M106 P1 S...``. ``P2`` (auxiliar) y ``P3`` (cámara)
    se descartan. Devuelve ``None`` si no hay ninguno antes de la pausa.
    """
    for i in range(min(pause_index, len(lines)) - 1, -1, -1):
        code = lines[i].split(";")[0].strip()
        if not code.startswith("M106"):
            continue
        fan = parse_float(code, "P")
        if fan is not None and int(fan) != 1:
            continue
        speed = parse_float(code, "S")
        if speed is not None:
            return speed
    return None


# Cuántas líneas se miran hacia delante buscando la des-retracción. La del
# laminador aparece unas pocas decenas de líneas después de la pausa (justo tras
# el cambio de capa); el tope evita recorrer el archivo entero cuando no hay.
_DERETRACT_LOOKAHEAD = 500


def get_deretract_after_pause(lines: List[str], pause_index: int) -> Optional[float]:
    """Cebado que el laminador hará al reanudar, en mm de filamento.

    Es el primer movimiento de solo extrusión positiva que sigue a la pausa
    (``G1 E.8 F1800``): deshace la retracción que el laminador había dejado hecha
    antes de parar. La secuencia *Final* tiene que retraer justo esa cantidad,
    porque después de la purga la boquilla vuelve a estar llena y ese cebado se
    sumaría entero como material de más en el primer cordón, que además es pared
    exterior.

    Se saltan las E negativas intermedias (``G1 E-.04``) y los desplazamientos,
    que llevan X/Y/Z. Devuelve ``None`` si no aparece ninguno.
    """
    end = min(pause_index + 1 + _DERETRACT_LOOKAHEAD, len(lines))
    for i in range(max(pause_index + 1, 0), end):
        code = lines[i].split(";")[0].strip()
        if not code or code.split()[0] not in ("G0", "G1"):
            continue
        if any(parse_float(code, axis) is not None for axis in ("X", "Y", "Z")):
            continue
        e = parse_float(code, "E")
        if e is not None and e > 0:
            return e
    return None


def extract_layer_moves_by_z(
    lines: List[str],
    moves: List[GCodeMove],
    target_z: float = None,
    z_tol: float = Z_TOL,
    features: List[str] = None,
    pause_index: int = None,
    pause_token: str = PAUSE_TOKEN,
) -> List[GCodeMove]:
    """Return all G1/G2/G3 moves of the layer exposed at the pause.

    La región es la de :func:`find_layer_region`: del marcador de capa a la
    pausa, es decir lo último que se imprimió antes de parar.

    G1 moves must have X, Y, E values.
    G2/G3 moves must have X, Y, I, J, E values.
    Optionally confined to specified features.
    (target_z parameter kept for backwards compatibility but is ignored)
    """
    layer_start_index, layer_end_index = find_layer_region(lines, pause_index, pause_token)

    # Extract all G1, G2 and G3 moves in this range with required parameters.
    # (G2 -arco horario- se omitía antes, lo que dejaba huecos en la geometría
    # dibujada siempre que el slicer usaba G2 para una parte de una pared.)
    layer_moves = []
    for m in moves:
        if m.index > layer_start_index and m.index < layer_end_index:
            if m.cmd == "G1" and m.x is not None and m.y is not None and m.e is not None:
                layer_moves.append(m)
            elif (
                m.cmd in ("G2", "G3")
                and m.x is not None and m.y is not None
                and m.i_offset is not None and m.j_offset is not None
                and m.e is not None
            ):
                layer_moves.append(m)

    if features:
        valid_indices = _feature_line_indices(
            lines, features, layer_start_index, layer_end_index
        )
        layer_moves = [m for m in layer_moves if m.index in valid_indices]

    return layer_moves


def _feature_line_indices(
    lines: List[str], features: List[str], start_index: int, end_index: int
) -> set:
    """Índices de línea de ``[start_index, end_index)`` dentro de un FEATURE pedido.

    Una sola pasada por la región de la capa: cada línea pertenece al último
    ``; FEATURE: ...`` que la precede. La versión anterior recorría el archivo
    entero (una vez por feature, más una búsqueda hacia delante por cada
    aparición) y marcaba también líneas de otras capas; aquí el trabajo se
    limita a la capa pausada, que es lo único que se usa. Con 400.000 líneas
    tarda ~la mitad, aunque la razón principal del cambio es acotar el ámbito.
    """
    wanted = [f.strip().lower() for f in features if f.strip()]
    # La región puede empezar en -1 (ver :func:`find_layer_region`): como límite
    # abierto significa "desde el principio", y un índice negativo en los rangos
    # de abajo contaría desde el final del archivo.
    start_index = max(start_index, 0)

    def is_wanted(name: str) -> bool:
        name = name.strip().lower()
        return any(w == name or w in name for w in wanted)

    # La región puede empezar en mitad de un bloque FEATURE: se arranca con el
    # estado del último marcador anterior para no perder esas primeras líneas.
    inside = False
    for i in range(min(start_index, len(lines)) - 1, -1, -1):
        m = _FEATURE_RE.search(lines[i])
        if m:
            inside = is_wanted(m.group(1))
            break

    valid = set()
    for i in range(start_index, min(end_index, len(lines))):
        m = _FEATURE_RE.search(lines[i])
        if m:
            inside = is_wanted(m.group(1))
        if inside:
            valid.add(i)
    return valid


def _region_has_extrusion(lines: List[str], start_index: int, end_index: int) -> bool:
    """True si entre ``start_index`` y ``end_index`` (abiertos) se extruye algo.

    "Algo" es un ``G1``/``G2``/``G3`` con X o Y y E positiva: material depositado
    sobre la placa. Las retracciones (E negativa) y los viajes no cuentan.
    """
    for i in range(max(start_index + 1, 0), min(end_index, len(lines))):
        code = lines[i].split(";")[0].strip()
        if not code or code.split()[0] not in ("G1", "G2", "G3"):
            continue
        if parse_float(code, "X") is None and parse_float(code, "Y") is None:
            continue
        e = parse_float(code, "E")
        if e is not None and e > 0:
            return True
    return False


def find_layer_region(
    lines: List[str], pause_index: int = None, pause_token: str = PAUSE_TOKEN
) -> Tuple[int, int]:
    """Return (layer_start_index, layer_end_index) delimiting the exposed layer.

    La capa que interesa es la que está **expuesta en la placa cuando la
    impresora para**: la última que se imprimió antes de la pausa, que es la que
    el usuario ve y sobre la que coloca los imanes. La región va, por tanto, del
    marcador ``; layer num/total_layer_count:`` de esa capa hasta la pausa
    (``M400 U1`` precedido de ``; PAUSE_PRINTING``), con los dos extremos
    abiertos.

    Antes la región iba de la pausa *hacia delante*, hasta el siguiente marcador
    de capa: eso es lo que se imprime **al reanudar**, encima de los imanes, y no
    lo que hay debajo. Con ello el visor dibujaba una capa y la etiqueta de Z
    (:func:`z_before_pause`) hablaba de la otra.

    El bloque candidato es ``(último marcador antes de la pausa, pausa)``. Si
    sale vacío se prueba con el bloque anterior: según dónde coloque el laminador
    la pausa, ésta puede caer justo tras el marcador de capa (antes del salto de
    Z), y entonces la capa expuesta es la de antes de ese marcador. Así funciona
    con las dos colocaciones, y coincide con lo que devuelve
    :func:`z_before_pause` en ambos casos.

    Se ancla en ``pause_index`` (o en la *última* pausa real, la misma que
    devuelve :func:`find_pause_line_and_z`), para que en un G-code con varias
    pausas la geometría, la Z y la temperatura hablen de la misma tanda.
    """
    if pause_index is None:
        pause_index = find_pause_index(lines, pause_token)

    marks = [
        i for i in range(min(pause_index, len(lines)))
        if "; layer num/total_layer_count:" in lines[i]
    ]

    layer_end_index = pause_index
    for layer_start_index in reversed(marks):
        if _region_has_extrusion(lines, layer_start_index, layer_end_index):
            return layer_start_index, layer_end_index
        layer_end_index = layer_start_index
    # Sin ningún marcador de capa con material delante: la pausa está en la
    # primera capa. Se coge desde el principio del archivo. El -1 es porque los
    # filtros de región son estrictamente abiertos y con 0 se perdería la
    # primera línea.
    return -1, layer_end_index


def group_extruding_runs(
    moves: List[GCodeMove], start_index: int, end_index: int
) -> List[List[GCodeMove]]:
    """Group consecutive extruding moves (G1/G2/G3, E>0) into connected runs.

    A non-extruding move (travel) between two extruding moves ends the current
    run and starts a new one. This mirrors exactly what the nozzle physically
    draws, so it is used both to detect hole contours and to render the layer
    without joining unrelated shapes with a phantom line.
    """
    return group_extruding_runs_with_starts(moves, start_index, end_index)[0]


def group_extruding_runs_with_starts(
    moves: List[GCodeMove], start_index: int, end_index: int
) -> Tuple[List[List[GCodeMove]], List[Optional[Tuple[float, float]]]]:
    """Como :func:`group_extruding_runs`, más el punto donde arranca cada tramo.

    El punto de arranque es la posición del cabezal justo antes del primer
    movimiento del tramo (normalmente el final del viaje que lo precede). Hace
    falta para reconstruir la geometría: un ``G2``/``G3`` define su centro
    **relativo a donde empieza**, así que sin ese punto el primer movimiento de
    un tramo pierde su curvatura. Es ``None`` cuando el tramo abre la región y
    no hay nada antes.
    """
    region = [m for m in moves if start_index < m.index < end_index]
    runs: List[List[GCodeMove]] = []
    starts: List[Optional[Tuple[float, float]]] = []
    current: List[GCodeMove] = []
    last_pos: Optional[Tuple[float, float]] = None
    pending_start: Optional[Tuple[float, float]] = None

    for m in region:
        extruding = (
            m.cmd in ("G1", "G2", "G3")
            and m.e is not None and m.e > 0
            and m.x is not None and m.y is not None
        )
        if extruding:
            if not current:
                pending_start = last_pos
            current.append(m)
        else:
            if current:
                runs.append(current)
                starts.append(pending_start)
            current = []
        if m.x is not None and m.y is not None:
            last_pos = (m.x, m.y)

    if current:
        runs.append(current)
        starts.append(pending_start)
    return runs, starts


def tag_runs_with_feature(
    lines: List[str], runs: List[List[GCodeMove]], start_index: int = 0
) -> List[str]:
    """Return, for each run, the name of the ``; FEATURE: ...`` block it belongs to.

    Uses the last FEATURE comment at or before the run's first move (searching
    from ``start_index`` onward, e.g. the region's ``layer_start_index``).
    Returns ``""`` for a run with no preceding FEATURE marker.
    """
    if not runs:
        return []
    hi = max(run[-1].index for run in runs)
    marks: List[Tuple[int, str]] = []
    # El -1 de una región que arranca al principio del archivo (ver
    # :func:`find_layer_region`) contaría desde el final en el rango.
    for i in range(max(start_index, 0), min(hi + 1, len(lines))):
        m = _FEATURE_RE.search(lines[i])
        if m:
            marks.append((i, m.group(1).strip()))
    mark_indices = [mk[0] for mk in marks]

    tags: List[str] = []
    for run in runs:
        pos = bisect.bisect_right(mark_indices, run[0].index) - 1
        tags.append(marks[pos][1] if pos >= 0 else "")
    return tags


def _fit_circle_lsq(pts: List[Tuple[float, float]]) -> Optional[Tuple[float, float, float]]:
    """Algebraic least-squares circle fit (Kåsa method).

    Unlike a naive centroid + mean-radius estimate, this stays accurate even
    for a *partial* arc (e.g. a wall fragment cut short by a wipe move), which
    is essential here since real slicer output frequently interrupts a wall's
    extrusion run with tiny in-place retraction/wipe moves.
    """
    n = len(pts)
    sx = sum(p[0] for p in pts)
    sy = sum(p[1] for p in pts)
    sxx = sum(p[0] * p[0] for p in pts)
    syy = sum(p[1] * p[1] for p in pts)
    sxy = sum(p[0] * p[1] for p in pts)
    sxz = sum(p[0] * (p[0] * p[0] + p[1] * p[1]) for p in pts)
    syz = sum(p[1] * (p[0] * p[0] + p[1] * p[1]) for p in pts)
    sz = sum(p[0] * p[0] + p[1] * p[1] for p in pts)

    a11, a12, a13 = sxx, sxy, sx
    a21, a22, a23 = sxy, syy, sy
    a31, a32, a33 = sx, sy, float(n)
    b1, b2, b3 = sxz, syz, sz

    def det3(m11, m12, m13, m21, m22, m23, m31, m32, m33):
        return (
            m11 * (m22 * m33 - m23 * m32)
            - m12 * (m21 * m33 - m23 * m31)
            + m13 * (m21 * m32 - m22 * m31)
        )

    d = det3(a11, a12, a13, a21, a22, a23, a31, a32, a33)
    if abs(d) < 1e-9:
        return None
    dx = det3(b1, a12, a13, b2, a22, a23, b3, a32, a33)
    dy = det3(a11, b1, a13, a21, b2, a23, a31, b3, a33)
    dc = det3(a11, a12, b1, a21, a22, b2, a31, a32, b3)

    cx = (dx / d) / 2.0
    cy = (dy / d) / 2.0
    r2 = (dc / d) + cx * cx + cy * cy
    if r2 < 0:
        return None
    return cx, cy, r2 ** 0.5


def _angular_coverage(pts: List[Tuple[float, float]], cx: float, cy: float) -> float:
    """Grados de circunferencia que abarca el contorno alrededor de ``(cx, cy)``.

    Es lo que distingue un agujero de un trozo de pared que casualmente se
    curva: la pared de un hueco lo rodea entero (o casi, si un movimiento de
    limpieza le corta un trozo), mientras que un fragmento de contorno exterior
    apenas cubre unos grados aunque encaje bien en un círculo.

    Se mide como 360° menos el mayor hueco angular entre puntos consecutivos.
    """
    if len(pts) < 3:
        return 0.0
    angles = sorted(math.atan2(p[1] - cy, p[0] - cx) for p in pts)
    gaps = [b - a for a, b in zip(angles, angles[1:])]
    gaps.append(angles[0] + 2 * math.pi - angles[-1])   # el hueco que cierra la vuelta
    return math.degrees(2 * math.pi - max(gaps))


# --- medidas reales del hueco -------------------------------------------------
#
# El detector ajusta un círculo al **trazado** del contorno, que es la línea que
# sigue el centro de la boquilla, no la pared del agujero: el plástico sale del
# ancho de extrusión y se reparte medio ancho a cada lado. Así que un agujero de
# 5,6 mm impreso con hilo de 0,41 mm se ajusta a Ø 6,01 y no a Ø 5,6.
#
#     Ø interior = 2·radio_trazado − ancho        (el hueco que queda libre)
#     Ø exterior = 2·radio_trazado + ancho        (si el círculo es una columna)
#
# El ancho no se lee de los ajustes del laminador —cada pared usa el suyo y hay
# archivos sin ese bloque— sino que se **mide del propio trazado**: el caudal que
# el G-code manda extruir en un contorno, repartido a lo largo de él y sobre la
# altura de capa, sólo puede dar un ancho. Sale exacto (0,4125 mm en el archivo
# de prueba, con el laminador declarando 0,42) y funciona igual con cualquier
# laminador, porque E y las coordenadas están siempre.

_LAYER_HEIGHT_RE = re.compile(r";\s*layer_height\s*=\s*([0-9]*\.?[0-9]+)")
_FILAMENT_DIAMETER_RE = re.compile(r";\s*filament_diameter\s*=\s*([0-9]*\.?[0-9]+)")

DEFAULT_LAYER_HEIGHT = 0.2
DEFAULT_FILAMENT_DIAMETER = 1.75


@dataclass
class CircleMeasurement:
    """Un contorno circular de la capa, con sus medidas en mm.

    ``path_radius`` es lo que se ajusta al trazado; las tres medidas derivadas
    dicen lo mismo desde los tres sitios que interesan: el hueco libre que deja
    (:attr:`inner_diameter`, el diámetro del agujero de verdad), la línea que
    recorre la boquilla (:attr:`path_diameter`) y el bulto exterior del plástico
    (:attr:`outer_diameter`, la medida buena si el círculo es una columna en vez
    de un agujero).
    """

    x: float
    y: float
    path_radius: float
    line_width: float = 0.0     # 0.0 = no se ha podido medir el caudal
    circularity: float = 0.0    # desviación radial relativa (0 = círculo exacto)
    arc: float = 360.0          # grados de circunferencia que cubre el contorno
    points: int = 0
    clockwise: bool = False
    rings: int = 1              # paredes concéntricas fundidas en esta medida
    # Lo hondo que es el hueco, en mm, medido de la capa de la pausa hacia abajo
    # (ver :func:`measure_hole_depths`). ``None`` = no se ha medido, y de lo que
    # no se sabe no se avisa.
    depth: Optional[float] = None

    @property
    def path_diameter(self) -> float:
        return 2.0 * self.path_radius

    @property
    def inner_diameter(self) -> float:
        """Diámetro del hueco libre, en mm (lo que mide un calibre)."""
        return max(0.0, 2.0 * self.path_radius - self.line_width)

    @property
    def outer_diameter(self) -> float:
        return 2.0 * self.path_radius + self.line_width

    @property
    def center(self) -> Tuple[float, float]:
        return (self.x, self.y)


def layer_height_at(lines: List[str], pause_index: int = None) -> float:
    """Altura de capa utilizable siempre, en mm.

    :func:`find_layer_height` la mide donde se puede —la Z de la capa pausada
    menos la de la anterior, que vale también con altura variable— y devuelve
    ``None`` cuando no hay capas suficientes. Aquí hace falta un número sí o sí
    para deshacer el caudal, así que se recurre al ``; layer_height = ...`` de
    los ajustes del laminador y, en último caso, a :data:`DEFAULT_LAYER_HEIGHT`.
    """
    if pause_index is not None:
        medida = find_layer_height(lines, pause_index)
        if medida:
            return medida
    for tramo in (lines[:400], lines[-800:]):
        for line in tramo:
            match = _LAYER_HEIGHT_RE.search(line)
            if match:
                try:
                    valor = float(match.group(1))
                except ValueError:
                    continue
                if 0.02 <= valor <= 1.0:
                    return valor
    return DEFAULT_LAYER_HEIGHT


def find_filament_diameter(lines: List[str]) -> float:
    """Diámetro del filamento en mm (1,75 salvo que el archivo diga otra cosa)."""
    for tramo in (lines[:400], lines[-800:]):
        for line in tramo:
            match = _FILAMENT_DIAMETER_RE.search(line)
            if match:
                try:
                    valor = float(match.group(1))
                except ValueError:
                    continue
                if 0.5 <= valor <= 5.0:
                    return valor
    return DEFAULT_FILAMENT_DIAMETER


def extrusion_deltas(
    lines: List[str], start_index: int = 0, end_index: int = None
) -> Dict[int, float]:
    """``{índice de línea: milímetros de filamento que extruye}``.

    Hay que recorrer el archivo desde el principio aunque sólo interese una
    capa, porque con E absoluta (``M82``) el avance de un movimiento es la
    diferencia con el anterior, y el modo (``M82``/``M83``) y los ceros
    (``G92 E0``) se declaran mucho antes. Sólo se guardan las líneas de la
    región pedida: es un diccionario pequeño aunque el archivo sea enorme.
    """
    tope = len(lines) if end_index is None else min(end_index, len(lines))
    relativa = False
    ultima_e = 0.0
    deltas: Dict[int, float] = {}
    for i in range(tope):
        linea = lines[i].split(";")[0].strip()
        if not linea:
            continue
        cmd = linea.split()[0]
        if cmd == "M83":
            relativa = True
        elif cmd == "M82":
            relativa = False
        elif cmd == "G92":
            valor = parse_float(linea, "E")
            if valor is not None:
                ultima_e = valor
        elif cmd in ("G0", "G1", "G2", "G3"):
            valor = parse_float(linea, "E")
            if valor is None:
                continue
            if relativa:
                delta = valor
            else:
                delta = valor - ultima_e
                ultima_e = valor
            if delta > 0.0 and i >= start_index:
                deltas[i] = delta
    return deltas


def _contour_line_width(
    run: List[GCodeMove],
    pts: List[Tuple[float, float]],
    deltas: Dict[int, float],
    layer_height: float,
    filament_area: float,
) -> float:
    """Ancho de extrusión de un contorno, en mm (0.0 si no se puede medir).

    El filamento que entra tiene que salir: repartido a lo largo del trazado da
    la sección del hilo depositado, y de ahí el ancho. La sección se toma como
    un rectángulo con los extremos redondeados —``A = w·h + h²·(π/4 − 1)``, el
    mismo modelo que usan los laminadores de la familia Slic3r para calcular E—,
    así que la cuenta deshace exactamente la que hizo el laminador.

    No sirve :func:`gcode_magnets.geometry.extrusion_width`, que es la misma
    idea con la sección rectangular a secas: vale de sobra para dibujar el
    cordón y para medir la huella, pero aquí el ancho se le **resta** a un
    diámetro, y esos 0,04 mm de diferencia se ven en la medida final.
    """
    if not deltas or layer_height <= 0.0 or len(pts) < 2:
        return 0.0
    e_total = 0.0
    for m in run:
        e_total += deltas.get(m.index, 0.0)
    if e_total <= 0.0:
        return 0.0
    longitud = sum(
        math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])
    )
    if longitud <= 1e-9:
        return 0.0
    seccion = e_total * filament_area / longitud
    ancho = (seccion - (math.pi / 4.0 - 1.0) * layer_height * layer_height) / layer_height
    # Un ancho fuera de lo posible significa que la cuenta no aplica (retracción
    # a medias, contorno cortado, E que no es de este tramo): mejor no corregir
    # nada que corregir con un número inventado.
    return ancho if 0.05 <= ancho <= 5.0 else 0.0


def _signed_area(pts: List[Tuple[float, float]]) -> float:
    """Área con signo del contorno (negativa si va en sentido horario)."""
    total = 0.0
    for a, b in zip(pts, pts[1:]):
        total += a[0] * b[1] - b[0] * a[1]
    return total / 2.0


def _radius_accepted(
    r: float,
    r_min: float,
    r_max: float,
    match_radii: Optional[List[float]],
    radius_tol: float,
) -> bool:
    """Si un contorno de radio ``r`` pasa el filtro de tamaño.

    Con ``match_radii`` manda la lista de radios buscados y el intervalo
    ``[r_min, r_max]`` se ignora: son dos formas distintas de decir lo mismo y
    aplicar las dos a la vez dejaría fuera un imán perfectamente válido sólo
    porque el intervalo ancho se quedó corto.
    """
    if match_radii:
        return any(abs(r - target) <= radius_tol for target in match_radii)
    return r_min <= r <= r_max


def measure_circles(
    moves: List[GCodeMove],
    start_index: int,
    end_index: int,
    lines: List[str] = None,
    r_min: float = 0.0,
    r_max: float = float("inf"),
    circ_tol: float = 0.12,
    cluster_dist: float = 2.0,
    min_points: int = 4,
    min_arc: float = 30.0,
    runs: List[List[GCodeMove]] = None,
    run_starts: List[Optional[Tuple[float, float]]] = None,
    match_diameters: Optional[List[float]] = None,
    diameter_tol: float = 0.5,
    layer_height: float = None,
    filament_diameter: float = None,
    deltas: Dict[int, float] = None,
) -> List["CircleMeasurement"]:
    """Mide todos los contornos circulares de la capa: dónde están y cuánto miden.

    Es el motor de la detección de agujeros, pero devuelve la medida completa
    (:class:`CircleMeasurement`) en vez de sólo el centro, porque el diámetro
    interior de un hueco sirve para más cosas que colocar un imán: comprobar que
    el agujero cabe, avisar de que se imprimió más estrecho de lo diseñado,
    listar los huecos de una placa...

    Los movimientos de la capa se agrupan en contornos de extrusión continua
    (:func:`group_extruding_runs`) y **se reconstruye su trazado real** con
    :func:`gcode_magnets.geometry.flatten_run` antes de ajustarles un círculo
    por mínimos cuadrados. Se acepta el contorno si es suficientemente circular
    (``std(radio) / radio <= circ_tol``) y si **rodea al centro**: tiene que
    cubrir al menos ``min_arc`` grados para ser un agujero y no un trozo de
    pared que casualmente se curva.

    Aplanar los arcos es lo que hace fiable la prueba de circularidad. Antes se
    ajustaba el círculo a los **extremos de cada movimiento**, y como el
    laminador dibuja una pared curva con dos o tres ``G2``/``G3``, el contorno
    llegaba aquí como 3-5 puntos: por tres puntos cualesquiera pasa un círculo
    exacto, así que la desviación salía ~0 y cualquier forma curva —los
    pétalos entre agujero y agujero, por ejemplo— se aceptaba como agujero.

    Con ``lines`` se mide además el ancho de extrusión de cada contorno y las
    medidas salen **en milímetros de pieza** y no de trazado (ver
    :class:`CircleMeasurement`). Sin ``lines`` el ancho queda a 0 y el diámetro
    interior es el del trazado, medio ancho de hilo más grande de lo que el
    calibre dirá: sale ~0,4 mm largo con una boquilla de 0,4.

    Args:
        moves: All parsed moves (with running absolute X/Y/Z and E).
        start_index, end_index: Bounds of the layer (see :func:`find_layer_region`).
        lines: Las líneas del archivo, para medir el ancho de extrusión.
        r_min, r_max: Intervalo de radio de **trazado** admitido, en mm. Es el
            filtro grueso; sólo se usa cuando no se pasa ``match_diameters``.
        circ_tol: Max relative radial deviation to count as a circle.
        cluster_dist: Merge centers closer than this (mm) — joins concentric walls.
        min_points: Minimum points for a contour to be considered.
        min_arc: Grados de circunferencia que el contorno debe abarcar.
        runs: Tramos ya agrupados (ver :func:`group_extruding_runs`). Si se
            pasan, se reutilizan en vez de recorrer ``moves`` otra vez.
        run_starts: Punto de arranque de cada tramo, si ya se conoce (ver
            :func:`group_extruding_runs_with_starts`). Solo se usa junto con
            ``runs``; sin él, un tramo que empiece con un arco pierde su
            curvatura y puede escaparse de la detección.
        match_diameters: Diámetros **interiores** concretos que se buscan, en
            mm. Si se pasan, un hueco sólo vale si mide como alguno de ellos
            (± ``diameter_tol``), y ``r_min``/``r_max`` dejan de mirarse. Es lo
            que permite pedir «sólo los agujeros de mis imanes»: con un módulo
            de 6 mm y otro de 3 mm se aceptan esos dos tamaños y se descartan
            los de en medio, cosa que un intervalo único no sabe hacer.
        diameter_tol: Margen admitido alrededor de cada diámetro buscado, en mm.
        layer_height, filament_diameter, deltas: Los datos que hacen falta para
            medir el ancho. Se sacan del archivo si no se dan.

    Returns:
        Una medida por hueco, con las paredes concéntricas ya fundidas.
    """
    if runs is None:
        runs, starts = group_extruding_runs_with_starts(moves, start_index, end_index)
    elif run_starts is not None:
        starts = list(run_starts)
    else:
        starts = [None] * len(runs)

    # Datos para medir el ancho. Sin `lines` no hay caudal que mirar y las
    # medidas se quedan en las del trazado.
    if lines is not None:
        if layer_height is None:
            layer_height = layer_height_at(lines, start_index)
        if filament_diameter is None:
            filament_diameter = find_filament_diameter(lines)
        if deltas is None:
            deltas = extrusion_deltas(lines, start_index, end_index)
    layer_height = layer_height or 0.0
    filament_area = math.pi * ((filament_diameter or DEFAULT_FILAMENT_DIAMETER) / 2.0) ** 2

    crudas: List[CircleMeasurement] = []
    for i, run in enumerate(runs):
        pts = geometry.flatten_run(run, start=starts[i] if i < len(starts) else None)
        if len(pts) < min_points:
            continue
        fit = _fit_circle_lsq(pts)
        if fit is None:
            continue
        cx, cy, r = fit
        if r < 1e-6:
            continue
        arc = _angular_coverage(pts, cx, cy)
        if arc < min_arc:
            continue
        radios = [((p[0] - cx) ** 2 + (p[1] - cy) ** 2) ** 0.5 for p in pts]
        media = sum(radios) / len(radios)
        desviacion = (sum((rr - media) ** 2 for rr in radios) / len(radios)) ** 0.5
        if desviacion / r > circ_tol:
            continue
        ancho = _contour_line_width(run, pts, deltas, layer_height, filament_area)
        medida = CircleMeasurement(
            x=cx, y=cy, path_radius=r, line_width=ancho,
            circularity=desviacion / r, arc=arc, points=len(pts),
            clockwise=_signed_area(pts) < 0.0,
        )
        if not _measurement_accepted(medida, r_min, r_max, match_diameters, diameter_tol):
            continue
        crudas.append(medida)

    return _cluster_measurements(crudas, cluster_dist)


# --- lo hondo que es el hueco -------------------------------------------------
#
# Medir el diámetro dice si el imán entra de lado; lo que dice si **cabe** es la
# profundidad, y esa no está en la capa de la pausa sino debajo de ella: el hueco
# se imprimió en las capas anteriores y su fondo es la última que pasó por encima
# del centro. Por eso se busca al revés de como se imprime, del ``M400 U1`` hacia
# atrás: la primera capa que tapa el centro del agujero es su fondo, y todo lo que
# hay entre ese fondo y la Z de la pausa es sitio para imanes.
#
#     profundidad = Z_pausa − Z_de_la_capa_que_tapa
#
# Sin ninguna capa que lo tape el agujero es **pasante** y el imán se apoya en la
# propia placa, así que la profundidad es la Z de la pausa entera.
#
# Se sondea sólo el centro —la mitad del radio— y no el hueco completo: las
# paredes del propio agujero están a un radio entero del centro, así que no lo
# tapan por mucho que se dibujen capa tras capa. Y los arcos se aplanan antes de
# mirarlos: la cuerda de media circunferencia pasa justo por el centro, y sin
# aplanarla la propia pared del agujero se tomaría por su fondo.

# Parte del radio del hueco que se considera "el centro" al sondear.
DEPTH_PROBE_FACTOR = 0.5

# Radio mínimo del sondeo, en mm: por debajo de esto un agujero diminuto podría
# colarse entre dos líneas de relleno sin que ninguna lo toque.
DEPTH_PROBE_MIN = 0.3


def _segment_distance(
    ax: float, ay: float, bx: float, by: float, px: float, py: float
) -> float:
    """Distancia del punto ``(px, py)`` al segmento ``a-b``, en mm."""
    dx, dy = bx - ax, by - ay
    largo = dx * dx + dy * dy
    if largo <= 1e-12:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / largo
    t = min(1.0, max(0.0, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _move_polyline(
    prev: Tuple[float, float], move: GCodeMove
) -> List[Tuple[float, float]]:
    """Trazado real de un movimiento, con los arcos ya troceados."""
    fin = (move.x, move.y)
    if move.cmd in ("G2", "G3") and move.i_offset is not None and move.j_offset is not None:
        return [prev] + geometry.arc_points(
            prev, fin, move.i_offset, move.j_offset, clockwise=(move.cmd == "G2")
        )
    return [prev, fin]


def measure_hole_depths(
    moves: List[GCodeMove],
    pause_index: int,
    pause_z: float,
    holes: List["CircleMeasurement"],
    z_tol: float = Z_TOL,
) -> List[Optional[float]]:
    """Mide lo hondo que es cada hueco y se lo guarda en su ``depth``.

    Devuelve las profundidades en el mismo orden que ``holes`` (y de paso deja
    cada una en su :attr:`CircleMeasurement.depth`, que es donde la busca el
    resto de la aplicación). Un hueco sin radio utilizable se queda en ``None``:
    de lo que no se ha podido medir no se avisa.

    Se recorren los movimientos **hacia atrás desde la pausa**, que es el orden
    en que se apilaron las capas visto desde arriba, y se para en cuanto todos
    los agujeros tienen fondo: un hueco de 3 mm en una pieza de 20 no obliga a
    releer la pieza entera.
    """
    if not holes:
        return []

    pendientes = []
    for i, hueco in enumerate(holes):
        radio = max(hueco.inner_diameter / 2.0, 0.0)
        if radio <= 0.0:
            hueco.depth = None
            continue
        pendientes.append((i, hueco.x, hueco.y,
                           max(radio * DEPTH_PROBE_FACTOR, DEPTH_PROBE_MIN)))

    fondos: Dict[int, float] = {}
    if pendientes:
        # Último movimiento anterior a la pausa: de ahí hacia atrás está todo lo
        # que se imprimió debajo de la capa expuesta.
        ultimo = len(moves) - 1
        while ultimo >= 0 and moves[ultimo].index >= pause_index:
            ultimo -= 1
        techo = float(pause_z) - float(z_tol)

        for j in range(ultimo, 0, -1):
            m = moves[j]
            if m.e is None or m.e <= 0 or m.x is None or m.y is None or m.z is None:
                continue
            if m.z > techo:
                continue
            anterior = moves[j - 1]
            if anterior.x is None or anterior.y is None:
                continue
            puntos = _move_polyline((anterior.x, anterior.y), m)
            tapados = []
            for i, cx, cy, radio in pendientes:
                for a, b in zip(puntos, puntos[1:]):
                    if _segment_distance(a[0], a[1], b[0], b[1], cx, cy) <= radio:
                        fondos[i] = m.z
                        tapados.append(i)
                        break
            if tapados:
                pendientes = [p for p in pendientes if p[0] not in fondos]
                if not pendientes:
                    break

    salida: List[Optional[float]] = []
    for i, hueco in enumerate(holes):
        if hueco.inner_diameter <= 0.0:
            salida.append(None)
            continue
        # Sin fondo el agujero es pasante: el imán se apoya en la placa.
        fondo = fondos.get(i, 0.0)
        hueco.depth = max(float(pause_z) - float(fondo), 0.0)
        salida.append(hueco.depth)
    return salida


def _measurement_accepted(
    medida: "CircleMeasurement",
    r_min: float,
    r_max: float,
    match_diameters: Optional[List[float]],
    diameter_tol: float,
) -> bool:
    """Si un contorno pasa el filtro de tamaño.

    Con ``match_diameters`` manda la lista de diámetros buscados —medidos en el
    hueco, no en el trazado— y el intervalo ``[r_min, r_max]`` se ignora: son
    dos formas distintas de decir lo mismo y aplicar las dos a la vez dejaría
    fuera un agujero perfectamente válido sólo porque el intervalo ancho se
    quedó corto.
    """
    if match_diameters:
        d = medida.inner_diameter
        return any(abs(d - objetivo) <= diameter_tol for objetivo in match_diameters)
    return r_min <= medida.path_radius <= r_max


def _cluster_measurements(
    medidas: List["CircleMeasurement"], cluster_dist: float
) -> List["CircleMeasurement"]:
    """Funde las paredes concéntricas de un mismo hueco en una sola medida.

    El centro es el promedio del grupo, pero el tamaño lo pone **el anillo más
    pequeño**: es el que toca la pared del agujero. Los de fuera son las paredes
    siguientes de la pieza y miden de más.
    """
    usadas = [False] * len(medidas)
    salida: List[CircleMeasurement] = []
    for i, base in enumerate(medidas):
        if usadas[i]:
            continue
        grupo = [base]
        usadas[i] = True
        for j in range(i + 1, len(medidas)):
            if usadas[j]:
                continue
            dx = base.x - medidas[j].x
            dy = base.y - medidas[j].y
            if (dx * dx + dy * dy) ** 0.5 <= cluster_dist:
                grupo.append(medidas[j])
                usadas[j] = True
        interior = min(grupo, key=lambda m: m.path_radius)
        salida.append(CircleMeasurement(
            x=sum(m.x for m in grupo) / len(grupo),
            y=sum(m.y for m in grupo) / len(grupo),
            path_radius=interior.path_radius,
            line_width=interior.line_width,
            circularity=interior.circularity,
            arc=interior.arc,
            points=interior.points,
            clockwise=interior.clockwise,
            rings=len(grupo),
        ))
    return salida


def detect_hole_centers(
    moves: List[GCodeMove],
    start_index: int,
    end_index: int,
    r_min: float = 1.5,
    r_max: float = 20.0,
    circ_tol: float = 0.12,
    cluster_dist: float = 2.0,
    min_points: int = 4,
    min_arc: float = 30.0,
    runs: List[List[GCodeMove]] = None,
    run_starts: List[Optional[Tuple[float, float]]] = None,
    match_diameters: Optional[List[float]] = None,
    diameter_tol: float = 0.5,
    lines: List[str] = None,
    layer_height: float = None,
    filament_diameter: float = None,
    deltas: Dict[int, float] = None,
) -> List[Tuple[float, float]]:
    """Centros de los agujeros de la capa (ver :func:`measure_circles`).

    Es el atajo de siempre para quien sólo quiere saber **dónde** poner los
    imanes; :func:`measure_circles` da lo mismo con las medidas.
    """
    return [
        (m.x, m.y)
        for m in measure_circles(
            moves, start_index, end_index,
            lines=lines, r_min=r_min, r_max=r_max, circ_tol=circ_tol,
            cluster_dist=cluster_dist, min_points=min_points, min_arc=min_arc,
            runs=runs, run_starts=run_starts,
            match_diameters=match_diameters, diameter_tol=diameter_tol,
            layer_height=layer_height, filament_diameter=filament_diameter,
            deltas=deltas,
        )
    ]


def detect_g3_centers(layer_moves: List[GCodeMove]) -> List[Tuple[float, float]]:
    """Return centers of G3 arcs found in the layer moves.
    
    Groups centers that are within 1mm diameter (0.5mm radius) and returns their average.
    """
    raw_centers = []
    for i, move in enumerate(layer_moves):
        if move.cmd == "G3" and move.i_offset is not None and move.j_offset is not None:
            if i > 0:
                prev = layer_moves[i - 1]
                if prev.x is not None and prev.y is not None:
                    cx = prev.x + move.i_offset
                    cy = prev.y + move.j_offset
                    raw_centers.append((cx, cy))
    
    if not raw_centers:
        return []
    
    # Cluster centers that are within 0.5mm radius (1mm diameter)
    CLUSTERING_RADIUS = 0.5  # mm
    processed = set()
    clustered_centers = []
    
    for start_idx, (cx, cy) in enumerate(raw_centers):
        if start_idx in processed:
            continue
        
        # Start a new cluster
        cluster = [(cx, cy)]
        processed.add(start_idx)
        
        # Find all nearby centers
        for check_idx, (cx2, cy2) in enumerate(raw_centers):
            if check_idx in processed:
                continue
            
            dist = ((cx - cx2) ** 2 + (cy - cy2) ** 2) ** 0.5
            if dist <= CLUSTERING_RADIUS:
                cluster.append((cx2, cy2))
                processed.add(check_idx)
        
        # Calculate average of cluster
        avg_x = sum(x for x, y in cluster) / len(cluster)
        avg_y = sum(y for x, y in cluster) / len(cluster)
        clustered_centers.append((avg_x, avg_y))
    
    return clustered_centers
