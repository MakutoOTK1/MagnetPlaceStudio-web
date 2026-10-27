# -*- coding: utf-8 -*-
"""Puente entre la página web y la lógica de MagnetPlace Studio.

En la app de escritorio este papel lo hace :mod:`magnet_app.main_window`, con
Qt. Aquí corre dentro de **Pyodide** (Python compilado a WebAssembly, dentro de
un Web Worker del navegador) y la página le habla con :func:`call`: un nombre de
función y sus argumentos en JSON, y una respuesta también en JSON.

Lo que hay aquí es solo el pegamento que en escritorio vivía en la ventana —el
estado de la sesión, los avisos y las rutas de exportación—. Las cuentas son las
mismas de siempre: ``gcode_magnets`` y ``magnet_app`` se cargan **sin tocar**,
copiados tal cual de la app de escritorio, así que el G-code que sale de la web
es el mismo que saldría del ``.exe``.

Los archivos viven en el sistema de ficheros en memoria de Pyodide: la página
escribe el que abre el usuario en :data:`WORK_DIR` y recoge de :data:`OUT_DIR`
lo que hay que descargar.
"""
from __future__ import annotations

import html
import json
import ntpath
import os
import traceback
from typing import Dict, List, Optional, Tuple

from gcode_magnets import adhesion, fit, geometry, magnetics
from gcode_magnets.analysis import is_infill_feature
from gcode_magnets.generator import MARK_START

from magnet_app import __app_name__, __version__, i18n, limits, pipeline
from magnet_app.features import feature_color, feature_table
from magnet_app.i18n import tr
from magnet_app.project import Project
from magnet_app.settings import (
    BED_MATERIALS,
    MAGNET_COLORS,
    MAGNET_DIAMETERS,
    MAGNET_GRADES,
    MAGNET_HEIGHTS,
    MAX_MODULES,
    Settings,
    allowed_heights,
    max_height_for,
)

WORK_DIR = "/work"
OUT_DIR = "/work/out"

Point = Tuple[float, float, str]

# Textos que necesita la página del visor 3D. Copia de
# `magnet_app.viewer3d.VIEWER_TEXT_KEYS`, que no se puede importar aquí porque
# ese módulo arrastra Qt.
VIEWER_TEXT_KEYS: List[str] = [
    "viewer.no_file_3d",
    "v3d.play", "v3d.pause", "v3d.reset", "v3d.speed", "v3d.layer",
    "v3d.color_by", "v3d.legend", "v3d.panel_hide", "v3d.panel_show",
    "v3d.color_feature", "v3d.color_phase",
    "v3d.color_layer", "v3d.color_speed",
    "v3d.show_travel", "v3d.show_volume", "v3d.show_model",
    "v3d.follow", "v3d.stop_at_pause",
    "v3d.phase_before", "v3d.phase_magnets", "v3d.phase_after",
    "v3d.phase_before_tip", "v3d.phase_magnets_tip", "v3d.phase_after_tip",
    "v3d.magnets", "v3d.no_pause",
    "feat.outer_wall", "feat.inner_wall", "feat.top_surface", "feat.bottom_surface",
    "feat.solid_infill", "feat.infill", "feat.bridge", "feat.support",
    "feat.skirt", "feat.gap", "feat.other",
]


def _basename(path: str) -> str:
    """Nombre del archivo, venga la ruta de Windows (un ``.mip`` de escritorio) o no."""
    return ntpath.basename(str(path or "").replace("/", "\\"))


def _esc(text) -> str:
    """Texto del usuario (nombres de archivo, el token) listo para ir en HTML.

    La página pinta los mensajes como HTML porque las traducciones llevan
    ``<b>``; lo que viene de fuera —un ``.mip`` compartido, un nombre de
    archivo— tiene que entrar escapado.
    """
    return html.escape(str(text or ""))


def _points(raw) -> List[Point]:
    return [
        (float(p[0]), float(p[1]), "blue" if str(p[2]).lower() == "blue" else "red")
        for p in raw or []
    ]


class WebApp:
    """El estado de una sesión: lo que en escritorio guardaba la ventana."""

    def __init__(self) -> None:
        self.settings = Settings()
        self.result: Optional[pipeline.AnalysisResult] = None
        self.name: Optional[str] = None     # nombre del archivo abierto
        self.path: Optional[str] = None     # su ruta en el FS virtual
        # Imanes de la placa a la vista, en orden de colocación, y los de todas.
        self.points: List[Point] = []
        self.points_by_pause: Dict[int, List[Point]] = {}
        self.auto_reorder = True
        # Riesgos asumidos en esta sesión (huellas, ver main_window).
        self.acks: Dict[str, set] = {k: set() for k in ("depth", "fit", "spacing", "adhesion")}
        self.measurements_cache: Dict[int, list] = {}
        # Un proyecto abierto sin su archivo: se aplica en cuanto se abra uno
        # con el mismo nombre.
        self.pending_project: Optional[dict] = None
        self.template_path: Optional[str] = None

    # ------------------------------------------------------------------ util
    def _all_points(self) -> Dict[int, List[Point]]:
        self._store_current_points()
        total = self.result.pause_count if self.result is not None else 0
        return {k: list(v) for k, v in self.points_by_pause.items() if v and 0 <= k < total}

    def _store_current_points(self) -> None:
        if self.result is None:
            return
        if self.points:
            self.points_by_pause[self.result.pause_ordinal] = list(self.points)
        else:
            self.points_by_pause.pop(self.result.pause_ordinal, None)

    def _label_plate(self, ordinal: int, msg: str) -> str:
        if self.result is None or self.result.pause_count <= 1:
            return msg
        return tr("pause.in_plate", n=ordinal + 1, msg=msg)

    # ------------------------------------------- distancia mínima y alcance
    def _magnet_dims(self, color: str) -> tuple:
        modulo = self.settings.module_for_color(color)
        if modulo and modulo.diameter > 0 and modulo.height > 0:
            return (modulo.diameter, modulo.height)
        return self.settings.worst_case_magnet()

    def _min_distance_for_color(self, layer_z: float, color: str) -> float:
        diametro, altura = self._magnet_dims(color)
        return magnetics.min_safe_distance(magnetics.magnet_gap(layer_z, altura), diametro)

    def _min_distances_for(self, layer_z: float) -> dict:
        return {c: self._min_distance_for_color(layer_z, c)
                for c in self.settings.available_colors()}

    def _min_distance_for(self, layer_z: float) -> float:
        por_color = self._min_distances_for(layer_z)
        if por_color:
            return max(por_color.values())
        diametro, altura = self.settings.worst_case_magnet()
        return magnetics.min_safe_distance(magnetics.magnet_gap(layer_z, altura), diametro)

    def _retreat_for(self, layer_z: float) -> float:
        return magnetics.module_travel(self._min_distance_for(layer_z))

    def _retreat(self) -> float:
        return 0.0 if self.result is None else self._retreat_for(self.result.layer_z)

    def _area(self) -> limits.Area:
        return limits.reachable_area(self.settings.offset_x, self.settings.offset_y,
                                     self._retreat())

    def _point_dmins(self, points: List[Point]) -> List[float]:
        """Lo que pide cada imán colocado (0 = sin archivo, no se comprueba)."""
        if self.result is None:
            return [0.0] * len(points)
        por_color = self._min_distances_for(self.result.layer_z)
        peor = self._min_distance_for(self.result.layer_z)
        return [por_color.get(c, peor) for _x, _y, c in points]

    def _refresh_pairs(self, dragging: bool = False):
        """Conflictos de la placa; con el reorden automático, los corrige."""
        ds = self._point_dmins(self.points)
        travel = magnetics.module_travels(self.points, ds)
        pairs = magnetics.close_pairs(self.points, ds, travel)
        reordered = False
        if (self.auto_reorder and not dragging
                and any(p.kind == magnetics.KIND_SWEEP for p in pairs)):
            orden = magnetics.placement_order(self.points)
            if orden != list(range(len(self.points))):
                self.points = [self.points[i] for i in orden]
                ds = self._point_dmins(self.points)
                travel = magnetics.module_travels(self.points, ds)
                pairs = magnetics.close_pairs(self.points, ds, travel)
                reordered = True
        return ds, travel, pairs, reordered

    # ------------------------------------------------------- estado a pintar
    def canvas_state(self, dragging: bool = False) -> dict:
        ds, travel, pairs, reordered = self._refresh_pairs(dragging)
        area = self._area()
        peor = 0.0
        if self.result is not None:
            peor = self._min_distance_for(self.result.layer_z)
        return {
            "points": [[x, y, c] for x, y, c in self.points],
            "dmins": ds,
            "dmin": peor,
            "travels": travel,
            "pairs": [
                {"a": p.a, "b": p.b, "kind": p.kind, "distance": p.distance,
                 "dx": p.dx, "dy": p.dy}
                for p in pairs
            ],
            "out": limits.points_out_of_area(self.points, area),
            "stacks": magnetics.stack_groups(self.points),
            "area": list(area),
            "retreat": self._retreat(),
            "sizes": {m.color: m.diameter for m in self.settings.modules},
            "colors": self.settings.available_colors(),
            "reordered": reordered,
            "kind_sweep": magnetics.KIND_SWEEP,
        }

    def _info_html(self) -> str:
        if self.result is None:
            return html.escape(tr("left.no_file"))
        r = self.result
        temp = (f"{r.temperatura_hotend:.0f} °C" if r.temperatura_hotend
                else tr("info.temp_undetected"))
        z_txt = f"{r.layer_z:.3f} mm"
        if r.layer_z > limits.MAX_PAUSE_Z:
            z_txt = f"<span class='bad'>{z_txt}</span>"
        altura = ""
        if r.print_height is not None:
            h_txt = f"{r.print_height:.2f} mm"
            if r.print_height > limits.MAX_PRINT_HEIGHT:
                h_txt = f"<span class='bad'>{h_txt}</span>"
            altura = f"{tr('info.height')}: <b>{h_txt}</b> · "
        return (
            f"<b>{html.escape(self.name or '')}</b><br>"
            f"{altura}"
            f"{tr('info.z_pause')}: <b>{z_txt}</b> · "
            f"{tr('info.temp')}: <b>{temp}</b> · "
            f"{tr('info.centers')}: <b>{len(r.suggested_centers)}</b>"
        )

    def _area_hint(self) -> str:
        x_min, x_max, y_min, y_max = self._area()
        texto = tr("params.area_hint", xmin=f"{x_min:g}", xmax=f"{x_max:g}",
                   ymin=f"{y_min:g}", ymax=f"{y_max:g}")
        retirada = self._retreat()
        if retirada > 0.0:
            texto += "  ·  " + tr("params.area_retreat", r=f"{retirada:.1f}")
        return texto

    def _spacing_hint(self) -> str:
        if self.result is None:
            return tr("params.spacing_unknown")
        z = self.result.layer_z
        por_color = self._min_distances_for(z)
        d_min = self._min_distance_for(z)
        h = magnetics.magnet_gap(z, self.settings.worst_case_magnet()[1])
        valores = sorted(set(round(v, 1) for v in por_color.values()))
        if len(valores) > 1:
            texto_d = f"{valores[0]:.1f} – {valores[-1]:.1f}"
        else:
            texto_d = f"{d_min:.1f}"
        return tr("params.spacing_hint", h=f"{h:.2f}",
                  f=f"{magnetics.pei_force(h):.2f}", d=texto_d)

    def _match_hint(self) -> str:
        if not self.settings.hole_match_modules:
            return ""
        diametros = [m.diameter for m in self.settings.modules if m.diameter > 0]
        if not diametros:
            return tr("params.match_none")
        lista = ", ".join(f"{d:g}" for d in sorted(set(diametros)))
        return tr("params.match_range", list=lista,
                  tol=f"{self.settings.hole_diameter_tol:g}")

    def _fit_hint(self) -> str:
        medidas = self.result.hole_measurements if self.result else []
        modulos = [m for m in self.settings.modules if m.diameter > 0]
        if not medidas or not modulos:
            return tr("fit.no_holes")
        casos: dict = {}
        for hueco in medidas:
            d = hueco.inner_diameter
            modulo = min(modulos, key=lambda m: abs(m.diameter - d))
            clave = (modulo.diameter, modulo.height, round(d, 2))
            casos[clave] = casos.get(clave, 0) + 1
        lineas = []
        for (d_iman, h_iman, d_hueco), n in sorted(casos.items()):
            nivel = self.settings.fit_level(d_hueco, d_iman)
            holgura = fit.radial_clearance(d_hueco, d_iman)
            linea = tr(
                "fit.summary", magnet=f"{d_iman:g}", hole=f"{d_hueco:.2f}",
                level=tr(f"fit.{nivel}"), gap=f"{holgura:.2f}",
                count=tr("fit.count", n=n) if len(casos) > 1 or n > 1 else "",
            )
            sobre_placa = magnetics.magnet_gap(self.result.layer_z, h_iman)
            if self.settings.magnet_may_stick(nivel, sobre_placa):
                linea += " " + tr("fit.stick_hint", over=f"{sobre_placa:.1f}")
            lineas.append(linea)
        return "<br>".join(lineas)

    def ui_state(self) -> dict:
        r = self.result
        return {
            "has_file": r is not None,
            "name": self.name,
            "is_3mf": bool(r and r.is_3mf),
            "info": self._info_html(),
            "area_hint": self._area_hint(),
            "spacing_hint": self._spacing_hint(),
            "match_hint": self._match_hint(),
            "fit_hint": self._fit_hint(),
            "pause_n": (r.pause_ordinal + 1) if r else 0,
            "pause_total": r.pause_count if r else 0,
            "layer_z": r.layer_z if r else None,
            "suggested": [list(c) for c in (r.suggested_centers if r else [])],
            "pending_project": (self.pending_project or {}).get("name"),
        }

    def _layer_payload(self) -> Optional[dict]:
        """La capa de la pausa, con los arcos ya aplanados y el ancho de cada cordón."""
        r = self.result
        if r is None:
            return None
        runs = []
        for i, run in enumerate(r.layer_runs):
            start = r.layer_run_starts[i] if i < len(r.layer_run_starts) else None
            pts = geometry.flatten_run(run, start=start)
            if len(pts) < 2:
                continue
            feat = r.layer_run_features[i] if i < len(r.layer_run_features) else ""
            flat = []
            for x, y in pts:
                flat.append(round(x, 3))
                flat.append(round(y, 3))
            runs.append({
                "p": flat,
                "w": round(geometry.run_mean_width(run, r.layer_height, start=start), 3),
                "c": feature_color(feat),
                "i": bool(is_infill_feature(feat)),
            })
        return {"runs": runs, "z": r.layer_z, "layer_height": r.layer_height}

    def _full(self, **extra) -> dict:
        salida = {
            "settings": self.settings.to_dict(),
            "ui": self.ui_state(),
            "canvas": self.canvas_state(),
        }
        salida.update(extra)
        return salida

    # ------------------------------------------------------------ arranque
    def init(self, saved_settings: Optional[str] = None, lang: str = "es",
             auto_reorder: bool = True) -> dict:
        if saved_settings:
            try:
                self.settings = Settings.from_dict(json.loads(saved_settings))
            except Exception:  # noqa: BLE001 - ajustes corruptos: los de fábrica
                self.settings = Settings()
        i18n.set_language(lang)
        self.auto_reorder = bool(auto_reorder)
        return self._full(
            tr=i18n.TR,
            languages=i18n.LANGUAGES,
            language=i18n.get_language(),
            app=__app_name__,
            version=__version__,
            defaults=Settings().to_dict(),
            options={
                "diameters": list(MAGNET_DIAMETERS),
                "heights": list(MAGNET_HEIGHTS),
                "allowed_heights": {f"{d:g}": list(allowed_heights(d)) for d in MAGNET_DIAMETERS},
                "max_height": {f"{d:g}": max_height_for(d) for d in MAGNET_DIAMETERS},
                "grades": list(MAGNET_GRADES),
                "materials": list(BED_MATERIALS),
                "colors": list(MAGNET_COLORS),
                "max_modules": MAX_MODULES,
            },
        )

    def set_language(self, lang: str) -> dict:
        i18n.set_language(lang)
        return {"ui": self.ui_state(), "language": i18n.get_language()}

    # ------------------------------------------------------------- ajustes
    def _detection_key(self, s: Settings) -> tuple:
        return (
            s.hole_detection_enabled,
            s.hole_match_modules,
            round(float(s.hole_diameter_tol), 4),
            tuple(s.detection_diameters()) if s.hole_match_modules else (),
        )

    def _recompute_detection(self) -> str:
        r = self.result
        if not self.settings.hole_detection_enabled:
            r.suggested_centers = []
            r.hole_measurements = []
            return tr("status.detection_off")
        centros = pipeline.recompute_centers(r, self.settings)
        self.measurements_cache = {}
        return tr("status.recomputed", n=len(centros))

    def set_settings(self, data: dict) -> dict:
        antes = self._detection_key(self.settings)
        self.settings = Settings.from_dict(data or {})
        status = None
        if self.result is not None and self._detection_key(self.settings) != antes:
            status = self._recompute_detection()
        else:
            self.measurements_cache = {}
        return self._full(status=status)

    def rerun_detection(self) -> dict:
        if self.result is None:
            return {"error": tr("msg.no_file_first")}
        return self._full(status=self._recompute_detection())

    def reset_params(self) -> dict:
        d = Settings()
        s = self.settings
        for campo in (
            "pause_token", "offset_x", "offset_y", "offset_z", "safe_z_offset",
            "travel_feed", "default_temp", "features", "hole_detection_enabled",
            "hole_match_modules", "hole_diameter_tol", "hole_r_min", "hole_r_max",
            "hole_circularity", "hole_cluster_dist", "hole_min_arc",
            "fit_very_tight", "fit_high_gap",
        ):
            setattr(s, campo, getattr(d, campo))
        if self.result is not None:
            self._recompute_detection()
        return self._full(status=tr("status.params_reset"))

    def reset_sequences(self) -> dict:
        d = Settings()
        for campo in ("seq_red", "seq_blue", "seq_start", "seq_end", "seq_final"):
            setattr(self.settings, campo, getattr(d, campo))
        return self._full()

    def set_auto_reorder(self, auto: bool) -> dict:
        self.auto_reorder = bool(auto)
        return {"canvas": self.canvas_state()}

    # ------------------------------------------------------------- archivo
    def load_file(self, path: str, name: str) -> dict:
        ordinal = 0
        pendiente = self.pending_project
        aplica = bool(pendiente and pendiente.get("name") == name)
        if aplica:
            ordinal = int(pendiente.get("ordinal", 0) or 0)
        try:
            result = pipeline.load_and_analyze(path, self.settings, ordinal)
        except Exception as exc:  # noqa: BLE001 - mostrar al usuario
            return {"error": tr("msg.error_analyze"), "detail": str(exc)}
        self.result = result
        self.name = name
        self.path = path
        self.points_by_pause = {}
        self.acks = {k: set() for k in self.acks}
        self.measurements_cache = {}
        if aplica:
            self.points_by_pause = {int(k): _points(v) for k, v in pendiente["by_pause"].items()}
            self.pending_project = None
        self.points = list(self.points_by_pause.get(result.pause_ordinal, []))
        problemas = self._height_items(result.layer_z)
        return self._full(
            layer=self._layer_payload(),
            status=tr("status.analyzed", name=_esc(name)),
            problems=problemas,
            problems_title=tr("limits.warning_title"),
            project_applied=aplica,
        )

    def go_to_pause(self, ordinal: int) -> dict:
        if self.result is None:
            return {"error": tr("msg.no_file_first")}
        ordinal = int(ordinal)
        if not (0 <= ordinal < self.result.pause_count) or ordinal == self.result.pause_ordinal:
            return self._full()
        self._store_current_points()
        try:
            result = pipeline.select_pause(self.result, ordinal, self.settings)
        except Exception as exc:  # noqa: BLE001
            return {"error": tr("msg.error_analyze"), "detail": str(exc)}
        self.result = result
        self.points = list(self.points_by_pause.get(ordinal, []))
        return self._full(
            layer=self._layer_payload(),
            status=tr("status.pause_selected", n=ordinal + 1, total=result.pause_count,
                      z=f"{result.layer_z:.3f}"),
        )

    # -------------------------------------------------------------- imanes
    def update_points(self, points, dragging: bool = False) -> dict:
        self.points = _points(points)
        return {"canvas": self.canvas_state(dragging=bool(dragging))}

    def sort_points(self) -> dict:
        orden = magnetics.placement_order(self.points)
        self.points = [self.points[i] for i in orden]
        return {"canvas": self.canvas_state()}

    # ------------------------------------------------------------ avisos
    def _height_items(self, layer_z: float) -> List[str]:
        return [
            tr(key, token=_esc(self.settings.pause_token), **params)
            for key, params in limits.height_problems(self.result.print_height, layer_z)
        ]

    def _blocking_problems(self, points_by_pause: dict) -> List[str]:
        problemas: List[str] = []
        for ordinal in sorted(points_by_pause):
            points = points_by_pause[ordinal]
            z = self.result.pauses[ordinal].layer_z
            area = limits.reachable_area(self.settings.offset_x, self.settings.offset_y,
                                         self._retreat_for(z))
            for texto in self._height_items(z):
                problemas.append(self._label_plate(ordinal, texto))
            fuera = limits.points_out_of_area(points, area)
            if fuera:
                problemas.append(self._label_plate(
                    ordinal, tr("limits.points_outside", n=len(fuera))))
        return problemas

    def _measurements_for(self, ordinal: int):
        if self.result is None:
            return []
        if ordinal == self.result.pause_ordinal:
            return self.result.hole_measurements
        if ordinal not in self.measurements_cache:
            try:
                otra = pipeline.select_pause(self.result, ordinal, self.settings)
                self.measurements_cache[ordinal] = otra.hole_measurements
            except Exception:  # noqa: BLE001 - un aviso no puede tumbar la app
                self.measurements_cache[ordinal] = []
        return self.measurements_cache[ordinal]

    def _bed_material(self) -> str:
        del_archivo = self.result.filament_type if self.result else None
        return del_archivo or self.settings.bed_material

    def _depth_dialogs(self, pbp: dict, always_ask: bool) -> List[dict]:
        dialogos = []
        for ordinal in sorted(pbp):
            medidas = self._measurements_for(ordinal)
            if not medidas:
                continue
            casos: dict = {}
            for pila in pipeline.evaluate_stacks(medidas, pbp[ordinal], self.settings):
                if pila.fits:
                    continue
                clave = (pila.count, pila.magnet_height, round(pila.hole_depth, 2),
                         round(pila.hole_diameter, 2), round(pila.overflow, 2),
                         pila.magnet_diameter)
                casos[clave] = casos.get(clave, 0) + 1
            avisos = []
            for (cuantos, alto, prof, hueco, sobra, diam), n in sorted(casos.items()):
                params = {
                    "n": n, "count": cuantos, "height": f"{alto:g}",
                    "total": f"{fit.stack_height(cuantos, alto):g}",
                    "depth": f"{prof:.2f}", "hole": f"{hueco:.2f}",
                    "over": f"{sobra:.2f}", "fits": fit.magnets_that_fit(prof, alto),
                    "magnet": f"{diam:g}",
                }
                avisos.append(("depth.warning_shallow" if cuantos == 1
                               else "depth.warning_stack", params))
            if not avisos:
                continue
            huella = repr((ordinal, tuple(sorted(
                (c, tuple(sorted(p.items()))) for c, p in avisos))))
            if not always_ask and huella in self.acks["depth"]:
                continue
            dialogos.append({
                "kind": "depth", "fp": huella, "title": tr("depth.warning_title"),
                "items": [self._label_plate(ordinal, tr(c, **p)) for c, p in avisos],
                "footer": tr("depth.continue_anyway"),
                "cancel_status": tr("status.depth_cancelled"),
            })
        return dialogos

    def _fit_dialogs(self, pbp: dict, always_ask: bool) -> List[dict]:
        dialogos = []
        for ordinal in sorted(pbp):
            medidas = self._measurements_for(ordinal)
            if not medidas:
                continue
            casos: dict = {}
            for ajuste in pipeline.evaluate_fits(
                medidas, pbp[ordinal], self.settings,
                pause_z=self.result.pauses[ordinal].layer_z,
            ):
                motivo = None
                if fit.is_warning(ajuste.level):
                    motivo = ajuste.level
                elif self.settings.magnet_may_stick(ajuste.level, ajuste.plate_gap):
                    motivo = "stick"
                if motivo is None:
                    continue
                clave = (motivo, ajuste.magnet_diameter, round(ajuste.plate_gap, 2),
                         round(ajuste.hole_diameter, 2), ajuste.magnet_height)
                casos[clave] = casos.get(clave, 0) + 1
            avisos = []
            for (motivo, d_iman, sobre, d_hueco, _h), n in sorted(casos.items()):
                holgura = fit.radial_clearance(d_hueco, d_iman)
                avisos.append((f"fit.warning_{motivo}", {
                    "n": n, "magnet": f"{d_iman:g}", "over": f"{sobre:.1f}",
                    "hole": f"{d_hueco:.2f}", "gap": f"{abs(holgura):.2f}",
                }))
            if not avisos:
                continue
            huella = repr((ordinal, tuple(sorted(
                (c, tuple(sorted(p.items()))) for c, p in avisos))))
            if not always_ask and huella in self.acks["fit"]:
                continue
            solo_cabezal = all(c == "fit.warning_stick" for c, _ in avisos)
            dialogos.append({
                "kind": "fit", "fp": huella,
                "title": tr("fit.stick_title" if solo_cabezal else "fit.warning_title"),
                "items": [self._label_plate(ordinal, tr(c, **p)) for c, p in avisos],
                "footer": tr("fit.continue_anyway"),
                "cancel_status": tr("status.fit_cancelled"),
            })
        return dialogos

    def _spacing_dialogs(self, pbp: dict, always_ask: bool) -> List[dict]:
        dialogos = []
        for ordinal in sorted(pbp):
            points = pbp[ordinal]
            z = self.result.pauses[ordinal].layer_z
            d_mins = [self._min_distance_for_color(z, c) for _x, _y, c in points]
            pares = magnetics.close_pairs(points, d_mins,
                                          magnetics.module_travels(points, d_mins))
            if not pares:
                continue
            d_min = max(d_mins) if d_mins else self._min_distance_for(z)

            def marca(i):
                x, y, _c = points[i]
                return (round(x, 2), round(y, 2), round(d_mins[i], 2))

            huella = repr((tuple(sorted((p.kind, marca(p.a), marca(p.b)) for p in pares)),))
            if not always_ask and huella in self.acks["spacing"]:
                continue
            filas = []
            for par in pares:
                if par.kind == magnetics.KIND_SWEEP:
                    filas.append(tr("spacing.sweep_row", a=par.b + 1, b=par.a + 1,
                                    r=f"{magnetics.module_travel(d_min):.1f}"))
                else:
                    filas.append(tr("spacing.pair_row", a=par.a + 1, b=par.b + 1,
                                    d=f"{par.distance:.1f}", dx=f"{par.dx:.1f}",
                                    dy=f"{par.dy:.1f}", min=f"{d_min:.1f}"))
            parrafos = [tr("spacing.warn_body")]
            if any(p.kind == magnetics.KIND_SWEEP for p in pares):
                parrafos.append(tr("spacing.sweep_body"))
            altura = self.settings.worst_case_magnet()[1]
            h = magnetics.magnet_gap(z, altura)
            dialogos.append({
                "kind": "spacing", "fp": huella, "title": tr("spacing.warn_title"),
                "header": self._label_plate(ordinal, tr("spacing.warn_header", n=len(pares))),
                "paragraphs": parrafos, "rows": filas,
                "box": tr("spacing.live_numbers", z=f"{z:.2f}", mh=f"{altura:g}",
                          h=f"{h:.2f}", f=f"{magnetics.pei_force(h):.2f}",
                          d=f"{d_min:.1f}"),
                "accept": tr("spacing.export_anyway"),
                "details": True, "pause_z": z,
                "cancel_status": tr("status.spacing_cancelled"),
            })
        return dialogos

    def _adhesion_dialogs(self, pbp: dict, always_ask: bool) -> List[dict]:
        dialogos = []
        for ordinal in sorted(pbp):
            z = self.result.pauses[ordinal].layer_z
            avisos = limits.adhesion_problems(
                self.result.footprints, pbp[ordinal], z,
                self.settings.lateral_forces(), self._bed_material(),
                self.settings.safety_factor,
            )
            if not avisos:
                continue
            huella = repr((ordinal, tuple(sorted(
                (c, tuple(sorted(p.items()))) for c, p in avisos))))
            if not always_ask and huella in self.acks["adhesion"]:
                continue
            dialogos.append({
                "kind": "adhesion", "fp": huella, "title": tr("adhesion.warning_title"),
                "items": [self._label_plate(ordinal, tr(c, **p)) for c, p in avisos],
                "footer": tr("adhesion.continue_anyway"),
                "cancel_status": tr("status.adhesion_cancelled"),
            })
        return dialogos

    def prepare_generate(self, always_ask: bool = False) -> dict:
        """Lo que hay que enseñar antes de generar: bloqueos o riesgos a asumir."""
        if self.result is None:
            return {"error": tr("msg.no_file_first")}
        pbp = self._all_points()
        if not pbp:
            return {"error": tr("msg.no_points")}
        problemas = self._blocking_problems(pbp)
        if problemas:
            return {"blocking": {"title": tr("limits.blocked"), "items": problemas}}
        dialogos = (
            self._depth_dialogs(pbp, always_ask)
            + self._fit_dialogs(pbp, always_ask)
            + self._spacing_dialogs(pbp, always_ask)
            + self._adhesion_dialogs(pbp, always_ask)
        )
        return {"dialogs": dialogos}

    def ack(self, kind: str, fp: str) -> dict:
        if kind in self.acks:
            self.acks[kind].add(fp)
        return {}

    # ------------------------------------------------------------ generar
    def generate(self) -> dict:
        pbp = self._all_points()
        try:
            text = pipeline.generate_output_multi(self.result, pbp, self.settings)
        except Exception as exc:  # noqa: BLE001
            return {"error": tr("msg.error_generate"), "detail": str(exc)}
        n = sum(len(p) for p in pbp.values())
        return {
            "text": text,
            "info": tr("preview.lines_magnets", lines=len(text.splitlines()), n=n),
            "mark": text.find(MARK_START),
        }

    def _export_name(self, fmt: str) -> str:
        nombre = _basename(pipeline.suggest_output_path(self.name or "salida.gcode"))
        if fmt == "gcode" and not nombre.lower().endswith(".gcode"):
            for ext in (".gcode.3mf", ".3mf"):
                if nombre.lower().endswith(ext):
                    nombre = nombre[: -len(ext)] + ".gcode"
                    break
        return nombre

    def export(self, fmt: str) -> dict:
        pbp = self._all_points()
        if not pbp:
            return {"error": tr("msg.no_points")}
        fmt = "gcode" if fmt == "gcode" or not self.result.is_3mf else "3mf"
        try:
            text = pipeline.generate_output_multi(self.result, pbp, self.settings)
            os.makedirs(OUT_DIR, exist_ok=True)
            nombre = self._export_name(fmt)
            salida = os.path.join(OUT_DIR, nombre)
            usado = pipeline.save_output(self.result, text, salida)
        except Exception as exc:  # noqa: BLE001
            return {"error": tr("msg.error_export"), "detail": str(exc)}
        return {"file": salida, "name": nombre,
                "status": tr("status.exported", fmt=usado, path=_esc(nombre)),
                "message": tr("msg.exported_ok", path=_esc(nombre))}

    def build_3d(self) -> dict:
        if self.result is None:
            return {"empty": True}
        points = list(self.points)
        try:
            if points:
                text, first, last = pipeline.generate_output_with_marks(
                    self.result, points, self.settings)
            else:
                text, first, last = "".join(self.result.lines), -1, -1
        except (ValueError, KeyError) as exc:
            return {"error": str(exc)}
        z = self.result.layer_z or 0.0
        altura_sobre = [0] * len(points)
        for grupo in magnetics.stack_groups(points):
            for k, i in enumerate(grupo):
                altura_sobre[i] = len(grupo) - 1 - k
        specs = []
        for i, (x, y, color) in enumerate(points):
            modulo = self.settings.module_for_color(color)
            alto = float(modulo.height) if modulo else 3.0
            specs.append({
                "x": float(x), "y": float(y), "z": float(z) - altura_sobre[i] * alto,
                "d": float(modulo.diameter) if modulo else 5.0, "h": alto,
                "color": str(color), "polarity": modulo.polarity if modulo else "N",
            })
        return {
            "gcode": text, "markStart": first, "markEnd": last, "magnets": specs,
            "features": feature_table(),
            "i18n": {k: tr(k) for k in VIEWER_TEXT_KEYS},
        }

    # ---------------------------------------------------- secuencia de prueba
    def set_template(self, path: str) -> dict:
        if not pipeline.is_valid_bambu_template(path):
            return {"error": tr("msg.template_invalid", path=_esc(_basename(path)))}
        self.template_path = path
        return {"ok": True}

    def test_sequence(self, fmt: str) -> dict:
        if self.result is not None:
            z = self.result.layer_z
            temp = (self.result.temperatura_hotend
                    if self.result.temperatura_hotend is not None
                    else self.settings.default_temp)
        else:
            z = pipeline.TEST_Z_FALLBACK
            temp = self.settings.default_temp
        nombre = _basename(pipeline.suggest_test_output_path(self.name))
        template = None
        if fmt == "gcode":
            nombre = nombre[: -len(".3mf")] + ".gcode"
        else:
            if self.result is not None and pipeline.is_valid_bambu_template(self.path):
                template = self.path
            elif self.template_path and pipeline.is_valid_bambu_template(self.template_path):
                template = self.template_path
            else:
                return {"need_template": True, "message": tr("msg.template_needed")}
        try:
            text = pipeline.build_test_sequence(self.settings, z, temp)
            os.makedirs(OUT_DIR, exist_ok=True)
            salida = os.path.join(OUT_DIR, nombre)
            usado = pipeline.save_test_sequence(text, salida, template)
        except Exception as exc:  # noqa: BLE001
            return {"error": tr("msg.error_export"), "detail": str(exc)}
        return {
            "file": salida, "name": nombre,
            "status": tr("status.exported", fmt=usado, path=_esc(nombre)),
            "message": tr("msg.test_exported_ok", path=_esc(nombre), z=f"{z:.3f}",
                          temp=f"{temp:.0f}"),
        }

    # ------------------------------------------------------------ proyectos
    def save_project(self) -> dict:
        ordinal = self.result.pause_ordinal if self.result else 0
        proj = Project(
            input_path=self.name or "",
            points=list(self.points),
            settings=self.settings,
            points_by_pause=self._all_points() if self.result else {},
            pause_ordinal=ordinal,
        )
        base = os.path.splitext(self.name)[0] if self.name else "proyecto"
        return {"text": json.dumps(proj.to_dict(), indent=2, ensure_ascii=False),
                "name": base + ".mip"}

    def load_project(self, text: str) -> dict:
        try:
            proj = Project.from_dict(json.loads(text))
        except Exception as exc:  # noqa: BLE001
            return {"error": tr("msg.error_analyze"), "detail": str(exc)}
        self.settings = proj.settings
        nombre = _basename(proj.input_path)
        by_pause = {k: list(v) for k, v in proj.points_by_pause.items()}
        if self.result is not None and nombre and nombre == self.name:
            # El mismo archivo ya está abierto: se reanaliza con los ajustes del
            # proyecto y su placa, y se reponen los imanes de cada una.
            self.pending_project = {"name": nombre, "ordinal": proj.pause_ordinal,
                                    "by_pause": by_pause}
            return self.load_file(self.path, self.name)
        self.result = None
        self.name = None
        self.path = None
        self.points_by_pause = {}
        self.points = list(proj.points)
        self.pending_project = (
            {"name": nombre, "ordinal": proj.pause_ordinal, "by_pause": by_pause}
            if nombre else None
        )
        return self._full(
            layer=None,
            warn=tr("msg.project_missing_file", path=_esc(nombre)) if nombre else None,
        )

    # --------------------------------------------------------- información
    def spacing_info(self) -> dict:
        """El contenido de «¿Por qué? Ver los detalles…», sin los dibujos."""
        pause_z = self.result.layer_z if self.result else None
        diameter, height = self.settings.worst_case_magnet()
        peor = (max(self.settings.modules, key=lambda m: m.lateral_force())
                if self.settings.modules else None)
        grade = peor.grade if peor else adhesion.DEFAULT_GRADE
        pull_kg = peor.pull_kg if peor else 0.0

        partes: List[str] = [f"<p>{tr('spacing.model_intro')}</p>"]
        if pause_z is not None:
            h = magnetics.magnet_gap(pause_z, height)
            partes.append("<div class='box'>" + tr(
                "spacing.live_numbers", z=f"{pause_z:.2f}", mh=f"{height:g}",
                h=f"{h:.2f}", f=f"{magnetics.pei_force(h):.2f}",
                d=f"{magnetics.min_safe_distance(h, diameter):.1f}") + "</div>")
        alturas = (0.0, 2.0, 4.0, 5.0, 6.0, 7.0, 8.0)
        partes.append(
            "<table class='mini'>"
            f"<tr><th>{tr('spacing.table_h')}</th>"
            + "".join(f"<td>{h:g}</td>" for h in alturas) + "</tr>"
            f"<tr><th>{tr('spacing.table_d')}</th>"
            + "".join(f"<td><b>{magnetics.min_safe_distance(h, diameter):.1f}</b></td>"
                      for h in alturas) + "</tr></table>"
        )
        tope = magnetics.MAX_SAFE_DISTANCE + diameter
        partes.append(f"<p>{tr('spacing.cap', tope=f'{tope:g}')}</p>")
        partes.append(f"<p>{tr('spacing.radial', tope=f'{tope:g}')}</p>")
        if pause_z is not None:
            h = magnetics.magnet_gap(pause_z, height)
            recorrido = magnetics.module_travel(magnetics.min_safe_distance(h, diameter))
            partes.append(f"<p>{tr('spacing.module_sweep', r=f'{recorrido:.1f}')}</p>")
        else:
            partes.append(f"<p>{tr('spacing.module_sweep_unknown')}</p>")
        partes.append(f"<p>{tr('spacing.zero_friction')}</p>")
        partes.append(f"<h4>{tr('spacing.case_friction_title')}</h4>")
        partes.append("<p>" + tr(
            "spacing.case_friction_body", d=f"{magnetics.FRICTION_MIN_DISTANCE:g}",
            ejemplo=f"{magnetics.min_safe_distance(10.0, diameter):.1f}") + "</p>")
        partes.append(f"<h4>{tr('spacing.case_deep_title', ratio=f'{magnetics.DEEP_HOLE_RATIO:g}')}</h4>")
        partes.append("<p>" + tr(
            "spacing.case_deep_body", ratio=f"{magnetics.DEEP_HOLE_RATIO:g}",
            prof=f"{height * magnetics.DEEP_HOLE_RATIO:g}", diam=f"{diameter:g}",
            alto=f"{height:g}",
            diag=f"{magnetics.escape_diagonal(diameter, height):.2f}",
            falta=f"{magnetics.tilt_clearance(diameter, height):.2f}") + "</p>")
        fuerza = adhesion.lateral_force(diameter, height, grade, pull_kg)
        partes.append(f"<h4>{tr('info.adhesion_title')}</h4>")
        partes.append("<p>" + tr(
            "info.adhesion_body", force=f"{fuerza:.1f}",
            z=f"{pause_z:.1f}" if pause_z is not None else "—") + "</p>")
        if pause_z is not None and pause_z > 0:
            lados = (10.0, 20.0, 30.0, 40.0, 60.0)
            aguantes = [adhesion.max_lateral_force(b * b, b ** 3 / 6.0, pause_z).limit
                        for b in lados]
            partes.append(f"<p>{tr('info.adhesion_table', z=f'{pause_z:.1f}')}</p>")
            partes.append(
                "<table class='mini'>"
                f"<tr><th>{tr('adh.table_b')}</th>"
                + "".join(f"<td>{b:g}</td>" for b in lados) + "</tr>"
                f"<tr><th>{tr('adh.table_f')}</th>"
                + "".join(f"<td><b>{f:.1f}</b></td>" for f in aguantes) + "</tr></table>"
            )
        return {"title": tr("spacing.info_title"), "html": "".join(partes)}


APP = WebApp()


def call(name: str, args_json: str = "[]") -> str:
    """Punto de entrada único desde JavaScript: ``(nombre, args en JSON) → JSON``."""
    try:
        args = json.loads(args_json or "[]")
        fn = getattr(APP, name, None)
        if fn is None or name.startswith("_"):
            raise AttributeError(f"Función desconocida: {name}")
        if isinstance(args, dict):
            result = fn(**args)
        else:
            result = fn(*args)
        return json.dumps(result if result is not None else {}, ensure_ascii=False)
    except Exception as exc:  # noqa: BLE001 - el error viaja a la página
        return json.dumps({"error": tr("msg.error_generate"), "detail": str(exc),
                           "trace": traceback.format_exc()}, ensure_ascii=False)
