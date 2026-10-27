# -*- coding: utf-8 -*-
"""Cuánta fuerza lateral aguanta la pieza antes de despegarse de la cama.

Al retirarse, el módulo MagnetPlace se lleva su propio imán pegado cara con cara
al que acaba de soltar (:func:`~gcode_magnets.magnetics.module_travel`). Para
separarlos no hay que vencer la atracción **axial** —el módulo no tira hacia
arriba— sino la **cizalla**: lo que cuesta deslizar un imán sobre el otro. Esa
fuerza la sufre la pieza como un empujón lateral, y no la sufre en la base sino
**a la altura de la capa de la pausa**, que es donde está el agujero del imán.

La cizalla está **medida con dinamómetro**, no sacada de una tabla: un disco N35
de ⌀8 × 5 pide 15 N (:data:`MEASURED_SHEAR`). Es mucho más de lo que suponía el
modelo de rozamiento que había aquí antes —seis veces más—, y por eso el aviso
salta bastante más a menudo de lo que saltaba. Los demás formatos salen de esa
medida escalada por la física; el porqué del salto está en :data:`SHEAR_RATIO`.

Ahí es donde el brazo de palanca lo cambia todo. La pieza puede fallar de dos
maneras y **el límite es el menor de los dos**:

* **Deslizamiento**: la huella entera cede a cortante, ``F ≤ τ·A``. No depende de
  la altura y casi nunca es el que manda.
* **Vuelco**: la pieza gira sobre el borde de delante y la adherencia se pela por
  el borde de atrás, ``F·h ≤ σ·W``. Cae como ``1/h`` y crece con el **cuadrado**
  de la anchura de la base, así que en una pieza alta y estrecha es el que manda
  con mucha diferencia.

``W = I/c`` es el módulo resistente de la huella (lo pone
:mod:`gcode_magnets.footprint`): reparto lineal de tensiones con el eje neutro en
el centroide, que es el modelo de una zapata y el conservador para el **inicio**
del despegue. Suponer que toda la huella se despega a la vez daría un número
mayor y más bonito, y describiría un fallo que no es el que ocurre.

**No se cuenta el peso de la pieza.** Ayudaría —su momento se opone al vuelco—
pero exige inventarse una masa a partir del filamento extruido, y dejarlo fuera
es el caso pesimista.

Los números de :data:`BED_ADHESION` son **de tabla, no medidos**: valen para
ordenar decisiones y para saber si un caso va sobrado o pelado, no como
certificado. La banda real anda por el ±50 %, y por eso lo que se compara no es
``F < F_max`` sino un factor de seguridad de :data:`DEFAULT_SAFETY_FACTOR`.

Como :mod:`gcode_magnets.magnetics`, aquí no se importa Qt: son cuentas puras.
"""
from __future__ import annotations

import math
from typing import Dict, NamedTuple, Optional

from . import magnetics

__all__ = [
    "MU0", "GRAVITY", "GRADES", "DEFAULT_GRADE", "PULL_CALIBRATION",
    "MEASURED_MAGNET", "MEASURED_SHEAR",
    "SHEAR_RATIO", "BED_ADHESION", "DEFAULT_MATERIAL", "DEFAULT_SAFETY_FACTOR",
    "MODE_SLIDING", "MODE_TIPPING",
    "BedAdhesion", "Strength",
    "grade_remanence", "raw_pull_force", "pull_force", "pull_force_from_kg",
    "shear_force", "lateral_force",
    "bed_adhesion", "sliding_limit", "tipping_limit", "max_lateral_force",
    "safety_factor",
]

MU0 = 4.0e-7 * math.pi          # permeabilidad del vacío, en H/m
GRAVITY = 9.80665               # m/s²: para pasar de kg de catálogo a newtons

# --- el imán ------------------------------------------------------------------
# Remanencia Br en teslas por grado comercial. Son el centro de la horquilla que
# dan los fabricantes (N52 se vende entre 1.42 y 1.47), no un máximo.
GRADES: Dict[str, float] = {"N35": 1.19, "N45": 1.34, "N52": 1.45}
DEFAULT_GRADE = "N52"


def grade_remanence(grade: Optional[str]) -> float:
    """Br del grado, en teslas. Un grado desconocido cae en :data:`DEFAULT_GRADE`."""
    return GRADES.get(str(grade or "").upper().strip(), GRADES[DEFAULT_GRADE])


def raw_pull_force(diameter: float, height: float, br: float) -> float:
    """Atracción en contacto **sin calibrar**, en N. Solo para :data:`PULL_CALIBRATION`.

    Modelo de carga superficial para un disco: ``F = A·B²/(2·μ₀)`` con el campo
    en la cara ``B = Br/2 · L/√(R²+L²)``. Es la forma correcta —dice bien cómo
    escala con el diámetro, con la altura y con el grado— pero se queda corta en
    valor absoluto para discos cortos, de ahí la calibración de abajo.
    """
    r = max(float(diameter), 0.0) / 2000.0      # mm → m
    l = max(float(height), 0.0) / 1000.0
    if r <= 0.0 or l <= 0.0:
        return 0.0
    b = (float(br) / 2.0) * (l / math.hypot(r, l))
    return (math.pi * r * r) * b * b / (2.0 * MU0)


# La fórmula de arriba da 4.35 N para el disco con el que está calibrado todo el
# proyecto (un ⌀6×5 N52, :data:`~gcode_magnets.magnetics.MODEL_MAGNET`), y ese
# mismo disco vale 12 N en :data:`~gcode_magnets.magnetics.F0_MAGNET`, que es el
# número contra el que están hechas las separaciones mínimas y los catálogos.
# Esta constante (≈2.76) es lo que ata las dos cosas. Se calcula en vez de
# escribirse para que siga cuadrando si algún día se retoca `F0_MAGNET`.
PULL_CALIBRATION = magnetics.F0_MAGNET / raw_pull_force(
    magnetics.MODEL_MAGNET[0], magnetics.MODEL_MAGNET[1], GRADES[DEFAULT_GRADE]
)

def pull_force(
    diameter: float, height: float, grade: str = DEFAULT_GRADE
) -> float:
    """Atracción entre dos imanes iguales pegados cara con cara, en N."""
    return PULL_CALIBRATION * raw_pull_force(diameter, height, grade_remanence(grade))


# --- la cizalla, medida ------------------------------------------------------
# Disco con el que se midió, y lo que costó separarlo del otro deslizándolo:
# (diámetro, altura, grado) y newtons.
MEASURED_MAGNET = (8.0, 5.0, "N35")
MEASURED_SHEAR = 15.0

# Fracción de la atracción que cuesta deslizar un imán sobre otro. **Sale de la
# medida de arriba**, no de una tabla, y por eso se calcula en vez de escribirse:
# así el disco medido devuelve exactamente sus 15 N y todos los demás formatos se
# mueven con él por la física (va con Br², con el área y con la esbeltez del
# disco), que es lo único que se puede hacer con una sola medida.
#
# Da ≈1.26, y eso son **seis veces** el 0.20 que decían las tablas de rozamiento
# entre caras niqueladas, que es lo que había aquí antes. La diferencia no es
# ruido de medida, es que el 0.20 describía otro fenómeno: para sacar un imán de
# encima de otro no basta con vencer el rozamiento, hay que sacarlo de su
# alineación magnética, y esa fuerza de recentrado es la que manda. Que el número
# pase de 1 dice además que :func:`pull_force` se queda corta en los discos
# anchos, cosa que :mod:`gcode_magnets.magnetics` ya avisaba de su modelo: está
# calibrado con un ⌀6 y "un disco más ancho tira más que el calibrado".
#
# Con una sola medida no se puede separar una cosa de la otra, así que las dos
# se van juntas en esta constante. Midiendo un segundo disco de diámetro muy
# distinto —un ⌀3, por ejemplo— se sabría cuánta culpa tiene cada una.
SHEAR_RATIO = MEASURED_SHEAR / pull_force(*MEASURED_MAGNET)


def pull_force_from_kg(kg: float) -> float:
    """Pasa a newtons la atracción que viene en kg en los catálogos."""
    return max(float(kg), 0.0) * GRAVITY


def shear_force(pull: float) -> float:
    """Fuerza para deslizar un imán sobre otro, en N: la fracción de la atracción."""
    return SHEAR_RATIO * max(float(pull), 0.0)


def lateral_force(
    diameter: float,
    height: float,
    grade: str = DEFAULT_GRADE,
    pull_kg: float = 0.0,
) -> float:
    """Empujón lateral que el módulo aplica a la pieza al retirarse, en N.

    ``pull_kg`` es la salida de escape para quien no sabe de qué grado es su
    imán pero sí lo que pone en la caja: si viene un valor positivo **manda
    sobre el grado**, porque un dato del fabricante vale más que la fórmula.
    """
    kg = max(float(pull_kg or 0.0), 0.0)
    pull = pull_force_from_kg(kg) if kg > 0.0 else pull_force(diameter, height, grade)
    return shear_force(pull)


# --- la pieza contra la cama --------------------------------------------------
class BedAdhesion(NamedTuple):
    """Tensiones de adherencia de un material sobre la cama, en N/mm².

    ``peel`` es a tracción, que es lo que resiste el vuelco, y ``slide`` a
    cortante, que es lo que resiste el deslizamiento. La segunda es siempre
    varias veces la primera: despegar por un borde es mucho más fácil que
    arrancar de plano.
    """

    peel: float
    slide: float


# Sobre PEI a la temperatura de cama habitual de cada material. Valores de tabla
# con una banda del ±50 %; ver el aviso del docstring del módulo.
BED_ADHESION: Dict[str, BedAdhesion] = {
    "PLA": BedAdhesion(0.15, 0.50),
    "PETG": BedAdhesion(0.25, 0.80),
    "ABS": BedAdhesion(0.10, 0.35),
    "ASA": BedAdhesion(0.10, 0.35),
    "TPU": BedAdhesion(0.20, 0.60),
}
DEFAULT_MATERIAL = "PLA"

# Por debajo de este margen se avisa. No es prudencia de más: las tensiones de
# arriba son estimaciones, y una cama con dedazos agarra la mitad.
DEFAULT_SAFETY_FACTOR = 2.0

MODE_SLIDING = "sliding"    # la huella cede a cortante
MODE_TIPPING = "tipping"    # la pieza vuelca sobre su borde


def bed_adhesion(material: Optional[str]) -> BedAdhesion:
    """Tensiones del material. Uno desconocido cae en :data:`DEFAULT_MATERIAL`.

    Se admite lo que escriben los laminadores en la cabecera del G-code, que no
    es el nombre pelado: de ``PLA Basic``, ``Generic PETG`` o ``pla-cf`` sale la
    familia buscando cuál de las conocidas aparece dentro.
    """
    name = str(material or "").upper()
    if name.strip() in BED_ADHESION:
        return BED_ADHESION[name.strip()]
    for key in BED_ADHESION:
        if key in name:
            return BED_ADHESION[key]
    return BED_ADHESION[DEFAULT_MATERIAL]


class Strength(NamedTuple):
    """Lo que aguanta una pieza, en N, y por dónde se rompe.

    ``limit`` es el menor de ``sliding`` y ``tipping``, y ``mode`` dice cuál de
    los dos manda (:data:`MODE_SLIDING` o :data:`MODE_TIPPING`).
    """

    sliding: float
    tipping: float
    limit: float
    mode: str


def sliding_limit(area: float, slide: float) -> float:
    """Fuerza lateral que la huella aguanta a cortante, en N: ``τ·A``."""
    return max(float(area), 0.0) * max(float(slide), 0.0)


def tipping_limit(modulus: float, peel: float, height: float) -> float:
    """Fuerza lateral que la pieza aguanta sin volcar, en N: ``σ·W/h``.

    Con ``height`` a cero (o negativa) no hay brazo de palanca y no se puede
    volcar: devuelve infinito, y entonces el que manda es el deslizamiento.
    """
    h = float(height)
    if h <= 0.0:
        return math.inf
    return max(float(modulus), 0.0) * max(float(peel), 0.0) / h


def max_lateral_force(
    area: float,
    modulus: float,
    height: float,
    material: Optional[str] = DEFAULT_MATERIAL,
) -> Strength:
    """Lo que aguanta la pieza a ``height`` mm de la cama, en N.

    ``area`` y ``modulus`` describen la huella (:mod:`gcode_magnets.footprint`);
    ``height`` es la Z de la capa de la pausa, que es donde se aplica la fuerza.

    El empate se resuelve a favor del vuelco: es el fallo que de verdad se ve.
    """
    tabla = bed_adhesion(material)
    desliza = sliding_limit(area, tabla.slide)
    vuelca = tipping_limit(modulus, tabla.peel, height)
    if vuelca <= desliza:
        return Strength(desliza, vuelca, vuelca, MODE_TIPPING)
    return Strength(desliza, vuelca, desliza, MODE_SLIDING)


def safety_factor(limit: float, force: float) -> float:
    """Cuántas veces cabe la fuerza aplicada en la que aguanta la pieza.

    Sin fuerza aplicada no hay nada de qué preocuparse: infinito.
    """
    f = max(float(force), 0.0)
    if f <= 0.0:
        return math.inf
    return max(float(limit), 0.0) / f
