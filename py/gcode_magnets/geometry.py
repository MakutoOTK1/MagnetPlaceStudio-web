# -*- coding: utf-8 -*-
"""Geometría real de los tramos de extrusión: arcos aplanados y ancho del cordón.

El parser (:mod:`gcode_magnets.parser`) guarda ``i_offset``/``j_offset`` de los
``G2``/``G3``, pero quien dibuja solo tenía los puntos final de cada movimiento:
un arco acababa pintado como la **cuerda** entre su inicio y su fin. Como el
laminador emite casi siempre los agujeros de los imanes con dos o tres arcos,
los círculos salían como triángulos o rombos. Aquí se reconstruye la curva.

Sin dependencias de Qt ni de matplotlib: es lógica pura y testeable.
"""
from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

from .parser import GCodeMove

Pt = Tuple[float, float]

# Filamento de 1.75 mm: sección usada para deducir el ancho del cordón del
# caudal de E (ver `segment_widths`).
FILAMENT_DIAMETER = 1.75
FIL_AREA = math.pi * (FILAMENT_DIAMETER / 2.0) ** 2  # ≈ 2.405 mm²

# Ancho típico de un cordón cuando no se puede deducir (movimiento sin E útil).
DEFAULT_WIDTH = 0.42
MIN_WIDTH = 0.15
MAX_WIDTH = 1.5

# Altura de capa de reserva cuando el análisis no consigue medirla.
DEFAULT_LAYER_HEIGHT = 0.2

# Un arco se trocea en pasos de este tamaño (mm de arco). 0.15 mm mantiene el
# error de cuerda por debajo de una micra en los radios de un imán (2-10 mm).
DEFAULT_MM_PER_SEGMENT = 0.15
MAX_ARC_STEPS = 256


def arc_points(
    start: Pt,
    end: Pt,
    i_offset: float,
    j_offset: float,
    clockwise: bool,
    mm_per_segment: float = DEFAULT_MM_PER_SEGMENT,
) -> List[Pt]:
    """Puntos intermedios y final de un arco ``G2``/``G3`` en forma I/J.

    ``i_offset``/``j_offset`` son el centro **relativo al punto de partida**,
    que es la única forma que emite Bambu Studio (no se admite la forma ``R``).
    El punto de partida NO se incluye en el resultado: se asume que ya está en
    la polilínea.

    El sentido se corrige como en cualquier intérprete de G-code: un arco
    horario debe terminar en un ángulo menor que el inicial y uno antihorario
    en uno mayor. Cuando inicio y fin coinciden —el círculo completo de 360°
    que genera :func:`gcode_magnets.generator.generate_concentric_circles`—
    eso es justo lo que hace que dé la vuelta entera en vez de quedarse en cero.
    """
    cx = start[0] + i_offset
    cy = start[1] + j_offset
    radius = math.hypot(start[0] - cx, start[1] - cy)
    if radius < 1e-9:
        return [end]

    a0 = math.atan2(start[1] - cy, start[0] - cx)
    a1 = math.atan2(end[1] - cy, end[0] - cx)
    if clockwise:
        if a1 >= a0:
            a1 -= 2.0 * math.pi
    else:
        if a1 <= a0:
            a1 += 2.0 * math.pi

    sweep = a1 - a0
    arc_len = abs(sweep) * radius
    steps = int(math.ceil(arc_len / max(mm_per_segment, 1e-6)))
    steps = max(2, min(MAX_ARC_STEPS, steps))

    pts: List[Pt] = []
    for k in range(1, steps):
        a = a0 + sweep * (k / steps)
        pts.append((cx + radius * math.cos(a), cy + radius * math.sin(a)))
    # El último punto se toma tal cual del G-code y no de la parametrización,
    # para no arrastrar el error del radio si el arco venía ligeramente
    # inconsistente (cosa habitual con el arc fitting del laminador).
    pts.append(end)
    return pts


def move_endpoint(move: GCodeMove) -> Optional[Pt]:
    """``(x, y)`` de un movimiento, o ``None`` si le falta alguna coordenada."""
    if move.x is None or move.y is None:
        return None
    return (move.x, move.y)


def flatten_run(
    run: Sequence[GCodeMove],
    mm_per_segment: float = DEFAULT_MM_PER_SEGMENT,
    start: Optional[Pt] = None,
) -> List[Pt]:
    """Polilínea real que dibuja la boquilla en un tramo de extrusión.

    ``run`` es uno de los tramos de
    :func:`gcode_magnets.analysis.group_extruding_runs`. Los ``G1`` aportan su
    punto; los ``G2``/``G3`` se sustituyen por el arco troceado.

    ``start`` es la posición del cabezal **antes** del primer movimiento del
    tramo, que se obtiene con
    :func:`gcode_magnets.analysis.group_extruding_runs_with_starts`. Importa
    más de lo que parece: un arco define su centro relativo a donde empieza,
    así que sin ese punto el primer movimiento del tramo pierde su curvatura y
    se queda en su extremo. En un archivo real uno de cada seis tramos empieza
    con un ``G2``/``G3``.
    """
    pts: List[Pt] = []
    prev: Optional[Pt] = start
    if start is not None:
        pts.append(start)
    for m in run:
        end = move_endpoint(m)
        if end is None:
            continue
        if prev is None:
            pts.append(end)
            prev = end
            continue
        if m.cmd in ("G2", "G3") and m.i_offset is not None and m.j_offset is not None:
            pts.extend(
                arc_points(
                    prev, end, m.i_offset, m.j_offset,
                    clockwise=(m.cmd == "G2"),
                    mm_per_segment=mm_per_segment,
                )
            )
        else:
            pts.append(end)
        prev = end
    return pts


def move_length(prev: Optional[Pt], move: GCodeMove) -> float:
    """Longitud recorrida por un movimiento (la del arco si es G2/G3)."""
    end = move_endpoint(move)
    if end is None or prev is None:
        return 0.0
    if move.cmd in ("G2", "G3") and move.i_offset is not None and move.j_offset is not None:
        cx = prev[0] + move.i_offset
        cy = prev[1] + move.j_offset
        radius = math.hypot(prev[0] - cx, prev[1] - cy)
        a0 = math.atan2(prev[1] - cy, prev[0] - cx)
        a1 = math.atan2(end[1] - cy, end[0] - cx)
        if move.cmd == "G2":
            if a1 >= a0:
                a1 -= 2.0 * math.pi
        else:
            if a1 <= a0:
                a1 += 2.0 * math.pi
        return abs(a1 - a0) * radius
    return math.hypot(end[0] - prev[0], end[1] - prev[1])


# Nombre anterior, de cuando esto solo lo usaba `segment_widths`. Lo necesita
# `gcode_magnets.footprint` para medir cuánto cordón hay pegado a la cama, así
# que ahora es público; el alias se queda por si algo de fuera lo llamaba así.
_move_length = move_length


def extrusion_width(
    e: Optional[float],
    distance: float,
    layer_height: float,
    default: float = DEFAULT_WIDTH,
) -> float:
    """Ancho del cordón deducido del caudal: ``E · área_filamento / (long · h)``.

    Modelo de sección rectangular, el mismo que usa cualquier previsualizador
    de laminador. ``e`` es el valor crudo de la línea, que sirve tal cual
    porque Bambu extruye en modo relativo (``M83``); un ``E`` negativo es una
    retracción y no dibuja nada, así que cae al valor por defecto.
    """
    if e is None or e <= 0 or distance <= 1e-9 or layer_height <= 1e-9:
        return default
    w = (e * FIL_AREA) / (distance * layer_height)
    if not math.isfinite(w) or w <= 0:
        return default
    return min(MAX_WIDTH, max(MIN_WIDTH, w))


def segment_widths(
    run: Sequence[GCodeMove],
    layer_height: float = DEFAULT_LAYER_HEIGHT,
    default: float = DEFAULT_WIDTH,
    start: Optional[Pt] = None,
) -> List[float]:
    """Ancho de cada movimiento del tramo, en mm (misma longitud que ``run``)."""
    widths: List[float] = []
    prev: Optional[Pt] = start
    for m in run:
        end = move_endpoint(m)
        if end is None:
            widths.append(default)
            continue
        dist = move_length(prev, m)
        widths.append(extrusion_width(m.e, dist, layer_height, default))
        prev = end
    return widths


def run_mean_width(
    run: Sequence[GCodeMove],
    layer_height: float = DEFAULT_LAYER_HEIGHT,
    default: float = DEFAULT_WIDTH,
    start: Optional[Pt] = None,
) -> float:
    """Ancho representativo de un tramo: la mediana de sus segmentos.

    Se dibuja el tramo entero con un solo grosor de pluma (mucho más rápido que
    un trazo por segmento) y la mediana aguanta mejor que la media los
    movimientos cortos de enlace, que salen artificialmente gruesos.
    """
    widths = [w for w in segment_widths(run, layer_height, default, start) if w > 0]
    if not widths:
        return default
    widths.sort()
    mid = len(widths) // 2
    if len(widths) % 2:
        return widths[mid]
    return (widths[mid - 1] + widths[mid]) / 2.0
