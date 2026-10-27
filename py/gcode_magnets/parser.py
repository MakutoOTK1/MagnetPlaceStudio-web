"""G-code parsing utilities and data structures."""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class GCodeMove:
    index: int
    cmd: str
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    e: Optional[float] = None
    i_offset: Optional[float] = None
    j_offset: Optional[float] = None



def parse_float(token: str, letter: str) -> Optional[float]:
    """Return a float value following a letter in a G-code token or None.
    
    Handles formats like: 123, 123.456, .456, -123, -123.456, -.456
    """
    m = re.search(rf"{letter}(-?\d*\.?\d+)", token)
    return float(m.group(1)) if m else None


def parse_gcode_moves(lines: List[str]) -> List[GCodeMove]:
    """Parse movement commands (G0/G1/G2/G3) and accumulate coordinates.

    The returned list holds a running absolute position for X, Y, Z.
    """
    moves: List[GCodeMove] = []
    x = y = z = None
    for i, line in enumerate(lines):
        stripped = line.split(";")[0].strip()
        if not stripped:
            continue
        parts = stripped.split()
        cmd = parts[0]
        if cmd in ("G0", "G1", "G2", "G3"):
            nx = parse_float(stripped, "X")
            ny = parse_float(stripped, "Y")
            nz = parse_float(stripped, "Z")
            ne = parse_float(stripped, "E")
            ni = parse_float(stripped, "I") if cmd in ("G2", "G3") else None
            nj = parse_float(stripped, "J") if cmd in ("G2", "G3") else None
            if nx is not None:
                x = nx
            if ny is not None:
                y = ny
            if nz is not None:
                z = nz
            move = GCodeMove(index=i, cmd=cmd, x=x, y=y, z=z, e=ne)
            if ni is not None:
                move.i_offset = ni
            if nj is not None:
                move.j_offset = nj
            moves.append(move)
    return moves
