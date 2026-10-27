"""Generate G-code blocks for inserting magnets and related sequences."""
import math
from typing import Callable, Dict, List, Optional, Sequence, Tuple
from . import magnetics
from .config import (
    FALLBACK_DERETRACT,
    FALLBACK_FAN,
    SAFE_Z_OFFSET,
    TRAVEL_FEED,
    MAGNET_SEQUENCE_RED,
    MAGNET_SEQUENCE_BLUE,
    MAGNET_END_SEQUENCE,
    get_magnet_start_sequence,
    final_end_sequence,
)


def generate_concentric_circles(x: float, y: float, num_circles: int = 5, 
                               initial_radius: float = 0.4, radius_offset: float = 0.4,
                               feed_rate: float = 600) -> List[str]:
    """Generate G-code for concentric circles at position (x, y).
    
    Creates num_circles circles with increasing radius, each offset by radius_offset.
    Uses G2 arcs to draw complete circles.
    
    Args:
        x: X coordinate of circle center
        y: Y coordinate of circle center
        num_circles: Number of circles to draw (default 5)
        initial_radius: Starting radius in mm (default 0.4)
        radius_offset: Offset between each circle in mm (default 0.4)
        feed_rate: Feed rate for the circular motion (default 600)
    
    Returns:
        List of G-code strings for the circular sequence
    """
    lines: List[str] = []
    lines.append("; CÍRCULOS CONCÉNTRICOS\n")
    
    for circle_idx in range(num_circles):
        radius = initial_radius + (circle_idx * radius_offset)
        
        # Move to starting point of circle (at 3 o'clock position relative to center)
        start_x = x + radius
        start_y = y
        
        lines.append(f"G1 X{start_x:.3f} Y{start_y:.3f} F{feed_rate}\n")
        
        # Draw complete circle using G2 arc (clockwise)
        # I and J are offsets from current position to arc center
        # End point is same as start point for 360° arc
        i_offset = -radius
        j_offset = 0.0
        
        lines.append(f"G2 X{start_x:.3f} Y{start_y:.3f} I{i_offset:.3f} J{j_offset:.3f} F{feed_rate}\n")
        lines.append(f"M400\n")
    
    lines.append("; FIN CÍRCULOS CONCÉNTRICOS\n")
    return lines


# Altura de imán de reserva cuando quien llama no sabe de módulos (la CLI).
DEFAULT_MAGNET_HEIGHT = 3.0

# Radio de seguridad de la retirada cuando **no se sabe qué imán se coloca**, en
# mm. Es el número fijo que hubo durante un tiempo para todos los casos; hoy solo
# queda de reserva, porque lo que hay que apartarse depende de la altura a la que
# quede el imán y lo dice `retreat_clearance()`.
FALLBACK_RETREAT_CLEARANCE = 24.0


def retreat_clearance(current_z: float, magnet_height: float,
                      magnet_diameter: float) -> float:
    """Lo que se aparta el colocador tras dejar un imán, en mm.

    Es la misma separación mínima que se pide entre dos imanes de la pieza, y por
    el mismo motivo: el módulo lleva **su propio imán** dentro, del mismo
    diámetro que el que suelta, así que el que acaba de dejar lo ve exactamente
    igual que vería a un vecino. Ver :func:`gcode_magnets.magnetics.module_travel`.

    Depende de la Z de la pausa: cuanto más arriba para la impresión, más lejos
    queda el imán de la placa PEI, menos lo sujeta y más hay que apartarse.
    """
    h = magnetics.magnet_gap(current_z, magnet_height)
    return magnetics.module_travel(
        magnetics.min_safe_distance(h, magnet_diameter)
    )


def compute_retreat_x(x: float, y: float, placed_points: List[Tuple[float, float]],
                      offset_x: float = 0.0, offset_y: float = 0.0,
                      clearance: float = FALLBACK_RETREAT_CLEARANCE,
                      step: float = 1.0,
                      max_advance: float = 100.0,
                      placed_clearances: Optional[Sequence[float]] = None) -> float:
    """Devuelve la X **de máquina** a la que retirarse tras colocar un imán.

    Quien no debe pasar por encima de un imán ya puesto no es la boquilla de la
    impresora sino la del colocador de imanes, y esa punta no está donde apunta
    el ``G1``: está en ``(x - offset_x, y - offset_y)``, que es justo el agujero
    sobre el que acaba de dejar el imán. Por eso el radio se mide ahí y no en la
    coordenada de máquina.

    El radio es una distancia **en 2D**: estorba un imán tanto si queda cerca en
    X como si queda cerca en Y (o en diagonal). Se parte de ``clearance`` mm a la
    derecha y se sigue avanzando de ``step`` en ``step`` mientras haya algún imán
    YA COLOCADO dentro de ese radio. Los de numeraje superior, que todavía no
    están puestos, no cuentan.

    Mira **dónde acaba** la retirada, no por dónde pasa. Un imán que quede en
    mitad del pasillo no se puede esquivar avanzando —avanzar es justo pasarle
    por encima—, así que ese caso no lo arregla esta función: lo detecta
    :func:`gcode_magnets.magnetics.sweep_conflicts` y se resuelve cambiando el
    orden de colocación, no el G-code.

    Args:
        x: X de máquina del ``G1`` con el que se ha colocado este imán.
        y: Y de máquina del ``G1`` con el que se ha colocado este imán.
        placed_points: Dónde están los imanes ya colocados, en coordenadas de
            placa (las del agujero que marcó el usuario), que es el mismo marco
            en el que se sitúa la punta del colocador.
        offset_x: Desplazamiento X del colocador respecto al cabezal.
        offset_y: Desplazamiento Y del colocador respecto al cabezal.
        clearance: Radio de seguridad en mm (también el desplazamiento inicial).
        step: Incremento en mm en cada intento.
        max_advance: Avance máximo extra en mm antes de rendirse.
        placed_clearances: Lo que pide cada imán ya colocado, en el mismo orden
            que ``placed_points``. Solo hace falta cuando los dispensadores
            llevan formatos distintos: entonces el radio de cada uno es la media
            de lo que piden los dos
            (:func:`gcode_magnets.magnetics.pair_distance`) y no ``clearance``
            para todos. Sin ella, ``clearance`` vale para todos, que es el caso
            de una máquina con un solo formato de imán.

    Returns:
        La X de máquina para el ``G1`` de retirada.
    """
    # Punta del colocador, en coordenadas de placa.
    tip_x = x - offset_x
    tip_y = y - offset_y

    if placed_clearances is None:
        radios = [clearance] * len(placed_points)
    else:
        radios = [magnetics.pair_distance(clearance, d)
                  for d in placed_clearances[:len(placed_points)]]
        radios += [clearance] * (len(placed_points) - len(radios))

    tip_x += clearance
    limit = tip_x + max_advance
    while tip_x <= limit:
        # hypot() = distancia en 2D, o sea el radio en X e Y a la vez.
        if not any(math.hypot(tip_x - mx, tip_y - my) < r
                   for (mx, my), r in zip(placed_points, radios)):
            break
        tip_x += step
    return tip_x + offset_x   # de vuelta a coordenada de máquina para el G1


MARK_START = "; INICIO INSERCIÓN IMANES AUTO"
MARK_END = "; FIN INSERCIÓN IMANES AUTO"


def assemble_magnet_block(
    points: Sequence[Tuple],
    current_z: float,
    *,
    sequence_for_color: Callable[[str], Sequence[str]],
    start_sequence: Sequence[str],
    end_sequence: Sequence[str],
    final_sequence: Sequence[str],
    offset_x: float,
    offset_y: float,
    offset_z: float,
    safe_z_offset: float,
    travel_feed: float,
    magnet_height: float = DEFAULT_MAGNET_HEIGHT,
    magnet_diameter: float = magnetics.MODEL_MAGNET[0],
    magnet_for_color: Optional[Callable[[str], Tuple[float, float]]] = None,
) -> List[str]:
    """Monta el bloque de G-code que coloca los imanes. Fuente única.

    Este es el único sitio donde se decide qué líneas salen y en qué orden. Sus
    dos usuarios se diferencian solo en de dónde sacan las secuencias y los
    parámetros, y eso llega ya resuelto: :class:`MagnetPlanner` las lee de
    ``gcode_magnets.config`` (constantes fijas, para la CLI) y
    ``magnet_app.pipeline.build_magnet_block`` las saca de los ajustes
    editables de la aplicación. Durante un tiempo fueron dos copias de la misma
    lógica y se separaron: la retirada lateral se arregló en una y la otra —la
    que usa la app y alimenta la simulación 3D— se quedó con el ``x + 10`` fijo.

    Args:
        points: ``(x, y, color)`` en coordenadas de placa (se tolera ``(x, y)``,
            que se toma como rojo). El orden es el de colocación.
        current_z: Z de la capa en la que se hace la pausa.
        sequence_for_color: Devuelve la secuencia de recogida de un color, ya
            renderizada.
        start_sequence: Secuencia de inicio, una vez, ya renderizada.
        end_sequence: Secuencia de cierre, una vez, ya renderizada.
        final_sequence: Secuencia de reanudación de la impresión.
        offset_x: Desplazamiento X del colocador respecto al cabezal.
        offset_y: Desplazamiento Y del colocador respecto al cabezal.
        offset_z: Altura extra de seguridad del colocador.
        safe_z_offset: Margen en Z sobre la capa para los desplazamientos.
        travel_feed: Avance de los movimientos en Z.
        magnet_height: Altura del imán que se coloca, en mm. Con la Z de la pausa
            sale lo que hay que apartarse; el caso peor es el imán **más bajo**,
            que es el que queda más lejos de la placa. Es la reserva para cuando
            no se sabe de qué color es cada imán (la CLI).
        magnet_diameter: Diámetro del imán que se coloca, en mm. El caso peor es
            el **más ancho**. Ver :func:`retreat_clearance`.
        magnet_for_color: Devuelve ``(diámetro, altura)`` del imán de un color de
            dispensador. Con esto la retirada se calcula **con el imán que se
            acaba de soltar** y no con el peor de la máquina: tras un ⌀4 el
            colocador se aparta menos que tras un ⌀8. Sin esto se usan
            ``magnet_height``/``magnet_diameter`` para todos, como siempre.

    Returns:
        Las líneas del bloque, cada una terminada en ``\\n``.
    """
    safe_z = current_z + safe_z_offset + offset_z
    # Todos los imanes de un bloque están en la misma pausa, o sea a la misma Z,
    # así que lo único que cambia de uno a otro es el formato de su dispensador.
    _cache: Dict[str, float] = {}

    def clearance_for(color: str) -> float:
        if color not in _cache:
            if magnet_for_color is None:
                dims = (magnet_diameter, magnet_height)
            else:
                dims = magnet_for_color(color) or (magnet_diameter, magnet_height)
            _cache[color] = retreat_clearance(current_z, dims[1], dims[0])
        return _cache[color]

    lines: List[str] = ["\n", MARK_START + "\n"]

    for seq in start_sequence:
        lines.append(seq + "\n")

    # Dónde han quedado los imanes ya colocados, en coordenadas de placa (las
    # que marcó el usuario). Es el marco en el que se mide el radio de
    # seguridad de la retirada. Ver `compute_retreat_x`.
    placed_magnets: List[Tuple[float, float]] = []
    # Y lo que pide cada uno de ellos, para medir el radio de la retirada entre
    # los dos imanes de verdad y no con el mayor de los dos por defecto.
    placed_clearances: List[float] = []

    for idx, point in enumerate(points, start=1):
        if len(point) == 3:
            hole_x, hole_y, color = point
        else:  # tolerancia a (x, y)
            hole_x, hole_y = point
            color = "red"
        # (hole_x, hole_y) es donde queda el imán en la placa; (x, y) es adónde
        # va el cabezal para que el colocador caiga justo ahí.
        x = hole_x + offset_x
        y = hole_y + offset_y
        clearance = clearance_for(color)

        lines.append(f"; Imán {idx} ({color})\n")
        for seq in sequence_for_color(color):
            lines.append(seq + "\n")
        lines.append(f"G1 X{x:.3f} Y{y:.3f} F3000\n")
        lines.append(f"G1 Z{safe_z - safe_z_offset:.3f} F1200\n")
        lines.extend(generate_concentric_circles(x, y))
        lines.append("G4 S1 \n")
        lines.append("M400 \n")
        # Retirada lateral: `clearance` mm, pero avanzando más si en ese
        # radio (medido en la punta del colocador) hay imanes ya colocados.
        #
        # Sale en tramos porque los bajar-esperar-subir tienen que ocurrir
        # SIEMPRE a `clearance/2` y a los `clearance` mm exactos del imán, avance
        # luego lo que avance: si se hiciera al final del recorrido, un imán que
        # obligara a apartarse 30 mm lo correría 6 mm más y dejaría de caer
        # donde debe.
        #
        # El tramo extra se hace a `safe_z - safe_z_offset` y no a `safe_z`: si está
        # ahí es porque hay un imán YA PUESTO cerca de la boquilla, y el imán
        # interno del colocador lo atrae; subiendo del todo se lo llevaría
        # pegado. La subida a `safe_z` se deja para después, cuando ya está
        # lejos, para que el ciclo de cada imán acabe siempre a la misma altura.
        retreat_x = compute_retreat_x(
            x, y, placed_magnets, offset_x, offset_y, clearance,
            placed_clearances=placed_clearances,
        )
        clearance_x = x + clearance
        lines.append(f"G1 X{(clearance_x) - clearance/2:.3f} Y{y:.3f} F120\n")
        lines.append(f"G1 Z{(safe_z - safe_z_offset) - 1:.3f} F300\n")
        lines.append(f"G4 P200\n")
        lines.append(f"G1 Z{safe_z - safe_z_offset:.3f} F300\n")
        lines.append(f"G1 X{clearance_x:.3f} Y{y:.3f} F120\n")
        lines.append(f"G1 Z{(safe_z - safe_z_offset) - 1:.3f} F300\n")
        lines.append(f"G4 P200\n")
        if retreat_x > clearance_x:
            lines.append(f"G1 Z{safe_z - safe_z_offset:.3f} F{travel_feed:g}\n")
            lines.append(f"G1 X{retreat_x:.3f} Y{y:.3f} F600\n")
        lines.append(f"G1 Z{safe_z:.3f} F{travel_feed:g}\n")
        lines.append("M400 \n")

        placed_magnets.append((hole_x, hole_y))
        placed_clearances.append(clearance)

    for seq in end_sequence:
        lines.append(seq + "\n")
    lines.append(MARK_END + "\n")
    lines.append("\n")

    for seq in final_sequence:
        lines.append(seq + "\n")
    lines.append("\n")

    return lines


class MagnetPlanner:
    """Encapsulate parameters and generation logic for magnet insertion."""

    def __init__(
        self,
        offset_x: float = -57,
        offset_y: float = 27.5,
        offset_z: float = 5,
        safe_z_offset: float = SAFE_Z_OFFSET,
        travel_feed: float = TRAVEL_FEED,
        start_sequence: Optional[List[str]] = None,
        end_sequence: List[str] = MAGNET_END_SEQUENCE,
        sequences_by_color: Optional[Dict[str, List[str]]] = None,
        magnet_height: float = DEFAULT_MAGNET_HEIGHT,
        magnet_diameter: float = magnetics.MODEL_MAGNET[0],
    ):
        self.magnet_height = magnet_height
        self.magnet_diameter = magnet_diameter
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.offset_z = offset_z
        self.safe_z_offset = safe_z_offset
        self.travel_feed = travel_feed
        self.start_sequence = start_sequence
        self.end_sequence = end_sequence
        if sequences_by_color is None:
            sequences_by_color = {
                "red": MAGNET_SEQUENCE_RED,
                "blue": MAGNET_SEQUENCE_BLUE,
            }
        self.sequences_by_color = sequences_by_color

    def generate(
        self,
        points: List[Tuple[float, float, str]],
        current_z: float,
        temperatura_hotend: Optional[float] = None,
        fan_speed: Optional[float] = None,
        deretract: Optional[float] = None,
    ) -> List[str]:
        """Return list of G-code lines for the given magnet points at layer Z.

        Resuelve las secuencias y los parámetros a partir de
        ``gcode_magnets.config`` y deja el montaje del bloque en
        :func:`assemble_magnet_block`, que es la fuente única.

        Args:
            points: List of (x, y, color) tuples where color is 'red' or 'blue'.
            current_z: Current Z height of the layer.
            temperatura_hotend: Optional hotend temperature to use in final sequence.
            fan_speed: Ventilador de pieza vigente antes de la pausa, para que la
                secuencia final lo restaure en vez de dejar un valor fijo.
            deretract: Cebado que el laminador hará al reanudar, para retraer
                justo esa cantidad tras la purga.
        """
        # Si el color no existe se usa la secuencia del rojo: antes caía en la
        # secuencia de INICIO global (purga, calentar la boquilla, ir a la
        # cesta...), que no recoge ningún imán y además reiniciaba el estado a
        # mitad del bloque.
        def sequence_for_color(color: str) -> List[str]:
            return self.sequences_by_color.get(
                color.lower(), self.sequences_by_color.get("red", MAGNET_SEQUENCE_RED)
            )

        final_temp = temperatura_hotend if temperatura_hotend is not None else 220
        final_fan = fan_speed if fan_speed is not None else FALLBACK_FAN
        final_deretract = deretract if deretract is not None else FALLBACK_DERETRACT
        return assemble_magnet_block(
            points,
            current_z,
            sequence_for_color=sequence_for_color,
            start_sequence=(self.start_sequence if self.start_sequence is not None
                            else get_magnet_start_sequence(current_z)),
            end_sequence=self.end_sequence,
            final_sequence=final_end_sequence(
                current_z, final_temp, final_fan, final_deretract
            ),
            offset_x=self.offset_x,
            offset_y=self.offset_y,
            offset_z=self.offset_z,
            safe_z_offset=self.safe_z_offset,
            travel_feed=self.travel_feed,
            magnet_height=self.magnet_height,
            magnet_diameter=self.magnet_diameter,
        )
