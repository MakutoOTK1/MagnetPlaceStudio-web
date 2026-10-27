# -*- coding: utf-8 -*-
"""Colores por tipo de trazo (``; FEATURE:`` del laminador).

Tabla única para los dos visores: la vista 2D la usa directamente y la 3D la
recibe en el mensaje de carga, de modo que una pared exterior es del mismo
color se mire como se mire.

El orden importa: la coincidencia es por subcadena, así que las claves más
específicas van **antes** que las genéricas. Si ``infill`` fuese antes que
``internal solid infill``, un relleno sólido acabaría pintado como relleno
normal.
"""
from __future__ import annotations

from typing import List, Tuple

# (claves de búsqueda, clave i18n del nombre, color)
FEATURES: List[Tuple[Tuple[str, ...], str, str]] = [
    (("outer wall", "external perimeter"), "feat.outer_wall", "#ff7d33"),
    (("inner wall", "perimeter"), "feat.inner_wall", "#ffd23e"),
    (("top surface", "top solid infill"), "feat.top_surface", "#ff5c8a"),
    (("bottom surface", "bottom solid infill"), "feat.bottom_surface", "#5cd6ff"),
    (("internal solid infill", "solid infill"), "feat.solid_infill", "#c06eff"),
    (("sparse infill", "internal infill", "infill"), "feat.infill", "#b03a3a"),
    (("bridge",), "feat.bridge", "#4fc3f7"),
    (("support",), "feat.support", "#8d9b6a"),
    (("skirt", "brim"), "feat.skirt", "#67e8a2"),
    (("gap",), "feat.gap", "#ffffff"),
]

DEFAULT_FEATURE_COLOR = "#9aa7b3"
DEFAULT_FEATURE_KEY = "feat.other"

# Color de cada dispensador de imanes. Lo comparten la placa 2D, las tarjetas
# de la pestaña Módulos y los cilindros del visor 3D, para que un imán rojo sea
# del mismo rojo se mire donde se mire.
MAGNET_COLOR_HEX = {"red": "#e23b3b", "blue": "#2b6cff"}
MAGNET_COLOR_DARK = {"red": "#a82626", "blue": "#1a49b8"}


def magnet_color(color: str, dark: bool = False) -> str:
    table = MAGNET_COLOR_DARK if dark else MAGNET_COLOR_HEX
    return table.get((color or "").lower(), table["red"])


def feature_index(name: str) -> int:
    """Índice en :data:`FEATURES` del nombre de FEATURE, o ``-1`` si no encaja."""
    low = (name or "").lower()
    for i, (keys, _label, _color) in enumerate(FEATURES):
        if any(k in low for k in keys):
            return i
    return -1


def feature_color(name: str) -> str:
    """Color hexadecimal del trazo para un nombre de ``; FEATURE:``."""
    idx = feature_index(name)
    return FEATURES[idx][2] if idx >= 0 else DEFAULT_FEATURE_COLOR


def feature_table() -> List[dict]:
    """La tabla en forma serializable, para enviarla al visor 3D."""
    return [
        {"keys": list(keys), "label": label, "color": color}
        for keys, label, color in FEATURES
    ] + [{"keys": [], "label": DEFAULT_FEATURE_KEY, "color": DEFAULT_FEATURE_COLOR}]
