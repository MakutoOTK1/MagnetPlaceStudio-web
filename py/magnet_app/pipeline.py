"""Orquestación headless: cargar, analizar, generar y guardar.

Esta capa no depende de Qt; envuelve el paquete ``gcode_magnets`` y la clase
:class:`~magnet_app.settings.Settings` para que tanto la GUI como los tests
puedan usar la misma lógica.
"""
from __future__ import annotations

import os
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Tuple

from gcode_magnets import analysis as analysis_mod
from gcode_magnets import fit as fit_mod
from gcode_magnets import footprint as footprint_mod
from gcode_magnets import geometry as geometry_mod
from gcode_magnets import io as io_mod
from gcode_magnets import magnetics as magnetics_mod
from gcode_magnets import parser as parser_mod
from gcode_magnets.generator import (
    MARK_END,
    MARK_START,
    assemble_magnet_block,
)

from .settings import (
    FALLBACK_DERETRACT,
    FALLBACK_FAN,
    Settings,
    render_sequence,
)

Point = Tuple[float, float, str]  # (x, y, color)


@dataclass
class PauseInfo:
    """Lo que hay que saber de una pausa para generarle su bloque de imanes.

    Se calcula para **todas** las pausas del archivo nada más abrirlo (es
    barato: son cuatro búsquedas alrededor de cada una), de modo que la
    exportación pueda montar el bloque de cada tanda de imanes sin volver a
    analizar la capa entera de todas ellas.
    """

    index: int                                   # línea del token de pausa
    layer_z: float                               # Z de la capa donde para
    temperatura_hotend: Optional[float] = None
    fan_speed: Optional[float] = None
    deretract: Optional[float] = None


@dataclass
class AnalysisResult:
    """Datos extraídos de un archivo tras el análisis de la pausa."""

    input_path: str
    is_3mf: bool
    gcode_filename: Optional[str]
    lines: List[str]
    moves: list
    pause_index: int
    layer_z: float
    temperatura_hotend: Optional[float]
    layer_moves: list
    suggested_centers: List[Tuple[float, float]] = field(default_factory=list)
    # La medida completa de cada centro sugerido, en el mismo orden: el diámetro
    # del hueco es lo que dice si el imán entrará o no (ver
    # `gcode_magnets.fit`).
    hole_measurements: List[analysis_mod.CircleMeasurement] = field(default_factory=list)
    layer_runs: list = field(default_factory=list)
    layer_run_features: List[str] = field(default_factory=list)
    # Posición del cabezal antes de cada tramo: sin ella, un tramo que empieza
    # con un arco pierde su curvatura al reconstruir la geometría.
    layer_run_starts: list = field(default_factory=list)
    # Región de la capa expuesta al pausar: del marcador de capa al `M400 U1`
    # (extremos abiertos). Ver `gcode_magnets.analysis.find_layer_region`.
    layer_start_index: int = -1
    layer_end_index: int = -1
    # Altura de capa medida en el archivo; el visor la necesita para deducir el
    # ancho del cordón a partir del caudal de E.
    layer_height: float = geometry_mod.DEFAULT_LAYER_HEIGHT
    # Estado que la secuencia *Final* tiene que devolver tal y como estaba: la
    # refrigeración vigente antes de parar y el cebado que el laminador hará al
    # reanudar. ``None`` = no estaba en el archivo, se usan los valores de
    # reserva de `magnet_app.settings`.
    fan_speed: Optional[float] = None
    deretract: Optional[float] = None
    # Altura total de la pieza, para comprobar que cabe bajo el colocador (ver
    # `magnet_app.limits`). ``None`` = el archivo no lo dice y no se ha podido
    # deducir; entonces no se avisa de nada.
    print_height: Optional[float] = None
    # Lo que las piezas apoyan en la cama y con qué material, para saber si el
    # módulo puede despegarlas al retirarse (ver `magnet_app.limits`). Los dos
    # son del archivo entero, no de la pausa: la primera capa es la misma se
    # mire la tanda de imanes que se mire. Vacío/``None`` = no se ha podido
    # medir, y entonces no se avisa de nada.
    footprints: List[footprint_mod.Footprint] = field(default_factory=list)
    filament_type: Optional[str] = None
    # Todas las pausas del archivo, en orden de impresión, y cuál de ellas es la
    # analizada aquí (su posición en la lista). El resto de campos —la capa, la
    # Z, la temperatura...— son los de ESA pausa; para cambiar de una a otra sin
    # releer el archivo está :func:`select_pause`.
    pauses: List[PauseInfo] = field(default_factory=list)
    pause_ordinal: int = 0

    @property
    def pause_count(self) -> int:
        """Cuántas pausas reales tiene el archivo (al menos 1)."""
        return len(self.pauses) or 1

    @property
    def layer_xy(self) -> Tuple[List[float], List[float]]:
        # Se filtra por move (no cada eje por separado) para que xs e ys sigan
        # emparejados aunque algún movimiento no traiga las dos coordenadas.
        pts = [(m.x, m.y) for m in self.layer_moves if m.x is not None and m.y is not None]
        return [p[0] for p in pts], [p[1] for p in pts]


def load_and_analyze(
    input_path: str, settings: Settings, pause_ordinal: int = 0
) -> AnalysisResult:
    """Carga un ``.3mf``/``.gcode`` y devuelve el análisis de una de sus pausas.

    ``pause_ordinal`` elige con cuál se trabaja (0 = la primera del archivo, que
    es la que se enseña al abrirlo). Las demás quedan listadas en
    ``result.pauses`` para poder saltar a ellas con :func:`select_pause`.

    Lanza ``ValueError`` con un mensaje claro si no encuentra la pausa o los
    marcadores necesarios (los propaga ``gcode_magnets``).
    """
    lower = input_path.lower()
    is_3mf = not lower.endswith(".gcode")

    if is_3mf:
        gcode_filename, gcode_text = io_mod.extract_gcode_from_3mf(input_path)
    else:
        gcode_filename = None
        with open(input_path, "r", encoding="utf-8", errors="replace") as fh:
            gcode_text = fh.read()

    lines = gcode_text.splitlines(keepends=True)
    moves = parser_mod.parse_gcode_moves(lines)
    pauses = _collect_pauses(lines, settings.pause_token)
    # La altura de la pieza es del archivo, no de la pausa: se calcula una vez
    # y se arrastra al cambiar de pausa (recorre todos los movimientos).
    print_height = analysis_mod.find_print_height(lines, moves)
    # La huella y el material también son del archivo: se miden una vez y se
    # arrastran al cambiar de pausa, como la altura.
    huellas = footprint_mod.footprints(moves)
    filamento = analysis_mod.find_filament_type(lines)

    return _analyze_pause(
        input_path=input_path,
        is_3mf=is_3mf,
        gcode_filename=gcode_filename,
        lines=lines,
        moves=moves,
        pauses=pauses,
        ordinal=pause_ordinal,
        settings=settings,
        print_height=print_height,
        footprints=huellas,
        filament_type=filamento,
    )


def _collect_pauses(lines: List[str], pause_token: str) -> List[PauseInfo]:
    """Datos de cada pausa real del archivo, en orden de impresión."""
    indices = analysis_mod.find_pause_indices(lines, pause_token)
    if not indices:
        raise ValueError(f"No se encontró la pausa '{pause_token}' en el G-code")

    pauses: List[PauseInfo] = []
    for n, index in enumerate(indices, start=1):
        layer_z = analysis_mod.z_before_pause(lines, index)
        if layer_z is None:
            raise ValueError(f"No se encontró ningún Z antes de la pausa nº {n}")
        pauses.append(PauseInfo(
            index=index,
            layer_z=layer_z,
            temperatura_hotend=analysis_mod.get_hotend_temperature_before_pause(lines, index),
            fan_speed=analysis_mod.get_fan_speed_before_pause(lines, index),
            deretract=analysis_mod.get_deretract_after_pause(lines, index),
        ))
    return pauses


def _analyze_pause(
    *,
    input_path: str,
    is_3mf: bool,
    gcode_filename: Optional[str],
    lines: List[str],
    moves: list,
    pauses: List[PauseInfo],
    ordinal: int,
    settings: Settings,
    print_height: Optional[float],
    footprints: Optional[List[footprint_mod.Footprint]] = None,
    filament_type: Optional[str] = None,
) -> AnalysisResult:
    """Analiza la capa de la pausa ``ordinal`` sobre un archivo ya leído."""
    ordinal = max(0, min(int(ordinal), len(pauses) - 1))
    pause = pauses[ordinal]
    pause_index = pause.index

    # Toda la capa se ancla en la MISMA pausa: geometría, Z y temperatura tienen
    # que hablar de la tanda de imanes que se está mirando. Y la capa es la que
    # queda expuesta al parar, no la que se imprime al reanudar (ver
    # :func:`gcode_magnets.analysis.find_layer_region`).
    layer_start_index, layer_end_index = analysis_mod.find_layer_region(lines, pause_index)
    layer_moves = analysis_mod.extract_layer_moves_by_z(
        lines, moves, pause.layer_z,
        features=settings.features or None, pause_index=pause_index,
    )
    # Tramos de extrusión conectados (sin viajes intermedios): es lo que
    # realmente dibuja la boquilla, y evita que el visor una zonas distintas
    # con una línea fantasma.
    layer_runs, layer_run_starts = analysis_mod.group_extruding_runs_with_starts(
        moves, layer_start_index, layer_end_index
    )
    layer_run_features = analysis_mod.tag_runs_with_feature(
        lines, layer_runs, layer_start_index
    )
    layer_height = (
        analysis_mod.find_layer_height(lines, pause_index)
        or geometry_mod.DEFAULT_LAYER_HEIGHT
    )
    # Detección de centros por contornos circulares (robusta a arc fitting).
    # Va después de la altura de capa porque la necesita: es el divisor con el
    # que se deduce el ancho del cordón de cada contorno.
    huecos = _detect_holes(
        lines, moves, settings, pause_index=pause_index,
        runs=layer_runs, run_starts=layer_run_starts, layer_height=layer_height,
    )
    # Y lo hondos que son, que es lo que dice cuántos imanes caben dentro. Se
    # mide aquí y no en la detección porque hay que mirar **debajo** de la capa
    # de la pausa, no dentro de ella (ver `analysis.measure_hole_depths`).
    analysis_mod.measure_hole_depths(moves, pause_index, pause.layer_z, huecos)
    suggested = [m.center for m in huecos]

    return AnalysisResult(
        input_path=input_path,
        is_3mf=is_3mf,
        gcode_filename=gcode_filename,
        lines=lines,
        moves=moves,
        pause_index=pause_index,
        layer_z=pause.layer_z,
        temperatura_hotend=pause.temperatura_hotend,
        layer_moves=layer_moves,
        suggested_centers=suggested,
        hole_measurements=huecos,
        layer_runs=layer_runs,
        layer_run_features=layer_run_features,
        layer_run_starts=layer_run_starts,
        layer_start_index=layer_start_index,
        layer_end_index=layer_end_index,
        layer_height=layer_height,
        fan_speed=pause.fan_speed,
        deretract=pause.deretract,
        print_height=print_height,
        footprints=list(footprints or []),
        filament_type=filament_type,
        pauses=pauses,
        pause_ordinal=ordinal,
    )


def select_pause(
    result: AnalysisResult, ordinal: int, settings: Settings
) -> AnalysisResult:
    """Análisis de otra pausa del MISMO archivo, sin volver a leerlo ni parsearlo.

    Devuelve un :class:`AnalysisResult` nuevo (el anterior se queda intacto) que
    comparte las líneas y los movimientos ya parseados: lo único que se rehace
    es lo que depende de la pausa —la capa, sus tramos y la detección de
    agujeros—, que es trabajo acotado a esa capa.
    """
    return _analyze_pause(
        input_path=result.input_path,
        is_3mf=result.is_3mf,
        gcode_filename=result.gcode_filename,
        lines=result.lines,
        moves=result.moves,
        pauses=result.pauses,
        ordinal=ordinal,
        settings=settings,
        print_height=result.print_height,
        footprints=result.footprints,
        filament_type=result.filament_type,
    )


def _detect_holes(
    lines, moves, settings: Settings, pause_index: Optional[int] = None,
    runs=None, run_starts=None, layer_height: Optional[float] = None,
) -> List[analysis_mod.CircleMeasurement]:
    """Mide los agujeros según la configuración (o [] si la detección está apagada)."""
    if not settings.hole_detection_enabled:
        return []
    layer_start_index, layer_end_index = analysis_mod.find_layer_region(lines, pause_index)
    return analysis_mod.measure_circles(
        moves,
        layer_start_index,
        layer_end_index,
        r_min=settings.hole_r_min,
        r_max=settings.hole_r_max,
        circ_tol=settings.hole_circularity,
        cluster_dist=settings.hole_cluster_dist,
        min_arc=settings.hole_min_arc,
        runs=runs,
        run_starts=run_starts,
        # Con el filtro por módulos encendido esto manda sobre r_min/r_max:
        # sólo se aceptan los agujeros del tamaño de los imanes definidos.
        match_diameters=settings.detection_diameters(),
        diameter_tol=settings.hole_diameter_tol,
        # Con las líneas, el detector mide el ancho del cordón y descuenta el
        # medio hilo que el trazado se come por cada lado: así el diámetro con
        # el que compara es el del agujero de verdad, no el de la trayectoria.
        lines=lines,
        layer_height=layer_height,
    )


def _detect_centers(
    lines, moves, settings: Settings, pause_index: Optional[int] = None,
    runs=None, run_starts=None, layer_height: Optional[float] = None,
) -> List[Tuple[float, float]]:
    """Sólo los centros de :func:`_detect_holes`, para quien no mire las medidas."""
    return [
        m.center for m in _detect_holes(
            lines, moves, settings, pause_index=pause_index,
            runs=runs, run_starts=run_starts, layer_height=layer_height,
        )
    ]


@dataclass
class MagnetFit:
    """Cómo entra un imán ya colocado en el agujero que le toca."""

    x: float
    y: float
    color: str
    magnet_diameter: float
    magnet_height: float
    hole_diameter: float
    clearance: float          # holgura por lado, en mm (negativa = no cabe)
    level: str                # ver `gcode_magnets.fit`
    # Lo alto que queda la cara inferior del imán sobre la placa, en mm: la ``h``
    # de la gráfica de separación mínima. Sale de la Z de la pausa, así que es
    # 0.0 cuando no se pasa (`evaluate_fits` sin `pause_z`).
    plate_gap: float = 0.0


@dataclass
class StackFit:
    """Los imanes de un mismo agujero, medidos contra lo hondo que es.

    Una "pila" es lo que el usuario ha puesto en un agujero: casi siempre un
    imán solo (``count = 1``), y varios cuando quiere más fuerza en ese punto.
    Lo que importa es lo mismo en los dos casos —que la suma de sus alturas no
    se salga del hueco— y por eso se mira igual: un imán solo no es más que una
    pila de uno.
    """

    x: float
    y: float
    color: str
    count: int
    magnet_height: float
    magnet_diameter: float
    hole_diameter: float
    hole_depth: float
    # Lo que la pila se sale del agujero, en mm (ver `gcode_magnets.fit`).
    overflow: float

    @property
    def height(self) -> float:
        """Lo que mide la pila entera, en mm."""
        return fit_mod.stack_height(self.count, self.magnet_height)

    @property
    def fits(self) -> bool:
        return self.overflow <= fit_mod.DEPTH_TOLERANCE


def hole_under(
    measurements: List[analysis_mod.CircleMeasurement], x: float, y: float
) -> Optional[analysis_mod.CircleMeasurement]:
    """El agujero medido en el que cae el punto (ver :func:`gcode_magnets.fit.hole_under`)."""
    return fit_mod.hole_under(measurements, x, y)


def evaluate_fits(
    measurements: List[analysis_mod.CircleMeasurement],
    points: List[Tuple[float, float, str]],
    settings: Settings,
    pause_z: Optional[float] = None,
) -> List[MagnetFit]:
    """El ajuste de cada imán colocado que caiga dentro de un agujero medido.

    Los imanes que no caen en ningún agujero detectado se quedan fuera de la
    lista: puede que el usuario los haya puesto sobre plástico macizo a
    propósito (un imán pegado en superficie, una pieza sin agujero laminado), y
    de un hueco que no se ha medido no hay nada que decir.

    Con ``pause_z`` se rellena además :attr:`MagnetFit.plate_gap`, lo alto que
    queda cada imán sobre la placa, que es lo que decide si el cabezal puede
    llevárselo pegado.
    """
    salida: List[MagnetFit] = []
    for punto in points:
        x, y = punto[0], punto[1]
        color = punto[2] if len(punto) > 2 else ""
        modulo = settings.module_for_color(color)
        if modulo is None or modulo.diameter <= 0:
            continue
        hueco = hole_under(measurements, x, y)
        if hueco is None:
            continue
        holgura = fit_mod.radial_clearance(hueco.inner_diameter, modulo.diameter)
        salida.append(MagnetFit(
            x=x, y=y, color=color,
            magnet_diameter=modulo.diameter,
            magnet_height=modulo.height,
            hole_diameter=hueco.inner_diameter,
            clearance=holgura,
            level=settings.fit_level(hueco.inner_diameter, modulo.diameter),
            plate_gap=(0.0 if pause_z is None
                       else magnetics_mod.magnet_gap(pause_z, modulo.height)),
        ))
    return salida


def evaluate_stacks(
    measurements: List[analysis_mod.CircleMeasurement],
    points: List[Tuple[float, float, str]],
    settings: Settings,
) -> List[StackFit]:
    """Cada agujero con imanes, con lo que mide la pila y lo que le sobra.

    Los imanes se agrupan por agujero (:func:`gcode_magnets.magnetics.stack_groups`:
    los que se han puesto en el mismo sitio son una pila) y de cada pila manda su
    imán **más alto**, que es el que decide si la suma se sale del hueco cuando
    hay dos dispensadores con formatos distintos.

    Se quedan fuera —como en :func:`evaluate_fits`— las pilas que no caen en
    ningún agujero medido y las que caen en uno sin profundidad medida: de lo que
    no se sabe no se avisa.
    """
    salida: List[StackFit] = []
    for grupo in magnetics_mod.stack_groups(points):
        primero = points[grupo[0]]
        x, y = float(primero[0]), float(primero[1])
        hueco = hole_under(measurements, x, y)
        if hueco is None or hueco.depth is None:
            continue
        modulos = []
        for i in grupo:
            color = points[i][2] if len(points[i]) > 2 else ""
            modulo = settings.module_for_color(color)
            if modulo is not None and modulo.height > 0:
                modulos.append(modulo)
        if not modulos:
            continue
        manda = max(modulos, key=lambda m: m.height)
        altura = manda.height
        salida.append(StackFit(
            x=x, y=y,
            color=str(primero[2]) if len(primero) > 2 else "",
            count=len(grupo),
            magnet_height=altura,
            magnet_diameter=manda.diameter,
            hole_diameter=hueco.inner_diameter,
            hole_depth=float(hueco.depth),
            overflow=fit_mod.depth_overflow(hueco.depth, altura, len(grupo)),
        ))
    return salida


def measure_layer_circles(
    result: AnalysisResult,
    r_min: float = 0.5,
    r_max: float = 50.0,
    circ_tol: float = 0.12,
    min_arc: float = 30.0,
    cluster_dist: float = 2.0,
) -> List[analysis_mod.CircleMeasurement]:
    """Todos los círculos de la capa pausada, medidos en mm de pieza.

    Es la detección sin el filtro del imán: devuelve cada hueco con su diámetro
    interior de verdad (:class:`~gcode_magnets.analysis.CircleMeasurement`), el
    ancho de cordón con el que se imprimió y lo redondo que le salió. Está aquí
    para lo que venga —comprobar que el agujero cabe, avisar de que quedó más
    estrecho de lo diseñado, listar los huecos de una placa—: la app no lo usa
    todavía, pero la medida ya no hay que volver a deducirla.
    """
    return analysis_mod.measure_circles(
        result.moves,
        result.layer_start_index,
        result.layer_end_index,
        lines=result.lines,
        # La altura de capa ya se midió al analizar; medirla otra vez sería
        # recorrer el archivo entero para llegar al mismo número.
        layer_height=result.layer_height,
        r_min=r_min,
        r_max=r_max,
        circ_tol=circ_tol,
        min_arc=min_arc,
        cluster_dist=cluster_dist,
        runs=result.layer_runs,
        run_starts=result.layer_run_starts,
    )


def recompute_centers(result: AnalysisResult, settings: Settings) -> List[Tuple[float, float]]:
    """Recalcula los centros sobre un análisis ya cargado (sin releer el archivo)."""
    # Se reutilizan los tramos ya agrupados: recalcular con "Rehacer detección"
    # no tiene por qué volver a recorrer todos los movimientos del archivo.
    huecos = _detect_holes(
        result.lines, result.moves, settings, pause_index=result.pause_index,
        runs=result.layer_runs, run_starts=result.layer_run_starts,
        layer_height=result.layer_height,
    )
    analysis_mod.measure_hole_depths(
        result.moves, result.pause_index, result.layer_z, huecos
    )
    result.hole_measurements = huecos
    result.suggested_centers = [m.center for m in huecos]
    return result.suggested_centers


# --- generación ---------------------------------------------------------------

# MARK_START / MARK_END se reexportan desde `gcode_magnets.generator`, que es
# quien los escribe en el bloque: definirlos aquí por segunda vez es justo cómo
# se separaron las dos copias de la generación.


def build_magnet_block(
    points: List[Point],
    current_z: float,
    temperatura_hotend: Optional[float],
    settings: Settings,
    *,
    fan_speed: Optional[float] = None,
    deretract: Optional[float] = None,
) -> List[str]:
    """Genera el bloque de líneas G-code (con ``\\n``) para colocar los imanes.

    Resuelve las secuencias editables de :class:`Settings` —que pueden llevar
    expresiones ``{z+0.4}``, ``{temp}``...— y deja el montaje del bloque en
    :func:`gcode_magnets.generator.assemble_magnet_block`, compartido con la CLI.

    ``fan_speed`` y ``deretract`` salen del archivo de entrada
    (:func:`gcode_magnets.analysis.get_fan_speed_before_pause` y
    :func:`~gcode_magnets.analysis.get_deretract_after_pause`) y son opcionales
    a propósito: van por palabra clave para no romper a quien llame con los
    cuatro argumentos posicionales de siempre, y si faltan se usan los valores
    de reserva.
    """
    temp = float(temperatura_hotend) if temperatura_hotend is not None else float(settings.default_temp)
    ctx = {
        "z": current_z,
        "safe_z": current_z + settings.safe_z_offset,
        "temp": temp,
        "fan": float(fan_speed) if fan_speed is not None else FALLBACK_FAN,
        "deretract": float(deretract) if deretract is not None else FALLBACK_DERETRACT,
        "offset_z": settings.offset_z,
        "safe_z_offset": settings.safe_z_offset,
    }

    # Cuánto tiene que apartarse el colocador tras soltar un imán lo decide **ese**
    # imán, no el peor de la máquina: el módulo se lleva dentro uno del mismo
    # formato. El peor caso se queda de reserva para un color sin módulo definido.
    # Sale de `Settings` para que sea el mismo criterio que usa el aviso de la
    # interfaz.
    diametro, altura = settings.worst_case_magnet()
    medidas = settings.magnet_sizes()

    def magnet_for_color(color: str):
        return medidas.get(str(color).lower())

    return assemble_magnet_block(
        points,
        current_z,
        sequence_for_color=lambda color: render_sequence(
            settings.color_sequence_text(color), ctx
        ),
        start_sequence=render_sequence(settings.seq_start, ctx),
        end_sequence=render_sequence(settings.seq_end, ctx),
        final_sequence=render_sequence(settings.seq_final, ctx),
        offset_x=settings.offset_x,
        offset_y=settings.offset_y,
        offset_z=settings.offset_z,
        safe_z_offset=settings.safe_z_offset,
        travel_feed=settings.travel_feed,
        magnet_height=altura,
        magnet_diameter=diametro,
        magnet_for_color=magnet_for_color,
    )


# --- secuencia de prueba ------------------------------------------------------

# Z de referencia cuando no hay ningún archivo cargado del que sacarla.
TEST_Z_FALLBACK = 10.0

# Preámbulo: un G-code de impresión ya trae este estado, pero un archivo de
# prueba arranca en frío. Sin G28 la posición es desconocida y un 'G1 Z192'
# puede estrellar el cabezal; sin M83 las retracciones de la secuencia de
# inicio (G1 E-1, G1 E-.04) se interpretan como extrusión absoluta.
TEST_PREAMBLE = [
    "G28              ; homing: la impresora necesita una posición conocida",
    "G92 E0           ; extrusor a cero",
    "M83              ; E relativa (las secuencias usan G1 E-1, G1 E-.04)",
    "G90              ; coordenadas XYZ absolutas",
]

TEST_STEPS = (
    ("Inicio (seq_start)", "seq_start"),
    ("Imán rojo (seq_red)", "seq_red"),
    ("Imán azul (seq_blue)", "seq_blue"),
    ("Fin (seq_end)", "seq_end"),
    ("Final / reanudar (seq_final)", "seq_final"),
)


def build_test_sequence(settings: Settings, z: float, temp: float) -> str:
    """G-code autónomo para probar las secuencias sin imprimir nada.

    Encadena preámbulo + Inicio + Imán rojo + Imán azul + Fin + Final tal como
    están en la pestaña *Secuencias*, resolviendo ``{z}``, ``{safe_z}``,
    ``{temp}``, ``{fan}`` y ``{deretract}`` con los valores dados (los dos
    últimos, con los de reserva). No incluye el movimiento de colocación
    (ir a XY, círculos, retirada): prueba solo el mecanismo de recogida.
    """
    ctx = {
        "z": float(z),
        "safe_z": float(z) + settings.safe_z_offset,
        "temp": float(temp),
        # Aquí no hay archivo del que leerlos, así que van los de reserva; sin
        # ellos '{fan}' saldría literal en el G-code de prueba.
        "fan": FALLBACK_FAN,
        "deretract": FALLBACK_DERETRACT,
        "offset_z": settings.offset_z,
        "safe_z_offset": settings.safe_z_offset,
    }

    out: List[str] = [
        "; " + "=" * 62,
        "; MagnetPlace Studio — SECUENCIA DE PRUEBA (no imprime nada)",
        f"; Generado: {datetime.now():%Y-%m-%d %H:%M}",
        f"; Z de referencia: {z:.3f} mm   ·   temperatura: {temp:.0f} °C",
        "; Orden: G28 · G92 · Inicio · Imán rojo · Imán azul · Fin · Final",
    ]
    if "M400 U1" in settings.seq_final:
        out.append("; Aviso: la secuencia Final acaba en 'M400 U1', que en Bambu es")
        out.append(";        una pausa: al terminar la impresora se quedará esperando.")
    out.append("; " + "=" * 62)
    out.extend(TEST_PREAMBLE)

    for title, attr in TEST_STEPS:
        out.append("")
        out.append(f"; --- {title} ---")
        out.extend(render_sequence(getattr(settings, attr), ctx))

    out.append("")
    return "\n".join(out) + "\n"


def save_test_sequence(
    gcode_text: str, output_path: str, template_path: Optional[str] = None
) -> str:
    """Guarda la secuencia de prueba como ``.gcode`` o como ``.3mf`` de Bambu.

    Para el ``.3mf`` hace falta ``template_path``: un proyecto ya laminado con
    Bambu Studio del que se clona todo (perfil, miniaturas, relaciones OPC)
    cambiando solo el bloque ejecutable del G-code. Ver
    :func:`gcode_magnets.io.write_gcode_into_bambu_template`.

    Devuelve el formato usado (``'gcode'`` o ``'3mf'``).
    """
    fmt = io_mod.detect_output_format(output_path)
    if fmt == "gcode":
        io_mod.write_gcode_to_file(output_path, gcode_text)
    else:
        if not template_path:
            raise ValueError(
                "Para exportar a .3mf hace falta una plantilla: un proyecto ya "
                "laminado con Bambu Studio para tu impresora."
            )
        io_mod.write_gcode_into_bambu_template(template_path, output_path, gcode_text)
    return fmt


def is_valid_bambu_template(path: Optional[str]) -> bool:
    """True si ``path`` es un ``.3mf`` con un G-code dentro (sirve de plantilla)."""
    if not path or not os.path.isfile(path) or path.lower().endswith(".gcode"):
        return False
    try:
        with zipfile.ZipFile(path, "r") as z:
            return io_mod.find_gcode_entry(z.namelist())[0] is not None
    except (OSError, zipfile.BadZipFile):
        return False


def suggest_test_output_path(input_path: Optional[str]) -> str:
    """Propone un nombre para la secuencia de prueba."""
    if input_path:
        base = input_path
        for ext in (".gcode.3mf", ".3mf", ".gcode"):
            if base.lower().endswith(ext):
                base = base[: -len(ext)]
                break
        return base + "-prueba-imanes.3mf"
    return "secuencia-prueba-imanes.3mf"


def _wipe_end_before(lines: List[str], pause_index: int) -> int:
    """Línea del ``; WIPE_END`` que precede a la pausa: ahí va el bloque."""
    for i in range(pause_index - 1, -1, -1):
        if "; WIPE_END" in lines[i]:
            return i
    raise ValueError("No se encontró '; WIPE_END' antes de la pausa")


def _assemble(
    lines: List[str], blocks: Sequence[Tuple[int, List[str]]]
) -> Tuple[str, Dict[int, Tuple[int, int]]]:
    """Inserta cada bloque tras el ``; WIPE_END`` de su pausa y borra esa pausa.

    ``blocks`` son pares ``(índice de la línea de pausa, bloque)``. Devuelve el
    texto montado y, para cada pausa tratada, las líneas ``(primera, última)``
    que ocupa su bloque en el texto de salida (base 0): son las que el visor 3D
    necesita para separar las fases.

    Solo se eliminan LAS pausas tratadas (su marca y su token). Las demás siguen
    en el archivo tal cual: son paradas que el usuario quiere conservar, y
    borrarlas a medias dejaría el G-code inconsistente.
    """
    inserts: Dict[int, Tuple[int, List[str]]] = {}
    drop = set()
    for pause_index, block in blocks:
        wipe_end_index = _wipe_end_before(lines, pause_index)
        inserts[wipe_end_index] = (pause_index, block)
        drop.add(pause_index)
        marker = pause_index - 1
        if marker >= 0 and "; PAUSE_PRINTING" in lines[marker]:
            drop.add(marker)

    new_lines: List[str] = []
    ranges: Dict[int, Tuple[int, int]] = {}
    for i, line in enumerate(lines):
        if i in drop:
            continue
        new_lines.append(line)
        if i in inserts:
            pause_index, block = inserts[i]
            first = len(new_lines)
            new_lines.extend(block)
            ranges[pause_index] = (first, len(new_lines) - 1)
    return "".join(new_lines), ranges


def assemble_gcode(
    result: AnalysisResult,
    magnet_block: List[str],
    settings: Settings = None,
) -> str:
    """Inserta el bloque de imanes tras el ``; WIPE_END`` de la pausa analizada."""
    text, _ranges = _assemble(result.lines, [(result.pause_index, magnet_block)])
    return text


def _blocks_for(
    result: AnalysisResult,
    points_by_pause: Dict[int, List[Point]],
    settings: Settings,
) -> List[Tuple[int, List[str]]]:
    """Un bloque por cada pausa con imanes, con los datos de ESA pausa.

    La Z, la temperatura, la refrigeración y el cebado son distintos en cada
    parada, así que cada bloque se construye con los suyos: usar los de la
    pausa que se está mirando dejaría las demás con la altura equivocada.
    """
    blocks: List[Tuple[int, List[str]]] = []
    for ordinal in sorted(points_by_pause):
        points = points_by_pause[ordinal]
        if not points:
            continue
        if not (0 <= ordinal < len(result.pauses)):
            raise ValueError(f"No existe la pausa nº {ordinal + 1} en el archivo")
        pause = result.pauses[ordinal]
        blocks.append((pause.index, build_magnet_block(
            points, pause.layer_z, pause.temperatura_hotend, settings,
            fan_speed=pause.fan_speed, deretract=pause.deretract,
        )))
    return blocks


def generate_output_multi(
    result: AnalysisResult,
    points_by_pause: Dict[int, List[Point]],
    settings: Settings,
) -> str:
    """G-code con un bloque de imanes en cada pausa que tenga imanes puestos.

    ``points_by_pause`` va indexado por el número de orden de la pausa (base 0,
    el mismo ``pause_ordinal`` del análisis); las pausas que no aparecen —o que
    aparecen sin imanes— se quedan como estaban, esperando al usuario.
    """
    text, _ranges = _assemble(result.lines, _blocks_for(result, points_by_pause, settings))
    return text


def generate_output_text(
    result: AnalysisResult,
    points: List[Point],
    settings: Settings,
) -> str:
    """Atajo: construye el bloque de la pausa analizada y ensambla el G-code."""
    return generate_output_multi(result, {result.pause_ordinal: points}, settings)


def generate_output_with_marks(
    result: AnalysisResult,
    points: List[Point],
    settings: Settings,
    points_by_pause: Optional[Dict[int, List[Point]]] = None,
) -> Tuple[str, int, int]:
    """G-code ensamblado junto con las líneas donde vive el bloque de imanes.

    Devuelve ``(texto, primera_linea, ultima_linea)`` en índices de línea del
    **texto de salida** (base 0). El visor 3D las usa para repartir cada
    movimiento entre las tres fases: lo impreso antes de la parada, la
    secuencia de colocación y lo que se imprime al reanudar.

    El rango cubre el bloque entero, incluida la secuencia *Final* que va tras
    ``MARK_END``: hasta que esa purga de reanudación termina, la impresora
    sigue sin construir la pieza, así que pertenece a la fase de la secuencia.

    Con ``points_by_pause`` se montan además los bloques de las demás pausas,
    pero las marcas siguen siendo las de la pausa que se está mirando: es la
    única cuyo antes/durante/después tiene sentido dibujar.
    """
    todos = dict(points_by_pause or {})
    todos[result.pause_ordinal] = points
    text, ranges = _assemble(result.lines, _blocks_for(result, todos, settings))
    first, last = ranges.get(result.pause_index, (-1, -1))
    return text, first, last


def save_output(result: AnalysisResult, gcode_text: str, output_path: str) -> str:
    """Guarda el G-code resultante como ``.gcode`` o reempaquetado en ``.3mf``.

    Devuelve el formato usado (``'gcode'`` o ``'3mf'``).
    """
    fmt = io_mod.detect_output_format(output_path)
    if fmt == "gcode":
        io_mod.write_gcode_to_file(output_path, gcode_text)
    else:
        if not result.is_3mf or result.gcode_filename is None:
            raise ValueError(
                "El origen no es un .3mf; usa una salida .gcode para entradas .gcode"
            )
        io_mod.write_gcode_into_3mf(
            result.input_path, output_path, result.gcode_filename, gcode_text
        )
    return fmt


def suggest_output_path(input_path: str) -> str:
    """Propone una ruta de salida junto al archivo de entrada."""
    base, _ = os.path.splitext(input_path)
    if input_path.lower().endswith(".gcode.3mf"):
        base = input_path[: -len(".gcode.3mf")]
        return base + "-imanes.gcode.3mf"
    if input_path.lower().endswith(".gcode"):
        return base + "-imanes.gcode"
    return base + "-imanes.3mf"
