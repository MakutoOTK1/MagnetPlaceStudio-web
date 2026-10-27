"""Utilities for reading and writing G-code inside 3MF containers."""
import gzip
import hashlib
import zipfile
import os
from typing import Optional, Tuple

# Marcadores del bloque ejecutable en el G-code de Bambu Studio. Todo lo demás
# (HEADER_BLOCK con tiempos/capas/filamento y CONFIG_BLOCK con el perfil) es lo
# que el laminador y la impresora leen para dar el archivo por válido.
EXEC_BLOCK_START = "; EXECUTABLE_BLOCK_START"
EXEC_BLOCK_END = "; EXECUTABLE_BLOCK_END"


def extract_gcode_from_3mf(path: str) -> Tuple[str, str]:
    """Return (filename, text) for the first .gcode file found in the 3MF archive.

    Acepta tanto el G-code suelto (``.gcode``) como el comprimido
    (``.gcode.gz``), que es como lo guarda Bambu Studio en algunos plates y
    como lo escribe :func:`write_gcode_as_bambu_3mf`.
    """
    with zipfile.ZipFile(path, "r") as z:
        for name in z.namelist():
            if name.endswith(".gcode"):
                return name, z.read(name).decode("utf-8")
        for name in z.namelist():
            if name.endswith(".gcode.gz"):
                return name, gzip.decompress(z.read(name)).decode("utf-8")
    raise ValueError("No se encontró G-code dentro del .3mf")


def find_gcode_entry(names) -> Tuple[Optional[str], bool]:
    """Devuelve ``(nombre, comprimido)`` del G-code dentro de un 3MF."""
    for name in names:
        if name.endswith(".gcode"):
            return name, False
    for name in names:
        if name.endswith(".gcode.gz"):
            return name, True
    return None, False


def replace_executable_block(template_gcode: str, new_body: str) -> str:
    """Sustituye el cuerpo entre los marcadores ``EXECUTABLE_BLOCK`` y nada más.

    Conserva el ``HEADER_BLOCK`` (capas, tiempos, filamento) y el
    ``CONFIG_BLOCK`` (perfil completo) de la plantilla, que es lo que Bambu
    Studio necesita para dar el archivo por bueno. Si la plantilla no trae esos
    marcadores se devuelve el G-code nuevo tal cual.
    """
    start = template_gcode.find(EXEC_BLOCK_START)
    end = template_gcode.find(EXEC_BLOCK_END)
    if start < 0 or end < 0 or end < start:
        return new_body
    head = template_gcode[: start + len(EXEC_BLOCK_START)]
    tail = template_gcode[end:]
    return f"{head}\n{new_body.strip(chr(10))}\n{tail}"


def write_gcode_into_bambu_template(
    template_path: str,
    output_path: str,
    gcode_content: str,
    executable_block_only: bool = True,
) -> str:
    """Clona un ``.3mf`` ya laminado y le mete otro G-code dentro.

    Un 3MF que Bambu Studio acepta no es solo el G-code: lleva ``_rels/.rels``,
    ``3D/3dmodel.model``, ``model_settings.config``, ``slice_info.config``,
    ``project_settings.config`` y las miniaturas. Construir todo eso a mano es
    frágil (si algo falta, el laminador responde «no se pudo cargar el archivo
    del modelo»), así que se parte de un proyecto que ya funciona y se cambia
    únicamente el G-code, recalculando su ``.md5``.

    Devuelve el nombre de la entrada de G-code que se ha reemplazado.
    """
    with zipfile.ZipFile(template_path, "r") as zin:
        gcode_name, gzipped = find_gcode_entry(zin.namelist())
        if gcode_name is None:
            raise ValueError(
                "La plantilla .3mf no contiene ningún G-code "
                "(se esperaba Metadata/plate_1.gcode). "
                "Usa un .3mf ya laminado con Bambu Studio."
            )

        raw = zin.read(gcode_name)
        template_text = (gzip.decompress(raw) if gzipped else raw).decode("utf-8", "replace")
        new_text = (
            replace_executable_block(template_text, gcode_content)
            if executable_block_only
            else gcode_content
        )

        payload = new_text.encode("utf-8")
        md5_name = gcode_name + ".md5"
        new_md5 = hashlib.md5(payload).hexdigest().upper().encode("ascii")
        stored = gzip.compress(payload) if gzipped else payload

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == gcode_name:
                    data = stored
                elif item.filename == md5_name:
                    data = new_md5
                else:
                    data = zin.read(item.filename)
                zout.writestr(item, data)
    return gcode_name


def write_gcode_into_3mf(
    original_path: str,
    output_path: str,
    gcode_filename: str,
    new_gcode: str,
) -> None:
    """Write a modified G-code string back into a copy of the 3MF archive."""
    with zipfile.ZipFile(original_path, "r") as zin:
        with zipfile.ZipFile(output_path, "w") as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == gcode_filename:
                    data = new_gcode.encode("utf-8")
                zout.writestr(item, data)


def write_gcode_to_file(output_path: str, gcode_content: str) -> None:
    """Write G-code content directly to a .gcode file."""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(gcode_content)


def detect_output_format(output_path: str) -> str:
    """Detect output format based on file extension.
    
    Returns:
        '3mf' or 'gcode'
    """
    lower_path = output_path.lower()
    if lower_path.endswith(".gcode"):
        return "gcode"
    else:
        return "3mf"
