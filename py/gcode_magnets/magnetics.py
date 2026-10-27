# -*- coding: utf-8 -*-
"""Cuánto se pueden acercar dos imanes sin arrancarse el uno al otro.

Un imán recién colocado lo sujeta la atracción a la **placa PEI de acero**, y esa
fuerza cae **exponencialmente** con la altura a la que queda: cada 1.45 mm que se
separa, la placa pierde dos tercios de lo que sujetaba, así que a 3 mm ya solo
aguanta con la octava parte y a 5 mm con la trigésima. La atracción **entre dos
imanes**, en cambio, cae mucho más despacio (como ``1/d²``) y sigue siendo fuerte
a varios milímetros. Cuando la segunda gana a la primera, el imán se sale de su
agujero y se va a buscar al vecino en mitad de la impresión.

La condición de equilibrio es ``F_imán(d) ≤ F_PEI(h)``; despejando ``d`` sale la
separación mínima, :func:`min_safe_distance`. Como una cae exponencial y la otra
como un cuadrado, **la separación crece exponencialmente con la altura**: se
multiplica por e cada 2.9 mm que sube el imán. Por eso está cortada por arriba en
:data:`MAX_SAFE_DISTANCE`, que es un techo de trabajo —lo que cabe en una cama—,
no una medida. A eso se le suma el **diámetro del imán que se coloca**, de modo
que el mínimo se pide entre los cuerpos y no entre los centros: a 5 mm de altura
la fórmula da 20.1 mm y un ⌀5 acaba pidiendo 25.1.

La curva está anclada a una medida real (:data:`CALIBRATION_POINT`): un ⌀5 × 3 a
5 mm de la placa pide unos **25 mm** entre centros. Ese punto manda sobre las
constantes: si se retoca ``F0_PEI`` o ``H0_PEI``, tiene que seguir saliendo.

Cada dispensador puede llevar un imán distinto, así que **el mínimo no es uno
solo para toda la placa**: cada imán pide el suyo, con su propio diámetro y su
propia altura. Entre dos que no piden lo mismo vale la media
(:func:`pair_distance`), que es lo que hace que sus círculos se toquen justo
cuando se cumple: el de un ⌀8 es más grande que el de un ⌀4 y el par se resuelve
a mitad de camino. Por eso las funciones de conflicto aceptan **un ``d_min`` por
imán** además del número único de siempre.

Esa separación se mide **en línea recta**, que es como trabaja la atracción: da
igual por dónde se separen dos imanes mientras la distancia de centro a centro
llegue al mínimo. El criterio es un círculo, no un cuadrado (ver
:func:`close_pairs`): cada imán lleva alrededor un círculo de **diámetro**
``d_min``, y dos imanes están en conflicto cuando esos dos círculos se solapan.

En la cuenta no hay dos imanes, sino tres: el **módulo MagnetPlace lleva el suyo
dentro**, del mismo diámetro que el que suelta. Tras dejar cada imán el módulo se
aparta lateralmente (:func:`module_travel`) casi a ras de la capa, así que
arrastra su propio círculo por encima de la placa y **barre un pasillo**
(:func:`path_distance`) donde no puede haber ningún imán ya colocado. Ahí el
**orden importa**: los de numeración superior todavía no están puestos y no
corren peligro (:func:`sweep_conflicts`).

El modelo está calibrado para un **disco N52 de 6 × 5 mm**. La altura de ese disco
es la mayor que admite la aplicación (:data:`~magnet_app.settings.MAGNET_HEIGHTS`
llega a 5), pero el diámetro no:
:data:`~magnet_app.settings.MAGNET_DIAMETERS` llega a 8 mm. Un disco más ancho
tira más que el calibrado, así que la curva de fuerza se queda corta para 7 y 8 mm;
lo que compensa es que :func:`min_safe_distance` **suma el diámetro entero** por
encima del mínimo, y con el corte de :data:`MAX_SAFE_DISTANCE` ese sumando es lo
que manda en los formatos grandes.

**Supone cero fricción entre el imán y su agujero.** Es el caso pesimista a
propósito: en una pieza alta la placa ya no sujeta nada y el mínimo se dispara
—pasados los 7 mm de altura la fórmula ya pide más de 50 mm y se queda pegada al
tope—. Las dos salidas reales —que el agujero apriete, y que sea más hondo que el
imán— están recogidas en :data:`FRICTION_MIN_DISTANCE` y :data:`DEEP_HOLE_RATIO`,
y se explican en el diálogo informativo. En una pieza alta son **la** respuesta,
no una nota al pie.

Vive en :mod:`gcode_magnets` y no en :mod:`magnet_app` —que es quien lo usa casi
siempre— para que también lo alcance :mod:`gcode_magnets.generator`, que necesita
la misma cuenta para saber cuánto tiene que apartarse el colocador. La
dependencia entre paquetes va en ese sentido y no al revés;
``magnet_app.magnetics`` es un reexport de este módulo.

Como :mod:`magnet_app.limits`, aquí no se importa Qt: son cuentas puras.
"""
from __future__ import annotations

import math
from typing import List, NamedTuple, Sequence, Tuple, Union

__all__ = [
    "F0_PEI", "H0_PEI", "F0_MAGNET", "D0_MAGNET", "MODEL_MAGNET",
    "CALIBRATION_POINT", "FRICTION_MIN_DISTANCE", "MAX_SAFE_DISTANCE",
    "DEEP_HOLE_RATIO", "KIND_NEIGHBOUR", "KIND_SWEEP", "STACK_TOL",
    "Point", "Segment", "Pair", "Distances",
    "pei_force", "magnet_force", "min_safe_distance", "magnet_gap",
    "pair_distance", "axis_separation", "center_distance",
    "same_stack", "stack_counts", "stack_groups",
    "module_travel", "module_travels",
    "retreat_path", "path_distance",
    "neighbour_pairs", "sweep_conflicts", "close_pairs", "placement_order",
    "escape_diagonal", "tilt_clearance",
]

# --- imán ↔ placa PEI ---------------------------------------------------------
F0_PEI = 3.0        # N: fuerza de sujeción con el imán pegado a la placa (h = 0)
# mm: **longitud de decaimiento** de esa sujeción, no una escala geométrica. La
# placa suelta al imán de forma exponencial —cada 1.45 mm que se separa, la
# fuerza queda en poco más de un tercio—, y ese es el número que fija toda la
# curva. Sale de una medida real: un ⌀5 × 3 a 5 mm de la placa necesita unos
# 25 mm entre centros, y con F0 = 3 N eso pide λ = 1.45.
H0_PEI = 1.45

# --- imán ↔ imán --------------------------------------------------------------
F0_MAGNET = 12.0    # N: atracción N52-N52 en contacto (d = 0)
D0_MAGNET = 1.8     # mm: constante de escala geométrica imán-imán

# Disco con el que se calibraron las cuatro constantes de arriba: (diámetro, altura).
MODEL_MAGNET = (6.0, 5.0)

# Y el punto medido con el que se ancló la curva: (diámetro, altura h, d_min).
# Un ⌀5 × 3 a 5 mm de la placa pide unos 25 mm entre centros. Cualquier retoque
# de F0_PEI o H0_PEI tiene que seguir pasando por aquí.
CALIBRATION_POINT = (5.0, 5.0, 25.0)

# Mínimo práctico cuando el agujero aprieta el imán: entonces quien lo sujeta es el
# rozamiento contra la pared, no la placa, y deja de depender de la altura.
FRICTION_MIN_DISTANCE = 10.0

# Techo **práctico** de la parte de fuerzas. La curva es exponencial: pasados
# unos 7 mm de altura pide ya más de 50 mm, y a 10 mm pediría 120. Seguir la
# fórmula hasta ahí no sirve de nada —en una cama de 256 mm no caben dos imanes
# a esa distancia— así que el modelo se corta aquí y lo que haya por encima se
# resuelve con las dos salidas reales: que el agujero apriete
# (:data:`FRICTION_MIN_DISTANCE`) o que sea más hondo (:data:`DEEP_HOLE_RATIO`).
# No es una medida, es un tope de trabajo.
MAX_SAFE_DISTANCE = 50.0

# Profundidad de agujero (en alturas de imán) a partir de la cual el imán, al
# inclinarse hacia su vecino, se traba contra la pared en vez de salirse.
DEEP_HOLE_RATIO = 1.5

# Los dos motivos por los que un par sale en la lista de conflictos.
KIND_NEIGHBOUR = "neighbour"   # imán contra imán: se buscan entre ellos
KIND_SWEEP = "sweep"           # el recorrido del módulo pisa un imán ya colocado

# Dos imanes en el MISMO agujero son una pila, no un conflicto: el segundo se
# suelta encima del primero a propósito, así que ni la separación mínima ni el
# recorrido del módulo tienen nada que decir de ese par (lo que sí tiene algo que
# decir es la profundidad del agujero: ver :func:`gcode_magnets.fit.depth_overflow`).
# El margen es de centésimas porque una pila se marca con el MISMO clic sobre el
# mismo centro detectado: dos agujeros distintos nunca caen tan cerca.
STACK_TOL = 0.01

Point = Tuple[float, float, str]
# El segmento que recorre el módulo al retirarse: (x_inicio, x_fin, y) en mm,
# en coordenadas de placa. La retirada es solo hacia +X y a la misma Y.
Segment = Tuple[float, float, float]

# Lo que piden los imanes de una placa: un número para todos, o uno por imán
# cuando los dispensadores llevan formatos distintos.
Distances = Union[float, Sequence[float]]


class Pair(NamedTuple):
    """Un conflicto entre dos imanes, con por qué lo es.

    ``a`` es siempre el índice menor. En un :data:`KIND_SWEEP` eso no es un
    detalle de ordenación sino el fondo del asunto: ``a`` es el imán **ya
    colocado** y ``b`` el que se está colocando cuando el módulo se retira por
    encima de él. ``dx``/``dy`` son la separación por ejes, en mm, que es lo que
    hace falta para saber **hacia dónde** hay que apartarlos; quien decide si el
    par está en conflicto es :attr:`distance`, la separación en línea recta.
    """

    a: int
    b: int
    dx: float
    dy: float
    kind: str = KIND_NEIGHBOUR

    @property
    def distance(self) -> float:
        """Separación en línea recta entre los dos centros, en mm."""
        return math.hypot(self.dx, self.dy)


def pei_force(h: float) -> float:
    """Fuerza con la que la placa PEI retiene un imán a ``h`` mm de altura, en N.

    Cae **exponencialmente**: ``F0 · e^(−h/λ)``. No es un ajuste cómodo, es lo
    que se mide —el acero deja de contar en cuanto hay aire de por medio— y es
    la razón de que la separación mínima se dispare tan pronto: a 1.45 mm la
    placa ya solo sujeta con un tercio de lo que sujetaba en contacto, y a 5 mm
    con la trigésima parte.
    """
    return F0_PEI * math.exp(-max(float(h), 0.0) / H0_PEI)


def magnet_force(d: float) -> float:
    """Atracción entre dos imanes separados ``d`` mm centro a centro, en N."""
    return F0_MAGNET / (1.0 + (max(float(d), 0.0) / D0_MAGNET) ** 2)


def min_safe_distance(h: float, diameter: float = 0.0) -> float:
    """Separación mínima segura entre centros, en mm, a ``h`` mm de la placa.

    La parte de fuerzas sale de igualarlas: el vecino no puede tirar más de lo
    que la placa sujeta. Se escribe con :func:`pei_force` en vez de con la
    constante ya sustituida (``1.8·√(12·e^(h/1.45)/3 − 1)``) para que se lea de
    dónde viene.

    Como la sujeción de la placa cae exponencialmente y la atracción del vecino
    solo como ``1/d²``, la distancia que hace falta **crece exponencialmente con
    la altura**: cada 2.9 mm que sube el imán, la separación se multiplica por
    e. De 5 mm de altura a 7 mm ya se pasa de 20 a 40 mm de fuerzas.

    Por eso la parte de fuerzas se corta en :data:`MAX_SAFE_DISTANCE`, que es un
    techo de trabajo y no una medida: a partir de ahí la fórmula pide distancias
    que no caben en la cama, y lo que hay que hacer no es separar más sino que
    el agujero agarre (ver :data:`FRICTION_MIN_DISTANCE`).

    Encima se suma el ``diameter`` del imán que se coloca. Así lo que pide el
    modelo deja de medirse de centro a centro y pasa a medirse **entre los
    cuerpos**: dos imanes cumplen cuando queda esa distancia libre entre ellos,
    no cuando sus centros llegan a ella. Es más exigente y escala con el imán
    real —un ⌀5 pide 5 mm más que un punto sin volumen—, que es lo que se ve en
    el visor, donde el círculo de cada imán tiene de diámetro este resultado.
    """
    razon = F0_MAGNET / pei_force(h)
    # razón ≥ 4 siempre (F0_MAGNET es 4× F0_PEI), así que la raíz nunca es de un
    # número negativo; el max() es solo un cinturón por si se tocan las constantes.
    d = D0_MAGNET * math.sqrt(max(razon - 1.0, 0.0))
    return min(d, MAX_SAFE_DISTANCE) + max(float(diameter), 0.0)


def magnet_gap(pause_z: float, magnet_height: float) -> float:
    """Altura ``h`` de la cara inferior del imán sobre la placa, en mm.

    Se supone el agujero tan hondo como alto es el imán y su cara superior a ras
    de la capa de la pausa, que es como queda al dejarlo caer: el imán apoya en
    el fondo del agujero, a ``Z_pausa − altura`` de la placa. Nunca negativo.
    """
    return max(float(pause_z) - float(magnet_height), 0.0)


def _per_point(n: int, values: Distances) -> List[float]:
    """Normaliza ``values`` a una lista de ``n`` distancias, nunca negativas.

    Quien pasa un solo número lo está pidiendo para todos los imanes, que es el
    caso de siempre (una placa con un único formato de imán). Quien pasa una
    lista la trae ya en el orden de ``points``. Si la lista se queda corta, lo
    que falta va a 0, o sea «de este no compruebes nada»: más vale no avisar que
    inventarse un mínimo para un imán del que no se sabe el formato.
    """
    if isinstance(values, (int, float)):
        return [max(float(values), 0.0)] * n
    fuera = [max(float(v), 0.0) for v in values][:n]
    return fuera + [0.0] * (n - len(fuera))


def pair_distance(da: float, db: float) -> float:
    """Separación mínima entre dos imanes que no piden lo mismo, en mm.

    Es la media de lo que pide cada uno. No es un apaño: en ``d_min`` va sumado
    el diámetro del imán, así que el círculo de cada uno tiene de diámetro su
    propia ``d_min`` y **dos círculos se tocan justo a la media** de los dos
    diámetros (la suma de sus radios). Un ⌀8 arrastra un círculo mayor que un ⌀4
    y el par se resuelve a mitad de camino, que es lo que se ve en el visor.

    Con los dos iguales devuelve ese mismo valor, así que una placa de un solo
    formato se comporta exactamente como antes.
    """
    return (max(float(da), 0.0) + max(float(db), 0.0)) / 2.0


def axis_separation(a: Point, b: Point) -> Tuple[float, float]:
    """Separación entre dos imanes en cada eje: ``(|Δx|, |Δy|)``, en mm.

    Ya no es el criterio —eso lo decide :func:`center_distance`—, pero se sigue
    guardando en cada :class:`Pair` porque es lo que dice **por dónde** hay que
    apartarlos.
    """
    return abs(float(a[0]) - float(b[0])), abs(float(a[1]) - float(b[1]))


def center_distance(a: Point, b: Point) -> float:
    """Separación entre dos imanes en línea recta, de centro a centro, en mm."""
    dx, dy = axis_separation(a, b)
    return math.hypot(dx, dy)


def same_stack(a: Point, b: Point, tol: float = STACK_TOL) -> bool:
    """True si los dos imanes están en el mismo agujero, uno encima del otro."""
    return center_distance(a, b) <= float(tol)


def stack_counts(points: Sequence[Point]) -> List[int]:
    """Cuántos imanes hay en el agujero de cada punto (1 = él solo).

    Mismo orden y misma longitud que ``points``: todos los imanes de una pila
    llevan la cuenta **entera** de la pila, que es lo que hace falta para medirla
    contra la profundidad del agujero sin importar por cuál de ellos se pregunte.
    """
    cuentas = [1] * len(points)
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            if same_stack(points[i], points[j]):
                cuentas[i] += 1
                cuentas[j] += 1
    return cuentas


def stack_groups(points: Sequence[Point]) -> List[List[int]]:
    """Índices de ``points`` agrupados por agujero, en orden de colocación.

    Cada grupo es una pila: el primero de la lista es el imán que va al fondo y
    el último el que queda arriba, que es el orden en que se sueltan.
    """
    grupos: List[List[int]] = []
    for i, p in enumerate(points):
        for grupo in grupos:
            if same_stack(points[grupo[0]], p):
                grupo.append(i)
                break
        else:
            grupos.append([i])
    return grupos


# --- el imán que llevan dentro ------------------------------------------------
def module_travel(d_min: float) -> float:
    """Lo que se aparta el módulo tras soltar un imán, en mm.

    El módulo MagnetPlace lleva **su propio imán** dentro, del mismo diámetro que
    el que acaba de dejar, así que entre los dos hace falta exactamente la misma
    separación que entre dos imanes de la pieza: ``d_min``. Ni más —apartarse de
    sobra alarga el pasillo que barre y encima puede salirse del recorrido de los
    ejes— ni menos, que es llevárselo pegado.

    Antes era un número fijo de 24 mm, que resultaba ser de más abajo (a 2 mm
    sobre la placa con un ⌀5 bastan 11.9) y **de menos arriba** (a 6 mm de
    altura la cuenta ya pide 33, y a 7 pasa de 45).
    """
    return max(float(d_min), 0.0)


def module_travels(points: Sequence[Point], d_min: Distances) -> List[float]:
    """Lo que se aparta el módulo tras cada imán de ``points``, en mm.

    Un imán por retirada, y cada uno con el suyo: el módulo se lleva dentro un
    imán del formato del que acaba de soltar, así que tras un ⌀4 se aparta menos
    que tras un ⌀8.
    """
    return [module_travel(d) for d in _per_point(len(points), d_min)]


def retreat_path(point: Point, travel: float) -> Segment:
    """Camino que recorre el imán interno del módulo al retirarse, en mm.

    La retirada es **solo hacia +X** y a la misma Y (ver
    :func:`gcode_magnets.generator.assemble_magnet_block`), así que el imán
    interno va del ``(x, y)`` del imán recién soltado a ``(x + travel, y)``.
    """
    x, y = float(point[0]), float(point[1])
    return (x, x + max(float(travel), 0.0), y)


def path_distance(a: Point, point: Point, travel: float) -> float:
    """Lo más que se acerca el imán interno del módulo a ``a`` al retirarse, en mm.

    Es la distancia de ``a`` al segmento de :func:`retreat_path`. Como el imán
    interno arrastra su círculo por todo el recorrido, lo que barre no es una
    caja sino una **pista de atletismo**: el círculo de ``d_min`` estirado
    ``travel`` mm hacia +X. Un imán ya colocado está dentro cuando esta distancia
    se queda por debajo de lo que piden los dos.

    Los bordes **no** cuentan, igual que en :func:`close_pairs`: un imán justo en
    el límite está bien.
    """
    x0, x1, y = retreat_path(point, travel)
    ax, ay = float(a[0]), float(a[1])
    # El segmento es horizontal, así que basta con recortar la X al tramo.
    return math.hypot(ax - min(max(ax, x0), x1), ay - y)


def neighbour_pairs(points: Sequence[Point], d_min: Distances) -> List[Pair]:
    """Pares de imanes demasiado juntos entre sí.

    El criterio es un **círculo, no un cuadrado**: hay conflicto cuando la
    separación **en línea recta** entre los centros se queda corta, sin importar
    por qué eje. Es así porque la atracción entre dos imanes no sabe de ejes:
    solo depende de lo lejos que estén, así que dos imanes en diagonal están tan
    bien como dos en fila si la distancia es la misma.

    Se comparan **todos** con todos, del color que sean: dos imanes con la misma
    polaridad hacia arriba se repelen de lado y con la contraria se atraen, pero
    el módulo de la fuerza es el mismo y en ambos casos el imán deja su agujero.

    Aquí el orden de colocación da igual: los dos acaban puestos, y una vez
    puestos se buscan.

    ``d_min`` puede ser uno para todos o **uno por imán**; entre dos que no
    piden lo mismo manda :func:`pair_distance`.

    Dos imanes del mismo agujero (:func:`same_stack`) no cuentan: están pegados
    a propósito y no hay separación que pedirles.
    """
    ds = _per_point(len(points), d_min)
    pares: List[Pair] = []
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            if same_stack(points[i], points[j]):
                continue
            pide = pair_distance(ds[i], ds[j])
            if pide <= 0.0:
                continue
            dx, dy = axis_separation(points[i], points[j])
            if math.hypot(dx, dy) < pide:
                pares.append(Pair(i, j, dx, dy, KIND_NEIGHBOUR))
    return pares


def sweep_conflicts(
    points: Sequence[Point], d_min: Distances, travel: Distances
) -> List[Pair]:
    """Imanes por encima de los que pasa el módulo al retirarse.

    Para cada imán ``j`` se mira lo cerca que le pasa su retirada
    (:func:`path_distance`) a los imanes ``i < j``. **Solo los anteriores**:
    cuando el módulo se retira del
    imán ``j``, los de numeración superior todavía no existen, así que no hay
    nada que arrancar. Es la única parte de este módulo en la que el orden de la
    lista cambia el resultado, y por eso reordenar la colocación arregla
    conflictos que mover imanes no arreglaría (ver :func:`placement_order`).

    Un imán arrancado así es peor que el caso de :func:`neighbour_pairs`: no se
    va a buscar al vecino, se sube pegado al módulo y aparece en cualquier sitio.

    El imán que lleva el módulo dentro es del formato del que acaba de soltar, así
    que el pasillo lo marca ``d_min`` del imán ``j``; lo que decide si el ``i``
    está dentro es lo que piden **los dos** (:func:`pair_distance`), y por eso el
    listón se calcula por par y no una vez por ``j``.
    """
    ds = _per_point(len(points), d_min)
    ts = _per_point(len(points), travel)
    pares: List[Pair] = []
    for j in range(len(points)):
        if ts[j] <= 0.0:
            continue
        for i in range(j):
            # El imán del fondo de la pila lo tapa el que se acaba de soltar
            # encima: el módulo no puede pisar lo que ya no está a su alcance.
            if same_stack(points[i], points[j]):
                continue
            pide = pair_distance(ds[i], ds[j])
            if pide <= 0.0:
                continue
            if path_distance(points[i], points[j], ts[j]) < pide:
                dx, dy = axis_separation(points[i], points[j])
                pares.append(Pair(i, j, dx, dy, KIND_SWEEP))
    return pares


def close_pairs(
    points: Sequence[Point], d_min: Distances, travel: Distances = 0.0
) -> List[Pair]:
    """Todos los conflictos de una placa, de más grave a menos.

    Junta los dos motivos: imanes que se buscan entre ellos
    (:func:`neighbour_pairs`) y imanes a los que el módulo les pasa por encima al
    retirarse (:func:`sweep_conflicts`). Un par que ya sale por vecindad no se
    repite como recorrido: es el mismo problema visto dos veces, y la vecindad es
    la que manda porque no se arregla reordenando.

    Con ``travel`` a 0 solo queda la comprobación de siempre, que es lo que
    quiere quien no está mirando una colocación real (los tests del modelo, o un
    visor sin archivo cargado).

    Dentro de cada motivo mandan los peores primero: los que menos distancia en
    línea recta dejan entre sus centros, que es lo que decide si el par pasa.
    """
    vecinos = sorted(neighbour_pairs(points, d_min), key=lambda p: p.distance)
    ya = {(p.a, p.b) for p in vecinos}
    barridos = sorted(
        (p for p in sweep_conflicts(points, d_min, travel) if (p.a, p.b) not in ya),
        key=lambda p: p.distance,
    )
    return vecinos + barridos


def placement_order(points: Sequence[Point]) -> List[int]:
    """Índices de ``points`` en el orden de colocación que evita los barridos.

    Como el módulo se retira **hacia +X**, su pasillo solo puede pisar imanes que
    estén a la derecha del que acaba de dejar. Colocándolos de izquierda a
    derecha, todo lo que ya está puesto queda **detrás** del pasillo, así que
    ningún :func:`sweep_conflicts` sobrevive salvo los que además son conflicto
    de vecindad —y esos no los arregla ningún orden, hay que separar los imanes—.

    No hace falta buscar el orden bueno probando: se ordena por X y ya está. El
    desempate por Y es solo para que dos imanes en la misma vertical salgan
    siempre igual y el botón de reordenar no baile.
    """
    return sorted(
        range(len(points)),
        key=lambda i: (float(points[i][0]), float(points[i][1])),
    )


def escape_diagonal(diameter: float, height: float) -> float:
    """Diagonal del imán, en mm: lo que mide de esquina a esquina al inclinarse.

    Es el número del caso del agujero profundo: para salir de un agujero más
    hondo que él, el imán tiene que ladearse, y ladeado ya no ocupa su diámetro
    sino esta diagonal. Si el agujero no da esa holgura, se traba.
    """
    return math.hypot(float(diameter), float(height))


def tilt_clearance(diameter: float, height: float) -> float:
    """Holgura que le faltaría al agujero para dejar que el imán se ladee, en mm."""
    return escape_diagonal(diameter, height) - float(diameter)
