"""Configuración editable de la aplicación.

Centraliza todos los parámetros numéricos y las secuencias G-code que antes
vivían en ``gcode_magnets/config.py``, de forma que el usuario pueda editarlos
desde la interfaz sin tocar el código. Las secuencias se guardan como texto
multilínea; cada línea puede contener expresiones entre llaves (``{z+0.4}``,
``{safe_z}``, ``{temp}``, ``{fan}``, ``{deretract}``) que se evalúan en el
momento de generar el G-code.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Tuple

from . import magnetics
from gcode_magnets import adhesion, fit

# --- Secuencias por defecto (equivalentes a gcode_magnets/config.py) ----------

DEFAULT_SEQ_RED = """\
G1 Z184 F1200
G1 X203 Y128 F3000
G1 X240 F600
G1 Z179 F1200
G1 X203 F120
M400"""

DEFAULT_SEQ_BLUE = """\
G1 Z193 F1200
G1 X203 Y128 F3000
G1 X264 F600
G1 Z188 F1200
G1 X238 F120
G1 X203 F600
G1 Z179 F1200
M400"""

# Secuencia de inicio (una vez). Usa {z+0.4} y {safe_z} (= z + safe_z_offset).
DEFAULT_SEQ_START = """\
G1 E-.04 F1800
M400
M204 S30000
G1 E-1 F1800
G1 Z {z+0.4} F1200
G1 X-48 F12000
M106 P1 S178
M109 S160
M106 P1 S0
G1 X-28.5 F12000
G1 X-48.2 F3000
G1 X-28.5 F12000
G1 X-48.2 F3000
M204 S6000
G1 Z {safe_z} F1200
G1 X-48 F6000
M17
G90
G1 X185.8 Y128 F6000
G1 Z180 F1200
G1 Z242 F600
G1 Z180 F1200
M400"""

DEFAULT_SEQ_END = """\
G1 Z170 F1200
G1 X185.8 Y128 F6000
G1 Z238 F600
G1 Z170 F1200
M400"""

# Valores de reserva para {fan} y {deretract} cuando no se pueden leer del
# G-code de entrada, o cuando se genera la secuencia de prueba, que no parte de
# ningún archivo. 178 ≈ 70 %, que es lo que la secuencia fijaba a ciegas antes;
# 0.8 mm es la retracción típica de un perfil de Bambu Studio.
FALLBACK_FAN = 178.0
FALLBACK_DERETRACT = 0.8

# Secuencia final (reanudar impresión). Usa {z+0.6}, {temp}, {fan} y {deretract}.
#
# Tres detalles que parecen menores y se notan al tacto en la capa de la pausa:
#   · Se purga a {temp}, no a 240: 'M109 S' solo espera cuando hay que CALENTAR,
#     así que tras un pico a 240 la impresión se reanudaba 20 °C caliente y el
#     cordón salía ancho y descolgado.
#   · El ventilador vuelve a {fan}, el valor que traía el perfil antes de parar,
#     en vez de quedarse a ciegas al 70 % durante toda esa capa.
#   · Se retrae {deretract}, exactamente lo que el laminador va a cebar al
#     reanudar: tras la purga la boquilla está llena, y ese cebado se sumaba
#     entero como material de más justo en la pared exterior.
# Y se sale en X antes de bajar en Z, para no cruzar por encima de la pieza (y de
# los imanes recién puestos) a 0.4 mm de la última capa.
DEFAULT_SEQ_FINAL = """\
G1 X-48 F6000
G1 Z {z+0.6} F1200
M400
M106 P1 S0
M109 S{temp} H300
G92 E0
G1 E30 F200
M400
M106 P1 S{fan}
G92 E0
G1 E10 F200
G92 E0
G1 E-{deretract} F300
G1 X-28.5 F15000
G1 X-48.2 F3000
G1 X-28.5 F15000
G1 X-48.2 F3000
G1 X-28.5 F15000
G1 X-48.2 F3000
G1 X1 F15000
G92 E0
M83"""


_EXPR_RE = re.compile(r"\{([^{}]+)\}")
_SAFE_GLOBALS = {"__builtins__": {}, "math": math}


def _fmt(value) -> str:
    """Formatea floats a 3 decimales sin ceros sobrantes; deja enteros tal cual."""
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def render_line(line: str, ctx: Dict[str, float]) -> str:
    """Sustituye las expresiones ``{...}`` de una línea usando ``ctx``.

    Las expresiones se evalúan en un entorno restringido (solo ``math`` y las
    variables de ``ctx``: ``z``, ``safe_z``, ``temp``...). Si una expresión
    falla se deja tal cual para que el usuario vea el error en la vista previa.
    """

    def repl(match: re.Match) -> str:
        expr = match.group(1)
        try:
            value = eval(expr, _SAFE_GLOBALS, ctx)  # noqa: S307 - entorno restringido
        except Exception:
            return match.group(0)
        return _fmt(value)

    return _EXPR_RE.sub(repl, line)


def render_sequence(text: str, ctx: Dict[str, float]) -> List[str]:
    """Convierte el texto multilínea de una secuencia en líneas renderizadas.

    Se ignoran las líneas vacías. Cada línea se procesa con :func:`render_line`.
    """
    lines: List[str] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        lines.append(render_line(stripped, ctx))
    return lines


# Medidas admitidas para un imán, en mm. Son listas cerradas a propósito: el
# mecanismo de recogida está hecho para estos formatos, así que la interfaz
# ofrece justo estos valores y no un campo libre.
MAGNET_DIAMETERS = (3.0, 4.0, 5.0, 6.0, 7.0, 8.0)
MAGNET_HEIGHTS = (2.0, 3.0, 4.0, 5.0)

# Tope de altura para los imanes anchos. Un ⌀7 o un ⌀8 más alto de 3 mm no lo
# admite el mecanismo de recogida: el disco se atraviesa en el dispensador. No es
# una preferencia sino un límite del módulo, así que la interfaz ni siquiera
# ofrece esas alturas y un proyecto guardado con ellas se corrige al abrirlo.
WIDE_MAGNET_DIAMETER = 7.0     # de aquí para arriba manda el tope
WIDE_MAGNET_MAX_HEIGHT = 3.0


def max_height_for(diameter: float) -> float:
    """Altura máxima admitida para un imán de ese diámetro, en mm."""
    try:
        d = float(diameter)
    except (TypeError, ValueError):
        return max(MAGNET_HEIGHTS)
    if d >= WIDE_MAGNET_DIAMETER:
        return WIDE_MAGNET_MAX_HEIGHT
    return max(MAGNET_HEIGHTS)


def allowed_heights(diameter: float) -> tuple:
    """Alturas que se pueden elegir con ese diámetro (nunca vacío)."""
    tope = max_height_for(diameter)
    validas = tuple(h for h in MAGNET_HEIGHTS if h <= tope)
    return validas or (min(MAGNET_HEIGHTS),)


def clamp_height(diameter: float, height: float) -> float:
    """Baja la altura al tope de ese diámetro si se ha pasado."""
    validas = allowed_heights(diameter)
    try:
        h = float(height)
    except (TypeError, ValueError):
        return max(validas)
    return h if h <= max(validas) else max(validas)

# Un módulo por color: cada color es un dispensador distinto de la máquina, así
# que no puede haber dos módulos del mismo (ver :data:`MAX_MODULES`).
MAGNET_COLORS = ("red", "blue")

# Polo que queda hacia arriba, o sea el sentido en que atrae el imán ya puesto.
MAGNET_POLARITIES = ("N", "S")

# Grados comerciales admitidos. La lista sale de `adhesion.GRADES` para que no
# haya dos sitios que decir cuáles hay; el orden es de menos a más potente.
MAGNET_GRADES = tuple(sorted(adhesion.GRADES, key=lambda g: adhesion.GRADES[g]))

# Materiales con adherencia tabulada, para el desplegable de la interfaz.
BED_MATERIALS = tuple(adhesion.BED_ADHESION)

MAX_MODULES = len(MAGNET_COLORS)

# Versión del formato de :class:`Settings`. Se sube cuando hay que arreglar
# ajustes ya guardados; ver :meth:`Settings.from_dict`.
#   1 -> 2: de fábrica solo existía el dispensador rojo.
#   2 -> 3: los imanes no tenían grado ni atracción de catálogo, que es lo que
#           mide el empujón lateral contra la pieza (`gcode_magnets.adhesion`).
SETTINGS_VERSION = 3

# Medidas del imán con el que se crea un módulo nuevo.
DEFAULT_MODULE_DIAMETER = 6.0
DEFAULT_MODULE_HEIGHT = 3.0


def _closest(value, options, default):
    """Ajusta un valor a la opción admitida más cercana."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    return min(options, key=lambda o: abs(o - v))


@dataclass
class MagnetModule:
    """Un tipo de imán: color del dispensador, medidas y polaridad."""

    # Vacío = sin nombre propio: la interfaz muestra el automático traducido.
    name: str = ""
    diameter: float = 6.0
    height: float = 3.0
    color: str = "red"
    polarity: str = "N"

    # Grado del neodimio. De él sale la atracción entre dos imanes pegados, y de
    # ahí la cizalla que el módulo le hace a la pieza al retirarse.
    grade: str = adhesion.DEFAULT_GRADE

    # Atracción de catálogo en kg, para quien no sabe el grado pero sí lo que
    # pone la caja. 0 = no se sabe, se deduce del grado.
    pull_kg: float = 0.0

    def __post_init__(self) -> None:
        # El tope de los imanes anchos se aplica aquí y no sólo en la interfaz:
        # un módulo también se construye desde un proyecto, desde la CLI o desde
        # un test, y ninguno de esos caminos pasa por la tarjeta.
        self.height = clamp_height(self.diameter, self.height)

    def to_dict(self) -> dict:
        return {
            "name": self.name, "diameter": self.diameter, "height": self.height,
            "color": self.color, "polarity": self.polarity,
            "grade": self.grade, "pull_kg": self.pull_kg,
        }

    def lateral_force(self) -> float:
        """Empujón lateral que este imán le hace a la pieza, en N.

        Es la fuerza de cizalla contra el imán que el módulo lleva dentro, que es
        del mismo formato (ver :func:`~gcode_magnets.magnetics.module_travel`).
        """
        return adhesion.lateral_force(
            self.diameter, self.height, self.grade, self.pull_kg
        )

    @classmethod
    def from_dict(cls, d: dict) -> "MagnetModule":
        # Los valores se ajustan a los admitidos: un proyecto guardado antes de
        # cerrar las listas puede traer un diámetro de 10 mm, y vale más
        # acercarlo al formato más parecido que rechazar el archivo.
        color = str(d.get("color", "red")).lower()
        polarity = str(d.get("polarity", "N")).upper()
        grade = str(d.get("grade", adhesion.DEFAULT_GRADE) or "").upper()
        try:
            pull_kg = max(float(d.get("pull_kg", 0.0) or 0.0), 0.0)
        except (TypeError, ValueError):
            pull_kg = 0.0
        return cls(
            name=str(d.get("name", "") or ""),
            diameter=_closest(d.get("diameter"), MAGNET_DIAMETERS, 6.0),
            height=_closest(d.get("height"), MAGNET_HEIGHTS, 3.0),
            color=color if color in MAGNET_COLORS else "red",
            polarity=polarity if polarity in MAGNET_POLARITIES else "N",
            # Un módulo guardado antes de la versión 3 no trae grado: entra con
            # el de fábrica, que es el imán más potente y por tanto el caso
            # prudente para el aviso.
            grade=grade if grade in MAGNET_GRADES else adhesion.DEFAULT_GRADE,
            pull_kg=pull_kg,
        )


def _complete_dispensers(modules: List[MagnetModule]) -> List[MagnetModule]:
    """Añade los módulos que falten para que ningún dispensador quede vacío."""
    definidos = {m.color for m in modules}
    completo = list(modules)
    for color in MAGNET_COLORS:
        if color not in definidos:
            completo.append(MagnetModule(
                name="", diameter=DEFAULT_MODULE_DIAMETER,
                height=DEFAULT_MODULE_HEIGHT, color=color,
            ))
    return completo[:MAX_MODULES]


def default_modules() -> List[MagnetModule]:
    """Un módulo por dispensador, con el imán estándar."""
    return [
        MagnetModule(name="", diameter=DEFAULT_MODULE_DIAMETER,
                     height=DEFAULT_MODULE_HEIGHT, color=color)
        for color in MAGNET_COLORS
    ]


@dataclass
class Settings:
    """Todos los parámetros editables de la generación de imanes."""

    pause_token: str = "M400 U1"
    offset_x: float = -55.4
    offset_y: float = 32.0
    offset_z: float = 8.0
    safe_z_offset: float = 30.0
    travel_feed: float = 1200.0
    default_temp: float = 220.0
    features: List[str] = field(default_factory=lambda: ["Inner wall", "Outer wall"])

    # Versión del formato guardado, para migrar ajustes de sesiones antiguas.
    version: int = SETTINGS_VERSION

    # Módulos de imán: uno por color de dispensador (rojo y azul). De fábrica
    # vienen los dos definidos, que es la máquina completa: así los dos
    # depósitos se ven llenos en el visor y se puede colocar de ambos colores
    # sin pasar antes por la pestaña Módulos.
    # El nombre va vacío a propósito: la tarjeta muestra el automático
    # ("Magnet 1" / "Imán 1"...) en el idioma que esté activo.
    modules: List[MagnetModule] = field(default_factory=lambda: default_modules())

    # Material con el que se imprime, para saber cuánto agarra la pieza a la
    # cama. Es solo la **reserva**: si el G-code lo dice, manda el archivo.
    bed_material: str = adhesion.DEFAULT_MATERIAL

    # Margen exigido entre lo que aguanta la pieza y lo que el módulo le empuja.
    safety_factor: float = adhesion.DEFAULT_SAFETY_FACTOR

    # Detección de agujeros (centros de círculos) por contornos.
    hole_detection_enabled: bool = True
    hole_r_min: float = 1.5      # radio mínimo del agujero (mm)
    hole_r_max: float = 20.0     # radio máximo del agujero (mm)
    hole_circularity: float = 0.12  # desviación radial relativa máxima (0 = círculo perfecto)
    hole_cluster_dist: float = 2.0  # fusiona paredes concéntricas (mm)
    hole_min_arc: float = 30.0      # grados que el contorno debe rodear al centro
    # Buscar sólo los agujeros del tamaño de los imanes definidos en Módulos,
    # en vez del intervalo de radios de arriba. Es lo normal: el usuario ya ha
    # dicho qué imán coloca, así que un agujero de otro diámetro no es suyo.
    hole_match_modules: bool = True
    # Margen del diámetro buscado, en mm (±). Ancho a propósito: el agujero no
    # se diseña de la medida del imán sino con holgura para que entre, y el
    # laminador se come otra décima. En el archivo de prueba, imanes de 6 mm
    # viven en agujeros de 5,6, así que con ±0,5 la detección iba al límite.
    hole_diameter_tol: float = 0.8

    # Holgura radial (mm) a partir de la cual el imán entra en su agujero (ver
    # :mod:`gcode_magnets.fit`); por debajo, puede que no quepa. Se toca en los
    # parámetros avanzados porque el punto en que un ajuste pasa de "apretado" a
    # "no entra" depende de la impresora y del material, no del imán.
    fit_very_tight: float = fit.DEFAULT_VERY_TIGHT
    # Altura sobre la placa (mm) a partir de la cual un imán que entra en su
    # agujero puede irse pegado al cabezal (ver `gcode_magnets.fit.may_stick_to_toolhead`).
    # Es la ``h`` del eje de la gráfica de separación mínima: ``Z_pausa`` menos
    # la altura del imán, no lo alto que es el imán.
    fit_high_gap: float = fit.DEFAULT_HIGH_GAP

    seq_red: str = DEFAULT_SEQ_RED
    seq_blue: str = DEFAULT_SEQ_BLUE
    seq_start: str = DEFAULT_SEQ_START
    seq_end: str = DEFAULT_SEQ_END
    seq_final: str = DEFAULT_SEQ_FINAL

    def color_sequence_text(self, color: str) -> str:
        return self.seq_blue if color.lower() == "blue" else self.seq_red

    # --- consultas sobre los módulos ---------------------------------------
    def module_for_color(self, color: str) -> "MagnetModule | None":
        """El módulo definido para ese color de dispensador, si existe."""
        wanted = (color or "").lower()
        for m in self.modules:
            if m.color == wanted:
                return m
        return None

    def available_colors(self) -> List[str]:
        """Colores con módulo definido, en el orden de :data:`MAGNET_COLORS`."""
        defined = {m.color for m in self.modules}
        return [c for c in MAGNET_COLORS if c in defined]

    def magnet_sizes(self) -> Dict[str, tuple]:
        """``{color: (diámetro, altura)}`` para dibujar cada imán a su tamaño."""
        return {m.color: (m.diameter, m.height) for m in self.modules}

    def detection_diameters(self) -> List[float]:
        """Diámetros de imán que la detección debe buscar, en mm.

        Vacío cuando el filtro está apagado o cuando no hay ningún módulo con
        medidas: en ese caso la detección vuelve al intervalo de radios, que es
        lo que había antes de que existiera este filtro.
        """
        if not self.hole_match_modules:
            return []
        return sorted({round(m.diameter, 3) for m in self.modules if m.diameter > 0})

    def fit_level(self, hole_diameter: float, magnet_diameter: float) -> str:
        """Si ese imán entra en ese agujero (ver :mod:`gcode_magnets.fit`)."""
        return fit.classify(
            fit.radial_clearance(hole_diameter, magnet_diameter),
            self.fit_very_tight,
        )

    def magnet_may_stick(self, level: str, plate_gap: float) -> bool:
        """Si ese imán puede irse con el cabezal (ver :mod:`gcode_magnets.fit`).

        ``plate_gap`` es lo alto que queda el imán sobre la placa, no lo alto
        que es el imán: :func:`~gcode_magnets.magnetics.magnet_gap`.
        """
        return fit.may_stick_to_toolhead(level, plate_gap, self.fit_high_gap)

    def lateral_forces(self) -> Dict[str, float]:
        """``{color: fuerza lateral en N}`` que cada dispensador le hace a la pieza."""
        return {m.color: m.lateral_force() for m in self.modules}

    def worst_lateral_force(self) -> float:
        """La mayor fuerza lateral de todos los módulos, en N.

        Es con la que se avisa cuando no se sabe de qué color es un imán, igual
        que :meth:`worst_case_magnet` hace con las medidas.
        """
        fuerzas = [m.lateral_force() for m in self.modules]
        return max(fuerzas) if fuerzas else 0.0

    def worst_case_magnet(self) -> Tuple[float, float]:
        """``(diámetro, altura)`` del imán más exigente de los módulos, en mm.

        Hoy cada dispensador tiene su propia separación mínima, con el diámetro y
        la altura de **su** imán (:meth:`magnet_sizes`), así que esto ha quedado
        para dos cosas: resumir la placa en un solo número y hacer de reserva
        cuando no se sabe de qué color es un imán. Y el peor caso no es el mismo
        imán por los dos lados:

        * el **más bajo** manda en la altura, porque cuanto menos alto es, más
          lejos de la placa queda su cara inferior (``h = Z_pausa − altura``),
          menos lo sujeta el PEI y más separación hace falta;
        * el **más ancho** manda en el diámetro, porque es el que más sitio ocupa
          y peor gira dentro de su agujero.

        Sin módulos definidos se usa el disco con el que está calibrado el modelo
        (:data:`~gcode_magnets.magnetics.MODEL_MAGNET`), un 6 × 5. Lo usan por
        igual el aviso de la interfaz y la
        retirada del colocador en el G-code, para que los dos digan lo mismo.
        """
        diametros = [m.diameter for m in self.modules if m.diameter > 0]
        alturas = [m.height for m in self.modules if m.height > 0]
        return (
            max(diametros) if diametros else magnetics.MODEL_MAGNET[0],
            min(alturas) if alturas else magnetics.MODEL_MAGNET[1],
        )

    # --- serialización -----------------------------------------------------
    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        known = {f for f in cls().__dict__}
        clean = {k: v for k, v in data.items() if k in known}
        if isinstance(clean.get("modules"), list):
            clean["modules"] = [
                MagnetModule.from_dict(m) if isinstance(m, dict) else m
                for m in clean["modules"]
            ]
            if int(data.get("version", 1) or 1) < 2:
                # Ajustes guardados cuando de fábrica solo había dispensador
                # rojo: el azul faltaba sin que el usuario lo hubiera quitado,
                # así que se completa (una sola vez, al subir de versión).
                clean["modules"] = _complete_dispensers(clean["modules"])
        # Ajustes de antes de la versión 3: no traían material ni margen, y los
        # valores por defecto del dataclass ya son los buenos. Lo que sí puede
        # llegar torcido es un archivo editado a mano.
        material = str(clean.get("bed_material", adhesion.DEFAULT_MATERIAL) or "")
        clean["bed_material"] = (
            material.upper() if material.upper() in BED_MATERIALS
            else adhesion.DEFAULT_MATERIAL
        )
        try:
            factor = float(clean.get("safety_factor", adhesion.DEFAULT_SAFETY_FACTOR))
        except (TypeError, ValueError):
            factor = adhesion.DEFAULT_SAFETY_FACTOR
        # Un margen por debajo de 1 sería pedir que la pieza falle; se ignora.
        clean["safety_factor"] = factor if factor >= 1.0 else adhesion.DEFAULT_SAFETY_FACTOR
        clean["version"] = SETTINGS_VERSION
        return cls(**clean)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str) -> "Settings":
        return cls.from_dict(json.loads(text))
