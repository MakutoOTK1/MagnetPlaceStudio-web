"""Top-level package for G-code magnet insertion utilities."""

from .config import *
from .parser import *
from .geometry import *
from .analysis import *
from .generator import *
from .io import *

# `gui` y `cli` NO se reexportan aquí a propósito. `gui` es la ventana antigua
# de matplotlib, que solo usa la CLI clásica (`python main.py`), pero al
# reexportarla desde el paquete la app de escritorio —que ya no dibuja con
# matplotlib— acababa arrastrando matplotlib, numpy y PIL: unos 50 MB de más en
# el ejecutable, para código que nunca ejecuta.
#
# Quien los necesite los importa por su nombre completo, como hace `main.py`:
#     from gcode_magnets.cli import main
#     from gcode_magnets.gui import select_magnet_points
