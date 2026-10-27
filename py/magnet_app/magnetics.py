# -*- coding: utf-8 -*-
"""Reexport de :mod:`gcode_magnets.magnetics`, donde están las cuentas.

Las mates viven un paquete más abajo porque las necesitan los dos lados: la
aplicación, para avisar de imanes demasiado juntos, y
:mod:`gcode_magnets.generator`, para saber cuánto tiene que apartarse el
colocador tras dejar cada imán. La dependencia entre paquetes va de
``magnet_app`` a ``gcode_magnets`` y no al revés, así que el archivo tiene que
estar allí.

Este módulo se queda para no cambiar los cientos de ``magnetics.min_safe_distance``
repartidos por la app y los tests: importar de aquí o de allí es lo mismo.
"""
from __future__ import annotations

from gcode_magnets.magnetics import *  # noqa: F401,F403
from gcode_magnets.magnetics import __all__  # noqa: F401
