"""Cómo de apretado queda un imán dentro de su agujero.

El agujero se mide del propio G-code (ver
:func:`gcode_magnets.analysis.measure_circles`, que descuenta el ancho del
cordón para dar el hueco libre de verdad) y el imán lo dice su módulo. La
diferencia entre los dos, **repartida a los dos lados**, es la holgura con la
que el imán entra:

    holgura = (Ø agujero − Ø imán) / 2

Es radial a propósito: un agujero de 5,6 con un imán de 5 tiene 0,6 mm de
diferencia de diámetro, pero el imán sólo puede moverse 0,3 mm hacia cada lado,
y es esa décima la que se nota con los dedos al meterlo.

Sólo hay un corte, el de «muy apretado»: por encima el imán entra, por debajo
puede que no. Lo apretado que entre no cuenta para nada más —ni para la
distancia mínima ni para el aviso del cabezal—, porque el rozamiento con la
pared depende de cómo imprima cada máquina y no se puede dar por hecho. El corte
se cambia en los parámetros avanzados.
"""

# Grados de ajuste.
FITS = "fits"                # entra
BARELY = "barely"            # puede que no quepa
TOO_BIG = "too_big"          # no cabe: el imán es más gordo que el agujero

# Holgura radial mínima (mm) para dar por hecho que el imán entra.
DEFAULT_VERY_TIGHT = 0.10

# Los dos grados que se avisan antes de generar: el imán se quedaría fuera y la
# impresión se echaría a perder.
WARNING_LEVELS = (BARELY, TOO_BIG)

# El corte pertenece al grado de arriba ("entra desde 0,10"), y eso hay que
# defenderlo del binario: un imán de 5 en un agujero de 5,6 da 0,29999999999998
# de holgura, que sin este margen caería del lado equivocado del 0,3 que el
# usuario acaba de teclear. Es ruido de coma flotante, muy por debajo de lo que
# nadie puede imprimir ni medir.
_EPS = 1e-9


def radial_clearance(hole_diameter: float, magnet_diameter: float) -> float:
    """Holgura por lado entre el imán y la pared del agujero, en mm.

    Negativa cuando el imán es más gordo que el hueco: entonces no entra, y
    cuánto le sobra es justo ese número cambiado de signo.
    """
    return (float(hole_diameter) - float(magnet_diameter)) / 2.0


def classify(clearance: float, very_tight: float = DEFAULT_VERY_TIGHT) -> str:
    """Grado de ajuste de una holgura radial (ver las constantes del módulo)."""
    if clearance < -_EPS:
        return TOO_BIG
    if clearance < float(very_tight) - _EPS:
        return BARELY
    return FITS


def is_warning(level: str) -> bool:
    """True si el grado merece parar y preguntar antes de generar el G-code."""
    return level in WARNING_LEVELS


# --- el imán que se va con el cabezal -----------------------------------------
#
# Sin contar con el rozamiento contra la pared, a un imán en su agujero no lo
# sujeta nada más que la placa PEI tirando de él desde abajo, y esa fuerza se
# desploma con la distancia (:func:`pei_force`):
# es la misma ``h`` del eje de la gráfica de separación mínima, lo alto que queda
# la cara inferior del imán sobre la placa. Cuanto más arriba pare la impresión,
# menos lo sujeta la placa y más manda el metal que le pasa por encima: la
# boquilla y, en la A1, la chapa que lleva el ventilador bajo el cabezal. El
# resultado es que al reanudar la impresión el cabezal se lo lleva pegado.
#
# Contra esto no hay separación que valga —no es cosa del vecino sino del
# cabezal—, así que no toca la distancia mínima: es un aviso.
DEFAULT_HIGH_GAP = 5.0


def may_stick_to_toolhead(
    level: str, plate_gap: float, high: float = DEFAULT_HIGH_GAP
) -> bool:
    """True si ese imán puede irse pegado al cabezal al reanudar.

    Hacen falta las dos cosas: que el imán entre (:data:`FITS`; el que no entra
    ya tiene su propio aviso) y que quede alto sobre la placa. ``plate_gap`` es
    esa altura, la que da :func:`gcode_magnets.magnetics.magnet_gap` con la Z de
    la pausa y la altura del imán. Uno que para cerca de la placa lo sigue
    sujetando el PEI.
    """
    return level == FITS and float(plate_gap) > float(high)


# --- lo que cabe a lo hondo ---------------------------------------------------
#
# El diámetro dice si el imán entra por la boca del agujero; la profundidad dice
# si cabe dentro. Un imán que sobresale del hueco es peor que uno que no entra:
# el que no entra se queda fuera y se ve, pero el que sobresale deja que la
# boquilla le pase por encima en la primera capa de después de la pausa, y eso
# arranca el imán, atasca el cabezal o estropea la pieza.
#
# La cuenta es directa —``n · altura`` contra la profundidad medida
# (:func:`gcode_magnets.analysis.measure_hole_depths`)— y vale igual para un imán
# solo que para varios apilados en el mismo agujero, que es el caso en el que la
# suma se escapa sin que ninguno de los dos números parezca raro.

# Lo que se le perdona al imán antes de avisar, en mm. Es una décima: por debajo
# de eso la diferencia es ruido de la propia medida (la altura de capa del
# laminador redondea el fondo del hueco) y no un imán que sobresalga de verdad.
DEPTH_TOLERANCE = 0.1


def stack_height(count: int, magnet_height: float) -> float:
    """Lo que miden ``count`` imanes apilados, en mm."""
    return max(int(count), 0) * max(float(magnet_height), 0.0)


def depth_overflow(depth: float, magnet_height: float, count: int = 1) -> float:
    """Lo que sobresale del agujero una pila de ``count`` imanes, en mm.

    Positivo = se sale del hueco (y hay que avisar); 0 o negativo = cabe. Con
    ``depth`` desconocida (``None``) no hay nada que decir y sale 0.
    """
    if depth is None:
        return 0.0
    return stack_height(count, magnet_height) - max(float(depth), 0.0)


def fits_in_depth(
    depth: float, magnet_height: float, count: int = 1,
    tolerance: float = DEPTH_TOLERANCE,
) -> bool:
    """True si esa pila de imanes cabe dentro del agujero."""
    return depth_overflow(depth, magnet_height, count) <= float(tolerance)


def magnets_that_fit(
    depth: float, magnet_height: float, tolerance: float = DEPTH_TOLERANCE
) -> int:
    """Cuántos imanes de esa altura caben en el agujero (0 si no cabe ninguno)."""
    if depth is None or float(magnet_height) <= 0.0:
        return 0
    return int((max(float(depth), 0.0) + float(tolerance)) // float(magnet_height))


def hole_under(holes, x: float, y: float):
    """El agujero medido en el que cae el punto ``(x, y)``, si cae en alguno.

    ``holes`` es cualquier cosa con ``x``, ``y`` e ``inner_diameter``, que es lo
    que devuelve :func:`gcode_magnets.analysis.measure_circles`. Vale el agujero
    cuyo hueco contiene al punto; entre varios —agujeros que se solapan no
    existen, pero un hueco dentro de otro sí— gana el más pequeño, que es el que
    de verdad sujeta al imán.
    """
    dentro = [
        h for h in holes
        if (h.x - x) ** 2 + (h.y - y) ** 2 <= (h.inner_diameter / 2.0) ** 2
    ]
    if not dentro:
        return None
    return min(dentro, key=lambda h: h.inner_diameter)
