"""Guardado y carga de proyectos (.mip = Magnet Insertion Project).

Un proyecto guarda la ruta del archivo de entrada, los puntos elegidos y la
configuración completa, de modo que el usuario pueda retomar el trabajo.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .settings import Settings

Point = Tuple[float, float, str]

PROJECT_EXT = ".mip"
PROJECT_VERSION = 1


def _read_points(raw) -> List[Point]:
    return [
        (float(p[0]), float(p[1]), str(p[2]) if len(p) > 2 else "red")
        for p in raw or []
    ]


@dataclass
class Project:
    input_path: str = ""
    points: List[Point] = field(default_factory=list)
    settings: Settings = field(default_factory=Settings)
    # Un archivo puede traer varias pausas ('M400 U1'), cada una con su tanda de
    # imanes: aquí van todas, por número de orden de la pausa (base 0), y
    # ``pause_ordinal`` es la que estaba abierta. ``points`` sigue siendo la de
    # esa pausa para que un proyecto nuevo se pueda abrir con la versión de
    # antes (y uno de antes, aquí).
    points_by_pause: Dict[int, List[Point]] = field(default_factory=dict)
    pause_ordinal: int = 0

    def to_dict(self) -> dict:
        return {
            "version": PROJECT_VERSION,
            "input_path": self.input_path,
            "points": [[float(x), float(y), str(c)] for x, y, c in self.points],
            "points_by_pause": {
                str(k): [[float(x), float(y), str(c)] for x, y, c in v]
                for k, v in self.points_by_pause.items()
            },
            "pause_ordinal": int(self.pause_ordinal),
            "settings": self.settings.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        points = _read_points(data.get("points"))
        ordinal = int(data.get("pause_ordinal", 0) or 0)
        by_pause = {
            int(k): _read_points(v)
            for k, v in (data.get("points_by_pause") or {}).items()
        }
        # Proyecto de antes de las pausas múltiples: sus imanes son los de la
        # única pausa que se manejaba entonces.
        if not by_pause and points:
            by_pause = {ordinal: points}
        settings = Settings.from_dict(data.get("settings", {}))
        return cls(
            input_path=data.get("input_path", ""),
            points=points,
            settings=settings,
            points_by_pause=by_pause,
            pause_ordinal=ordinal,
        )

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: str) -> "Project":
        with open(path, "r", encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))
