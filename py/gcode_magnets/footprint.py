# -*- coding: utf-8 -*-
"""La huella que deja la pieza sobre la cama: cuánto agarra y cuánto se resiste a volcar.

:mod:`gcode_magnets.adhesion` necesita dos números de la primera capa para saber
qué empujón lateral aguanta la pieza: el **área** pegada a la cama y el **módulo
resistente** de esa área, que es lo que se opone al vuelco. Los dos salen de
aquí, y salen de los ``GCodeMove`` que :func:`~gcode_magnets.parser.parse_gcode_moves`
ya ha dejado en memoria: no se vuelve a leer el archivo.

Cada movimiento con extrusión de la primera capa aporta un rectángulo de
``longitud × ancho de cordón`` (:func:`~gcode_magnets.geometry.extrusion_width`,
el mismo ancho que dibuja el visor). Sumando esos rectángulos salen el área, el
centroide y los segundos momentos, que es todo lo que hace falta.

**Se agrupa en islas.** Una placa con cuatro piezas no es una huella grande sino
cuatro pequeñas, y tratarla como una sola sería tremendamente optimista: el
módulo resistente crece con el cuadrado de la anchura, así que juntar cuatro
piezas separadas multiplicaría por mucho lo que parece que aguantan. La
agrupación es por proximidad sobre una rejilla de :data:`ISLAND_GAP` mm, que
cierra los saltos entre perímetro y relleno sin llegar a unir dos piezas
vecinas. La línea de purga del borde de la cama sale como su propia isla, y como
allí no se coloca ningún imán, no molesta.

**Dos aproximaciones, las dos dichas en voz alta.** Los cordones que se solapan
se cuentan dos veces, así que el área sale algo pasada de largo (en una primera
capa el solape real es pequeño); y cada tramo se trata como una línea sin
grosor al calcular su inercia propia, que frente a los milímetros de la pieza no
se nota.

Sin Qt, como el resto de :mod:`gcode_magnets`.
"""
from __future__ import annotations

import math
from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple

from . import geometry
from .parser import GCodeMove

__all__ = [
    "LAYER_Z_TOL", "ISLAND_GAP", "MIN_ISLAND_AREA",
    "Footprint", "first_layer_z", "footprints", "footprint_at",
]

# Margen para decidir qué Z es "la primera capa": un archivo real repite el
# mismo valor con redondeos distintos (0.2 y 0.200001).
LAYER_Z_TOL = 0.02

# Dos trozos de cordón a menos de esto son la misma pieza. Algo más de dos
# anchos de cordón: cierra el hueco entre el perímetro y el relleno, y entre dos
# piezas vecinas siempre hay bastante más.
ISLAND_GAP = 1.0

# Por debajo de esto no es una isla, es ruido: un movimiento suelto, el final de
# una purga. No llega ni a un cuadrado de 2 mm de lado.
MIN_ISLAND_AREA = 4.0

# Y esto descarta lo que tiene área pero no tiene forma: la **línea de purga**
# que Bambu traza en el borde de la cama son 45 mm de largo por un cordón de
# ancho, o sea 50 mm² con cero de fondo. Como isla es venenosa —su módulo
# resistente es cero, así que «no aguanta nada» y avisaría de un despegue que no
# existe—, y como pieza no es ninguna: no hay parte impresa de medio milímetro
# de lado. Se mide sobre el lado corto.
MIN_ISLAND_SPAN = 2.0

Pt = Tuple[float, float]


class Footprint(NamedTuple):
    """Lo que una pieza apoya en la cama, en mm y mm².

    ``i_yy`` es ``∫(x−cx)²dA`` y ``i_xx`` es ``∫(y−cy)²dA``: el primero es el que
    se opone a un empujón en **X** y el segundo a uno en **Y** (el subíndice es
    el del eje del giro, no el de la fuerza).
    """

    area: float
    cx: float
    cy: float
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    i_yy: float
    i_xx: float

    @property
    def width(self) -> float:
        """Lo que mide la huella en X, en mm."""
        return self.x_max - self.x_min

    @property
    def depth(self) -> float:
        """Lo que mide la huella en Y, en mm."""
        return self.y_max - self.y_min

    def modulus_x(self) -> float:
        """Módulo resistente frente a un empujón en X, en mm³.

        Es ``I/c`` con ``c`` la distancia del centroide al borde **más lejano**:
        de los dos sentidos posibles se devuelve el peor, porque el módulo se
        acerca a la pieza por un lado y se retira por el otro y no se sabe cuál
        de los dos tirones manda.
        """
        c = max(self.cx - self.x_min, self.x_max - self.cx)
        return self.i_yy / c if c > 1e-9 else 0.0

    def modulus_y(self) -> float:
        """Módulo resistente frente a un empujón en Y, en mm³."""
        c = max(self.cy - self.y_min, self.y_max - self.cy)
        return self.i_xx / c if c > 1e-9 else 0.0

    def modulus(self) -> float:
        """El peor de los dos ejes, en mm³: por ahí es por donde volcaría."""
        return min(self.modulus_x(), self.modulus_y())

    def contains(self, x: float, y: float, margin: float = 0.0) -> bool:
        """True si ``(x, y)`` cae dentro del rectángulo que envuelve la huella."""
        m = max(float(margin), 0.0)
        return (
            self.x_min - m <= float(x) <= self.x_max + m
            and self.y_min - m <= float(y) <= self.y_max + m
        )


def first_layer_z(moves: Sequence[GCodeMove]) -> Optional[float]:
    """Z de la primera capa, en mm: la más baja a la que se extruye algo.

    ``None`` si en el archivo no hay ningún movimiento con extrusión y Z, que es
    lo que pasa con un G-code de prueba hecho a mano.
    """
    alturas = [
        m.z for m in moves
        if m.e is not None and m.e > 0.0 and m.z is not None and m.z > 0.0
    ]
    return min(alturas) if alturas else None


class _Segment(NamedTuple):
    """Un trocito recto de cordón ya aplanado, con su área."""

    a: float        # área que apoya, mm²
    xm: float       # centro del trozo
    ym: float
    lx: float       # cuánto abarca en cada eje, para su inercia propia
    ly: float
    x0: float
    y0: float
    x1: float
    y1: float


def _extruding(move: GCodeMove) -> bool:
    return move.e is not None and move.e > 0.0


def _flatten(prev: Pt, move: GCodeMove) -> List[Pt]:
    """Puntos que dibuja un movimiento, con los arcos ya troceados."""
    end = geometry.move_endpoint(move)
    if end is None:
        return []
    if move.cmd in ("G2", "G3") and move.i_offset is not None and move.j_offset is not None:
        return geometry.arc_points(
            prev, end, move.i_offset, move.j_offset, clockwise=(move.cmd == "G2")
        )
    return [end]


def _segments(
    moves: Sequence[GCodeMove], layer_z: float, layer_height: float
) -> List[_Segment]:
    """Trocitos de cordón de la primera capa, con su área ya calculada."""
    techo = layer_z + LAYER_Z_TOL
    salida: List[_Segment] = []
    prev: Optional[Pt] = None
    for m in moves:
        end = geometry.move_endpoint(m)
        if end is None:
            continue
        if not _extruding(m) or m.z is None or m.z > techo:
            prev = end
            continue
        if prev is None:
            prev = end
            continue
        largo = geometry.move_length(prev, m)
        ancho = geometry.extrusion_width(m.e, largo, layer_height)
        # El ancho se deduce del caudal del movimiento entero, así que todos los
        # trocitos de un arco heredan el mismo: es el mismo cordón.
        punto = prev
        for siguiente in _flatten(prev, m):
            dx = siguiente[0] - punto[0]
            dy = siguiente[1] - punto[1]
            trozo = math.hypot(dx, dy)
            if trozo > 1e-9:
                salida.append(_Segment(
                    a=trozo * ancho,
                    xm=(punto[0] + siguiente[0]) / 2.0,
                    ym=(punto[1] + siguiente[1]) / 2.0,
                    lx=abs(dx), ly=abs(dy),
                    x0=punto[0], y0=punto[1], x1=siguiente[0], y1=siguiente[1],
                ))
            punto = siguiente
        prev = end
    return salida


class _Groups:
    """Union-find del montón, para juntar trocitos en islas."""

    def __init__(self, n: int) -> None:
        self._padre = list(range(n))

    def find(self, i: int) -> int:
        while self._padre[i] != i:
            self._padre[i] = self._padre[self._padre[i]]
            i = self._padre[i]
        return i

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._padre[rb] = ra


def _cells(seg: _Segment, lado: float) -> List[Tuple[int, int]]:
    """Casillas de la rejilla por las que pasa un trocito.

    Se muestrea el trocito a medio lado de casilla, que es lo que hace falta
    para no saltarse ninguna por la que pase de refilón.
    """
    largo = math.hypot(seg.x1 - seg.x0, seg.y1 - seg.y0)
    pasos = max(1, int(math.ceil(largo / (lado / 2.0))))
    vistas = []
    for k in range(pasos + 1):
        t = k / pasos
        x = seg.x0 + (seg.x1 - seg.x0) * t
        y = seg.y0 + (seg.y1 - seg.y0) * t
        celda = (int(math.floor(x / lado)), int(math.floor(y / lado)))
        if celda not in vistas:
            vistas.append(celda)
    return vistas


def _islands(segs: Sequence[_Segment], gap: float) -> List[List[_Segment]]:
    """Reparte los trocitos en islas: los que se tocan van juntos."""
    grupos = _Groups(len(segs))
    dueno: Dict[Tuple[int, int], int] = {}
    for i, seg in enumerate(segs):
        for cx, cy in _cells(seg, gap):
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    vecino = dueno.get((cx + dx, cy + dy))
                    if vecino is not None:
                        grupos.union(vecino, i)
            dueno[(cx, cy)] = grupos.find(i)
    por_raiz: Dict[int, List[_Segment]] = {}
    for i, seg in enumerate(segs):
        por_raiz.setdefault(grupos.find(i), []).append(seg)
    return list(por_raiz.values())


def _measure(segs: Sequence[_Segment]) -> Optional[Footprint]:
    """Área, centroide, extremos e inercias de una isla."""
    area = sum(s.a for s in segs)
    if area <= 0.0:
        return None
    cx = sum(s.a * s.xm for s in segs) / area
    cy = sum(s.a * s.ym for s in segs) / area
    # Steiner por trocito: su inercia propia (una línea de largo `lx` en el eje)
    # más el traslado de su área al centroide de la isla.
    i_yy = sum(s.a * ((s.xm - cx) ** 2 + s.lx * s.lx / 12.0) for s in segs)
    i_xx = sum(s.a * ((s.ym - cy) ** 2 + s.ly * s.ly / 12.0) for s in segs)
    return Footprint(
        area=area, cx=cx, cy=cy,
        x_min=min(min(s.x0, s.x1) for s in segs),
        x_max=max(max(s.x0, s.x1) for s in segs),
        y_min=min(min(s.y0, s.y1) for s in segs),
        y_max=max(max(s.y0, s.y1) for s in segs),
        i_yy=i_yy, i_xx=i_xx,
    )


def footprints(
    moves: Sequence[GCodeMove],
    layer_height: float = geometry.DEFAULT_LAYER_HEIGHT,
    layer_z: Optional[float] = None,
    gap: float = ISLAND_GAP,
    min_area: float = MIN_ISLAND_AREA,
    min_span: float = MIN_ISLAND_SPAN,
) -> List[Footprint]:
    """Una huella por pieza apoyada en la cama, de mayor a menor área.

    ``layer_z`` se deduce con :func:`first_layer_z` si no se dice. Lista vacía =
    no se ha podido medir nada, y quien avisa **no debe avisar de nada**: vale
    más callarse que inventarse un aguante.

    Lo que no llegue a ``min_area`` de superficie o a ``min_span`` por su lado
    corto se descarta: son la purga y los cordones sueltos, no piezas.
    """
    z = first_layer_z(moves) if layer_z is None else float(layer_z)
    if z is None:
        return []
    segs = _segments(moves, z, layer_height)
    if not segs:
        return []
    medidas = [_measure(isla) for isla in _islands(segs, max(float(gap), 1e-3))]
    huellas = [
        f for f in medidas
        if f is not None
        and f.area >= float(min_area)
        and min(f.width, f.depth) >= float(min_span)
    ]
    huellas.sort(key=lambda f: f.area, reverse=True)
    return huellas


def footprint_at(
    huellas: Sequence[Footprint], x: float, y: float, margin: float = 0.0
) -> Optional[Footprint]:
    """La huella sobre la que cae ``(x, y)``, o ``None`` si no cae en ninguna.

    Entre varias que lo contengan gana la del **rectángulo más ajustado**, que es
    la que de verdad está debajo del punto: los rectángulos de dos piezas pueden
    solaparse aunque las piezas no se toquen, y la que envuelve al punto más de
    cerca es la buena.

    El criterio era antes «la de menos material», y con eso el **skirt** se
    llevaba los imanes de la pieza que rodea: su vuelta de cordón encierra la
    pieza entera, así que contiene el punto, y como es una sola línea tiene mucha
    menos área que la pieza. Un ⌀20 con skirt daba 47 mm² y 439 mm³ de módulo en
    vez de los 403 y 1344 de la pieza, o sea tres veces menos aguante del real y
    un aviso de despegue inventado. Por rectángulo no pasa: el del skirt es
    **mayor** que el de la pieza, siempre, porque va por fuera.
    """
    dentro = [f for f in huellas if f.contains(x, y, margin)]
    if not dentro:
        return None
    return min(dentro, key=lambda f: f.width * f.depth)
