# -*- coding: utf-8 -*-
"""Límites físicos de la máquina: hasta dónde llega y hasta dónde sube.

El colocador de imanes es un accesorio montado a un lado del cabezal, así que no
alcanza toda la placa: para dejar un imán en ``(x, y)`` el cabezal tiene que irse
a ``(x + offset_x, y + offset_y)`` (ver
:func:`gcode_magnets.generator.assemble_magnet_block`), y esa coordenada tiene
que caber en el recorrido real de los ejes. Y no basta con llegar: dejar el imán
no se acaba al bajar, el colocador **sigue hacia +X** para despegarse de él, así
que lo que tiene que caber es el final de esa retirada, y quien tiene que caber
es la punta del colocador —que va por delante del cabezal— y no el cabezal. Por
eso en X 256 no se puede poner un imán aunque el cabezal esté a 200: la punta ya
está en el borde y aún le queda la retirada. Y por arriba, el mecanismo deja de
poder trabajar pasados los 170 mm.

Y hay un tercer límite que no es de la máquina sino **de la pieza**: al retirarse
el módulo le da un empujón lateral a la altura de la pausa, y una pieza alta de
base estrecha se despega de la cama. Esa cuenta vive en
:mod:`gcode_magnets.adhesion` y aquí solo se convierte en avisos
(:func:`adhesion_problems`), igual que se hace con las alturas.

Aquí viven esos números y las cuentas que salen de ellos. El módulo no importa
Qt a propósito —igual que :mod:`magnet_app.pipeline`— para que la comprobación
se pueda usar (y probar) sin levantar una ventana.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple, Union

from gcode_magnets import adhesion, footprint as footprint_mod

# --- alturas ------------------------------------------------------------------
# Por encima de esto el colocador ya no puede trabajar sobre la pieza.
MAX_PRINT_HEIGHT = 170.0

# Holgura que la capa de la pausa necesita por encima para las maniobras del
# bloque de imanes. Es una constante de la máquina, no el `safe_z_offset` de los
# parámetros: aunque hoy valgan lo mismo, ese se puede editar y este no.
MAGNET_LAYER_CLEARANCE = 20.0

# Z máxima a la que puede quedar la capa con el `M400 U1`.
MAX_PAUSE_Z = MAX_PRINT_HEIGHT - MAGNET_LAYER_CLEARANCE   # 150.0

# --- recorrido de los ejes ----------------------------------------------------
# X llega a negativos porque ahí está la zona de purga/recogida, fuera de la cama.
MACHINE_X_MIN, MACHINE_X_MAX = -48.0, 256.0
MACHINE_Y_MIN, MACHINE_Y_MAX = 0.0, 256.0

# Margen de seguridad en el borde que limita: colocar justo en el final de
# carrera no deja sitio para el círculo concéntrico ni para la retirada.
EDGE_MARGIN = 1.0

# Lado de la placa, en mm. Repetido de `magnet_app.bed_canvas.BED_SIZE`, que no
# se puede importar aquí sin arrastrar Qt; `tests/test_limits.py` comprueba que
# los dos valores siguen coincidiendo.
BED_SIZE = 256.0

# Hasta dónde puede llegar por la derecha **la punta del colocador**, en
# coordenadas de placa. Vale lo mismo que la cama, pero no es lo mismo: es un
# tope del MagnetPlace —de dónde puede estar su cabezal— y no del recorrido del
# eje X de la impresora, que es `MACHINE_X_MAX` y se mide en el cabezal de la
# impresora. Se separan porque a este hay que descontarle la retirada: la punta
# sigue hacia +X después de soltar el imán y tiene que acabar de este lado.
PLACER_X_MAX = BED_SIZE

Area = Tuple[float, float, float, float]   # (x_min, x_max, y_min, y_max)


def reachable_area(offset_x: float, offset_y: float,
                   retreat: float = 0.0) -> Area:
    """Zona de la placa donde se puede dejar un imán, en coordenadas de placa.

    Es la intersección de dos cosas: la cama (0–256 en los dos ejes) y el
    recorrido de los ejes trasladado por los offsets del colocador. Como el
    cabezal va a ``x + offset_x``, el límite ``MACHINE_X_MIN`` de la máquina se
    convierte en ``MACHINE_X_MIN - offset_x`` en coordenadas de placa.

    ``retreat`` son los milímetros que se recorren **hacia +X** después de soltar
    el imán, para despegar el colocador de él
    (:func:`gcode_magnets.generator.retreat_clearance`). Ese movimiento forma
    parte de colocar: si no cabe, el imán tampoco se puede poner, aunque se
    llegue de sobra al agujero. Y quien tiene que caber es **la punta del
    colocador**, no el cabezal: la punta arranca en el propio agujero y acaba en
    ``x + retreat``, así que el tope de la derecha —los 256 mm de
    :data:`PLACER_X_MAX`, que son del colocador y no del cabezal— se le queda a
    ``PLACER_X_MAX - retreat``. Por eso un imán en X 256 no se puede poner en
    cuanto hay retirada, aunque el cabezal esté a 200 y le sobre recorrido.

    De ahí que la retirada entre en los dos topes de la derecha y no en uno: en
    el del colocador, que es el que manda casi siempre, y en el del cabezal, que
    tampoco puede pasarse de ``MACHINE_X_MAX`` mientras lleva la punta hasta
    ahí. En los otros tres bordes no pinta nada: la retirada es solo en +X y a
    la misma Y.

    Lo que no entra aquí es el avance extra de
    :func:`gcode_magnets.generator.compute_retreat_x`, que alarga la retirada
    cuando hay un imán ya colocado en medio: depende de dónde esté cada imán y
    del orden, así que no cabe en un rectángulo. Lo mismo con el formato: se
    espera el peor caso de la placa (el imán que más pide), y no lo que pide el
    de cada dispensador, para que el rectángulo siga siendo uno solo.

    Con los valores de fábrica (``offset_x = -55.4``, ``offset_y = 32``) y sin
    retirada sale X 8.4–256 e Y 0–223: por la izquierda manda el cabezal y por
    arriba también, mientras que por la derecha y por abajo manda la placa. Con
    24 mm de retirada la derecha baja a 232, y con los 46 que pide un imán a
    7 mm sobre la placa, a 210.
    """
    retreat = max(float(retreat), 0.0)
    return (
        max(0.0, MACHINE_X_MIN - offset_x + EDGE_MARGIN),
        min(PLACER_X_MAX - retreat,
            MACHINE_X_MAX - offset_x - retreat - EDGE_MARGIN),
        max(0.0, MACHINE_Y_MIN - offset_y + EDGE_MARGIN),
        min(BED_SIZE, MACHINE_Y_MAX - offset_y - EDGE_MARGIN),
    )


def in_area(x: float, y: float, area: Area) -> bool:
    """True si ``(x, y)`` cae dentro del área (bordes incluidos)."""
    x_min, x_max, y_min, y_max = area
    return x_min <= x <= x_max and y_min <= y <= y_max


def is_reachable(x: float, y: float, offset_x: float, offset_y: float,
                 retreat: float = 0.0) -> bool:
    """True si el colocador puede dejar un imán en ``(x, y)`` y retirarse."""
    return in_area(x, y, reachable_area(offset_x, offset_y, retreat))


def clamp_to_area(x: float, y: float, area: Area) -> Tuple[float, float]:
    """Acerca ``(x, y)`` al punto válido más próximo (para el arrastre)."""
    x_min, x_max, y_min, y_max = area
    # Si el área saliera vacía (offsets absurdos), min/max se cruzan; el orden
    # de las llamadas deja el punto en el borde en vez de dar un valor loco.
    return (
        min(max(x, x_min), max(x_max, x_min)),
        min(max(y, y_min), max(y_max, y_min)),
    )


def points_out_of_area(points, area: Area) -> List[int]:
    """Índices (base 0) de los imanes de ``points`` que caen fuera del área."""
    return [
        i for i, p in enumerate(points)
        if not in_area(float(p[0]), float(p[1]), area)
    ]


def height_problems(
    print_height: Optional[float], pause_z: Optional[float]
) -> List[Tuple[str, dict]]:
    """Avisos de altura: ``[(clave i18n, parámetros del texto)]``.

    Lista vacía = nada que objetar. Se devuelven claves y no textos ya montados
    para no atar este módulo al idioma activo: quien avisa es quien traduce.
    Una altura desconocida (``None``) no se inventa: no genera aviso.
    """
    avisos: List[Tuple[str, dict]] = []
    if print_height is not None and print_height > MAX_PRINT_HEIGHT:
        avisos.append((
            "limits.too_tall",
            {"h": f"{print_height:.2f}", "max": f"{MAX_PRINT_HEIGHT:.0f}"},
        ))
    if pause_z is not None and pause_z > MAX_PAUSE_Z:
        avisos.append((
            "limits.pause_too_high",
            {"z": f"{pause_z:.2f}", "max": f"{MAX_PAUSE_Z:.0f}"},
        ))
    return avisos


# --- la pieza contra la cama --------------------------------------------------
# Fuerza lateral por imán: una para todos, o una por color de dispensador.
Forces = Union[float, Dict[str, float]]


def _force_for(point, forces: Forces) -> float:
    """Fuerza lateral que le toca a un imán, en N.

    Un color sin fuerza declarada se queda a 0, o sea sin aviso: más vale no
    avisar que inventarse un imán del que no se sabe nada.
    """
    if isinstance(forces, (int, float)):
        return max(float(forces), 0.0)
    color = str(point[2]).lower() if len(point) > 2 else ""
    return max(float(forces.get(color, 0.0) or 0.0), 0.0)


def adhesion_problems(
    footprints: Sequence[footprint_mod.Footprint],
    points: Sequence[tuple],
    pause_z: Optional[float],
    forces: Forces,
    material: Optional[str] = None,
    factor: float = adhesion.DEFAULT_SAFETY_FACTOR,
) -> List[Tuple[str, dict]]:
    """Avisos de piezas que el módulo puede despegar de la cama.

    Mismo contrato que :func:`height_problems`: ``[(clave i18n, parámetros)]``,
    claves y no textos, y **lista vacía cuando falta un dato**. Sin huellas
    medidas (un G-code que no deja verlas) o sin Z de pausa no se avisa de nada.

    Cada imán se apunta a la pieza sobre la que cae (:func:`footprint_at`) y de
    cada pieza manda **su imán más fuerte**: es el que la despegaría. Un imán que
    no caiga sobre ninguna huella se ignora, que es el caso del que se coloca en
    el aire de un puente o el de una detección que se ha ido de sitio.

    Los avisos salen de peor a mejor margen, para que el primero de la lista sea
    el que hay que arreglar.
    """
    if not footprints or not points or pause_z is None or pause_z <= 0.0:
        return []

    # La fuerza de cada pieza es la del imán más bruto que lleva encima.
    por_pieza: Dict[int, float] = {}
    indice = {id(f): i for i, f in enumerate(footprints)}
    for p in points:
        huella = footprint_mod.footprint_at(footprints, float(p[0]), float(p[1]))
        if huella is None:
            continue
        fuerza = _force_for(p, forces)
        if fuerza <= 0.0:
            continue
        clave = indice[id(huella)]
        por_pieza[clave] = max(por_pieza.get(clave, 0.0), fuerza)

    avisos: List[Tuple[float, str, dict]] = []
    for i, fuerza in por_pieza.items():
        huella = footprints[i]
        aguante = adhesion.max_lateral_force(
            huella.area, huella.modulus(), float(pause_z), material
        )
        margen = adhesion.safety_factor(aguante.limit, fuerza)
        if margen >= float(factor):
            continue
        clave = (
            "adhesion.tipping" if aguante.mode == adhesion.MODE_TIPPING
            else "adhesion.sliding"
        )
        avisos.append((margen, clave, {
            "force": f"{fuerza:.1f}",
            "limit": f"{aguante.limit:.1f}",
            "margin": f"{margen:.1f}",
            "z": f"{float(pause_z):.1f}",
            "base": f"{min(huella.width, huella.depth):.0f}",
            "area": f"{huella.area:.0f}",
        }))

    avisos.sort(key=lambda a: a[0])
    return [(clave, params) for _margen, clave, params in avisos]
