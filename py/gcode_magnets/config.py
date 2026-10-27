"""Configuration constants and default sequences for magnet placement."""

PAUSE_TOKEN = "M400 U1"
Z_TOL = 0.0005
SAFE_Z_OFFSET = 20
TRAVEL_FEED = 1200
MAGNET_DWELL_MS = 500

# Secuencia G-code para colocar el imán (edita aquí las líneas que necesites)
# que hayan dos magnets sequences, uno para iman rojo y otro para iman azul, y que se seleccione segun el color del imán a insertar

MAGNET_SEQUENCE_RED = [
    "G1 X203 Y128 F3000",
    "G1 X240 F600",
    "G1 X203 F600",
    "M400",
]

MAGNET_SEQUENCE_BLUE = [
    "G1 X203 Y128 F3000",  
    "G1 X260 F600",
    "G1 X203 F600",
    "M400",
]

# Secuencia global de inicio para todos los imanes (ejecutada una vez al principio)
def get_magnet_start_sequence(current_z: float) -> list[str]:
    safe_z = current_z + SAFE_Z_OFFSET
    return [
        "G1 E-.04 F1800",
        "M400",
        "M204 S30000",
        "G1 E-1 F1800",
        f"G1 Z {current_z + 0.4} F1200",
        "G1 X-48 F12000",
        "M106 P1 S178",
        "M109 S160",
        "M106 P1 S0",
        "G1 X-28.5 F30000",
        "G1 X-48.2 F3000",
        "G1 X-28.5 F30000",
        "G1 X-48.2 F3000",
        "M204 S6000",
        f"G1 Z {safe_z} F1200",
        "G1 X-48 F6000",
        "M17",
        "G90",
        "G1 Z192 F1200",
        "G1 X203 Y128 F6000",
        "G1 Z232 F600",
        "G1 Z256 F600",
        "G1 Z232 F1200",
        "G1 Z192 F1200",
        "M400",
    ]

# Secuencia global de fin para todos los imanes (ejecutada una vez al final)
MAGNET_END_SEQUENCE = [
    "G1 Z192 F1200",
    "G1 X203 Y128 F6000",
    "G1 Z232 F600",
    "G1 Z252 F600",
    "G1 Z232 F1200",
    "G1 Z192 F1200",
    "M400",
]

# Valores de reserva de la refrigeración y del cebado cuando no se leen del
# archivo. Mismos que los de `magnet_app.settings`, que es la copia editable.
FALLBACK_FAN = 178
FALLBACK_DERETRACT = 0.8


def final_end_sequence(
    current_z: float,
    temperatura_hotend: float = 220,
    fan: float = FALLBACK_FAN,
    deretract: float = FALLBACK_DERETRACT,
) -> list[str]:
    """Secuencia de reanudación tras colocar los imanes.

    Copia para la CLI de ``magnet_app.settings.DEFAULT_SEQ_FINAL``; los motivos
    de cada línea están documentados allí. En resumen: se purga a la temperatura
    de impresión (``M109 S`` no espera al enfriar, así que un pico a 240 dejaba
    la capa 20 °C caliente), se devuelve el ventilador al valor que traía el
    perfil y se retrae justo lo que el laminador va a cebar al reanudar. El
    desplazamiento en X va antes que la bajada en Z para no cruzar sobre la
    pieza a 0.4 mm de la última capa.
    """
    return [
        "G1 X-48 F6000",
        f"G1 Z {current_z + 0.6:.3f} F1200",
        "M400",
        "M106 P1 S0",
        f"M109 S{int(temperatura_hotend)} H300",
        "G92 E0",
        "G1 E30 F200",
        "M400",
        f"M106 P1 S{fan:g}",
        "G92 E0",
        "G1 E10 F200",
        "G92 E0",
        f"G1 E-{deretract:g} F300",
        "G1 X-28.5 F30000",
        "G1 X-48.2 F3000",
        "G1 X-28.5 F30000",
        "G1 X-48.2 F3000",
        "G1 X-28.5 F30000",
        "G1 X-48.2 F3000",
        "G92 E0",
        "M83",
    ]
