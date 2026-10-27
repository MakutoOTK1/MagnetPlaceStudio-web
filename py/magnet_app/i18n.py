# -*- coding: utf-8 -*-
"""Internacionalización ligera basada en diccionarios (sin toolchain de Qt).

Uso:
    from .i18n import tr, set_language
    set_language("en")
    label.setText(tr("menu.open_file"))

``tr`` admite parámetros con formato: ``tr("lic.active", name=…, edition=…, exp=…)``.
El idioma activo es global; al cambiarlo, la ventana se "retraduce".
"""
from __future__ import annotations

# (código, nombre nativo) — orden de aparición en el selector
LANGUAGES = [
    ("es", "Español"),
    ("en", "English"),
    ("zh", "中文"),
    ("ja", "日本語"),
    ("it", "Italiano"),
    ("fr", "Français"),
    ("de", "Deutsch"),
    ("pt", "Português"),
]

_DEFAULT = "es"
_current = _DEFAULT


def available_languages():
    return list(LANGUAGES)


def language_name(code: str) -> str:
    for c, n in LANGUAGES:
        if c == code:
            return n
    return code


def get_language() -> str:
    return _current


def set_language(code: str) -> None:
    global _current
    _current = code if any(c == code for c, _ in LANGUAGES) else _DEFAULT


def tr(key: str, **kwargs) -> str:
    entry = TR.get(key)
    if entry is None:
        return key
    text = entry.get(_current) or entry.get("en") or entry.get("es") or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text


# clave -> { idioma -> texto }
TR = {
    # --- menú ---
    "menu.file": {"es": "&Archivo", "en": "&File", "zh": "文件(&F)", "ja": "ファイル(&F)",
                  "it": "&File", "fr": "&Fichier", "de": "&Datei", "pt": "&Arquivo"},
    "menu.open_file": {"es": "Abrir archivo…", "en": "Open file…", "zh": "打开文件…",
                       "ja": "ファイルを開く…", "it": "Apri file…", "fr": "Ouvrir un fichier…",
                       "de": "Datei öffnen…", "pt": "Abrir arquivo…"},
    "menu.open_project": {"es": "Abrir proyecto…", "en": "Open project…", "zh": "打开项目…",
                          "ja": "プロジェクトを開く…", "it": "Apri progetto…",
                          "fr": "Ouvrir un projet…", "de": "Projekt öffnen…",
                          "pt": "Abrir projeto…"},
    "menu.save_project": {"es": "Guardar proyecto…", "en": "Save project…", "zh": "保存项目…",
                          "ja": "プロジェクトを保存…", "it": "Salva progetto…",
                          "fr": "Enregistrer le projet…", "de": "Projekt speichern…",
                          "pt": "Salvar projeto…"},
    "menu.export": {"es": "Exportar G-code / 3MF…", "en": "Export G-code / 3MF…",
                    "zh": "导出 G-code / 3MF…", "ja": "G-code / 3MF をエクスポート…",
                    "it": "Esporta G-code / 3MF…", "fr": "Exporter G-code / 3MF…",
                    "de": "G-code / 3MF exportieren…", "pt": "Exportar G-code / 3MF…"},
    "menu.preferences": {"es": "Preferencias…", "en": "Preferences…", "zh": "首选项…",
                         "ja": "環境設定…", "it": "Preferenze…", "fr": "Préférences…",
                         "de": "Einstellungen…", "pt": "Preferências…"},
    "menu.exit": {"es": "Salir", "en": "Exit", "zh": "退出", "ja": "終了",
                  "it": "Esci", "fr": "Quitter", "de": "Beenden", "pt": "Sair"},
    "menu.view": {"es": "&Ver", "en": "&View", "zh": "视图(&V)", "ja": "表示(&V)",
                  "it": "&Vista", "fr": "&Affichage", "de": "&Ansicht", "pt": "&Exibir"},
    "menu.theme_to_light": {"es": "Cambiar a tema claro", "en": "Switch to light theme",
                            "zh": "切换到浅色主题", "ja": "ライトテーマに切り替え",
                            "it": "Passa al tema chiaro", "fr": "Passer au thème clair",
                            "de": "Zum hellen Thema wechseln", "pt": "Mudar para tema claro"},
    "menu.theme_to_dark": {"es": "Cambiar a tema oscuro", "en": "Switch to dark theme",
                           "zh": "切换到深色主题", "ja": "ダークテーマに切り替え",
                           "it": "Passa al tema scuro", "fr": "Passer au thème sombre",
                           "de": "Zum dunklen Thema wechseln", "pt": "Mudar para tema escuro"},
    "menu.hide_infill": {"es": "Ocultar relleno (infill)", "en": "Hide infill",
                         "zh": "隐藏填充", "ja": "インフィルを隠す",
                         "it": "Nascondi riempimento", "fr": "Masquer le remplissage",
                         "de": "Füllung ausblenden", "pt": "Ocultar preenchimento"},
    "menu.view_2d": {"es": "Vista 2D (placa)", "en": "2D view (bed)", "zh": "2D 视图（热床）",
                     "ja": "2Dビュー（ベッド）", "it": "Vista 2D (piano)", "fr": "Vue 2D (plateau)",
                     "de": "2D-Ansicht (Druckbett)", "pt": "Vista 2D (mesa)"},
    "menu.view_3d": {"es": "Vista 3D (simulación)", "en": "3D view (simulation)",
                     "zh": "3D 视图（模拟）", "ja": "3Dビュー（シミュレーション）",
                     "it": "Vista 3D (simulazione)", "fr": "Vue 3D (simulation)",
                     "de": "3D-Ansicht (Simulation)", "pt": "Vista 3D (simulação)"},
    "menu.help": {"es": "A&yuda", "en": "&Help", "zh": "帮助(&H)", "ja": "ヘルプ(&H)",
                  "it": "&Aiuto", "fr": "A&ide", "de": "&Hilfe", "pt": "A&juda"},
    "menu.license": {"es": "Licencia…", "en": "License…", "zh": "许可证…", "ja": "ライセンス…",
                     "it": "Licenza…", "fr": "Licence…", "de": "Lizenz…", "pt": "Licença…"},
    "menu.about": {"es": "Acerca de {app}", "en": "About {app}", "zh": "关于 {app}",
                   "ja": "{app} について", "it": "Informazioni su {app}", "fr": "À propos de {app}",
                   "de": "Über {app}", "pt": "Sobre o {app}"},
    # --- calibración ---
    # Los textos nuevos van en español e inglés; los otros seis idiomas se
    # completan en tandas (ver tests/test_i18n.py).
    "menu.calibration": {"es": "&Calibración", "en": "&Calibration"},
    "calib.menu_beginner": {"es": "1. Beginner test", "en": "1. Beginner test"},
    "calib.menu_offsets": {"es": "2. Offsets test", "en": "2. Offsets test"},
    "calib.menu_slot3": {"es": "3. (próximamente)", "en": "3. (coming soon)"},
    "calib.menu_coming_soon": {"es": "{name} (próximamente)", "en": "{name} (coming soon)"},
    "calib.title": {"es": "¡Calibra tu MagnetPlace!", "en": "Calibrate your MagnetPlace!"},
    "calib.first_run_hint": {
        "es": "Puedes volver aquí cuando quieras desde el menú «Calibración».",
        "en": "You can come back any time from the “Calibration” menu."},
    "calib.step_counter": {"es": "Paso {n} de {total}", "en": "Step {n} of {total}"},
    "calib.prev": {"es": "‹ Anterior", "en": "‹ Back"},
    "calib.next": {"es": "Siguiente ›", "en": "Next ›"},
    "calib.skip": {"es": "Omitir", "en": "Skip"},
    "calib.download": {"es": "Descargar {file}", "en": "Download {file}"},
    "calib.skip_confirm_title": {"es": "¿Estás seguro?", "en": "Are you sure?"},
    "calib.skip_confirm_body": {
        "es": "La calibración es lo que hace que los imanes caigan donde tienen que "
              "caer. Si la omites ahora, podrás hacerla en cualquier momento desde "
              "el menú «Calibración».\n\n¿Seguro que quieres omitirla?",
        "en": "Calibration is what makes the magnets land where they should. If you "
              "skip it now, you can run it any time from the “Calibration” menu.\n\n"
              "Skip it anyway?"},
    "calib.missing_image": {"es": "(falta la imagen: {name})", "en": "(missing image: {name})"},
    "calib.missing_video": {"es": "(falta el vídeo: {name})", "en": "(missing video: {name})"},
    "calib.save_title": {"es": "Guardar {file}", "en": "Save {file}"},
    "calib.saved": {"es": "Archivo guardado:\n{path}\n\nÁbrelo en Bambu Studio para "
                          "continuar con la prueba.",
                    "en": "File saved:\n{path}\n\nOpen it in Bambu Studio to carry on "
                          "with the test."},
    "calib.save_error": {"es": "No se ha podido guardar el archivo:\n{error}",
                         "en": "The file could not be saved:\n{error}"},
    "calib.missing_file_title": {"es": "Falta el archivo de la prueba",
                                 "en": "The test file is missing"},
    "calib.missing_file_body": {
        "es": "No se encuentra {file} en esta instalación.\n\nDebería estar en:\n{dir}",
        "en": "{file} cannot be found in this installation.\n\nIt should be in:\n{dir}"},

    "calib.beginner.name": {"es": "Prueba de iniciación", "en": "Beginner test"},
    "calib.beginner.intro": {
        "es": "Dos vídeos para comprobar que tu MagnetPlace coloca imanes como debe: "
              "primero la comprobación a mano, después la prueba automática.",
        "en": "Two videos to check that your MagnetPlace places magnets the way it "
              "should: first the check by hand, then the automatic test."},
    "calib.beginner.s1.title": {"es": "Antes de nada, compruébalo a mano",
                                "en": "First, check it by hand"},
    "calib.beginner.s1.body": {
        "es": "Haz lo que ves en el vídeo <b>antes</b> de descargar el archivo y "
              "mandarlo a la impresora. Si a mano algo no encaja, la prueba "
              "automática tampoco saldrá bien.",
        "en": "Do what the video shows <b>before</b> you download the file and send "
              "it to the printer. If something doesn't fit by hand, the automatic "
              "test won't go right either."},
    "calib.beginner.s2.title": {"es": "La prueba automática",
                                "en": "The automatic test"},
    "calib.beginner.s2.body": {
        "es": "Esto es lo que hará tu A1 con <b>MagnetPlace_Calibration.3mf</b>. "
              "Descárgalo con el botón de abajo, ábrelo en Bambu Studio, envíalo a la "
              "impresora y comprueba que hace lo mismo que en el vídeo.",
        "en": "This is what your A1 will do with <b>MagnetPlace_Calibration.3mf</b>. "
              "Download it with the button below, open it in Bambu Studio, send it to "
              "the printer and check that it does the same as in the video."},

    "calib.offsets.name": {"es": "Prueba de offsets", "en": "Offsets test"},
    "calib.offsets.intro": {
        "es": "La misma pauta, pero para afinar la puntería: esta pieza te dice cuánto "
              "se desvía el imán en X y en Y para que lo corrijas.",
        "en": "Same routine, but for aim: this part tells you how far the magnet "
              "drifts in X and Y so you can correct it."},
    "calib.offsets.s1.title": {"es": "Descarga el archivo de offsets",
                               "en": "Download the offsets file"},
    "calib.offsets.s1.body": {
        "es": "El botón del final descarga <b>MagnetPlace_Offsets.3mf</b>: una rejilla "
              "de agujeros con marcas de referencia alrededor.",
        "en": "The button at the end downloads <b>MagnetPlace_Offsets.3mf</b>: a grid "
              "of holes with reference marks around it."},
    "calib.offsets.s2.title": {"es": "Ábrelo en Bambu Studio",
                               "en": "Open it in Bambu Studio"},
    "calib.offsets.s2.body": {
        "es": "Ábrelo y lamínalo sin mover la pieza de sitio: la rejilla tiene que "
              "quedar donde viene, o las marcas dejan de valer.",
        "en": "Open and slice it without moving the part: the grid has to stay where "
              "it comes, or the marks no longer mean anything."},
    "calib.offsets.s3.title": {"es": "Imprímela entera",
                               "en": "Print the whole thing"},
    "calib.offsets.s3.body": {
        "es": "Envía el trabajo y déjalo terminar. Colocará un imán en cada agujero de "
              "la rejilla, uno por pausa.",
        "en": "Send the job and let it finish. It places one magnet in each hole of "
              "the grid, one per pause."},
    "calib.offsets.s4.title": {"es": "Mide el desvío y anótalo",
                               "en": "Measure the drift and write it down"},
    "calib.offsets.s4.body": {
        "es": "Mira dónde ha caído cada imán respecto a la marca de su agujero: eso es "
              "el desvío. Apunta los milímetros en X y en Y (con su signo) y súmalos "
              "a <b>Offset X</b> y <b>Offset Y</b>, en la pestaña <b>Parámetros</b>.",
        "en": "Look at where each magnet landed against the mark on its hole: that is "
              "the drift. Write down the millimetres in X and Y (with their sign) and "
              "add them to <b>Offset X</b> and <b>Offset Y</b>, on the "
              "<b>Parameters</b> tab."},
    # --- toolbar ---
    "tb.preview": {"es": "Generar vista previa", "en": "Generate preview", "zh": "生成预览",
                   "ja": "プレビューを生成", "it": "Genera anteprima", "fr": "Générer un aperçu",
                   "de": "Vorschau erzeugen", "pt": "Gerar pré-visualização"},
    # --- panel izquierdo ---
    "left.no_file": {"es": "Sin archivo cargado.", "en": "No file loaded.", "zh": "未加载文件。",
                     "ja": "ファイルが読み込まれていません。", "it": "Nessun file caricato.",
                     "fr": "Aucun fichier chargé.", "de": "Keine Datei geladen.",
                     "pt": "Nenhum arquivo carregado."},
    "left.magnet_to_place": {"es": "Imán a colocar:", "en": "Magnet to place:",
                             "zh": "要放置的磁铁：", "ja": "配置する磁石：",
                             "it": "Magnete da posizionare:", "fr": "Aimant à placer :",
                             "de": "Zu platzierender Magnet:", "pt": "Ímã a colocar:"},
    "left.red": {"es": "Rojo (M)", "en": "Red (M)", "zh": "红色 (M)", "ja": "赤 (M)",
                 "it": "Rosso (M)", "fr": "Rouge (M)", "de": "Rot (M)", "pt": "Vermelho (M)"},
    "left.no_module": {"es": "No hay ningún imán de este color (pestaña Imanes)",
                       "en": "There is no magnet of this colour (Magnets tab)",
                       "zh": "没有此颜色的模块（模块选项卡）",
                       "ja": "この色のモジュールがありません（モジュールタブ）",
                       "it": "Non c'è nessun modulo di questo colore (scheda Moduli)",
                       "fr": "Aucun module de cette couleur (onglet Modules)",
                       "de": "Es gibt kein Modul dieser Farbe (Reiter Module)",
                       "pt": "Não há nenhum módulo desta cor (separador Módulos)"},
    "left.blue": {"es": "Azul (N)", "en": "Blue (N)", "zh": "蓝色 (N)", "ja": "青 (N)",
                  "it": "Blu (N)", "fr": "Bleu (N)", "de": "Blau (N)", "pt": "Azul (N)"},
    # --- pestañas ---
    "tab.points": {"es": "Puntos", "en": "Points", "zh": "点位", "ja": "ポイント",
                   "it": "Punti", "fr": "Points", "de": "Punkte", "pt": "Pontos"},
    "tab.params": {"es": "Parámetros", "en": "Parameters", "zh": "参数", "ja": "パラメータ",
                   "it": "Parametri", "fr": "Paramètres", "de": "Parameter", "pt": "Parâmetros"},
    "tab.sequences": {"es": "Secuencias", "en": "Sequences", "zh": "序列", "ja": "シーケンス",
                      "it": "Sequenze", "fr": "Séquences", "de": "Sequenzen", "pt": "Sequências"},
    "tab.preview": {"es": "Vista previa", "en": "Preview", "zh": "预览", "ja": "プレビュー",
                    "it": "Anteprima", "fr": "Aperçu", "de": "Vorschau", "pt": "Pré-visualização"},
    # --- pestaña puntos ---
    "points.placed": {"es": "Imanes colocados:", "en": "Placed magnets:", "zh": "已放置的磁铁：",
                      "ja": "配置済みの磁石：", "it": "Magneti posizionati:",
                      "fr": "Aimants placés :", "de": "Platzierte Magnete:", "pt": "Ímãs colocados:"},
    "points.delete_selected": {"es": "Borrar seleccionado", "en": "Delete selected",
                               "zh": "删除选中", "ja": "選択を削除", "it": "Elimina selezionato",
                               "fr": "Supprimer la sélection", "de": "Auswahl löschen",
                               "pt": "Excluir selecionado"},
    "points.delete_all": {"es": "Borrar todos", "en": "Delete all", "zh": "全部删除",
                          "ja": "すべて削除", "it": "Elimina tutti", "fr": "Tout supprimer",
                          "de": "Alle löschen", "pt": "Excluir todos"},
    # --- pestaña parámetros ---
    "params.advanced": {"es": "Avanzado", "en": "Advanced", "zh": "高级", "ja": "詳細設定",
                        "it": "Avanzate", "fr": "Avancé", "de": "Erweitert",
                        "pt": "Avançado"},
    "params.pause_token": {"es": "Token de pausa:", "en": "Pause token:", "zh": "暂停标记：",
                           "ja": "一時停止トークン：", "it": "Token di pausa:",
                           "fr": "Jeton de pause :", "de": "Pause-Token:", "pt": "Token de pausa:"},
    "params.offset_x": {"es": "Offset X (mm):", "en": "Offset X (mm):", "zh": "偏移 X (mm)：",
                        "ja": "オフセット X (mm)：", "it": "Offset X (mm):", "fr": "Décalage X (mm) :",
                        "de": "Versatz X (mm):", "pt": "Deslocamento X (mm):"},
    "params.offset_y": {"es": "Offset Y (mm):", "en": "Offset Y (mm):", "zh": "偏移 Y (mm)：",
                        "ja": "オフセット Y (mm)：", "it": "Offset Y (mm):", "fr": "Décalage Y (mm) :",
                        "de": "Versatz Y (mm):", "pt": "Deslocamento Y (mm):"},
    "params.offset_z": {"es": "Offset Z (mm):", "en": "Offset Z (mm):", "zh": "偏移 Z (mm)：",
                        "ja": "オフセット Z (mm)：", "it": "Offset Z (mm):", "fr": "Décalage Z (mm) :",
                        "de": "Versatz Z (mm):", "pt": "Deslocamento Z (mm):"},
    "params.safe_z": {"es": "Safe Z offset (mm):", "en": "Safe Z offset (mm):",
                      "zh": "安全 Z 偏移 (mm)：", "ja": "安全 Z オフセット (mm)：",
                      "it": "Offset Z sicuro (mm):", "fr": "Décalage Z sûr (mm) :",
                      "de": "Sicherer Z-Versatz (mm):", "pt": "Offset Z seguro (mm):"},
    "params.travel_feed": {"es": "Avance de viaje (F):", "en": "Travel feed (F):",
                           "zh": "空驶进给 (F)：", "ja": "移動送り (F)：",
                           "it": "Avanzamento spostamento (F):", "fr": "Vitesse de déplacement (F) :",
                           "de": "Eilgang-Vorschub (F):", "pt": "Avanço de viagem (F):"},
    "params.default_temp": {"es": "Temp. por defecto (°C):", "en": "Default temp. (°C):",
                            "zh": "默认温度 (°C)：", "ja": "既定温度 (°C)：",
                            "it": "Temp. predefinita (°C):", "fr": "Temp. par défaut (°C) :",
                            "de": "Standardtemp. (°C):", "pt": "Temp. padrão (°C):"},
    "params.features": {"es": "Features (coma):", "en": "Features (comma):", "zh": "特征（逗号）：",
                        "ja": "フィーチャー（カンマ）：", "it": "Feature (virgola):",
                        "fr": "Features (virgule) :", "de": "Features (Komma):",
                        "pt": "Features (vírgula):"},
    # --- área alcanzable por el colocador ---
    "params.area_header": {"es": "Área alcanzable por el colocador",
                           "en": "Area the placer can reach", "zh": "放置器可达区域",
                           "ja": "設置ヘッドが届く範囲",
                           "it": "Area raggiungibile dal posizionatore",
                           "fr": "Zone atteignable par le poseur",
                           "de": "Vom Setzer erreichbarer Bereich",
                           "pt": "Área alcançável pelo colocador"},
    "params.show_area": {"es": "Mostrar el área en el visor",
                         "en": "Show the area in the viewer", "zh": "在视图中显示该区域",
                         "ja": "ビューに範囲を表示", "it": "Mostra l'area nel visore",
                         "fr": "Afficher la zone dans la vue",
                         "de": "Bereich in der Ansicht zeigen",
                         "pt": "Mostrar a área no visor"},
    "params.area_hint": {"es": "X {xmin} – {xmax} mm  ·  Y {ymin} – {ymax} mm",
                         "en": "X {xmin} – {xmax} mm  ·  Y {ymin} – {ymax} mm",
                         "zh": "X {xmin} – {xmax} mm  ·  Y {ymin} – {ymax} mm",
                         "ja": "X {xmin} – {xmax} mm  ·  Y {ymin} – {ymax} mm",
                         "it": "X {xmin} – {xmax} mm  ·  Y {ymin} – {ymax} mm",
                         "fr": "X {xmin} – {xmax} mm  ·  Y {ymin} – {ymax} mm",
                         "de": "X {xmin} – {xmax} mm  ·  Y {ymin} – {ymax} mm",
                         "pt": "X {xmin} – {xmax} mm  ·  Y {ymin} – {ymax} mm"},
    # Sólo aparece cuando la retirada es la que recorta el área por la derecha:
    # si no, el borde lo explica la cama y este número sobra.
    "params.area_retreat": {"es": "retirada del cabezal {r} mm en +X",
                            "en": "head retreat {r} mm in +X"},
    # --- distancia mínima entre imanes ---
    "params.spacing_header": {"es": "Distancia mínima entre imanes",
                              "en": "Minimum distance between magnets",
                              "zh": "磁铁之间的最小距离", "ja": "磁石どうしの最小距離",
                              "it": "Distanza minima tra magneti",
                              "fr": "Distance minimale entre aimants",
                              "de": "Mindestabstand zwischen Magneten",
                              "pt": "Distância mínima entre ímãs"},
    "params.show_spacing": {"es": "Mostrar el círculo de seguridad de cada imán",
                            "en": "Show each magnet's safety circle",
                            "zh": "显示每个磁铁的安全圈",
                            "ja": "各磁石の安全円を表示",
                            "it": "Mostra il cerchio di sicurezza di ogni magnete",
                            "fr": "Afficher le cercle de sécurité de chaque aimant",
                            "de": "Sicherheitskreis jedes Magneten anzeigen",
                            "pt": "Mostrar o círculo de segurança de cada ímã"},
    "params.auto_reorder": {
        "es": "Reordenar la colocación si el recorrido del módulo pisa un imán",
        "en": "Reorder placement when the module’s travel runs over a magnet",
        "zh": "当模块退避路径经过磁铁时，自动重排放置顺序",
        "ja": "モジュールの退避経路が磁石の上を通るときは配置順を並べ替える",
        "it": "Riordina la posa se la corsa del modulo passa sopra un magnete",
        "fr": "Réordonner la pose si la course du module passe sur un aimant",
        "de": "Setzreihenfolge ändern, wenn der Rückzug über einen Magneten führt",
        "pt": "Reordenar a colocação se o percurso do módulo passar por cima de um íman"},
    "params.spacing_hint": {
        "es": "h = {h} mm sobre la placa  ·  la placa sujeta {f} N  ·  mínimo {d} mm",
        "en": "h = {h} mm above the plate  ·  the plate holds {f} N  ·  minimum {d} mm",
        "zh": "h = {h} mm（离板面）  ·  板面吸力 {f} N  ·  最小 {d} mm",
        "ja": "h = {h} mm（プレートから）  ·  プレートの保持力 {f} N  ·  最小 {d} mm",
        "it": "h = {h} mm sopra il piano  ·  il piano trattiene {f} N  ·  minimo {d} mm",
        "fr": "h = {h} mm au-dessus du plateau  ·  le plateau retient {f} N  ·  minimum {d} mm",
        "de": "h = {h} mm über der Platte  ·  die Platte hält {f} N  ·  Minimum {d} mm",
        "pt": "h = {h} mm acima da placa  ·  a placa segura {f} N  ·  mínimo {d} mm"},
    "params.spacing_unknown": {
        "es": "Abre un archivo: el mínimo depende de la Z de la pausa",
        "en": "Open a file: the minimum depends on the pause Z",
        "zh": "请打开文件：最小值取决于暂停的 Z 高度",
        "ja": "ファイルを開いてください：最小値は一時停止の Z に依存します",
        "it": "Apri un file: il minimo dipende dalla Z della pausa",
        "fr": "Ouvrez un fichier : le minimum dépend du Z de la pause",
        "de": "Datei öffnen: das Minimum hängt vom Pausen-Z ab",
        "pt": "Abra um arquivo: o mínimo depende do Z da pausa"},
    "params.spacing_info": {"es": "¿Por qué? Ver los detalles…",
                            "en": "Why? See the details…", "zh": "为什么？查看详情…",
                            "ja": "なぜ？詳細を見る…", "it": "Perché? Vedi i dettagli…",
                            "fr": "Pourquoi ? Voir les détails…",
                            "de": "Warum? Details ansehen…",
                            "pt": "Porquê? Ver os detalhes…"},
    "params.detection_header": {"es": "Detección de agujeros (centros de círculos)",
                                "en": "Hole detection (circle centers)", "zh": "孔检测（圆心）",
                                "ja": "穴検出（円の中心）", "it": "Rilevamento fori (centri dei cerchi)",
                                "fr": "Détection des trous (centres des cercles)",
                                "de": "Locherkennung (Kreismittelpunkte)",
                                "pt": "Detecção de furos (centros de círculos)"},
    "params.detection_enable": {"es": "Activar detección de agujeros", "en": "Enable hole detection",
                                "zh": "启用孔检测", "ja": "穴検出を有効にする",
                                "it": "Attiva rilevamento fori", "fr": "Activer la détection des trous",
                                "de": "Locherkennung aktivieren", "pt": "Ativar detecção de furos"},
    "params.match_modules": {
        "es": "Sólo agujeros del diámetro de mis imanes",
        "en": "Only holes matching my magnet diameters",
        "zh": "仅检测与磁铁直径相符的孔",
        "ja": "自分の磁石の直径に合う穴だけ",
        "it": "Solo fori del diametro dei miei magneti",
        "fr": "Seulement les trous au diamètre de mes aimants",
        "de": "Nur Löcher im Durchmesser meiner Magnete",
        "pt": "Só furos com o diâmetro dos meus ímãs"},
    "params.diam_tol": {
        "es": "Margen de diámetro (± mm):", "en": "Diameter margin (± mm):",
        "zh": "直径公差 (± mm)：", "ja": "直径の許容差 (± mm)：",
        "it": "Margine di diametro (± mm):", "fr": "Marge de diamètre (± mm) :",
        "de": "Durchmessertoleranz (± mm):", "pt": "Margem de diâmetro (± mm):"},
    "params.match_range": {
        "es": "Buscando agujeros de Ø {list} mm (± {tol} mm), medidos en la pared.",
        "en": "Looking for Ø {list} mm holes (± {tol} mm), measured at the wall.",
        "zh": "正在查找 Ø {list} mm 的孔（± {tol} mm），按孔壁测量。",
        "ja": "Ø {list} mm の穴を探しています（± {tol} mm、穴の壁で測定）。",
        "it": "Cerco fori da Ø {list} mm (± {tol} mm), misurati sulla parete.",
        "fr": "Recherche de trous de Ø {list} mm (± {tol} mm), mesurés à la paroi.",
        "de": "Es wird nach Löchern mit Ø {list} mm gesucht (± {tol} mm), an der Wand gemessen.",
        "pt": "A procurar furos de Ø {list} mm (± {tol} mm), medidos na parede."},
    "params.match_none": {
        "es": "Ningún imán con diámetro: se usan los radios mín./máx.",
        "en": "No magnet has a diameter: the min/max radii are used instead.",
        "zh": "没有设置直径的模块：改用最小/最大半径。",
        "ja": "直径のあるモジュールがありません：最小／最大半径を使います。",
        "it": "Nessun modulo con diametro: si usano i raggi min./max.",
        "fr": "Aucun module avec diamètre : les rayons min./max. sont utilisés.",
        "de": "Kein Modul mit Durchmesser: es gelten die Min./Max.-Radien.",
        "pt": "Nenhum módulo com diâmetro: usam-se os raios mín./máx."},
    # --- ajuste del imán en su agujero ---
    "params.fit_header": {
        "es": "Ajuste del imán en el agujero (holgura por lado)",
        "en": "Magnet fit in the hole (clearance per side)",
        "zh": "磁铁与孔的配合（单边间隙）",
        "ja": "穴に対する磁石の嵌め合い（片側のすきま）",
        "it": "Accoppiamento del magnete nel foro (gioco per lato)",
        "fr": "Ajustement de l’aimant dans le trou (jeu par côté)",
        "de": "Passung des Magneten im Loch (Spiel je Seite)",
        "pt": "Ajuste do ímã no furo (folga por lado)"},
    "params.fit_very_tight": {
        "es": "Muy apretado desde (mm):", "en": "Very tight from (mm):",
        "zh": "很紧起始 (mm)：", "ja": "非常にきつい（mm 以上）：",
        "it": "Molto stretto da (mm):", "fr": "Très serré à partir de (mm) :",
        "de": "Sehr stramm ab (mm):", "pt": "Muito apertado a partir de (mm):"},
    "params.fit_high": {
        "es": "Alto sobre la placa desde (mm):", "en": "High above the plate from (mm):",
        "zh": "离板高度起始 (mm)：", "ja": "プレートからの高さ（mm 超）：",
        "it": "Alto sul piatto da (mm):", "fr": "Haut au-dessus du plateau à partir de (mm) :",
        "de": "Hoch über der Platte ab (mm):", "pt": "Alto sobre a placa a partir de (mm):"},
    "fit.stick_hint": {
        "es": "Y queda a {over} mm sobre la placa: puede irse pegado al cabezal.",
        "en": "And it sits {over} mm above the plate: the toolhead may drag it away.",
        "zh": "而且离板 {over} mm：可能被打印头带走。",
        "ja": "しかもプレートから {over} mm の高さなので、ツールヘッドに持って行かれるおそれがあります。",
        "it": "E resta a {over} mm sopra il piatto: può andarsene attaccato alla testa.",
        "fr": "Et il reste à {over} mm au-dessus du plateau : la tête peut l’emporter.",
        "de": "Und er sitzt {over} mm über der Platte: der Druckkopf kann ihn mitnehmen.",
        "pt": "E fica a {over} mm sobre a placa: pode ir agarrado à cabeça."},
    "fit.stick_title": {
        "es": "El imán puede pegarse al cabezal",
        "en": "The magnet may stick to the toolhead",
        "zh": "磁铁可能吸附到打印头", "ja": "磁石がツールヘッドに付くおそれ",
        "it": "Il magnete può attaccarsi alla testa",
        "fr": "L’aimant peut se coller à la tête",
        "de": "Der Magnet kann am Druckkopf haften",
        "pt": "O ímã pode agarrar-se à cabeça"},
    "fit.warning_stick": {
        "es": "{n} imán(es) Ø{magnet} quedan en agujeros de Ø{hole} ({gap} mm de holgura "
              "por lado) y a {over} mm sobre la placa. Sin contar con el rozamiento contra "
              "la pared del agujero, y tan lejos de la placa que el PEI apenas tira de "
              "ellos, hay bastante riesgo de que se peguen a la boquilla o a la chapa del "
              "ventilador que va bajo el cabezal (la A1 la lleva metálica) cuando pase por "
              "encima al reanudar la impresión.",
        "en": "{n} Ø{magnet} magnet(s) sit in Ø{hole} holes ({gap} mm of clearance per side), "
              "{over} mm above the plate. Not counting on friction against the hole wall, "
              "and far enough from the plate that the PEI barely pulls on them, there is a "
              "fair risk they stick to the nozzle or to the fan shroud under the toolhead "
              "(the A1's is metal) as it passes over them when printing resumes.",
        "zh": "{n} 个 Ø{magnet} 磁铁在 Ø{hole} 的孔中很松（单边 {gap} mm 间隙），且离板 {over} mm。"
              "孔壁没有摩擦力固定它们，离板又远到 PEI 几乎吸不住，恢复打印时打印头经过上方，"
              "很可能被喷嘴或打印头下方的风扇金属罩（A1 是金属的）吸走。",
        "ja": "Ø{magnet} の磁石 {n} 個が Ø{hole} の穴でゆるく（片側 {gap} mm）、プレートから "
              "{over} mm の高さにあります。穴の壁の摩擦で押さえられず、PEI の吸着もほとんど"
              "届かないため、印刷再開時に上を通るノズルやツールヘッド下のファンカバー"
              "（A1 は金属製）に付いてしまうおそれがかなりあります。",
        "it": "{n} magnete/i Ø{magnet} restano laschi in fori Ø{hole} ({gap} mm di gioco per "
              "lato) e a {over} mm sopra il piatto. Senza attrito contro la parete che li "
              "trattenga, e così lontani dal piatto che il PEI quasi non li tira, c'è un bel "
              "rischio che si attacchino all'ugello o alla lamiera della ventola sotto la "
              "testa (quella della A1 è metallica) quando ci passa sopra alla ripresa.",
        "fr": "{n} aimant(s) Ø{magnet} restent libres dans des trous Ø{hole} ({gap} mm de jeu "
              "par côté) et à {over} mm au-dessus du plateau. Sans frottement contre la paroi "
              "pour les retenir, et si loin du plateau que le PEI ne les retient presque plus, "
              "ils risquent fort de se coller à la buse ou à la tôle du ventilateur sous la "
              "tête (celle de l'A1 est métallique) quand elle passe au-dessus à la reprise.",
        "de": "{n} Magnet(e) Ø{magnet} sitzen locker in Löchern Ø{hole} ({gap} mm Spiel je "
              "Seite), {over} mm über der Platte. Ohne Reibung an der Lochwand, die sie hält, "
              "und so weit von der Platte, dass das PEI kaum noch zieht, besteht ein "
              "spürbares Risiko, dass sie an der Düse oder am Blech des Lüfters unter dem "
              "Druckkopf (bei der A1 aus Metall) hängen bleiben, wenn er beim Fortsetzen des "
              "Drucks darüber fährt.",
        "pt": "{n} ímã(s) Ø{magnet} ficam soltos em furos Ø{hole} ({gap} mm de folga por lado) "
              "e a {over} mm sobre a placa. Sem atrito contra a parede do furo que os segure, "
              "e tão longe da placa que o PEI quase não os puxa, há um risco considerável de "
              "se agarrarem ao bico ou à chapa do ventilador sob a cabeça (a da A1 é "
              "metálica) quando passar por cima ao retomar a impressão."},
    "params.fit_hint": {
        "es": "La holgura es lo que le sobra al imán a cada lado: (Ø agujero − Ø imán) / 2. "
              "Por debajo de «muy apretado» se avisa antes de generar el G-code.",
        "en": "The clearance is the room the magnet has on each side: (hole Ø − magnet Ø) / 2. "
              "Below \"very tight\" you get a warning before generating G-code.",
        "zh": "间隙是磁铁每侧多出的余量：（孔径 − 磁铁直径）/ 2。低于最后一个阈值时，生成 G-code 前会发出警告。",
        "ja": "すきまは磁石の片側に残る余裕です：（穴径 − 磁石径）÷ 2。最後のしきい値を下回ると、"
              "G-code を作る前に警告します。",
        "it": "Il gioco è quello che avanza al magnete su ogni lato: (Ø foro − Ø magnete) / 2. "
              "Sotto l’ultima soglia si avvisa prima di generare il G-code.",
        "fr": "Le jeu est ce qui reste à l’aimant de chaque côté : (Ø trou − Ø aimant) / 2. "
              "Sous le dernier seuil, un avertissement s’affiche avant de générer le G-code.",
        "de": "Das Spiel ist der Platz, der dem Magneten je Seite bleibt: (Ø Loch − Ø Magnet) / 2. "
              "Unter dem letzten Schwellwert wird vor dem Erzeugen des G-codes gewarnt.",
        "pt": "A folga é o que sobra ao ímã de cada lado: (Ø furo − Ø ímã) / 2. "
              "Abaixo do último limite avisa-se antes de gerar o G-code."},
    "fit.fits": {"es": "entra", "en": "fits"},
    "fit.barely": {"es": "puede que no quepa", "en": "may not fit", "zh": "可能装不进",
                   "ja": "入らないおそれ", "it": "potrebbe non entrare",
                   "fr": "risque de ne pas rentrer", "de": "passt möglicherweise nicht",
                   "pt": "pode não caber"},
    "fit.too_big": {"es": "no cabe", "en": "does not fit", "zh": "装不进",
                    "ja": "入らない", "it": "non entra", "fr": "ne rentre pas",
                    "de": "passt nicht", "pt": "não cabe"},
    "fit.summary": {
        "es": "Imán Ø{magnet} en agujero Ø{hole}: <b>{level}</b> ({gap} mm por lado){count}.",
        "en": "Ø{magnet} magnet in a Ø{hole} hole: <b>{level}</b> ({gap} mm per side){count}.",
        "zh": "Ø{magnet} 磁铁装入 Ø{hole} 的孔：<b>{level}</b>（单边 {gap} mm）{count}。",
        "ja": "Ø{magnet} の磁石を Ø{hole} の穴へ：<b>{level}</b>（片側 {gap} mm）{count}。",
        "it": "Magnete Ø{magnet} in un foro Ø{hole}: <b>{level}</b> ({gap} mm per lato){count}.",
        "fr": "Aimant Ø{magnet} dans un trou Ø{hole} : <b>{level}</b> ({gap} mm par côté){count}.",
        "de": "Magnet Ø{magnet} in einem Loch Ø{hole}: <b>{level}</b> ({gap} mm je Seite){count}.",
        "pt": "Ímã Ø{magnet} num furo Ø{hole}: <b>{level}</b> ({gap} mm por lado){count}."},
    "fit.count": {"es": " · {n} agujero(s)", "en": " · {n} hole(s)", "zh": " · {n} 个孔",
                  "ja": " · 穴 {n} 個", "it": " · {n} foro/i", "fr": " · {n} trou(s)",
                  "de": " · {n} Loch/Löcher", "pt": " · {n} furo(s)"},
    "fit.no_holes": {
        "es": "Sin agujeros detectados que medir.", "en": "No detected holes to measure.",
        "zh": "没有可测量的已检测孔。", "ja": "測れる検出穴がありません。",
        "it": "Nessun foro rilevato da misurare.", "fr": "Aucun trou détecté à mesurer.",
        "de": "Keine erkannten Löcher zum Messen.", "pt": "Sem furos detetados para medir."},
    "fit.warning_title": {
        "es": "El imán puede no entrar", "en": "The magnet may not fit",
        "zh": "磁铁可能装不进", "ja": "磁石が入らないおそれ",
        "it": "Il magnete potrebbe non entrare", "fr": "L’aimant risque de ne pas rentrer",
        "de": "Der Magnet passt möglicherweise nicht", "pt": "O ímã pode não caber"},
    "fit.warning_barely": {
        "es": "{n} imán(es) Ø{magnet} en agujeros de Ø{hole}: sólo {gap} mm de holgura por "
              "lado. Puede que no entren.",
        "en": "{n} Ø{magnet} magnet(s) in Ø{hole} holes: only {gap} mm of clearance per "
              "side. They may not fit.",
        "zh": "{n} 个 Ø{magnet} 磁铁装入 Ø{hole} 的孔：单边仅 {gap} mm 间隙，可能装不进。",
        "ja": "Ø{magnet} の磁石 {n} 個が Ø{hole} の穴に：片側 {gap} mm しかありません。"
              "入らないおそれがあります。",
        "it": "{n} magnete/i Ø{magnet} in fori Ø{hole}: solo {gap} mm di gioco per lato. "
              "Potrebbero non entrare.",
        "fr": "{n} aimant(s) Ø{magnet} dans des trous Ø{hole} : seulement {gap} mm de jeu "
              "par côté. Ils risquent de ne pas rentrer.",
        "de": "{n} Magnet(e) Ø{magnet} in Löchern Ø{hole}: nur {gap} mm Spiel je Seite. "
              "Sie passen möglicherweise nicht.",
        "pt": "{n} ímã(s) Ø{magnet} em furos Ø{hole}: só {gap} mm de folga por lado. "
              "Podem não caber."},
    "fit.warning_too_big": {
        "es": "{n} imán(es) Ø{magnet} no caben en agujeros de Ø{hole}: les sobra {gap} mm "
              "de radio.",
        "en": "{n} Ø{magnet} magnet(s) do not fit in Ø{hole} holes: {gap} mm too wide in "
              "radius.",
        "zh": "{n} 个 Ø{magnet} 磁铁装不进 Ø{hole} 的孔：半径超出 {gap} mm。",
        "ja": "Ø{magnet} の磁石 {n} 個が Ø{hole} の穴に入りません：半径が {gap} mm 大きすぎます。",
        "it": "{n} magnete/i Ø{magnet} non entrano in fori Ø{hole}: {gap} mm di raggio in più.",
        "fr": "{n} aimant(s) Ø{magnet} ne rentrent pas dans des trous Ø{hole} : {gap} mm de "
              "rayon en trop.",
        "de": "{n} Magnet(e) Ø{magnet} passen nicht in Löcher Ø{hole}: {gap} mm zu viel Radius.",
        "pt": "{n} ímã(s) Ø{magnet} não cabem em furos Ø{hole}: sobram {gap} mm de raio."},
    "fit.continue_anyway": {
        "es": "¿Generar el G-code de todas formas?",
        "en": "Generate the G-code anyway?",
        "zh": "仍要生成 G-code 吗？", "ja": "それでも G-code を作りますか？",
        "it": "Generare comunque il G-code?", "fr": "Générer le G-code quand même ?",
        "de": "G-code trotzdem erzeugen?", "pt": "Gerar o G-code mesmo assim?"},
    # --- lo hondo que es el agujero ---
    "depth.warning_title": {
        "es": "El imán se sale del agujero",
        "en": "The magnet sticks out of the hole"},
    "depth.warning_shallow": {
        "es": "{n} imán(es) de {height} mm en agujeros de {depth} mm de fondo: "
              "sobresalen {over} mm. Al reanudar, la boquilla pasa justo por ahí.",
        "en": "{n} magnet(s) {height} mm tall in {depth} mm deep holes: they stick "
              "out {over} mm. The nozzle passes right over that when printing resumes."},
    "depth.warning_stack": {
        "es": "{n} agujero(s) con {count} imanes apilados ({total} mm) y sólo "
              "{depth} mm de fondo: sobresalen {over} mm. Ahí caben {fits}.",
        "en": "{n} hole(s) with {count} stacked magnets ({total} mm) and only "
              "{depth} mm of depth: they stick out {over} mm. Only {fits} fit there."},
    "depth.continue_anyway": {
        "es": "¿Generar el G-code de todas formas?",
        "en": "Generate the G-code anyway?"},
    "status.depth_cancelled": {
        "es": "Generación cancelada: los imanes no caben a lo hondo.",
        "en": "Generation cancelled: the magnets do not fit deep enough."},
    # --- el recuadro de responsabilidad, lo último antes de exportar ---
    "risk.accept": {
        "es": "Acepto la responsabilidad de exportar con estos avisos.",
        "en": "I accept responsibility for exporting with these warnings."},
    "risk.accept_hint": {
        "es": "Marca la casilla para poder seguir: el archivo se genera tal cual, "
              "con los riesgos que acabas de ver.",
        "en": "Tick the box to continue: the file is generated as it is, with the "
              "risks you have just seen."},
    "status.fit_cancelled": {
        "es": "Generación cancelada por el ajuste del imán.",
        "en": "Generation cancelled because of the magnet fit.",
        "zh": "因磁铁配合问题已取消生成。", "ja": "磁石の嵌め合いのため生成を中止しました。",
        "it": "Generazione annullata per l’accoppiamento del magnete.",
        "fr": "Génération annulée à cause de l’ajustement de l’aimant.",
        "de": "Erzeugung wegen der Magnetpassung abgebrochen.",
        "pt": "Geração cancelada pelo ajuste do ímã."},
    "params.r_min": {"es": "Radio mínimo (mm):", "en": "Min radius (mm):", "zh": "最小半径 (mm)：",
                     "ja": "最小半径 (mm)：", "it": "Raggio minimo (mm):", "fr": "Rayon min. (mm) :",
                     "de": "Min. Radius (mm):", "pt": "Raio mínimo (mm):"},
    "params.r_max": {"es": "Radio máximo (mm):", "en": "Max radius (mm):", "zh": "最大半径 (mm)：",
                     "ja": "最大半径 (mm)：", "it": "Raggio massimo (mm):", "fr": "Rayon max. (mm) :",
                     "de": "Max. Radius (mm):", "pt": "Raio máximo (mm):"},
    "params.circularity": {"es": "Circularidad máx. (0-1):", "en": "Max circularity (0-1):",
                           "zh": "最大圆度 (0-1)：", "ja": "最大真円度 (0-1)：",
                           "it": "Circolarità max (0-1):", "fr": "Circularité max (0-1) :",
                           "de": "Max. Rundheit (0-1):", "pt": "Circularidade máx. (0-1):"},
    "params.cluster": {"es": "Fusión concéntricas (mm):", "en": "Concentric merge (mm):",
                       "zh": "同心合并 (mm)：", "ja": "同心円の結合 (mm)：",
                       "it": "Unione concentriche (mm):", "fr": "Fusion concentriques (mm) :",
                       "de": "Konzentrische Zusammenführung (mm):", "pt": "Fusão concêntricas (mm):"},
    "params.min_arc": {"es": "Arco mínimo (grados):", "en": "Minimum arc (degrees):",
                       "zh": "最小圆弧（度）：", "ja": "最小円弧（度）：",
                       "it": "Arco minimo (gradi):", "fr": "Arc minimum (degrés) :",
                       "de": "Mindestbogen (Grad):", "pt": "Arco mínimo (graus):"},
    "params.reset": {"es": "Restaurar parámetros por defecto", "en": "Reset default parameters",
                     "zh": "恢复默认参数", "ja": "既定のパラメータに戻す",
                     "it": "Ripristina parametri predefiniti",
                     "fr": "Réinitialiser les paramètres",
                     "de": "Standardparameter zurücksetzen",
                     "pt": "Restaurar parâmetros padrão"},
    "params.rerun": {"es": "Rehacer detección", "en": "Re-run detection", "zh": "重新检测",
                     "ja": "検出をやり直す", "it": "Riesegui rilevamento",
                     "fr": "Relancer la détection", "de": "Erkennung neu ausführen",
                     "pt": "Refazer detecção"},
    "params.hint": {
        "es": "Con «Sólo agujeros del diámetro de mis imanes» el detector busca los tamaños "
              "definidos en Módulos, con el margen indicado, y se rehace solo al cambiarlos. "
              "El diámetro se mide en la pared del agujero, como con un calibre: al trazado "
              "se le descuenta el ancho del cordón, que el propio archivo dice. "
              "Sin esa casilla vale cualquier radio entre los límites de abajo. "
              "Sube la circularidad si no detecta agujeros poco redondos. Pulsa «Rehacer "
              "detección» tras cambiar los valores.",
        "en": "With “Only holes matching my magnet diameters” the detector looks for the sizes "
              "set in Modules, within the given margin, and re-runs itself when they change. "
              "Without that box any radius between the limits below is accepted. "
              "Raise the circularity if it misses less-round holes. Press “Re-run detection” "
              "after changing values.",
        "zh": "检测器会查找半径在指定范围内的圆形轮廓。请将半径设置为与磁铁匹配；"
              "如果漏掉不太圆的孔，请提高圆度。更改数值后请点击“重新检测”。",
        "ja": "指定した範囲の半径を持つ円形の輪郭を検出します。磁石に合わせて半径を設定し、"
              "丸みの少ない穴を見逃す場合は真円度を上げてください。値を変更したら「検出をやり直す」を押します。",
        "it": "Il rilevatore cerca contorni circolari con raggio entro i limiti indicati. "
              "Imposta il raggio in base ai tuoi magneti; aumenta la circolarità se non rileva "
              "fori poco rotondi. Premi «Riesegui rilevamento» dopo aver cambiato i valori.",
        "fr": "Le détecteur recherche des contours circulaires dont le rayon est compris dans "
              "les limites indiquées. Réglez le rayon selon vos aimants ; augmentez la circularité "
              "s’il rate des trous peu ronds. Cliquez sur « Relancer la détection » après modification.",
        "de": "Der Detektor sucht kreisförmige Konturen mit einem Radius innerhalb der Grenzen. "
              "Stellen Sie den Radius passend zu Ihren Magneten ein; erhöhen Sie die Rundheit, "
              "wenn weniger runde Löcher übersehen werden. Danach „Erkennung neu ausführen“ drücken.",
        "pt": "O detector procura contornos circulares com raio dentro dos limites indicados. "
              "Ajuste o raio aos seus ímãs; aumente a circularidade se não detectar furos pouco "
              "redondos. Clique em «Refazer detecção» após alterar os valores.",
    },
    # --- pestaña secuencias ---
    "seq.info": {
        "es": "Secuencias G-code (una instrucción por línea). Puedes usar expresiones entre "
              "llaves: {{z}}, {{safe_z}}, {{z+0.4}}, {{temp}}, {{fan}}, {{deretract}}.",
        "en": "G-code sequences (one instruction per line). You can use brace expressions: "
              "{{z}}, {{safe_z}}, {{z+0.4}}, {{temp}}, {{fan}}, {{deretract}}.",
        "zh": "G-code 序列（每行一条指令）。可使用花括号表达式：{{z}}、{{safe_z}}、{{z+0.4}}、{{temp}}、{{fan}}、{{deretract}}。",
        "ja": "G-code シーケンス（1 行に 1 命令）。波括弧の式が使えます：{{z}}、{{safe_z}}、{{z+0.4}}、{{temp}}、{{fan}}、{{deretract}}。",
        "it": "Sequenze G-code (un'istruzione per riga). Puoi usare espressioni tra parentesi "
              "graffe: {{z}}, {{safe_z}}, {{z+0.4}}, {{temp}}, {{fan}}, {{deretract}}.",
        "fr": "Séquences G-code (une instruction par ligne). Vous pouvez utiliser des expressions "
              "entre accolades : {{z}}, {{safe_z}}, {{z+0.4}}, {{temp}}, {{fan}}, {{deretract}}.",
        "de": "G-code-Sequenzen (eine Anweisung pro Zeile). Ausdrücke in geschweiften Klammern "
              "möglich: {{z}}, {{safe_z}}, {{z+0.4}}, {{temp}}, {{fan}}, {{deretract}}.",
        "pt": "Sequências G-code (uma instrução por linha). Você pode usar expressões entre "
              "chaves: {{z}}, {{safe_z}}, {{z+0.4}}, {{temp}}, {{fan}}, {{deretract}}.",
    },
    "seq.red": {"es": "Imán rojo", "en": "Red magnet", "zh": "红色磁铁", "ja": "赤の磁石",
                "it": "Magnete rosso", "fr": "Aimant rouge", "de": "Roter Magnet", "pt": "Ímã vermelho"},
    "seq.blue": {"es": "Imán azul", "en": "Blue magnet", "zh": "蓝色磁铁", "ja": "青の磁石",
                 "it": "Magnete blu", "fr": "Aimant bleu", "de": "Blauer Magnet", "pt": "Ímã azul"},
    "seq.start": {"es": "Inicio", "en": "Start", "zh": "开始", "ja": "開始",
                  "it": "Inizio", "fr": "Début", "de": "Start", "pt": "Início"},
    "seq.end": {"es": "Fin", "en": "End", "zh": "结束", "ja": "終了",
                "it": "Fine", "fr": "Fin", "de": "Ende", "pt": "Fim"},
    "seq.final": {"es": "Final (reanudar)", "en": "Final (resume)", "zh": "最终（恢复）",
                  "ja": "最終（再開）", "it": "Finale (riprendi)", "fr": "Final (reprendre)",
                  "de": "Abschluss (fortsetzen)", "pt": "Final (retomar)"},
    "seq.reset": {"es": "Restaurar secuencias por defecto", "en": "Reset default sequences",
                  "zh": "恢复默认序列", "ja": "既定のシーケンスに戻す",
                  "it": "Ripristina sequenze predefinite", "fr": "Réinitialiser les séquences",
                  "de": "Standardsequenzen zurücksetzen", "pt": "Restaurar sequências padrão"},
    # --- pestaña vista previa ---
    "preview.generate": {"es": "Generar vista previa", "en": "Generate preview", "zh": "生成预览",
                         "ja": "プレビューを生成", "it": "Genera anteprima", "fr": "Générer un aperçu",
                         "de": "Vorschau erzeugen", "pt": "Gerar pré-visualização"},
    "preview.goto": {"es": "Ir a zona de imanes", "en": "Go to magnet zone", "zh": "跳转到磁铁区域",
                     "ja": "磁石ゾーンへ移動", "it": "Vai alla zona magneti",
                     "fr": "Aller à la zone des aimants", "de": "Zur Magnetzone springen",
                     "pt": "Ir para a zona dos ímãs"},
    "preview.lines_magnets": {"es": "{lines} líneas · {n} imán(es)", "en": "{lines} lines · {n} magnet(s)",
                              "zh": "{lines} 行 · {n} 个磁铁", "ja": "{lines} 行 · 磁石 {n} 個",
                              "it": "{lines} righe · {n} magnete/i", "fr": "{lines} lignes · {n} aimant(s)",
                              "de": "{lines} Zeilen · {n} Magnet(e)", "pt": "{lines} linhas · {n} ímã(s)"},
    # --- lienzo ---
    "canvas.empty": {"es": "Carga un archivo .3mf / .gcode para empezar",
                     "en": "Load a .3mf / .gcode file to start", "zh": "加载 .3mf / .gcode 文件以开始",
                     "ja": ".3mf / .gcode ファイルを読み込んで開始", "it": "Carica un file .3mf / .gcode per iniziare",
                     "fr": "Chargez un fichier .3mf / .gcode pour commencer",
                     "de": "Laden Sie eine .3mf-/.gcode-Datei, um zu beginnen",
                     "pt": "Carregue um arquivo .3mf / .gcode para começar"},
    "canvas.help": {"es": "Clic: añadir/mover imán · Ctrl+clic: apilar otro · "
                          "Clic derecho: borrar · N=azul M=rojo",
                    "en": "Click: add/move magnet · Ctrl+click: stack another · "
                          "Right-click: delete · N=blue M=red",
                    "zh": "单击：添加/移动磁铁 · 右键：删除 · N=蓝 M=红",
                    "ja": "クリック：磁石を追加/移動 · 右クリック：削除 · N=青 M=赤",
                    "it": "Clic: aggiungi/sposta magnete · Tasto destro: elimina · N=blu M=rosso",
                    "fr": "Clic : ajouter/déplacer · Clic droit : supprimer · N=bleu M=rouge",
                    "de": "Klick: Magnet hinzufügen/verschieben · Rechtsklick: löschen · N=blau M=rot",
                    "pt": "Clique: adicionar/mover ímã · Botão direito: excluir · N=azul M=vermelho"},
    "canvas.centers_prefix": {"es": "{n} centros detectados (verde) · ",
                              "en": "{n} centers detected (green) · ", "zh": "检测到 {n} 个圆心（绿色） · ",
                              "ja": "{n} 個の中心を検出（緑） · ", "it": "{n} centri rilevati (verde) · ",
                              "fr": "{n} centres détectés (vert) · ", "de": "{n} Mittelpunkte erkannt (grün) · ",
                              "pt": "{n} centros detectados (verde) · "},
    "canvas.hud_z": {"es": "Capa de la pausa · Z = {z} mm", "en": "Pause layer · Z = {z} mm",
                     "zh": "暂停层 · Z = {z} mm", "ja": "一時停止レイヤー · Z = {z} mm",
                     "it": "Strato della pausa · Z = {z} mm", "fr": "Couche de la pause · Z = {z} mm",
                     "de": "Pausen-Schicht · Z = {z} mm", "pt": "Camada da pausa · Z = {z} mm"},
    # --- avisos del área alcanzable (mensaje efímero, arriba a la derecha) ---
    "canvas.out_of_area_title": {
        "es": "Ahí no llega el colocador", "en": "The placer cannot reach there",
        "zh": "放置器无法到达此处", "ja": "設置ヘッドが届きません",
        "it": "Il posizionatore non arriva lì", "fr": "Le poseur n’atteint pas cet endroit",
        "de": "Dorthin reicht der Setzer nicht", "pt": "O colocador não alcança aí"},
    "canvas.out_of_area_fix": {
        "es": "Pon el imán dentro del rectángulo verde: X {xmin}–{xmax} · Y {ymin}–{ymax} mm",
        "en": "Place the magnet inside the green rectangle: X {xmin}–{xmax} · Y {ymin}–{ymax} mm",
        "zh": "请将磁铁放在绿色矩形内：X {xmin}–{xmax} · Y {ymin}–{ymax} mm",
        "ja": "緑の長方形の中に磁石を置いてください：X {xmin}–{xmax} · Y {ymin}–{ymax} mm",
        "it": "Metti il magnete dentro il rettangolo verde: X {xmin}–{xmax} · Y {ymin}–{ymax} mm",
        "fr": "Placez l’aimant dans le rectangle vert : X {xmin}–{xmax} · Y {ymin}–{ymax} mm",
        "de": "Setzen Sie den Magneten in das grüne Rechteck: X {xmin}–{xmax} · Y {ymin}–{ymax} mm",
        "pt": "Coloque o ímã dentro do retângulo verde: X {xmin}–{xmax} · Y {ymin}–{ymax} mm"},
    "canvas.points_outside_title": {
        "es": "{n} imán(es) fuera del alcance", "en": "{n} magnet(s) out of reach",
        "zh": "{n} 个磁铁超出可达范围", "ja": "{n} 個の磁石が範囲外です",
        "it": "{n} magnete/i fuori portata", "fr": "{n} aimant(s) hors de portée",
        "de": "{n} Magnet(e) außerhalb der Reichweite", "pt": "{n} ímã(s) fora do alcance"},
    "canvas.points_outside_fix": {
        "es": "Van marcados en rojo: muévelos dentro del rectángulo verde para poder exportar",
        "en": "They are marked in red: move them inside the green rectangle to export",
        "zh": "它们以红色标出：请移入绿色矩形内才能导出",
        "ja": "赤で示されています。書き出すには緑の長方形の中へ移動してください",
        "it": "Sono segnati in rosso: spostali dentro il rettangolo verde per esportare",
        "fr": "Ils sont marqués en rouge : déplacez-les dans le rectangle vert pour exporter",
        "de": "Sie sind rot markiert: zum Exportieren in das grüne Rechteck verschieben",
        "pt": "Estão marcados a vermelho: mova-os para dentro do retângulo verde para exportar"},
    # Etiqueta corta sobre la línea que une un imán ya puesto con el que lo pisa:
    # aquí no interesa una distancia sino de quién es el recorrido que pasa.
    "canvas.sweep_label": {
        "es": "recorrido {n}", "en": "travel {n}", "zh": "{n} 号退避",
        "ja": "退避 {n}", "it": "corsa {n}", "fr": "course {n}",
        "de": "Rückzug {n}", "pt": "recuo {n}"},
    # --- límites físicos de la máquina ---
    "limits.too_tall": {
        "es": "La pieza mide {h} mm de alto y el máximo es {max} mm. "
              "Baja la altura del modelo o divídelo en partes.",
        "en": "The part is {h} mm tall and the maximum is {max} mm. "
              "Lower the model or split it into parts.",
        "zh": "该零件高 {h} mm，最大值为 {max} mm。请降低模型高度或将其分割。",
        "ja": "部品の高さは {h} mm で、上限は {max} mm です。モデルを低くするか分割してください。",
        "it": "Il pezzo è alto {h} mm e il massimo è {max} mm. "
              "Abbassa il modello o dividilo in parti.",
        "fr": "La pièce mesure {h} mm de haut et le maximum est {max} mm. "
              "Réduisez la hauteur du modèle ou découpez-le.",
        "de": "Das Teil ist {h} mm hoch, das Maximum sind {max} mm. "
              "Modell niedriger machen oder aufteilen.",
        "pt": "A peça tem {h} mm de altura e o máximo é {max} mm. "
              "Reduza a altura do modelo ou divida-o em partes."},
    "limits.pause_too_high": {
        "es": "La pausa está a Z {z} mm y el máximo es {max} mm. "
              "Mueve el «{token}» a una capa más baja.",
        "en": "The pause is at Z {z} mm and the maximum is {max} mm. "
              "Move the “{token}” to a lower layer.",
        "zh": "暂停位于 Z {z} mm，最大值为 {max} mm。请把“{token}”移到更低的层。",
        "ja": "一時停止は Z {z} mm にあり、上限は {max} mm です。「{token}」をより低い層に移動してください。",
        "it": "La pausa è a Z {z} mm e il massimo è {max} mm. "
              "Sposta il «{token}» su uno strato più basso.",
        "fr": "La pause est à Z {z} mm et le maximum est {max} mm. "
              "Déplacez le « {token} » vers une couche plus basse.",
        "de": "Die Pause liegt bei Z {z} mm, das Maximum sind {max} mm. "
              "Verschieben Sie das „{token}“ auf eine niedrigere Schicht.",
        "pt": "A pausa está a Z {z} mm e o máximo é {max} mm. "
              "Mova o «{token}» para uma camada mais baixa."},
    "limits.warning_title": {
        "es": "Fuera de los límites de la máquina", "en": "Outside the machine limits",
        "zh": "超出机器限制", "ja": "機械の制限を超えています",
        "it": "Fuori dai limiti della macchina", "fr": "Hors des limites de la machine",
        "de": "Außerhalb der Maschinengrenzen", "pt": "Fora dos limites da máquina"},
    "limits.blocked": {
        "es": "No se puede generar el G-code:", "en": "The G-code cannot be generated:",
        "zh": "无法生成 G-code：", "ja": "G-code を生成できません：",
        "it": "Impossibile generare il G-code:", "fr": "Impossible de générer le G-code :",
        "de": "Der G-Code kann nicht erzeugt werden:", "pt": "Não é possível gerar o G-code:"},
    "limits.points_outside": {
        "es": "Hay {n} imán(es) fuera del área que alcanza el colocador "
              "(marcados en rojo). Muévelos dentro del rectángulo verde.",
        "en": "{n} magnet(s) fall outside the area the placer can reach "
              "(marked in red). Move them inside the green rectangle.",
        "zh": "有 {n} 个磁铁位于放置器可达区域之外（以红色标出）。请将其移入绿色矩形内。",
        "ja": "設置ヘッドが届かない範囲に磁石が {n} 個あります（赤で表示）。緑の長方形の中へ移動してください。",
        "it": "Ci sono {n} magnete/i fuori dall'area raggiungibile dal posizionatore "
              "(segnati in rosso). Spostali dentro il rettangolo verde.",
        "fr": "{n} aimant(s) se trouvent hors de la zone atteignable par le poseur "
              "(marqués en rouge). Déplacez-les dans le rectangle vert.",
        "de": "{n} Magnet(e) liegen außerhalb des Bereichs, den der Setzer erreicht "
              "(rot markiert). Verschieben Sie sie in das grüne Rechteck.",
        "pt": "Há {n} ímã(s) fora da área alcançável pelo colocador "
              "(marcados a vermelho). Mova-os para dentro do retângulo verde."},
    # --- la pieza contra la cama ---
    "adhesion.warning_title": {
        "es": "La pieza puede despegarse de la cama",
        "en": "The part may come off the bed",
        "zh": "工件可能从热床上脱落", "ja": "造形物がベッドから剥がれるおそれがあります",
        "it": "Il pezzo può staccarsi dal piano",
        "fr": "La pièce peut se décoller du plateau",
        "de": "Das Teil kann sich vom Druckbett lösen",
        "pt": "A peça pode descolar-se da mesa"},
    "adhesion.tipping": {
        "es": "Al retirarse, el módulo empuja la pieza con {force} N a {z} mm de altura, "
              "y con una base de {base} mm aguanta {limit} N antes de volcar "
              "(margen {margin}×). Baja la pausa, ensancha la base con un ala o un "
              "brim, o usa un imán más pequeño.",
        "en": "As it retreats, the module pushes the part with {force} N at {z} mm high, "
              "and with a {base} mm base it withstands {limit} N before tipping over "
              "(margin {margin}×). Lower the pause, widen the base with a tab or a "
              "brim, or use a smaller magnet.",
        "zh": "模块退回时会在 {z} mm 高处以 {force} N 推动工件，而 {base} mm 的底面在倾覆前"
              "只能承受 {limit} N（安全系数 {margin}×）。请降低暂停高度、用加强片或裙边"
              "加宽底面，或改用更小的磁铁。",
        "ja": "モジュールが退避する際、高さ {z} mm の位置で {force} N の力が加わりますが、"
              "底面 {base} mm では転倒前に {limit} N しか耐えられません（余裕 {margin} 倍）。"
              "一時停止を低くするか、タブやブリムで底面を広げるか、小さい磁石を使ってください。",
        "it": "Ritirandosi, il modulo spinge il pezzo con {force} N a {z} mm di altezza, "
              "e con una base di {base} mm regge {limit} N prima di ribaltarsi "
              "(margine {margin}×). Abbassa la pausa, allarga la base con un'aletta o "
              "un brim, oppure usa un magnete più piccolo.",
        "fr": "En se retirant, le module pousse la pièce avec {force} N à {z} mm de "
              "hauteur, et avec une base de {base} mm elle tient {limit} N avant de "
              "basculer (marge {margin}×). Abaissez la pause, élargissez la base avec "
              "une patte ou une bordure, ou utilisez un aimant plus petit.",
        "de": "Beim Zurückfahren drückt das Modul mit {force} N in {z} mm Höhe gegen das "
              "Teil; mit einer {base} mm breiten Basis hält es {limit} N aus, bevor es "
              "kippt (Reserve {margin}×). Senken Sie die Pause, verbreitern Sie die "
              "Basis mit einer Lasche oder einem Brim, oder nehmen Sie einen kleineren "
              "Magneten.",
        "pt": "Ao recuar, o módulo empurra a peça com {force} N a {z} mm de altura e, "
              "com uma base de {base} mm, aguenta {limit} N antes de tombar "
              "(margem {margin}×). Baixe a pausa, alargue a base com uma aba ou um "
              "brim, ou use um íman mais pequeno."},
    "adhesion.sliding": {
        "es": "Al retirarse, el módulo empuja la pieza con {force} N y sus {area} mm² "
              "pegados a la cama aguantan {limit} N antes de deslizarse "
              "(margen {margin}×). Aumenta la superficie de contacto o usa un imán "
              "más pequeño.",
        "en": "As it retreats, the module pushes the part with {force} N, and its "
              "{area} mm² stuck to the bed withstand {limit} N before sliding "
              "(margin {margin}×). Increase the contact area or use a smaller magnet.",
        "zh": "模块退回时以 {force} N 推动工件，而粘在热床上的 {area} mm² 在滑移前只能承受 "
              "{limit} N（安全系数 {margin}×）。请增大接触面积或改用更小的磁铁。",
        "ja": "モジュールが退避する際に {force} N の力が加わりますが、ベッドに接した "
              "{area} mm² ではずれる前に {limit} N しか耐えられません（余裕 {margin} 倍）。"
              "接地面積を増やすか、小さい磁石を使ってください。",
        "it": "Ritirandosi, il modulo spinge il pezzo con {force} N e i suoi {area} mm² "
              "attaccati al piano reggono {limit} N prima di scivolare "
              "(margine {margin}×). Aumenta la superficie di contatto o usa un magnete "
              "più piccolo.",
        "fr": "En se retirant, le module pousse la pièce avec {force} N, et ses "
              "{area} mm² collés au plateau tiennent {limit} N avant de glisser "
              "(marge {margin}×). Augmentez la surface de contact ou utilisez un aimant "
              "plus petit.",
        "de": "Beim Zurückfahren drückt das Modul mit {force} N gegen das Teil; die "
              "{area} mm², die am Bett haften, halten {limit} N aus, bevor es "
              "verrutscht (Reserve {margin}×). Vergrößern Sie die Kontaktfläche oder "
              "nehmen Sie einen kleineren Magneten.",
        "pt": "Ao recuar, o módulo empurra a peça com {force} N e os seus {area} mm² "
              "colados à mesa aguentam {limit} N antes de deslizar (margem {margin}×). "
              "Aumente a área de contacto ou use um íman mais pequeno."},
    "adhesion.continue_anyway": {
        "es": "El cálculo usa valores de adherencia orientativos, no medidos. "
              "«Aceptar» genera el G-code de todas formas.",
        "en": "The calculation uses indicative adhesion values, not measured ones. "
              "“OK” generates the G-code anyway.",
        "zh": "该计算使用的是参考性的附着力数值，并非实测值。点击“确定”仍会生成 G-code。",
        "ja": "この計算は実測ではなく目安の密着強度を使っています。「OK」を押すとそのまま "
              "G-code を生成します。",
        "it": "Il calcolo usa valori di adesione indicativi, non misurati. "
              "«OK» genera comunque il G-code.",
        "fr": "Le calcul utilise des valeurs d'adhérence indicatives, non mesurées. "
              "« OK » génère quand même le G-code.",
        "de": "Die Rechnung verwendet Richtwerte für die Haftung, keine Messwerte. "
              "„OK“ erzeugt den G-Code trotzdem.",
        "pt": "O cálculo usa valores de aderência indicativos, não medidos. "
              "«OK» gera o G-code na mesma."},
    "status.adhesion_cancelled": {
        "es": "Generación cancelada por el aviso de despegue.",
        "en": "Generation cancelled after the bed-adhesion warning.",
        "zh": "已因脱落警告取消生成。", "ja": "剥がれの警告により生成を中止しました。",
        "it": "Generazione annullata per l'avviso di distacco.",
        "fr": "Génération annulée suite à l'avertissement de décollement.",
        "de": "Erzeugung wegen der Haftungswarnung abgebrochen.",
        "pt": "Geração cancelada pelo aviso de descolamento."},
    "mod.grade": {
        "es": "Grado", "en": "Grade", "zh": "牌号", "ja": "グレード",
        "it": "Grado", "fr": "Nuance", "de": "Güte", "pt": "Grau"},
    "mod.pull_kg": {
        "es": "Atracción (kg)", "en": "Pull (kg)", "zh": "吸力（kg）",
        "ja": "吸着力 (kg)", "it": "Attrazione (kg)", "fr": "Force (kg)",
        "de": "Haftkraft (kg)", "pt": "Atração (kg)"},
    "mod.pull_kg_hint": {
        "es": "Lo que pone en la caja del imán. Con 0 se deduce del grado.",
        "en": "What the magnet's box says. With 0 it is derived from the grade.",
        "zh": "磁铁包装上标注的数值。填 0 则由牌号推算。",
        "ja": "磁石の箱に書かれている値。0 ならグレードから推定します。",
        "it": "Quanto indica la scatola del magnete. Con 0 si ricava dal grado.",
        "fr": "Ce qu'indique la boîte de l'aimant. À 0, elle est déduite de la nuance.",
        "de": "Was auf der Magnetpackung steht. Bei 0 wird sie aus der Güte abgeleitet.",
        "pt": "O que diz a caixa do íman. Com 0 deduz-se do grau."},
    "info.adhesion_title": {
        "es": "Y la pieza, ¿aguanta el empujón?",
        "en": "And the part — does it take the push?",
        "zh": "工件顶得住这一推吗？", "ja": "造形物はその力に耐えるのか",
        "it": "E il pezzo, regge la spinta?",
        "fr": "Et la pièce, tient-elle la poussée ?",
        "de": "Und das Teil — hält es den Stoß aus?",
        "pt": "E a peça, aguenta o empurrão?"},
    "info.adhesion_body": {
        "es": "Para separarse del imán que acaba de dejar, el módulo tiene que vencer "
              "la <b>cizalla</b> entre los dos, que está <b>medida con dinamómetro</b>: "
              "un ⌀8×5 N35 pide 15 N. Con este imán son <b>{force} N</b>, y no los "
              "recibe la base de la pieza sino la capa de la pausa, a <b>{z} mm</b> de "
              "la cama. Ahí la palanca manda: lo que aguanta la pieza cae con la altura "
              "y crece con el <b>cuadrado</b> de la anchura de su base.",
        "en": "To break away from the magnet it has just placed, the module must "
              "overcome the <b>shear</b> between the two, which is <b>measured with a "
              "gauge</b>: a ⌀8×5 N35 takes 15 N. With this magnet that is "
              "<b>{force} N</b>, and it lands not on the part's base but on the pause "
              "layer, <b>{z} mm</b> above the bed. The lever rules there: what the part "
              "withstands falls with height and grows with the <b>square</b> of its "
              "base width.",
        "zh": "要脱离刚放下的磁铁，模块必须克服两者之间的<b>剪切力</b>，该值为<b>实测值</b>："
              "⌀8×5 N35 需要 15 N。本磁铁为 <b>{force} N</b>，而受力点不是底面，"
              "而是距热床 <b>{z} mm</b> 的暂停层。此处杠杆效应主导：承受能力随高度下降，"
              "随底面宽度的<b>平方</b>增长。",
        "ja": "置いたばかりの磁石から離れるには、モジュールは両者間の<b>せん断力</b>に"
              "打ち勝つ必要があります。この値は<b>実測</b>で、⌀8×5 N35 では 15 N です。"
              "この磁石では <b>{force} N</b> で、その力は底面ではなくベッドから "
              "<b>{z} mm</b> の一時停止層に加わります。そこではてこが効き、"
              "耐える力は高さに反比例し、底面幅の<b>二乗</b>で増えます。",
        "it": "Per staccarsi dal magnete appena posato, il modulo deve vincere il "
              "<b>taglio</b> fra i due, che è <b>misurato col dinamometro</b>: un "
              "⌀8×5 N35 chiede 15 N. Con questo magnete sono <b>{force} N</b>, e non li "
              "riceve la base del pezzo ma lo strato della pausa, a <b>{z} mm</b> dal "
              "piano. Lì comanda la leva: quanto regge il pezzo cala con l'altezza e "
              "cresce con il <b>quadrato</b> della larghezza della base.",
        "fr": "Pour se détacher de l'aimant qu'il vient de poser, le module doit vaincre "
              "le <b>cisaillement</b> entre les deux, qui est <b>mesuré au "
              "dynamomètre</b> : un ⌀8×5 N35 demande 15 N. Avec cet aimant, cela fait "
              "<b>{force} N</b>, et ce n'est pas la base de la pièce qui les reçoit "
              "mais la couche de la pause, à <b>{z} mm</b> du plateau. Le bras de levier "
              "y commande : ce que la pièce supporte diminue avec la hauteur et croît "
              "avec le <b>carré</b> de la largeur de sa base.",
        "de": "Um sich von dem gerade abgelegten Magneten zu lösen, muss das Modul die "
              "<b>Scherkraft</b> zwischen beiden überwinden, die <b>gemessen</b> ist: "
              "ein ⌀8×5 N35 braucht 15 N. Bei diesem Magneten sind das <b>{force} N</b>, "
              "und sie treffen nicht die Grundfläche, sondern die Pausenschicht in "
              "<b>{z} mm</b> Höhe über dem Bett. Dort regiert der Hebel: was das Teil "
              "aushält, sinkt mit der Höhe und wächst mit dem <b>Quadrat</b> der Breite "
              "seiner Basis.",
        "pt": "Para se separar do íman que acabou de pousar, o módulo tem de vencer o "
              "<b>corte</b> entre os dois, que está <b>medido com dinamómetro</b>: um "
              "⌀8×5 N35 pede 15 N. Com este íman são <b>{force} N</b>, e não os recebe a "
              "base da peça mas a camada da pausa, a <b>{z} mm</b> da mesa. Aí manda a "
              "alavanca: o que a peça aguenta cai com a altura e cresce com o "
              "<b>quadrado</b> da largura da sua base."},
    # --- gráficos de Parámetros ---
    "chart.z_axis": {
        "es": "Z de la pausa (mm)", "en": "Pause Z (mm)", "zh": "暂停 Z（mm）",
        "ja": "一時停止 Z (mm)", "it": "Z della pausa (mm)", "fr": "Z de la pause (mm)",
        "de": "Pausen-Z (mm)", "pt": "Z da pausa (mm)"},
    "chart.n_axis": {
        "es": "Aguanta (N) · 1 kg ≈ 9.8 N · cada línea ×10",
        "en": "Withstands (N) · 1 kg ≈ 9.8 N · each line ×10",
        "zh": "承受力（N）· 1 kg ≈ 9.8 N · 每格 ×10",
        "ja": "耐力 (N) · 1 kg ≈ 9.8 N · 1 目盛 ×10",
        "it": "Regge (N) · 1 kg ≈ 9.8 N · ogni linea ×10",
        "fr": "Supporte (N) · 1 kg ≈ 9,8 N · chaque ligne ×10",
        "de": "Hält aus (N) · 1 kg ≈ 9,8 N · jede Linie ×10",
        "pt": "Aguenta (N) · 1 kg ≈ 9,8 N · cada linha ×10"},
    "chart.mm_axis": {
        "es": "Separación mínima (mm)", "en": "Minimum spacing (mm)",
        "zh": "最小间距（mm）", "ja": "最小間隔 (mm)",
        "it": "Distanza minima (mm)", "fr": "Écart minimal (mm)",
        "de": "Mindestabstand (mm)", "pt": "Distância mínima (mm)"},
    "chart.h_axis": {
        "es": "Altura del imán (mm)", "en": "Magnet height (mm)", "zh": "磁铁离台高度（mm）",
        "ja": "磁石の高さ (mm)", "it": "Altezza del magnete (mm)",
        "fr": "Hauteur de l'aimant (mm)", "de": "Magnethöhe (mm)",
        "pt": "Altura do íman (mm)"},
    "params.strength_header": {
        "es": "Aguante de la pieza", "en": "What the part withstands",
        "zh": "工件的承受能力", "ja": "造形物の耐力",
        "it": "Tenuta del pezzo", "fr": "Résistance de la pièce",
        "de": "Belastbarkeit des Teils", "pt": "Resistência da peça"},
    "params.strength_chart_hint": {
        "es": "El eje vertical es la fuerza lateral que la pieza aguanta antes de "
              "despegarse, en newtons: <b>1 kg de tirón son 9.8 N</b>. Sube por "
              "décadas, o sea que cada línea horizontal vale diez veces la de abajo. "
              "El eje de abajo es la altura de la pausa.<br>"
              "Las curvas azules son bases cuadradas de ese lado en mm; la verde, tu "
              "pieza. La roja es lo que empuja el imán y la naranja el margen que se "
              "exige: donde tu curva baje de ella, sale el aviso.",
        "en": "The vertical axis is the lateral force the part withstands before "
              "coming off, in newtons: <b>1 kg of pull is 9.8 N</b>. It rises by "
              "decades, so each horizontal line is ten times the one below. The bottom "
              "axis is the pause height.<br>"
              "Blue curves are square bases of that side in mm; the green one is your "
              "part. Red is what the magnet pushes with and orange is the required "
              "margin: where your curve drops below it, the warning fires.",
        "zh": "纵轴是工件在脱落前可承受的侧向力，单位牛顿：<b>1 kg 吸力约合 9.8 N</b>。"
              "刻度按数量级递增，每条横线是下一条的十倍。横轴是暂停高度。<br>"
              "蓝色曲线为对应边长（mm）的方形底面，绿色为你的工件。红线是磁铁的推力，"
              "橙线是要求的安全余量：曲线低于橙线即触发警告。",
        "ja": "縦軸は造形物が剥がれるまでに耐えられる横方向の力で、単位はニュートンです。"
              "<b>吸着力 1 kg は 9.8 N</b>。目盛は一桁ずつ上がるので、横線 1 本ごとに 10 倍"
              "になります。横軸は一時停止の高さです。<br>"
              "青は各辺（mm）の正方形底面、緑はあなたの造形物。赤は磁石が加える力、"
              "橙は必要な余裕で、曲線が橙を下回ると警告が出ます。",
        "it": "L'asse verticale è la forza laterale che il pezzo regge prima di "
              "staccarsi, in newton: <b>1 kg di attrazione sono 9.8 N</b>. Sale per "
              "decadi, quindi ogni linea orizzontale vale dieci volte quella sotto. "
              "L'asse in basso è l'altezza della pausa.<br>"
              "Le curve blu sono basi quadrate di quel lato in mm; la verde è il tuo "
              "pezzo. La rossa è quanto spinge il magnete e l'arancione il margine "
              "richiesto: dove la tua curva scende sotto, scatta l'avviso.",
        "fr": "L'axe vertical est la force latérale que la pièce supporte avant de se "
              "décoller, en newtons : <b>1 kg de traction fait 9,8 N</b>. Il monte par "
              "décades, donc chaque ligne horizontale vaut dix fois celle du dessous. "
              "L'axe du bas est la hauteur de la pause.<br>"
              "Les courbes bleues sont des bases carrées de ce côté en mm ; la verte, "
              "votre pièce. La rouge est la poussée de l'aimant et l'orange la marge "
              "exigée : là où votre courbe passe dessous, l'avertissement se déclenche.",
        "de": "Die senkrechte Achse ist die Querkraft, die das Teil aushält, bevor es "
              "sich löst, in Newton: <b>1 kg Haftkraft sind 9,8 N</b>. Sie steigt in "
              "Dekaden, jede waagerechte Linie ist also das Zehnfache der darunter. "
              "Die untere Achse ist die Pausenhöhe.<br>"
              "Die blauen Kurven sind quadratische Basen dieser Seitenlänge in mm, die "
              "grüne ist Ihr Teil. Rot ist der Druck des Magneten, orange die "
              "geforderte Reserve: wo Ihre Kurve darunter fällt, kommt die Warnung.",
        "pt": "O eixo vertical é a força lateral que a peça aguenta antes de descolar, "
              "em newtons: <b>1 kg de atração são 9,8 N</b>. Sobe por décadas, ou seja, "
              "cada linha horizontal vale dez vezes a de baixo. O eixo de baixo é a "
              "altura da pausa.<br>"
              "As curvas azuis são bases quadradas desse lado em mm; a verde é a sua "
              "peça. A vermelha é o que o íman empurra e a laranja a margem exigida: "
              "onde a sua curva descer abaixo, surge o aviso."},
    "params.spacing_chart_hint": {
        "es": "Separación mínima según lo alto que quede el imán sobre la placa. Crece "
              "de forma exponencial porque el PEI lo suelta igual de rápido, y se corta "
              "en el tope, que es lo que cabe en una cama.",
        "en": "Minimum spacing against how high the magnet sits above the plate. It grows "
              "exponentially, because the PEI lets go just as fast, and is capped at the "
              "ceiling, which is what fits on a bed."},
    "adh.table_b": {
        "es": "Lado de la base (mm)", "en": "Base side (mm)", "zh": "底面边长（mm）",
        "ja": "底面の一辺 (mm)", "it": "Lato della base (mm)", "fr": "Côté de la base (mm)",
        "de": "Basisseite (mm)", "pt": "Lado da base (mm)"},
    "adh.table_f": {
        "es": "Aguanta (N)", "en": "Withstands (N)", "zh": "可承受（N）",
        "ja": "耐力 (N)", "it": "Regge (N)", "fr": "Supporte (N)",
        "de": "Hält aus (N)", "pt": "Aguenta (N)"},
    "info.adhesion_table": {
        "es": "Base cuadrada de lado (PLA sobre PEI) — lo que aguanta a {z} mm:",
        "en": "Square base of side (PLA on PEI) — what it withstands at {z} mm:",
        "zh": "方形底面边长（PEI 上的 PLA）——在 {z} mm 处的承受力：",
        "ja": "正方形底面の一辺（PEI 上の PLA）— 高さ {z} mm での耐力：",
        "it": "Base quadrata di lato (PLA su PEI) — quanto regge a {z} mm:",
        "fr": "Base carrée de côté (PLA sur PEI) — ce qu'elle tient à {z} mm :",
        "de": "Quadratische Basis mit Seitenlänge (PLA auf PEI) — Belastbarkeit bei {z} mm:",
        "pt": "Base quadrada de lado (PLA sobre PEI) — o que aguenta a {z} mm:"},
    # --- visor: modos y controles 3D ---
    "viewer.mode_2d": {"es": "2D", "en": "2D", "zh": "2D", "ja": "2D", "it": "2D", "fr": "2D",
                       "de": "2D", "pt": "2D"},
    "viewer.mode_3d": {"es": "3D", "en": "3D", "zh": "3D", "ja": "3D", "it": "3D", "fr": "3D",
                       "de": "3D", "pt": "3D"},
    "viewer.mode_2d_tip": {"es": "Vista de la placa: colocar los imanes",
                           "en": "Bed view: place the magnets", "zh": "热床视图：放置磁铁",
                           "ja": "ベッドビュー：磁石を配置", "it": "Vista del piano: posiziona i magneti",
                           "fr": "Vue du plateau : placer les aimants",
                           "de": "Druckbett-Ansicht: Magnete platzieren",
                           "pt": "Vista da mesa: colocar os ímanes"},
    "viewer.mode_3d_tip": {"es": "Simulación 3D de la impresión y de la secuencia",
                           "en": "3D simulation of the print and the sequence",
                           "zh": "打印与序列的 3D 模拟", "ja": "印刷とシーケンスの3Dシミュレーション",
                           "it": "Simulazione 3D della stampa e della sequenza",
                           "fr": "Simulation 3D de l'impression et de la séquence",
                           "de": "3D-Simulation des Drucks und der Sequenz",
                           "pt": "Simulação 3D da impressão e da sequência"},
    "viewer.refresh": {"es": "Actualizar 3D", "en": "Refresh 3D", "zh": "刷新 3D",
                       "ja": "3Dを更新", "it": "Aggiorna 3D", "fr": "Actualiser la 3D",
                       "de": "3D aktualisieren", "pt": "Atualizar 3D"},
    "viewer.refresh_tip": {"es": "Vuelve a generar el G-code con los imanes actuales y lo carga en 3D",
                           "en": "Regenerate the G-code with the current magnets and load it in 3D",
                           "zh": "使用当前磁铁重新生成 G-code 并载入 3D",
                           "ja": "現在の磁石でG-codeを再生成して3Dに読み込む",
                           "it": "Rigenera il G-code con i magneti attuali e lo carica in 3D",
                           "fr": "Régénère le G-code avec les aimants actuels et le charge en 3D",
                           "de": "G-Code mit den aktuellen Magneten neu erzeugen und in 3D laden",
                           "pt": "Regenera o G-code com os ímanes atuais e carrega-o em 3D"},
    "viewer.loading": {"es": "Cargando…", "en": "Loading…", "zh": "加载中…", "ja": "読み込み中…",
                       "it": "Caricamento…", "fr": "Chargement…", "de": "Wird geladen…",
                       "pt": "A carregar…"},
    "viewer.no_file_3d": {"es": "Carga un archivo para ver la simulación 3D",
                          "en": "Load a file to see the 3D simulation",
                          "zh": "加载文件以查看 3D 模拟", "ja": "3Dシミュレーションを見るにはファイルを読み込んでください",
                          "it": "Carica un file per vedere la simulazione 3D",
                          "fr": "Chargez un fichier pour voir la simulation 3D",
                          "de": "Laden Sie eine Datei, um die 3D-Simulation zu sehen",
                          "pt": "Carregue um ficheiro para ver a simulação 3D"},
    "viewer.unavailable": {"es": "La vista 3D no está disponible: falta el componente QtWebEngine.",
                           "en": "The 3D view is unavailable: the QtWebEngine component is missing.",
                           "zh": "3D 视图不可用：缺少 QtWebEngine 组件。",
                           "ja": "3Dビューを利用できません：QtWebEngine コンポーネントがありません。",
                           "it": "La vista 3D non è disponibile: manca il componente QtWebEngine.",
                           "fr": "La vue 3D est indisponible : le composant QtWebEngine est absent.",
                           "de": "Die 3D-Ansicht ist nicht verfügbar: Die QtWebEngine-Komponente fehlt.",
                           "pt": "A vista 3D não está disponível: falta o componente QtWebEngine."},
    "v3d.play": {"es": "Reproducir", "en": "Play", "zh": "播放", "ja": "再生", "it": "Riproduci",
                 "fr": "Lecture", "de": "Abspielen", "pt": "Reproduzir"},
    "v3d.pause": {"es": "Pausar", "en": "Pause", "zh": "暂停", "ja": "一時停止", "it": "Pausa",
                  "fr": "Pause", "de": "Pause", "pt": "Pausa"},
    "v3d.reset": {"es": "Reiniciar", "en": "Reset", "zh": "重置", "ja": "リセット", "it": "Reimposta",
                  "fr": "Réinitialiser", "de": "Zurücksetzen", "pt": "Reiniciar"},
    "v3d.speed": {"es": "Velocidad", "en": "Speed", "zh": "速度", "ja": "速度", "it": "Velocità",
                  "fr": "Vitesse", "de": "Geschwindigkeit", "pt": "Velocidade"},
    "v3d.layer": {"es": "Capa", "en": "Layer", "zh": "层", "ja": "レイヤー", "it": "Strato",
                  "fr": "Couche", "de": "Schicht", "pt": "Camada"},
    "v3d.color_by": {"es": "Colorear por", "en": "Color by", "zh": "着色方式", "ja": "配色",
                     "it": "Colora per", "fr": "Colorer par", "de": "Einfärben nach",
                     "pt": "Colorir por"},
    "v3d.legend": {"es": "Leyenda", "en": "Legend", "zh": "图例", "ja": "凡例",
                   "it": "Legenda", "fr": "Légende", "de": "Legende", "pt": "Legenda"},
    "v3d.panel_hide": {"es": "Minimizar el panel", "en": "Minimise the panel", "zh": "收起面板",
                       "ja": "パネルを最小化", "it": "Riduci il pannello",
                       "fr": "Réduire le panneau", "de": "Bedienfeld minimieren",
                       "pt": "Minimizar o painel"},
    "v3d.panel_show": {"es": "Mostrar el panel", "en": "Show the panel", "zh": "展开面板",
                       "ja": "パネルを表示", "it": "Mostra il pannello",
                       "fr": "Afficher le panneau", "de": "Bedienfeld anzeigen",
                       "pt": "Mostrar o painel"},
    "v3d.color_feature": {"es": "Tipo de trazo", "en": "Feature", "zh": "线型", "ja": "種別",
                          "it": "Tipo di tratto", "fr": "Type de tracé", "de": "Linienart",
                          "pt": "Tipo de traço"},
    "v3d.color_layer": {"es": "Capa", "en": "Layer", "zh": "层", "ja": "レイヤー", "it": "Strato",
                        "fr": "Couche", "de": "Schicht", "pt": "Camada"},
    "v3d.color_speed": {"es": "Velocidad", "en": "Speed", "zh": "速度", "ja": "速度",
                        "it": "Velocità", "fr": "Vitesse", "de": "Geschwindigkeit",
                        "pt": "Velocidade"},
    "v3d.color_phase": {"es": "Fase", "en": "Phase", "zh": "阶段", "ja": "フェーズ", "it": "Fase",
                        "fr": "Phase", "de": "Phase", "pt": "Fase"},
    "v3d.show_travel": {"es": "Mostrar viajes", "en": "Show travels", "zh": "显示空驶",
                        "ja": "移動を表示", "it": "Mostra spostamenti", "fr": "Afficher les trajets",
                        "de": "Leerfahrten anzeigen", "pt": "Mostrar deslocações"},
    "v3d.show_volume": {"es": "Mostrar volumen", "en": "Show volume", "zh": "显示成型空间",
                        "ja": "造形空間を表示", "it": "Mostra volume", "fr": "Afficher le volume",
                        "de": "Bauraum anzeigen", "pt": "Mostrar volume"},
    "v3d.show_model": {"es": "Mostrar impresora", "en": "Show printer", "zh": "显示打印机",
                       "ja": "プリンターを表示", "it": "Mostra stampante", "fr": "Afficher l'imprimante",
                       "de": "Drucker anzeigen", "pt": "Mostrar impressora"},
    "v3d.follow": {"es": "Cámara sigue al cabezal", "en": "Camera follows the head",
                   "zh": "相机跟随喷头", "ja": "カメラがヘッドを追従",
                   "it": "La camera segue la testa", "fr": "La caméra suit la tête",
                   "de": "Kamera folgt dem Kopf", "pt": "A câmara segue a cabeça"},
    "v3d.stop_at_pause": {"es": "Parar en la pausa", "en": "Stop at the pause", "zh": "在暂停处停止",
                          "ja": "一時停止で止まる", "it": "Fermati alla pausa",
                          "fr": "S'arrêter à la pause", "de": "Bei der Pause anhalten",
                          "pt": "Parar na pausa"},
    "v3d.phase_before": {"es": "Antes", "en": "Before", "zh": "之前", "ja": "前", "it": "Prima",
                         "fr": "Avant", "de": "Davor", "pt": "Antes"},
    "v3d.phase_magnets": {"es": "Secuencia", "en": "Sequence", "zh": "序列", "ja": "シーケンス",
                          "it": "Sequenza", "fr": "Séquence", "de": "Sequenz", "pt": "Sequência"},
    "v3d.phase_after": {"es": "Después", "en": "After", "zh": "之后", "ja": "後", "it": "Dopo",
                        "fr": "Après", "de": "Danach", "pt": "Depois"},
    "v3d.phase_before_tip": {"es": "La pieza imprimiéndose hasta la parada M400 U1",
                             "en": "The part printing up to the M400 U1 stop",
                             "zh": "打印至 M400 U1 停止点", "ja": "M400 U1 の停止までの造形",
                             "it": "Il pezzo in stampa fino all'arresto M400 U1",
                             "fr": "La pièce s'imprimant jusqu'à l'arrêt M400 U1",
                             "de": "Das Teil druckt bis zum Stopp M400 U1",
                             "pt": "A peça a imprimir até à paragem M400 U1"},
    "v3d.phase_magnets_tip": {"es": "Movimientos de recogida y colocación de los imanes",
                              "en": "Magnet pick-up and placement moves",
                              "zh": "取放磁铁的动作", "ja": "磁石の取得と設置の動作",
                              "it": "Movimenti di prelievo e posa dei magneti",
                              "fr": "Mouvements de prise et de pose des aimants",
                              "de": "Bewegungen zum Aufnehmen und Setzen der Magnete",
                              "pt": "Movimentos de recolha e colocação dos ímanes"},
    "v3d.phase_after_tip": {"es": "La pieza cerrándose sobre los imanes al reanudar",
                            "en": "The part closing over the magnets after resuming",
                            "zh": "恢复后覆盖磁铁的部分", "ja": "再開後に磁石を覆う造形",
                            "it": "Il pezzo che si chiude sui magneti alla ripresa",
                            "fr": "La pièce se refermant sur les aimants à la reprise",
                            "de": "Das Teil schließt sich beim Fortsetzen über den Magneten",
                            "pt": "A peça a fechar sobre os ímanes ao retomar"},
    "v3d.magnets": {"es": "Imanes", "en": "Magnets", "zh": "磁铁", "ja": "磁石", "it": "Magneti",
                    "fr": "Aimants", "de": "Magnete", "pt": "Ímanes"},
    "v3d.no_pause": {"es": "Sin bloque de imanes: se muestra el archivo original",
                     "en": "No magnet block: showing the original file",
                     "zh": "无磁铁块：显示原始文件", "ja": "磁石ブロックなし：元のファイルを表示",
                     "it": "Nessun blocco magneti: si mostra il file originale",
                     "fr": "Aucun bloc d'aimants : le fichier original est affiché",
                     "de": "Kein Magnetblock: Die Originaldatei wird angezeigt",
                     "pt": "Sem bloco de ímanes: mostra-se o ficheiro original"},
    # --- nombres de los tipos de trazo (leyenda del visor) ---
    "feat.outer_wall": {"es": "Pared exterior", "en": "Outer wall", "zh": "外墙", "ja": "外壁",
                        "it": "Parete esterna", "fr": "Paroi extérieure", "de": "Außenwand",
                        "pt": "Parede exterior"},
    "feat.inner_wall": {"es": "Pared interior", "en": "Inner wall", "zh": "内墙", "ja": "内壁",
                        "it": "Parete interna", "fr": "Paroi intérieure", "de": "Innenwand",
                        "pt": "Parede interior"},
    "feat.top_surface": {"es": "Superficie superior", "en": "Top surface", "zh": "顶面",
                         "ja": "上面", "it": "Superficie superiore", "fr": "Surface supérieure",
                         "de": "Oberfläche oben", "pt": "Superfície superior"},
    "feat.bottom_surface": {"es": "Superficie inferior", "en": "Bottom surface", "zh": "底面",
                            "ja": "下面", "it": "Superficie inferiore", "fr": "Surface inférieure",
                            "de": "Oberfläche unten", "pt": "Superfície inferior"},
    "feat.solid_infill": {"es": "Relleno sólido", "en": "Solid infill", "zh": "实心填充",
                          "ja": "ソリッド充填", "it": "Riempimento solido", "fr": "Remplissage plein",
                          "de": "Massive Füllung", "pt": "Enchimento sólido"},
    "feat.infill": {"es": "Relleno", "en": "Infill", "zh": "填充", "ja": "充填",
                    "it": "Riempimento", "fr": "Remplissage", "de": "Füllung", "pt": "Enchimento"},
    "feat.bridge": {"es": "Puente", "en": "Bridge", "zh": "桥接", "ja": "ブリッジ", "it": "Ponte",
                    "fr": "Pont", "de": "Brücke", "pt": "Ponte"},
    "feat.support": {"es": "Soporte", "en": "Support", "zh": "支撑", "ja": "サポート",
                     "it": "Supporto", "fr": "Support", "de": "Stütze", "pt": "Suporte"},
    "feat.skirt": {"es": "Falda / Brim", "en": "Skirt / Brim", "zh": "裙边 / Brim",
                   "ja": "スカート / ブリム", "it": "Skirt / Brim", "fr": "Jupe / Bordure",
                   "de": "Skirt / Brim", "pt": "Saia / Brim"},
    "feat.gap": {"es": "Relleno de huecos", "en": "Gap fill", "zh": "间隙填充", "ja": "隙間充填",
                 "it": "Riempimento vuoti", "fr": "Remplissage des vides", "de": "Lückenfüllung",
                 "pt": "Enchimento de vãos"},
    "feat.other": {"es": "Otro", "en": "Other", "zh": "其他", "ja": "その他", "it": "Altro",
                   "fr": "Autre", "de": "Sonstige", "pt": "Outro"},
    # --- etiqueta de información ---
    "info.z_pause": {"es": "Z de la pausa", "en": "Pause Z", "zh": "暂停 Z", "ja": "一時停止 Z",
                     "it": "Z della pausa", "fr": "Z de la pause", "de": "Pausen-Z", "pt": "Z da pausa"},
    "info.temp": {"es": "Temp. hotend", "en": "Hotend temp.", "zh": "热端温度", "ja": "ホットエンド温度",
                  "it": "Temp. hotend", "fr": "Temp. hotend", "de": "Hotend-Temp.", "pt": "Temp. hotend"},
    "info.centers": {"es": "Centros sugeridos", "en": "Suggested centers", "zh": "建议圆心",
                     "ja": "推奨中心", "it": "Centri suggeriti", "fr": "Centres suggérés",
                     "de": "Vorgeschlagene Mittelpunkte", "pt": "Centros sugeridos"},
    "info.temp_undetected": {"es": "no detectada", "en": "not detected", "zh": "未检测到",
                             "ja": "未検出", "it": "non rilevata", "fr": "non détectée",
                             "de": "nicht erkannt", "pt": "não detectada"},
    "info.height": {"es": "Altura", "en": "Height", "zh": "高度", "ja": "高さ",
                    "it": "Altezza", "fr": "Hauteur", "de": "Höhe", "pt": "Altura"},
    # --- navegación entre las pausas del archivo ---
    "pause.nav": {"es": "Placa {n} de {total}", "en": "Plate {n} of {total}",
                  "zh": "第 {n} 块 / 共 {total} 块", "ja": "プレート {n} / {total}",
                  "it": "Piastra {n} di {total}", "fr": "Plaque {n} sur {total}",
                  "de": "Platte {n} von {total}", "pt": "Placa {n} de {total}"},
    "pause.prev": {"es": "Placa anterior (pausa anterior del archivo)",
                   "en": "Previous plate (previous pause in the file)",
                   "zh": "上一块（文件中的上一个暂停）",
                   "ja": "前のプレート（ファイル内の前の一時停止）",
                   "it": "Piastra precedente (pausa precedente del file)",
                   "fr": "Plaque précédente (pause précédente du fichier)",
                   "de": "Vorherige Platte (vorherige Pause der Datei)",
                   "pt": "Placa anterior (pausa anterior do arquivo)"},
    "pause.next": {"es": "Placa siguiente (pausa siguiente del archivo)",
                   "en": "Next plate (next pause in the file)",
                   "zh": "下一块（文件中的下一个暂停）",
                   "ja": "次のプレート（ファイル内の次の一時停止）",
                   "it": "Piastra successiva (pausa successiva del file)",
                   "fr": "Plaque suivante (pause suivante du fichier)",
                   "de": "Nächste Platte (nächste Pause der Datei)",
                   "pt": "Placa seguinte (pausa seguinte do arquivo)"},
    "pause.in_plate": {"es": "Placa {n}: {msg}", "en": "Plate {n}: {msg}",
                       "zh": "第 {n} 块：{msg}", "ja": "プレート {n}：{msg}",
                       "it": "Piastra {n}: {msg}", "fr": "Plaque {n} : {msg}",
                       "de": "Platte {n}: {msg}", "pt": "Placa {n}: {msg}"},
    # --- barra de estado ---
    "status.ready": {"es": "Listo. Abre un archivo .3mf o .gcode para empezar.",
                     "en": "Ready. Open a .3mf or .gcode file to start.",
                     "zh": "就绪。打开 .3mf 或 .gcode 文件以开始。",
                     "ja": "準備完了。.3mf または .gcode ファイルを開いて開始します。",
                     "it": "Pronto. Apri un file .3mf o .gcode per iniziare.",
                     "fr": "Prêt. Ouvrez un fichier .3mf ou .gcode pour commencer.",
                     "de": "Bereit. Öffnen Sie eine .3mf- oder .gcode-Datei.",
                     "pt": "Pronto. Abra um arquivo .3mf ou .gcode para começar."},
    "status.analyzed": {"es": "Archivo analizado: {name}", "en": "File analyzed: {name}",
                        "zh": "已分析文件：{name}", "ja": "解析済みファイル：{name}",
                        "it": "File analizzato: {name}", "fr": "Fichier analysé : {name}",
                        "de": "Datei analysiert: {name}", "pt": "Arquivo analisado: {name}"},
    "status.pause_selected": {
        "es": "Placa {n} de {total} · pausa a Z {z} mm",
        "en": "Plate {n} of {total} · pause at Z {z} mm",
        "zh": "第 {n} 块 / 共 {total} 块 · 在 Z {z} mm 暂停",
        "ja": "プレート {n} / {total} · Z {z} mm で一時停止",
        "it": "Piastra {n} di {total} · pausa a Z {z} mm",
        "fr": "Plaque {n} sur {total} · pause à Z {z} mm",
        "de": "Platte {n} von {total} · Pause bei Z {z} mm",
        "pt": "Placa {n} de {total} · pausa em Z {z} mm",
    },
    "status.exported": {"es": "Exportado ({fmt}): {path}", "en": "Exported ({fmt}): {path}",
                        "zh": "已导出（{fmt}）：{path}", "ja": "エクスポート済み（{fmt}）：{path}",
                        "it": "Esportato ({fmt}): {path}", "fr": "Exporté ({fmt}) : {path}",
                        "de": "Exportiert ({fmt}): {path}", "pt": "Exportado ({fmt}): {path}"},
    "status.recomputed": {"es": "Detección rehecha: {n} centro(s).", "en": "Detection re-run: {n} center(s).",
                          "zh": "已重新检测：{n} 个圆心。", "ja": "検出をやり直しました：中心 {n} 個。",
                          "it": "Rilevamento rieseguito: {n} centro/i.", "fr": "Détection relancée : {n} centre(s).",
                          "de": "Erkennung neu: {n} Mittelpunkt(e).", "pt": "Detecção refeita: {n} centro(s)."},
    "status.params_reset": {"es": "Parámetros restaurados a los valores por defecto.",
                            "en": "Parameters reset to their default values.",
                            "zh": "参数已恢复为默认值。", "ja": "パラメータを既定値に戻しました。",
                            "it": "Parametri ripristinati ai valori predefiniti.",
                            "fr": "Paramètres réinitialisés aux valeurs par défaut.",
                            "de": "Parameter auf Standardwerte zurückgesetzt.",
                            "pt": "Parâmetros restaurados aos valores padrão."},
    "status.detection_off": {"es": "Detección de agujeros desactivada.", "en": "Hole detection disabled.",
                             "zh": "孔检测已禁用。", "ja": "穴検出は無効です。",
                             "it": "Rilevamento fori disattivato.", "fr": "Détection des trous désactivée.",
                             "de": "Locherkennung deaktiviert.", "pt": "Detecção de furos desativada."},
    "status.spacing_cancelled": {
        "es": "Cancelado: hay imanes demasiado juntos. Sepáralos o acepta el riesgo.",
        "en": "Cancelled: some magnets are too close. Separate them or accept the risk.",
        "zh": "已取消：部分磁铁间距过近。请拉开距离或接受风险。",
        "ja": "中止しました：近すぎる磁石があります。離すか、リスクを承知で進めてください。",
        "it": "Annullato: ci sono magneti troppo vicini. Allontanali o accetta il rischio.",
        "fr": "Annulé : des aimants sont trop proches. Écartez-les ou acceptez le risque.",
        "de": "Abgebrochen: Magnete liegen zu dicht. Trennen Sie sie oder nehmen Sie das Risiko an.",
        "pt": "Cancelado: há ímãs demasiado juntos. Afaste-os ou aceite o risco."},
    # --- diálogos / mensajes ---
    "msg.warning": {"es": "Aviso", "en": "Warning", "zh": "提示", "ja": "警告",
                    "it": "Avviso", "fr": "Avertissement", "de": "Hinweis", "pt": "Aviso"},
    "msg.no_file_first": {"es": "Primero abre un archivo .3mf o .gcode.",
                          "en": "Open a .3mf or .gcode file first.", "zh": "请先打开 .3mf 或 .gcode 文件。",
                          "ja": "先に .3mf または .gcode ファイルを開いてください。",
                          "it": "Apri prima un file .3mf o .gcode.",
                          "fr": "Ouvrez d’abord un fichier .3mf ou .gcode.",
                          "de": "Öffnen Sie zuerst eine .3mf- oder .gcode-Datei.",
                          "pt": "Abra primeiro um arquivo .3mf ou .gcode."},
    "msg.no_points": {"es": "No has colocado ningún imán. Añade al menos uno en el visor.",
                      "en": "No magnets placed. Add at least one in the viewer.",
                      "zh": "尚未放置磁铁。请在视图中至少添加一个。",
                      "ja": "磁石が配置されていません。ビューアで少なくとも 1 つ追加してください。",
                      "it": "Nessun magnete posizionato. Aggiungine almeno uno nel visore.",
                      "fr": "Aucun aimant placé. Ajoutez-en au moins un dans la vue.",
                      "de": "Keine Magnete platziert. Fügen Sie mindestens einen hinzu.",
                      "pt": "Nenhum ímã colocado. Adicione pelo menos um no visualizador."},
    "msg.export_title": {"es": "Exportar resultado", "en": "Export result", "zh": "导出结果",
                         "ja": "結果をエクスポート", "it": "Esporta risultato", "fr": "Exporter le résultat",
                         "de": "Ergebnis exportieren", "pt": "Exportar resultado"},
    "msg.exported_title": {"es": "Exportado", "en": "Exported", "zh": "已导出", "ja": "エクスポート完了",
                           "it": "Esportato", "fr": "Exporté", "de": "Exportiert", "pt": "Exportado"},
    "msg.exported_ok": {"es": "Archivo guardado correctamente:\n{path}",
                        "en": "File saved successfully:\n{path}", "zh": "文件已成功保存：\n{path}",
                        "ja": "ファイルを保存しました：\n{path}", "it": "File salvato correttamente:\n{path}",
                        "fr": "Fichier enregistré :\n{path}", "de": "Datei gespeichert:\n{path}",
                        "pt": "Arquivo salvo com sucesso:\n{path}"},
    "msg.error_analyze": {"es": "No se pudo analizar el archivo", "en": "Could not analyze the file",
                          "zh": "无法分析文件", "ja": "ファイルを解析できませんでした",
                          "it": "Impossibile analizzare il file", "fr": "Impossible d’analyser le fichier",
                          "de": "Datei konnte nicht analysiert werden", "pt": "Não foi possível analisar o arquivo"},
    "msg.error_export": {"es": "No se pudo exportar", "en": "Could not export", "zh": "无法导出",
                         "ja": "エクスポートできませんでした", "it": "Impossibile esportare",
                         "fr": "Impossible d’exporter", "de": "Export fehlgeschlagen", "pt": "Não foi possível exportar"},
    "msg.error_generate": {"es": "Error generando el G-code", "en": "Error generating G-code",
                           "zh": "生成 G-code 出错", "ja": "G-code の生成エラー",
                           "it": "Errore nella generazione del G-code", "fr": "Erreur de génération du G-code",
                           "de": "Fehler beim Erzeugen des G-codes", "pt": "Erro ao gerar o G-code"},
    "seq.export_test": {
        "es": "Exportar secuencia de prueba…", "en": "Export test sequence…",
        "zh": "导出测试序列…", "ja": "テストシーケンスを書き出す…",
        "it": "Esporta sequenza di prova…", "fr": "Exporter la séquence de test…",
        "de": "Testsequenz exportieren…", "pt": "Exportar sequência de teste…",
    },
    "seq.export_test_hint": {
        "es": "Genera un G-code suelto (G28 · G92 · Inicio · Rojo · Azul · Fin · Final) "
              "para enviarlo a la impresora desde Bambu Studio. No imprime nada.",
        "en": "Builds a standalone G-code (G28 · G92 · Start · Red · Blue · End · Final) "
              "to send to the printer from Bambu Studio. It prints nothing.",
        "zh": "生成独立的 G-code（G28 · G92 · 开始 · 红 · 蓝 · 结束 · 收尾），"
              "可从 Bambu Studio 发送到打印机。不会打印任何东西。",
        "ja": "単独の G-code（G28 · G92 · 開始 · 赤 · 青 · 終了 · 仕上げ）を生成し、"
              "Bambu Studio からプリンターへ送れます。何も造形しません。",
        "it": "Genera un G-code autonomo (G28 · G92 · Inizio · Rosso · Blu · Fine · Finale) "
              "da inviare alla stampante da Bambu Studio. Non stampa nulla.",
        "fr": "Génère un G-code autonome (G28 · G92 · Début · Rouge · Bleu · Fin · Final) "
              "à envoyer à l’imprimante depuis Bambu Studio. N’imprime rien.",
        "de": "Erzeugt einen eigenständigen G-code (G28 · G92 · Start · Rot · Blau · Ende · Finale) "
              "zum Senden an den Drucker aus Bambu Studio. Es wird nichts gedruckt.",
        "pt": "Gera um G-code autónomo (G28 · G92 · Início · Vermelho · Azul · Fim · Final) "
              "para enviar à impressora a partir do Bambu Studio. Não imprime nada.",
    },
    "msg.template_needed": {
        "es": "Para el .3mf hace falta una plantilla.\n\n"
              "Bambu Studio no acepta un 3MF creado desde cero: necesita el perfil de "
              "impresión, las miniaturas y las relaciones internas de un proyecto real.\n\n"
              "Elige un .3mf ya laminado con Bambu Studio para tu impresora. Se copiará "
              "entero y solo se cambiará el G-code de dentro. Se recordará para la próxima vez.",
        "en": "A template is required for .3mf.\n\n"
              "Bambu Studio does not accept a 3MF built from scratch: it needs the print "
              "profile, the thumbnails and the internal relationships of a real project.\n\n"
              "Pick a .3mf already sliced with Bambu Studio for your printer. It will be "
              "copied whole and only the G-code inside will be replaced. It will be remembered.",
        "zh": "导出 .3mf 需要一个模板。\n\n"
              "Bambu Studio 不接受从零创建的 3MF：它需要真实项目的打印配置、缩略图和内部关系。\n\n"
              "请选择一个已用 Bambu Studio 为你的打印机切片的 .3mf。它会被整体复制，只替换里面的 G-code，并会被记住。",
        "ja": ".3mf の書き出しにはテンプレートが必要です。\n\n"
              "Bambu Studio はゼロから作った 3MF を受け付けません: 実際のプロジェクトの"
              "印刷プロファイル・サムネイル・内部リレーションが必要です。\n\n"
              "お使いのプリンター用に Bambu Studio でスライス済みの .3mf を選んでください。"
              "丸ごとコピーし、中の G-code だけを差し替えます。次回のために記憶します。",
        "it": "Per il .3mf serve un modello di partenza.\n\n"
              "Bambu Studio non accetta un 3MF creato da zero: servono il profilo di stampa, "
              "le miniature e le relazioni interne di un progetto reale.\n\n"
              "Scegli un .3mf già processato con Bambu Studio per la tua stampante. Verrà "
              "copiato per intero e sarà sostituito solo il G-code interno. Verrà ricordato.",
        "fr": "Un modèle est nécessaire pour le .3mf.\n\n"
              "Bambu Studio n’accepte pas un 3MF créé de zéro : il lui faut le profil "
              "d’impression, les vignettes et les relations internes d’un vrai projet.\n\n"
              "Choisissez un .3mf déjà tranché avec Bambu Studio pour votre imprimante. Il sera "
              "copié entièrement et seul le G-code interne sera remplacé. Il sera mémorisé.",
        "de": "Für .3mf wird eine Vorlage benötigt.\n\n"
              "Bambu Studio akzeptiert kein von Grund auf erzeugtes 3MF: Es braucht das "
              "Druckprofil, die Vorschaubilder und die internen Beziehungen eines echten Projekts.\n\n"
              "Wähle ein mit Bambu Studio für deinen Drucker geslictes .3mf. Es wird komplett "
              "kopiert und nur der G-code darin ersetzt. Es wird gemerkt.",
        "pt": "Para o .3mf é necessário um modelo base.\n\n"
              "O Bambu Studio não aceita um 3MF criado do zero: precisa do perfil de impressão, "
              "das miniaturas e das relações internas de um projeto real.\n\n"
              "Escolhe um .3mf já fatiado com o Bambu Studio para a tua impressora. Será copiado "
              "por inteiro e só o G-code interno será substituído. Ficará memorizado.",
    },
    "msg.template_pick_title": {
        "es": "Elegir plantilla .3mf (proyecto ya laminado)",
        "en": "Choose .3mf template (already sliced project)",
        "zh": "选择 .3mf 模板（已切片的项目）",
        "ja": ".3mf テンプレートを選択（スライス済みプロジェクト）",
        "it": "Scegli modello .3mf (progetto già processato)",
        "fr": "Choisir un modèle .3mf (projet déjà tranché)",
        "de": ".3mf-Vorlage wählen (bereits geslictes Projekt)",
        "pt": "Escolher modelo .3mf (projeto já fatiado)",
    },
    "msg.template_invalid": {
        "es": "Ese archivo no sirve como plantilla:\n{path}\n\n"
              "No contiene ningún G-code dentro. Usa un .3mf que hayas laminado "
              "con Bambu Studio (no un .3mf de solo modelo).",
        "en": "That file cannot be used as a template:\n{path}\n\n"
              "It contains no G-code inside. Use a .3mf you have sliced with "
              "Bambu Studio (not a model-only .3mf).",
        "zh": "该文件不能用作模板：\n{path}\n\n"
              "其中不包含 G-code。请使用你用 Bambu Studio 切片过的 .3mf（不是仅含模型的 .3mf）。",
        "ja": "そのファイルはテンプレートとして使えません:\n{path}\n\n"
              "中に G-code がありません。Bambu Studio でスライス済みの .3mf を"
              "使ってください（モデルだけの .3mf は不可）。",
        "it": "Quel file non può essere usato come modello:\n{path}\n\n"
              "Non contiene G-code. Usa un .3mf processato con Bambu Studio "
              "(non un .3mf di solo modello).",
        "fr": "Ce fichier ne peut pas servir de modèle :\n{path}\n\n"
              "Il ne contient aucun G-code. Utilisez un .3mf tranché avec Bambu "
              "Studio (pas un .3mf contenant seulement le modèle).",
        "de": "Diese Datei taugt nicht als Vorlage:\n{path}\n\n"
              "Sie enthält keinen G-code. Nimm ein mit Bambu Studio geslictes .3mf "
              "(kein reines Modell-3MF).",
        "pt": "Esse ficheiro não serve como modelo:\n{path}\n\n"
              "Não contém G-code. Usa um .3mf fatiado com o Bambu Studio "
              "(não um .3mf só com o modelo).",
    },
    "msg.test_export_title": {
        "es": "Exportar secuencia de prueba", "en": "Export test sequence",
        "zh": "导出测试序列", "ja": "テストシーケンスの書き出し",
        "it": "Esporta sequenza di prova", "fr": "Exporter la séquence de test",
        "de": "Testsequenz exportieren", "pt": "Exportar sequência de teste",
    },
    "msg.test_exported_ok": {
        "es": "Secuencia de prueba guardada:\n{path}\n\n"
              "Orden: G28 · G92 · Inicio · Rojo · Azul · Fin · Final\n"
              "Z de referencia: {z} mm   ·   temperatura: {temp} °C\n\n"
              "Ábrelo con Bambu Studio y envíalo a la impresora.",
        "en": "Test sequence saved:\n{path}\n\n"
              "Order: G28 · G92 · Start · Red · Blue · End · Final\n"
              "Reference Z: {z} mm   ·   temperature: {temp} °C\n\n"
              "Open it with Bambu Studio and send it to the printer.",
        "zh": "测试序列已保存：\n{path}\n\n"
              "顺序：G28 · G92 · 开始 · 红 · 蓝 · 结束 · 收尾\n"
              "参考 Z：{z} mm   ·   温度：{temp} °C\n\n用 Bambu Studio 打开并发送到打印机。",
        "ja": "テストシーケンスを保存しました:\n{path}\n\n"
              "順序: G28 · G92 · 開始 · 赤 · 青 · 終了 · 仕上げ\n"
              "基準 Z: {z} mm   ·   温度: {temp} °C\n\n"
              "Bambu Studio で開いてプリンターへ送信してください。",
        "it": "Sequenza di prova salvata:\n{path}\n\n"
              "Ordine: G28 · G92 · Inizio · Rosso · Blu · Fine · Finale\n"
              "Z di riferimento: {z} mm   ·   temperatura: {temp} °C\n\n"
              "Aprila con Bambu Studio e inviala alla stampante.",
        "fr": "Séquence de test enregistrée :\n{path}\n\n"
              "Ordre : G28 · G92 · Début · Rouge · Bleu · Fin · Final\n"
              "Z de référence : {z} mm   ·   température : {temp} °C\n\n"
              "Ouvrez-la avec Bambu Studio et envoyez-la à l’imprimante.",
        "de": "Testsequenz gespeichert:\n{path}\n\n"
              "Reihenfolge: G28 · G92 · Start · Rot · Blau · Ende · Finale\n"
              "Referenz-Z: {z} mm   ·   Temperatur: {temp} °C\n\n"
              "Öffne sie mit Bambu Studio und sende sie an den Drucker.",
        "pt": "Sequência de teste guardada:\n{path}\n\n"
              "Ordem: G28 · G92 · Início · Vermelho · Azul · Fim · Final\n"
              "Z de referência: {z} mm   ·   temperatura: {temp} °C\n\n"
              "Abre-a com o Bambu Studio e envia-a para a impressora.",
    },
    "msg.project_missing_file": {
        "es": "No se encuentra el archivo del proyecto:\n{path}\n\n"
              "Se han restaurado los imanes y los ajustes, pero tendrás que abrir el archivo de nuevo.",
        "en": "The project's file could not be found:\n{path}\n\n"
              "Magnets and settings were restored, but you will have to open the file again.",
        "zh": "找不到项目的文件：\n{path}\n\n已恢复磁铁和设置，但你需要重新打开该文件。",
        "ja": "プロジェクトのファイルが見つかりません:\n{path}\n\n"
              "磁石と設定は復元しましたが、ファイルを開き直す必要があります。",
        "it": "File del progetto non trovato:\n{path}\n\n"
              "Magneti e impostazioni sono stati ripristinati, ma dovrai riaprire il file.",
        "fr": "Le fichier du projet est introuvable :\n{path}\n\n"
              "Les aimants et les réglages ont été restaurés, mais vous devrez rouvrir le fichier.",
        "de": "Die Datei des Projekts wurde nicht gefunden:\n{path}\n\n"
              "Magnete und Einstellungen wurden wiederhergestellt, aber die Datei muss erneut geöffnet werden.",
        "pt": "Não foi possível encontrar o arquivo do projeto:\n{path}\n\n"
              "Os ímãs e os ajustes foram restaurados, mas você terá de abrir o arquivo de novo.",
    },
    "msg.file_dialog_open": {"es": "Abrir archivo de impresión", "en": "Open print file",
                             "zh": "打开打印文件", "ja": "印刷ファイルを開く", "it": "Apri file di stampa",
                             "fr": "Ouvrir un fichier d’impression", "de": "Druckdatei öffnen",
                             "pt": "Abrir arquivo de impressão"},
    # --- módulos ---
    "tab.modules": {"es": "Imanes", "en": "Magnets", "zh": "模块", "ja": "モジュール",
                    "it": "Moduli", "fr": "Modules", "de": "Module", "pt": "Módulos"},
    "mod.add": {"es": "Añadir imán", "en": "Add magnet", "zh": "添加模块", "ja": "モジュールを追加",
                "it": "Aggiungi modulo", "fr": "Ajouter un module", "de": "Modul hinzufügen",
                "pt": "Adicionar módulo"},
    "mod.remove": {"es": "Quitar imán", "en": "Remove magnet", "zh": "移除模块", "ja": "モジュールを削除",
                   "it": "Rimuovi modulo", "fr": "Supprimer le module", "de": "Modul entfernen",
                   "pt": "Remover módulo"},
    "mod.name": {"es": "Nombre", "en": "Name", "zh": "名称", "ja": "名前",
                 "it": "Nome", "fr": "Nom", "de": "Name", "pt": "Nome"},
    "mod.diameter": {"es": "Diámetro (mm)", "en": "Diameter (mm)", "zh": "直径 (mm)",
                     "ja": "直径 (mm)", "it": "Diametro (mm)", "fr": "Diamètre (mm)",
                     "de": "Durchmesser (mm)", "pt": "Diâmetro (mm)"},
    "mod.height": {"es": "Altura (mm)", "en": "Height (mm)", "zh": "高度 (mm)",
                   "ja": "高さ (mm)", "it": "Altezza (mm)", "fr": "Hauteur (mm)",
                   "de": "Höhe (mm)", "pt": "Altura (mm)"},
    "mod.height_capped": {
        "es": "Altura (mm) · máx. {max} con este diámetro",
        "en": "Height (mm) · max. {max} with this diameter"},
    "mod.color": {"es": "Dispensador", "en": "Dispenser", "zh": "供料器", "ja": "ディスペンサー",
                  "it": "Dispensatore", "fr": "Distributeur", "de": "Spender",
                  "pt": "Dispensador"},
    "mod.color_red": {"es": "Rojo", "en": "Red", "zh": "红色", "ja": "赤", "it": "Rosso",
                      "fr": "Rouge", "de": "Rot", "pt": "Vermelho"},
    "mod.color_blue": {"es": "Azul", "en": "Blue", "zh": "蓝色", "ja": "青", "it": "Blu",
                       "fr": "Bleu", "de": "Blau", "pt": "Azul"},
    "mod.polarity": {"es": "Polo hacia arriba", "en": "Pole facing up", "zh": "朝上的磁极",
                     "ja": "上を向く極", "it": "Polo verso l'alto", "fr": "Pôle vers le haut",
                     "de": "Pol nach oben", "pt": "Polo para cima"},
    "mod.pole_n": {"es": "N", "en": "N", "zh": "N", "ja": "N", "it": "N", "fr": "N",
                   "de": "N", "pt": "N"},
    "mod.pole_s": {"es": "S", "en": "S", "zh": "S", "ja": "S", "it": "S", "fr": "S",
                   "de": "S", "pt": "S"},
    "mod.pole_hint": {"es": "Atrae con el polo {pole} hacia arriba",
                      "en": "Attracts with the {pole} pole facing up",
                      "zh": "{pole} 极朝上吸附", "ja": "{pole} 極を上にして吸着",
                      "it": "Attrae con il polo {pole} verso l'alto",
                      "fr": "Attire avec le pôle {pole} vers le haut",
                      "de": "Zieht mit dem {pole}-Pol nach oben an",
                      "pt": "Atrai com o polo {pole} para cima"},
    "mod.max_hint": {"es": "Un imán por dispensador: rojo y azul.",
                     "en": "One magnet per dispenser: red and blue.",
                     "zh": "每个供料器一个模块：红色和蓝色。",
                     "ja": "ディスペンサーごとに1モジュール：赤と青。",
                     "it": "Un modulo per dispensatore: rosso e blu.",
                     "fr": "Un module par distributeur : rouge et bleu.",
                     "de": "Ein Modul pro Spender: Rot und Blau.",
                     "pt": "Um módulo por dispensador: vermelho e azul."},
    "mod.default_name": {"es": "Imán {n}", "en": "Magnet {n}", "zh": "磁铁 {n}", "ja": "磁石 {n}",
                         "it": "Magnete {n}", "fr": "Aimant {n}", "de": "Magnet {n}", "pt": "Ímã {n}"},
    "panel.toggle": {"es": "Mostrar / ocultar panel", "en": "Show / hide panel", "zh": "显示 / 隐藏面板",
                     "ja": "パネルの表示 / 非表示", "it": "Mostra / nascondi pannello",
                     "fr": "Afficher / masquer le panneau", "de": "Panel ein-/ausblenden",
                     "pt": "Mostrar / ocultar painel"},
    # --- preferencias ---
    "prefs.title": {"es": "Preferencias", "en": "Preferences", "zh": "首选项", "ja": "環境設定",
                    "it": "Preferenze", "fr": "Préférences", "de": "Einstellungen", "pt": "Preferências"},
    "prefs.language": {"es": "Idioma:", "en": "Language:", "zh": "语言：", "ja": "言語：",
                       "it": "Lingua:", "fr": "Langue :", "de": "Sprache:", "pt": "Idioma:"},
    "prefs.theme": {"es": "Tema:", "en": "Theme:", "zh": "主题：", "ja": "テーマ：",
                    "it": "Tema:", "fr": "Thème :", "de": "Thema:", "pt": "Tema:"},
    "prefs.template": {
        "es": "Plantilla .3mf (prueba):", "en": ".3mf template (test):",
        "zh": ".3mf 模板（测试）：", "ja": ".3mf テンプレート（テスト）:",
        "it": "Modello .3mf (prova):", "fr": "Modèle .3mf (test) :",
        "de": ".3mf-Vorlage (Test):", "pt": "Modelo .3mf (teste):",
    },
    "prefs.template_none": {
        "es": "(se pedirá al exportar)", "en": "(will be asked on export)",
        "zh": "（导出时询问）", "ja": "（書き出し時に確認します）",
        "it": "(verrà chiesto all’esportazione)", "fr": "(demandé à l’export)",
        "de": "(wird beim Export abgefragt)", "pt": "(será pedido ao exportar)",
    },
    "prefs.theme_dark": {"es": "Oscuro", "en": "Dark", "zh": "深色", "ja": "ダーク",
                         "it": "Scuro", "fr": "Sombre", "de": "Dunkel", "pt": "Escuro"},
    "prefs.theme_light": {"es": "Claro", "en": "Light", "zh": "浅色", "ja": "ライト",
                          "it": "Chiaro", "fr": "Clair", "de": "Hell", "pt": "Claro"},
    "lic.active": {
        "es": "Licencia activa — {name} ({edition}, exp.: {exp})",
        "en": "License active — {name} ({edition}, exp.: {exp})",
        "zh": "许可证有效 — {name}（{edition}，到期：{exp}）",
        "ja": "ライセンス有効 — {name}（{edition}、期限：{exp}）",
        "it": "Licenza attiva — {name} ({edition}, scad.: {exp})",
        "fr": "Licence active — {name} ({edition}, exp. : {exp})",
        "de": "Lizenz aktiv — {name} ({edition}, gültig bis: {exp})",
        "pt": "Licença ativa — {name} ({edition}, exp.: {exp})",
    },
    "lic.perpetual": {"es": "perpetua", "en": "perpetual", "zh": "永久", "ja": "無期限",
                      "it": "perpetua", "fr": "perpétuelle", "de": "unbefristet", "pt": "perpétua"},
    "lic.none": {
        "es": "Sin licencia — se requiere activación", "en": "No license — activation required",
        "zh": "无许可证 — 需要激活", "ja": "ライセンスなし — アクティベーションが必要です",
        "it": "Nessuna licenza — attivazione richiesta", "fr": "Aucune licence — activation requise",
        "de": "Keine Lizenz — Aktivierung erforderlich", "pt": "Sem licença — ativação necessária",
    },
    # --- actualizaciones ---
    "upd.title": {"es": "Actualización disponible", "en": "Update available", "zh": "有可用更新",
                  "ja": "アップデートがあります", "it": "Aggiornamento disponibile",
                  "fr": "Mise à jour disponible", "de": "Update verfügbar",
                  "pt": "Atualização disponível"},
    "upd.header": {
        "es": "Ya está disponible {app} {version}", "en": "{app} {version} is available",
        "zh": "{app} {version} 已发布", "ja": "{app} {version} が利用可能です",
        "it": "{app} {version} è disponibile", "fr": "{app} {version} est disponible",
        "de": "{app} {version} ist verfügbar", "pt": "{app} {version} já está disponível",
    },
    "upd.current": {
        "es": "Versión instalada: {version}", "en": "Installed version: {version}",
        "zh": "当前安装版本：{version}", "ja": "インストール済みバージョン: {version}",
        "it": "Versione installata: {version}", "fr": "Version installée : {version}",
        "de": "Installierte Version: {version}", "pt": "Versão instalada: {version}",
    },
    "upd.notes": {"es": "Novedades", "en": "What's new", "zh": "更新内容", "ja": "変更点",
                  "it": "Novità", "fr": "Nouveautés", "de": "Neuerungen", "pt": "Novidades"},
    "upd.verified": {
        "es": "Se descargará desde GitHub y se comprobarán su firma y su huella SHA-256 "
              "antes de instalar.",
        "en": "It will be downloaded from GitHub; its signature and SHA-256 are checked "
              "before installing.",
        "zh": "将从 GitHub 下载，安装前会校验其签名和 SHA-256 摘要。",
        "ja": "GitHub からダウンロードし、インストール前に署名と SHA-256 を検証します。",
        "it": "Verrà scaricato da GitHub; firma e SHA-256 sono verificati prima "
              "dell'installazione.",
        "fr": "Le téléchargement se fait depuis GitHub ; la signature et l'empreinte "
              "SHA-256 sont vérifiées avant l'installation.",
        "de": "Der Download erfolgt von GitHub; Signatur und SHA-256 werden vor der "
              "Installation geprüft.",
        "pt": "Será descarregado do GitHub; a assinatura e o SHA-256 são verificados "
              "antes de instalar.",
    },
    "upd.install": {"es": "Descargar e instalar", "en": "Download and install",
                    "zh": "下载并安装", "ja": "ダウンロードしてインストール",
                    "it": "Scarica e installa", "fr": "Télécharger et installer",
                    "de": "Herunterladen und installieren", "pt": "Descarregar e instalar"},
    "upd.skip": {"es": "Omitir esta versión", "en": "Skip this version", "zh": "跳过此版本",
                 "ja": "このバージョンをスキップ", "it": "Salta questa versione",
                 "fr": "Ignorer cette version", "de": "Diese Version überspringen",
                 "pt": "Ignorar esta versão"},
    "upd.later": {"es": "Ahora no", "en": "Not now", "zh": "以后再说", "ja": "後で",
                  "it": "Non ora", "fr": "Plus tard", "de": "Später", "pt": "Agora não"},
    "upd.cancel": {"es": "Cancelar", "en": "Cancel", "zh": "取消", "ja": "キャンセル",
                   "it": "Annulla", "fr": "Annuler", "de": "Abbrechen", "pt": "Cancelar"},
    "upd.downloading": {
        "es": "Descargando… {done} de {total} MB", "en": "Downloading… {done} of {total} MB",
        "zh": "正在下载… {done} / {total} MB", "ja": "ダウンロード中… {done} / {total} MB",
        "it": "Download… {done} di {total} MB", "fr": "Téléchargement… {done} sur {total} Mo",
        "de": "Wird heruntergeladen… {done} von {total} MB",
        "pt": "A descarregar… {done} de {total} MB",
    },
    "upd.downloading_unknown": {
        "es": "Descargando… {done} MB", "en": "Downloading… {done} MB",
        "zh": "正在下载… {done} MB", "ja": "ダウンロード中… {done} MB",
        "it": "Download… {done} MB", "fr": "Téléchargement… {done} Mo",
        "de": "Wird heruntergeladen… {done} MB", "pt": "A descarregar… {done} MB",
    },
    "upd.ready": {
        "es": "La descarga ha terminado y la firma es correcta. Se abrirá el instalador "
              "y {app} se cerrará.",
        "en": "Download complete and signature verified. The installer will open and "
              "{app} will close.",
        "zh": "下载完成且签名验证通过。安装程序将启动，{app} 将关闭。",
        "ja": "ダウンロードが完了し、署名を確認しました。インストーラーを開き、{app} を終了します。",
        "it": "Download completato e firma verificata. Si aprirà il programma di "
              "installazione e {app} si chiuderà.",
        "fr": "Téléchargement terminé et signature vérifiée. Le programme d'installation "
              "va s'ouvrir et {app} se fermera.",
        "de": "Download abgeschlossen und Signatur geprüft. Das Installationsprogramm "
              "wird geöffnet und {app} wird beendet.",
        "pt": "Descarga concluída e assinatura verificada. O instalador será aberto e o "
              "{app} será fechado.",
    },
    "upd.launch_failed": {
        "es": "No se ha podido abrir el instalador. Ejecútalo a mano:\n{path}",
        "en": "The installer could not be started. Run it manually:\n{path}",
        "zh": "无法启动安装程序，请手动运行：\n{path}",
        "ja": "インストーラーを起動できませんでした。手動で実行してください:\n{path}",
        "it": "Impossibile avviare il programma di installazione. Eseguilo manualmente:\n{path}",
        "fr": "Impossible de lancer le programme d'installation. Exécutez-le "
              "manuellement :\n{path}",
        "de": "Das Installationsprogramm konnte nicht gestartet werden. Bitte manuell "
              "ausführen:\n{path}",
        "pt": "Não foi possível iniciar o instalador. Execute-o manualmente:\n{path}",
    },
    "upd.status_available": {
        "es": "Actualización disponible: v{version}", "en": "Update available: v{version}",
        "zh": "有可用更新：v{version}", "ja": "アップデートあり: v{version}",
        "it": "Aggiornamento disponibile: v{version}",
        "fr": "Mise à jour disponible : v{version}", "de": "Update verfügbar: v{version}",
        "pt": "Atualização disponível: v{version}",
    },
    "upd.menu_check": {"es": "Buscar actualizaciones…", "en": "Check for updates…",
                       "zh": "检查更新…", "ja": "アップデートを確認…",
                       "it": "Controlla aggiornamenti…",
                       "fr": "Rechercher des mises à jour…", "de": "Nach Updates suchen…",
                       "pt": "Procurar atualizações…"},
    "upd.menu_auto": {
        "es": "Buscar actualizaciones automáticamente",
        "en": "Check for updates automatically", "zh": "自动检查更新",
        "ja": "自動的にアップデートを確認", "it": "Controlla aggiornamenti automaticamente",
        "fr": "Rechercher les mises à jour automatiquement",
        "de": "Automatisch nach Updates suchen",
        "pt": "Procurar atualizações automaticamente",
    },
    "upd.up_to_date": {
        "es": "{app} está actualizado (v{version}).", "en": "{app} is up to date (v{version}).",
        "zh": "{app} 已是最新版本（v{version}）。", "ja": "{app} は最新です（v{version}）。",
        "it": "{app} è aggiornato (v{version}).", "fr": "{app} est à jour (v{version}).",
        "de": "{app} ist aktuell (v{version}).", "pt": "O {app} está atualizado (v{version}).",
    },
    "upd.not_configured": {
        "es": "Esta versión no tiene canal de actualizaciones configurado.",
        "en": "This build has no update channel configured.",
        "zh": "此版本未配置更新通道。",
        "ja": "このビルドには更新チャンネルが設定されていません。",
        "it": "Questa build non ha un canale di aggiornamento configurato.",
        "fr": "Cette version n'a pas de canal de mise à jour configuré.",
        "de": "Für diese Version ist kein Update-Kanal konfiguriert.",
        "pt": "Esta versão não tem canal de atualizações configurado.",
    },
    # --- aviso y vista informativa de la distancia mínima ---
    "spacing.warn_title": {"es": "Imanes demasiado juntos", "en": "Magnets too close together",
                           "zh": "磁铁间距过近", "ja": "磁石が近すぎます",
                           "it": "Magneti troppo vicini", "fr": "Aimants trop proches",
                           "de": "Magnete zu dicht beieinander", "pt": "Ímãs demasiado juntos"},
    # Neutral a propósito: la lista mezcla imanes demasiado juntos con imanes por
    # encima de los que pasa el módulo, y son dos problemas distintos.
    "spacing.warn_header": {
        "es": "{n} conflicto(s) entre imanes en esta placa",
        "en": "{n} magnet conflict(s) on this plate",
        "zh": "本板上有 {n} 处磁铁冲突",
        "ja": "このプレートに磁石の問題が {n} 件あります",
        "it": "{n} conflitto/i tra magneti su questa piastra",
        "fr": "{n} conflit(s) entre aimants sur cette plaque",
        "de": "{n} Magnetkonflikt(e) auf dieser Platte",
        "pt": "{n} conflito(s) entre ímãs nesta placa"},
    "spacing.warn_body": {
        "es": "Así de cerca se atraen con más fuerza de la que la placa PEI usa para "
              "sujetarlos, así que uno de los dos puede salirse de su agujero y pegarse "
              "al otro <b>en mitad de la impresión</b>, arruinando la pieza y pudiendo "
              "chocar con la boquilla. La separación se mide <b>en línea recta</b>: lo "
              "que cuenta es la distancia entre los dos centros, por donde sea.",
        "en": "This close they pull on each other harder than the PEI plate holds them, "
              "so one of the two can jump out of its hole and stick to the other "
              "<b>mid-print</b>, ruining the part and possibly hitting the nozzle. "
              "Separation is measured <b>in a straight line</b>: what counts is the "
              "distance between the two centres, whichever way it runs.",
        "zh": "这么近时，两者之间的吸引力大于 PEI 板的吸附力，因此其中一个可能"
              "<b>在打印过程中</b>脱离孔位并吸到另一个上，毁掉零件，甚至撞到喷嘴。"
              "间距按<b>直线距离</b>计算：关键是两个中心之间的距离，方向不限。",
        "ja": "これほど近いと、PEI プレートが保持する力より磁石どうしの引力が強く、"
              "<b>印刷の途中で</b>片方が穴から飛び出してもう片方にくっつき、造形物が"
              "台無しになったりノズルに衝突したりする恐れがあります。距離は<b>直線</b>"
              "で見ます。向きに関係なく、2 つの中心間の距離が効きます。",
        "it": "Così vicini si attraggono più forte di quanto il piano PEI li trattenga, "
              "quindi uno dei due può uscire dal foro e attaccarsi all'altro "
              "<b>durante la stampa</b>, rovinando il pezzo e magari urtando l'ugello. "
              "La distanza si misura <b>in linea retta</b>: conta la distanza fra i due "
              "centri, in qualunque direzione.",
        "fr": "Aussi proches, ils s’attirent plus fort que le plateau PEI ne les "
              "retient : l’un des deux peut sortir de son trou et se coller à l’autre "
              "<b>en pleine impression</b>, ruinant la pièce et pouvant heurter la buse. "
              "L’écart se mesure <b>en ligne droite</b> : ce qui compte est la distance "
              "entre les deux centres, quelle que soit la direction.",
        "de": "So dicht ziehen sie sich stärker an, als die PEI-Platte sie hält: Einer "
              "der beiden kann <b>mitten im Druck</b> aus seinem Loch springen und am "
              "anderen haften — das Teil ist hin und die Düse in Gefahr. Der Abstand "
              "zählt <b>in Luftlinie</b>: Es geht um den Abstand der beiden Mittelpunkte, "
              "in welcher Richtung auch immer.",
        "pt": "Assim tão perto atraem-se com mais força do que a placa PEI os segura, "
              "por isso um dos dois pode sair do furo e colar-se ao outro <b>a meio da "
              "impressão</b>, estragando a peça e podendo bater no bico. A separação "
              "mede-se <b>em linha reta</b>: conta a distância entre os dois centros, "
              "seja em que direção for."},
    "spacing.pair_row": {
        "es": "Imán {a} ↔ imán {b}   ·   {d} mm en recta  (X {dx} · Y {dy})   "
              "(hacen falta {min} mm)",
        "en": "Magnet {a} ↔ magnet {b}   ·   {d} mm apart  (X {dx} · Y {dy})   "
              "({min} mm needed)",
        "zh": "磁铁 {a} ↔ 磁铁 {b}   ·   直线 {d} mm（X {dx} · Y {dy}）（需达到 {min} mm）",
        "ja": "磁石 {a} ↔ 磁石 {b}   ·   直線 {d} mm（X {dx} · Y {dy}）"
              "（{min} mm 必要）",
        "it": "Magnete {a} ↔ magnete {b}   ·   {d} mm in linea retta  (X {dx} · Y {dy})   "
              "(servono {min} mm)",
        "fr": "Aimant {a} ↔ aimant {b}   ·   {d} mm en ligne droite  (X {dx} · Y {dy})   "
              "({min} mm nécessaires)",
        "de": "Magnet {a} ↔ Magnet {b}   ·   {d} mm Luftlinie  (X {dx} · Y {dy})   "
              "({min} mm nötig)",
        "pt": "Ímã {a} ↔ ímã {b}   ·   {d} mm em linha reta  (X {dx} · Y {dy})   "
              "(faltam {min} mm)"},
    "spacing.sweep_body": {
        "es": "El módulo lleva <b>su propio imán</b> dentro, del mismo diámetro que el "
              "que suelta, y al retirarse pasa casi a ras de la capa: se lleva pegado "
              "cualquier imán ya colocado que le quede en el camino. Esto no se arregla "
              "separándolos sino <b>cambiando el orden</b>: en <i>Parámetros</i>, con "
              "<i>Avanzado</i> marcado, la casilla de reordenar los coloca de izquierda "
              "a derecha, que es el sentido en el que el módulo se aparta.",
        "en": "The module carries <b>its own magnet</b> inside, the same diameter as the "
              "one it drops, and its retreat runs just above the layer: it takes with it "
              "any already-placed magnet left in the way. Separating them does not fix "
              "this — <b>changing the order</b> does: in <i>Parameters</i>, with "
              "<i>Advanced</i> ticked, the reorder checkbox places them left to right, "
              "the way the module moves aside.",
        "zh": "模块内部装有<b>自己的磁铁</b>，直径与放置的磁铁相同；退避时几乎贴着当前层移动，"
              "会把挡在路上的已放置磁铁一并带走。这不能靠拉开距离解决，而要<b>改变顺序</b>："
              "在<i>参数</i>中勾选<i>高级</i>后，重排复选框会按模块退避的方向，从左到右放置。",
        "ja": "モジュールの内部には、置く磁石と<b>同じ直径の磁石</b>が入っています。退避は層の"
              "すぐ上を通るため、経路上にある設置済みの磁石を持ち去ってしまいます。これは間隔を"
              "空けても直りません。直るのは<b>順番を変える</b>ことです。<i>パラメータ</i>で"
              "<i>詳細</i>にチェックを入れると出てくる並べ替えのチェックボックスが、モジュール"
              "が退避する向き、つまり左から右に並べ直します。",
        "it": "Il modulo porta <b>il proprio magnete</b> dentro, dello stesso diametro di "
              "quello che posa, e nel ritirarsi passa quasi a filo dello strato: si porta "
              "via qualsiasi magnete già posato che trovi sul percorso. Non si risolve "
              "allontanandoli ma <b>cambiando l’ordine</b>: in <i>Parametri</i>, con "
              "<i>Avanzato</i> attivo, la casella di riordino li dispone da sinistra a "
              "destra, il verso in cui il modulo si sposta.",
        "fr": "Le module embarque <b>son propre aimant</b>, du même diamètre que celui "
              "qu’il dépose, et son retrait passe au ras de la couche : il emporte tout "
              "aimant déjà posé resté sur son chemin. Les éloigner n’y change rien ; ce "
              "qui règle le problème, c’est <b>l’ordre</b> : dans <i>Paramètres</i>, avec "
              "<i>Avancé</i> coché, la case de réordonnancement les pose de gauche à "
              "droite, le sens du retrait.",
        "de": "Das Modul trägt <b>einen eigenen Magneten</b> im Inneren, mit demselben "
              "Durchmesser wie der abgelegte, und zieht sich knapp über der Schicht "
              "zurück: Jeden bereits gesetzten Magneten im Weg nimmt es mit. Das lässt "
              "sich nicht durch mehr Abstand lösen, sondern durch die <b>Reihenfolge</b>: "
              "Unter <i>Parameter</i> setzt das Kontrollkästchen zum Neuordnen – bei "
              "aktiviertem <i>Erweitert</i> – sie von links nach rechts, die Richtung, in "
              "die das Modul ausweicht.",
        "pt": "O módulo leva <b>o seu próprio íman</b> dentro, do mesmo diâmetro do que "
              "larga, e ao recuar passa quase rente à camada: leva colado qualquer íman "
              "já colocado que lhe fique no caminho. Isto não se resolve afastando-os mas "
              "<b>mudando a ordem</b>: em <i>Parâmetros</i>, com <i>Avançado</i> marcado, "
              "a caixa de reordenar coloca-os da esquerda para a direita, o sentido em "
              "que o módulo se afasta."},
    "spacing.sweep_row": {
        "es": "Al colocar el imán {a}, el módulo se retira {r} mm por encima del "
              "imán {b}, que ya está puesto",
        "en": "Placing magnet {a}, the module retreats {r} mm right over magnet {b}, "
              "already in place",
        "zh": "放置磁铁 {a} 时，模块退避 {r} mm，正好经过已放置的磁铁 {b} 上方",
        "ja": "磁石 {a} を置いたあとの {r} mm の退避が、設置済みの磁石 {b} の真上を通ります",
        "it": "Posando il magnete {a}, il modulo si ritira di {r} mm passando sopra il "
              "magnete {b}, già posato",
        "fr": "En posant l’aimant {a}, le module recule de {r} mm juste au-dessus de "
              "l’aimant {b}, déjà posé",
        "de": "Beim Setzen von Magnet {a} zieht sich das Modul {r} mm zurück – direkt "
              "über den bereits gesetzten Magnet {b}",
        "pt": "Ao colocar o íman {a}, o módulo recua {r} mm por cima do íman {b}, que "
              "já está posto"},
    "spacing.see_details": {"es": "Ver detalles…", "en": "See details…", "zh": "查看详情…",
                            "ja": "詳細を見る…", "it": "Vedi dettagli…",
                            "fr": "Voir les détails…", "de": "Details ansehen…",
                            "pt": "Ver detalhes…"},
    "spacing.export_anyway": {
        "es": "Sé lo que puede pasar: exportar igualmente",
        "en": "I know what can happen: export anyway",
        "zh": "我了解风险：仍然导出",
        "ja": "リスクを理解した上で書き出す",
        "it": "So cosa può succedere: esporta comunque",
        "fr": "Je sais ce qui peut arriver : exporter quand même",
        "de": "Mir sind die Folgen klar: trotzdem exportieren",
        "pt": "Sei o que pode acontecer: exportar mesmo assim"},
    "spacing.info_title": {"es": "Distancia mínima entre imanes",
                           "en": "Minimum distance between magnets",
                           "zh": "磁铁之间的最小距离", "ja": "磁石どうしの最小距離",
                           "it": "Distanza minima tra magneti",
                           "fr": "Distance minimale entre aimants",
                           "de": "Mindestabstand zwischen Magneten",
                           "pt": "Distância mínima entre ímãs"},
    "spacing.model_intro": {
        "es": "A un imán recién colocado lo sujeta la atracción a la <b>placa PEI de "
              "acero</b>, y esa fuerza cae <b>exponencialmente</b> con la altura: en "
              "contacto son 3 N, a 1.45 mm ya solo 1.1 N y a 5 mm quedan 0.1 N. La "
              "atracción <b>entre dos imanes</b> parte de 12 N y cae mucho más despacio "
              "(como 1/d²). El mínimo es donde se igualan:<br>"
              "<code>F_imán(d) = F_PEI(h) = 3 · e^(−h/1.45)  →  "
              "d_min = 1.8 · √(4·e^(h/1.45) − 1) + ⌀</code>"
              "<br>Una cae exponencial y la otra como un cuadrado, así que <b>el mínimo "
              "crece exponencialmente</b>: se multiplica por e cada 2.9 mm que sube el "
              "imán. Esa distancia tiene que quedar libre <b>entre los cuerpos</b>, así "
              "que se le suma el <b>diámetro ⌀</b> del imán: a h = 5 mm la fórmula da "
              "20.1 mm y un ⌀5 pide <b>25.1</b> entre centros."
              "<br>La curva está anclada a una medida real: un <b>⌀5 × 3 a 5 mm</b> de la "
              "placa necesita unos 25 mm. El modelo de fuerzas es el de un disco "
              "<b>N52 de 6 × 5 mm</b>, el más fuerte que admite la app, así que con "
              "imanes menores queda del lado seguro.",
        "en": "A magnet that has just been placed is held by its attraction to the "
              "<b>steel PEI plate</b>, and that force decays <b>exponentially</b> with "
              "height: 3 N in contact, only 1.1 N at 1.45 mm and 0.1 N at 5 mm. The "
              "attraction <b>between two magnets</b> starts at 12 N and decays far more "
              "slowly (as 1/d²). The minimum is where they match:<br>"
              "<code>F_magnet(d) = F_PEI(h) = 3 · e^(−h/1.45)  →  "
              "d_min = 1.8 · √(4·e^(h/1.45) − 1) + ⌀</code>"
              "<br>One decays exponentially and the other as a square, so <b>the minimum "
              "grows exponentially</b>: it multiplies by e for every 2.9 mm the magnet "
              "rises. That distance has to be clear <b>between the bodies</b>, so the "
              "<b>diameter ⌀</b> of the magnet is added on top: at h = 5 mm the formula "
              "gives 20.1 mm and a ⌀5 asks for <b>25.1</b> between centres."
              "<br>The curve is anchored to a real measurement: a <b>⌀5 × 3 at 5 mm</b> "
              "above the plate needs about 25 mm. The force model is that of an "
              "<b>N52 disc, 6 × 5 mm</b>, the strongest the app allows, so smaller "
              "magnets stay on the safe side."},
    "spacing.live_numbers": {
        "es": "Esta pieza: pausa a Z {z} mm − imán de {mh} mm → <b>h = {h} mm</b> sobre "
              "la placa · la placa sujeta <b>{f} N</b> · mínimo <b>{d} mm</b> entre centros",
        "en": "This part: pause at Z {z} mm − {mh} mm magnet → <b>h = {h} mm</b> above "
              "the plate · the plate holds <b>{f} N</b> · minimum <b>{d} mm</b> between centres",
        "zh": "本零件：暂停于 Z {z} mm − {mh} mm 磁铁 → 离板 <b>h = {h} mm</b> · "
              "板面吸力 <b>{f} N</b> · 中心间最小 <b>{d} mm</b>",
        "ja": "この部品：一時停止 Z {z} mm − 磁石 {mh} mm → プレートから <b>h = {h} mm</b> · "
              "プレートの保持力 <b>{f} N</b> · 中心間の最小 <b>{d} mm</b>",
        "it": "Questo pezzo: pausa a Z {z} mm − magnete da {mh} mm → <b>h = {h} mm</b> "
              "sopra il piano · il piano trattiene <b>{f} N</b> · minimo <b>{d} mm</b> tra i centri",
        "fr": "Cette pièce : pause à Z {z} mm − aimant de {mh} mm → <b>h = {h} mm</b> "
              "au-dessus du plateau · le plateau retient <b>{f} N</b> · minimum <b>{d} mm</b> entre centres",
        "de": "Dieses Teil: Pause bei Z {z} mm − {mh}-mm-Magnet → <b>h = {h} mm</b> über "
              "der Platte · die Platte hält <b>{f} N</b> · Minimum <b>{d} mm</b> zwischen den Mittelpunkten",
        "pt": "Esta peça: pausa a Z {z} mm − ímã de {mh} mm → <b>h = {h} mm</b> acima da "
              "placa · a placa segura <b>{f} N</b> · mínimo <b>{d} mm</b> entre centros"},
    "spacing.table_h": {"es": "Altura h (mm)", "en": "Height h (mm)", "zh": "高度 h (mm)",
                        "ja": "高さ h (mm)", "it": "Altezza h (mm)", "fr": "Hauteur h (mm)",
                        "de": "Höhe h (mm)", "pt": "Altura h (mm)"},
    "spacing.table_d": {"es": "Mínimo (mm)", "en": "Minimum (mm)", "zh": "最小 (mm)",
                        "ja": "最小 (mm)", "it": "Minimo (mm)", "fr": "Minimum (mm)",
                        "de": "Minimum (mm)", "pt": "Mínimo (mm)"},
    "spacing.cap": {
        "es": "Al crecer exponencialmente, la fórmula se dispara: pasados unos "
              "<b>7 mm</b> de altura ya pide más de 50 mm, y a 10 mm pediría 120. Eso no "
              "cabe en una cama de 256 mm, así que el mínimo se corta en "
              "<b>{tope} mm</b>. Es un <b>techo de trabajo</b>, no una medida: por encima "
              "de él la respuesta ya no es separar más, sino que el agujero agarre el "
              "imán (los dos casos de abajo).",
        "en": "Growing exponentially, the formula runs away: past about <b>7 mm</b> of "
              "height it already asks for more than 50 mm, and at 10 mm it would ask for "
              "120. That does not fit on a 256 mm bed, so the minimum is capped at "
              "<b>{tope} mm</b>. It is a <b>working ceiling</b>, not a measurement: above "
              "it the answer is no longer to separate them further but to have the hole "
              "grip the magnet (the two cases below)."},
    "spacing.zero_friction": {
        "es": "Ojo: el modelo supone <b>cero fricción</b> entre el imán y su agujero, que "
              "es el caso pesimista. En una pieza real el agujero sujeta, y ahí entran "
              "los dos casos de abajo.",
        "en": "Note: the model assumes <b>zero friction</b> between the magnet and its "
              "hole, which is the pessimistic case. On a real part the hole grips, and "
              "that is what the two cases below are about.",
        "zh": "注意：该模型假设磁铁与孔之间<b>没有摩擦</b>，属于最悲观的情况。"
              "实际零件中孔会夹住磁铁，这正是下面两种情况所讨论的。",
        "ja": "注意：このモデルは磁石と穴のあいだの<b>摩擦ゼロ</b>を前提とした最悪ケース"
              "です。実際の部品では穴が磁石を保持します。それが以下の 2 つのケースです。",
        "it": "Attenzione: il modello presuppone <b>attrito zero</b> tra magnete e foro, "
              "cioè il caso pessimistico. In un pezzo reale il foro trattiene, ed è di "
              "questo che parlano i due casi qui sotto.",
        "fr": "Attention : le modèle suppose un <b>frottement nul</b> entre l’aimant et "
              "son trou, c’est le cas pessimiste. Sur une pièce réelle le trou retient, "
              "et c’est l’objet des deux cas ci-dessous.",
        "de": "Achtung: Das Modell nimmt <b>null Reibung</b> zwischen Magnet und Loch an — "
              "der pessimistische Fall. An einem echten Teil hält das Loch, und genau "
              "darum geht es in den beiden Fällen unten.",
        "pt": "Atenção: o modelo assume <b>atrito zero</b> entre o ímã e o seu furo, que é "
              "o caso pessimista. Numa peça real o furo segura, e é disso que tratam os "
              "dois casos abaixo."},
    "spacing.module_sweep": {
        "es": "Y en la cuenta no hay dos imanes, sino tres: el <b>módulo lleva el suyo "
              "dentro</b>, del mismo diámetro que el que suelta. Tras dejar cada uno se "
              "aparta <b>{r} mm hacia +X</b> —lo mismo que se pide entre dos imanes, y por "
              "el mismo motivo— arrastrando su círculo casi a ras de la capa. En ese "
              "pasillo no puede quedar ningún imán <b>ya colocado</b>, así que aquí el "
              "orden de colocación importa: los que todavía no están puestos no corren "
              "peligro.",
        "en": "And the sum is not over two magnets but three: the <b>module carries its "
              "own</b>, the same diameter as the one it drops. After each one it moves "
              "<b>{r} mm along +X</b> — the same distance asked between two magnets, for "
              "the same reason — dragging its circle just above the layer. No <b>already "
              "placed</b> magnet may be left in that corridor, so the placement order "
              "matters here: the ones not yet placed are in no danger.",
        "zh": "参与计算的不是两块磁铁，而是三块：<b>模块内部也有一块</b>，直径与放置的相同。"
              "每放下一块后，模块会<b>沿 +X 退避 {r} mm</b>（与两块磁铁之间要求的距离相同，"
              "原因也一样），并几乎贴着当前层带走它的圆形范围。该通道内不能留有<b>已放置</b>的"
              "磁铁，因此放置顺序在这里很重要：尚未放置的磁铁没有风险。",
        "ja": "計算に関わる磁石は 2 個ではなく 3 個です。<b>モジュールにも同じ直径の磁石</b>が"
              "入っています。1 個置くごとに <b>+X 方向へ {r} mm</b> 退避し（2 個の磁石に求める"
              "距離と同じで、理由も同じです）、その円を層のすぐ上で引きずります。この通路に"
              "<b>設置済み</b>の磁石があってはいけないので、ここでは配置順が効きます。まだ置いて"
              "いない磁石は危険にさらされません。",
        "it": "E in gioco non ci sono due magneti ma tre: il <b>modulo porta il suo</b>, "
              "dello stesso diametro di quello che posa. Dopo ognuno si sposta di "
              "<b>{r} mm verso +X</b> — la stessa distanza che si chiede fra due magneti, "
              "e per lo stesso motivo — trascinando il suo cerchio quasi a filo dello "
              "strato. In quel corridoio non può restare nessun magnete <b>già posato</b>, "
              "quindi qui l’ordine di posa conta: quelli non ancora posati non rischiano.",
        "fr": "Et le calcul ne porte pas sur deux aimants mais trois : le <b>module "
              "embarque le sien</b>, du même diamètre que celui qu’il dépose. Après chacun "
              "il s’écarte de <b>{r} mm vers +X</b> — la distance demandée entre deux "
              "aimants, pour la même raison — en traînant son cercle au ras de la couche. "
              "Aucun aimant <b>déjà posé</b> ne doit rester dans ce couloir : l’ordre de "
              "pose compte donc ici, ceux qui ne sont pas encore posés ne risquent rien.",
        "de": "Und es sind nicht zwei Magnete im Spiel, sondern drei: Das <b>Modul führt "
              "seinen eigenen</b> mit, im selben Durchmesser wie der abgelegte. Nach jedem "
              "weicht es <b>{r} mm in +X</b> aus — derselbe Abstand, der zwischen zwei "
              "Magneten verlangt wird, und aus demselben Grund — und zieht dabei seinen "
              "Kreis knapp über der Schicht mit. In diesem Korridor darf kein "
              "<b>bereits gesetzter</b> Magnet liegen; die Setzreihenfolge zählt hier "
              "also: Die noch nicht gesetzten sind nicht in Gefahr.",
        "pt": "E na conta não há dois ímanes, mas três: o <b>módulo leva o seu dentro</b>, "
              "do mesmo diâmetro do que larga. Depois de cada um afasta-se <b>{r} mm para "
              "+X</b> — a mesma distância que se pede entre dois ímanes, e pelo mesmo "
              "motivo — arrastando o seu círculo quase rente à camada. Nesse corredor não "
              "pode ficar nenhum íman <b>já colocado</b>, por isso a ordem de colocação "
              "conta aqui: os que ainda não estão postos não correm perigo."},
    "spacing.module_sweep_unknown": {
        "es": "Y en la cuenta no hay dos imanes, sino tres: el <b>módulo lleva el suyo "
              "dentro</b>, del mismo diámetro que el que suelta. Tras dejar cada uno se "
              "aparta hacia +X esa misma distancia mínima, arrastrando su círculo casi a "
              "ras de la capa. En ese pasillo no puede quedar ningún imán <b>ya "
              "colocado</b>, así que el orden de colocación importa. Abre un archivo para "
              "ver cuánto se aparta con esta pieza.",
        "en": "And the sum is not over two magnets but three: the <b>module carries its "
              "own</b>, the same diameter as the one it drops. After each one it moves "
              "along +X by that same minimum distance, dragging its circle just above the "
              "layer. No <b>already placed</b> magnet may be left in that corridor, so the "
              "placement order matters. Open a file to see how far it moves on this part.",
        "zh": "参与计算的不是两块磁铁，而是三块：<b>模块内部也有一块</b>，直径与放置的相同。"
              "每放下一块后，模块会沿 +X 退避同样的最小距离，并几乎贴着当前层带走它的圆形范围。"
              "该通道内不能留有<b>已放置</b>的磁铁，因此放置顺序很重要。打开文件即可看到本件的"
              "退避距离。",
        "ja": "計算に関わる磁石は 2 個ではなく 3 個です。<b>モジュールにも同じ直径の磁石</b>が"
              "入っています。1 個置くごとに、同じ最小距離だけ +X 方向へ退避し、その円を層の"
              "すぐ上で引きずります。この通路に<b>設置済み</b>の磁石があってはいけないので、配置"
              "順が効きます。この部品での退避量はファイルを開くと分かります。",
        "it": "E in gioco non ci sono due magneti ma tre: il <b>modulo porta il suo</b>, "
              "dello stesso diametro di quello che posa. Dopo ognuno si sposta verso +X "
              "della stessa distanza minima, trascinando il suo cerchio quasi a filo "
              "dello strato. In quel corridoio non può restare nessun magnete <b>già "
              "posato</b>, quindi l’ordine di posa conta. Apri un file per vedere di "
              "quanto si sposta con questo pezzo.",
        "fr": "Et le calcul ne porte pas sur deux aimants mais trois : le <b>module "
              "embarque le sien</b>, du même diamètre que celui qu’il dépose. Après chacun "
              "il s’écarte vers +X de cette même distance minimale, en traînant son cercle "
              "au ras de la couche. Aucun aimant <b>déjà posé</b> ne doit rester dans ce "
              "couloir : l’ordre de pose compte donc. Ouvrez un fichier pour voir de "
              "combien il s’écarte sur cette pièce.",
        "de": "Und es sind nicht zwei Magnete im Spiel, sondern drei: Das <b>Modul führt "
              "seinen eigenen</b> mit, im selben Durchmesser wie der abgelegte. Nach jedem "
              "weicht es um genau diesen Mindestabstand in +X aus und zieht seinen Kreis "
              "knapp über der Schicht mit. In diesem Korridor darf kein <b>bereits "
              "gesetzter</b> Magnet liegen; die Setzreihenfolge zählt also. Öffne eine "
              "Datei, um zu sehen, wie weit es bei diesem Teil ausweicht.",
        "pt": "E na conta não há dois ímanes, mas três: o <b>módulo leva o seu dentro</b>, "
              "do mesmo diâmetro do que larga. Depois de cada um afasta-se para +X essa "
              "mesma distância mínima, arrastando o seu círculo quase rente à camada. "
              "Nesse corredor não pode ficar nenhum íman <b>já colocado</b>, por isso a "
              "ordem de colocação conta. Abre um ficheiro para ver quanto se afasta nesta "
              "peça."},
    "spacing.radial": {
        "es": "La separación se mide <b>en línea recta</b>: lo que cuenta es la distancia "
              "entre los dos centros, no cuánto se apartan en X o en Y. Por eso en el "
              "visor cada imán lleva un <b>círculo</b> de {tope} mm de diámetro y no un "
              "cuadrado: si dos círculos se solapan, ese par hay que separarlo. Es así "
              "porque la atracción entre dos imanes no sabe de ejes, solo de lo lejos "
              "que estén.",
        "en": "Separation is measured <b>in a straight line</b>: what counts is the "
              "distance between the two centres, not how far apart they are in X or in Y. "
              "That is why in the viewer each magnet carries a <b>circle</b> {tope} mm "
              "across and not a square: if two circles overlap, that pair has to be "
              "separated. It works this way because the pull between two magnets knows "
              "nothing about axes, only about distance.",
        "zh": "间距按<b>直线距离</b>计算：关键是两个中心之间的距离，而不是在 X 或 Y 上"
              "分开多少。因此视图中每块磁铁配的是直径 {tope} mm 的<b>圆</b>而不是方框："
              "两个圆重叠，就必须把这一对分开。这是因为磁铁之间的吸引力与坐标轴无关，"
              "只与距离有关。",
        "ja": "距離は<b>直線</b>で測ります。効くのは 2 つの中心間の距離であって、X や Y で"
              "どれだけ離れているかではありません。だからビューでは各磁石に正方形ではなく"
              "直径 {tope} mm の<b>円</b>が付きます。2 つの円が重なったら、その組は離す"
              "必要があります。磁石どうしの引力は軸ではなく距離だけで決まるためです。",
        "it": "La distanza si misura <b>in linea retta</b>: conta la distanza fra i due "
              "centri, non quanto si allontanano in X o in Y. Per questo nel visore ogni "
              "magnete ha un <b>cerchio</b> di {tope} mm di diametro e non un quadrato: "
              "se due cerchi si sovrappongono, quella coppia va separata. Funziona così "
              "perché l’attrazione fra due magneti non sa nulla degli assi, solo della "
              "distanza.",
        "fr": "L’écart se mesure <b>en ligne droite</b> : ce qui compte est la distance "
              "entre les deux centres, pas l’écart en X ou en Y. C’est pourquoi dans la "
              "vue chaque aimant porte un <b>cercle</b> de {tope} mm de diamètre et non un "
              "carré : si deux cercles se chevauchent, il faut écarter cette paire. C’est "
              "ainsi parce que l’attraction entre deux aimants ignore les axes, elle ne "
              "connaît que la distance.",
        "de": "Der Abstand zählt <b>in Luftlinie</b>: Es geht um den Abstand der beiden "
              "Mittelpunkte, nicht darum, wie weit sie in X oder Y auseinander liegen. "
              "Deshalb trägt in der Ansicht jeder Magnet einen <b>Kreis</b> von {tope} mm "
              "Durchmesser und kein Quadrat: Überlappen sich zwei Kreise, muss das Paar "
              "getrennt werden. Das liegt daran, dass die Anziehung zwischen zwei Magneten "
              "nichts von Achsen weiß, nur von Entfernung.",
        "pt": "A separação mede-se <b>em linha reta</b>: o que conta é a distância entre "
              "os dois centros, não o quanto se afastam em X ou em Y. Por isso no visor "
              "cada ímã leva um <b>círculo</b> de {tope} mm de diâmetro e não um quadrado: "
              "se dois círculos se sobrepõem, esse par tem de ser separado. É assim porque "
              "a atração entre dois ímãs não sabe de eixos, só de distância."},
    "spacing.case_friction_title": {
        "es": "1. Si el agujero aprieta el imán (fricción)",
        "en": "1. If the hole grips the magnet (friction)",
        "zh": "1. 如果孔夹紧磁铁（摩擦）",
        "ja": "1. 穴が磁石を締めつける場合（摩擦）",
        "it": "1. Se il foro stringe il magnete (attrito)",
        "fr": "1. Si le trou serre l’aimant (frottement)",
        "de": "1. Wenn das Loch den Magneten klemmt (Reibung)",
        "pt": "1. Se o furo aperta o ímã (atrito)"},
    "spacing.case_friction_body": {
        "es": "Con el agujero a medida, quien sujeta el imán ya no es la placa sino el "
              "<b>rozamiento contra la pared</b>, y eso no depende de la altura. El "
              "mínimo práctico baja entonces a unos <b>{d} mm</b>: donde el modelo sin "
              "fricción pedía {ejemplo} mm (a 10 mm de altura), con un agujero que "
              "agarra bastan {d}. Compruébalo en una pieza de prueba antes de fiarte.",
        "en": "With a snug hole, what holds the magnet is no longer the plate but "
              "<b>friction against the wall</b>, and that does not depend on height. The "
              "practical minimum then drops to about <b>{d} mm</b>: where the "
              "frictionless model asked for {ejemplo} mm (at 10 mm height), a hole that "
              "grips makes {d} enough. Check it on a test part before relying on it.",
        "zh": "孔配合紧密时，固定磁铁的不再是板面，而是<b>与孔壁的摩擦</b>，这与高度无关。"
              "此时实际最小值降到约 <b>{d} mm</b>：无摩擦模型在 10 mm 高度要求 {ejemplo} mm，"
              "而夹紧的孔只需 {d} mm。请先用试件验证再依赖它。",
        "ja": "穴がぴったりなら、磁石を支えるのはプレートではなく<b>壁との摩擦</b>で、"
              "高さには依存しません。実用上の最小値は約 <b>{d} mm</b> まで下がります："
              "摩擦なしのモデルが（高さ 10 mm で）{ejemplo} mm を要求するところ、"
              "しっかり掴む穴なら {d} mm で足ります。頼る前にテスト部品で確認してください。",
        "it": "Con il foro su misura, a tenere il magnete non è più il piano ma "
              "<b>l'attrito contro la parete</b>, e questo non dipende dall'altezza. Il "
              "minimo pratico scende allora a circa <b>{d} mm</b>: dove il modello senza "
              "attrito chiedeva {ejemplo} mm (a 10 mm d'altezza), con un foro che stringe "
              "bastano {d}. Verificalo su un pezzo di prova prima di fidarti.",
        "fr": "Avec un trou ajusté, ce qui retient l’aimant n’est plus le plateau mais le "
              "<b>frottement contre la paroi</b>, et cela ne dépend pas de la hauteur. Le "
              "minimum pratique tombe alors à environ <b>{d} mm</b> : là où le modèle sans "
              "frottement exigeait {ejemplo} mm (à 10 mm de hauteur), un trou qui serre "
              "suffit à {d}. Vérifiez-le sur une pièce test avant de vous y fier.",
        "de": "Bei passgenauem Loch hält den Magneten nicht mehr die Platte, sondern die "
              "<b>Reibung an der Wand</b> — und die hängt nicht von der Höhe ab. Das "
              "praktische Minimum sinkt dann auf etwa <b>{d} mm</b>: Wo das reibungsfreie "
              "Modell {ejemplo} mm verlangte (bei 10 mm Höhe), genügen mit klemmendem Loch "
              "{d}. Prüfen Sie es an einem Testteil, bevor Sie sich darauf verlassen.",
        "pt": "Com o furo à medida, quem segura o ímã já não é a placa mas o <b>atrito "
              "contra a parede</b>, e isso não depende da altura. O mínimo prático desce "
              "então para cerca de <b>{d} mm</b>: onde o modelo sem atrito pedia "
              "{ejemplo} mm (a 10 mm de altura), com um furo que agarra bastam {d}. "
              "Confirme numa peça de teste antes de confiar."},
    "spacing.case_deep_title": {
        "es": "2. Si el agujero es {ratio}× más hondo que el imán",
        "en": "2. If the hole is {ratio}× deeper than the magnet",
        "zh": "2. 如果孔深是磁铁高度的 {ratio} 倍",
        "ja": "2. 穴が磁石の {ratio} 倍の深さの場合",
        "it": "2. Se il foro è {ratio}× più profondo del magnete",
        "fr": "2. Si le trou est {ratio}× plus profond que l’aimant",
        "de": "2. Wenn das Loch {ratio}× tiefer ist als der Magnet",
        "pt": "2. Se o furo é {ratio}× mais fundo que o ímã"},
    "spacing.case_deep_body": {
        "es": "Con el imán en el fondo de un agujero de {prof} mm, el vecino no tira en "
              "horizontal sino <b>en diagonal y hacia arriba</b>: antes de salir, el imán "
              "se inclina. Y al inclinarse deja de ocupar sus {diam} mm de diámetro para "
              "ocupar su diagonal, <b>√({diam}² + {alto}²) = {diag} mm</b>, que no cabe en "
              "el agujero: le faltan {falta} mm de holgura, así que <b>se atasca contra la "
              "pared</b> en vez de escaparse. Es el mismo motivo por el que una caja alta "
              "no pasa ladeada por su propio hueco.",
        "en": "With the magnet at the bottom of a {prof} mm hole, the neighbour does not "
              "pull sideways but <b>diagonally upwards</b>: before it can leave, the "
              "magnet tilts. And once tilted it no longer takes up its {diam} mm of "
              "diameter but its diagonal, <b>√({diam}² + {alto}²) = {diag} mm</b>, which "
              "does not fit the hole: it is {falta} mm short of clearance, so it "
              "<b>jams against the wall</b> instead of escaping. Same reason a tall box "
              "will not go through its own opening at an angle.",
        "zh": "磁铁位于 {prof} mm 深孔底部时，邻近磁铁的拉力不是水平的，而是<b>斜向上</b>的："
              "磁铁在脱出之前会先倾斜。一旦倾斜，它占据的就不再是 {diam} mm 的直径，"
              "而是其对角线 <b>√({diam}² + {alto}²) = {diag} mm</b>，孔里放不下："
              "还差 {falta} mm 的余隙，因此它会<b>卡在孔壁上</b>而不是逃出去。"
              "就像高箱子斜着过不了自己的开口一样。",
        "ja": "深さ {prof} mm の穴の底に磁石があると、隣の磁石は水平ではなく"
              "<b>斜め上向き</b>に引きます。抜け出す前に磁石が傾くのです。傾くと直径の "
              "{diam} mm ではなく対角線 <b>√({diam}² + {alto}²) = {diag} mm</b> を占めるため"
              "穴に収まりません（余裕が {falta} mm 足りない）。結果、逃げ出す代わりに"
              "<b>壁に引っかかります</b>。背の高い箱が斜めでは自分の開口を通れないのと同じです。",
        "it": "Con il magnete sul fondo di un foro da {prof} mm, il vicino non tira in "
              "orizzontale ma <b>in diagonale verso l'alto</b>: prima di uscire, il "
              "magnete si inclina. E inclinato non occupa più i suoi {diam} mm di "
              "diametro ma la sua diagonale, <b>√({diam}² + {alto}²) = {diag} mm</b>, che "
              "nel foro non ci sta: gli mancano {falta} mm di gioco, quindi <b>si "
              "incastra contro la parete</b> invece di scappare. Lo stesso motivo per cui "
              "una scatola alta non passa di sbieco dalla sua apertura.",
        "fr": "Avec l’aimant au fond d’un trou de {prof} mm, le voisin ne tire pas à "
              "l’horizontale mais <b>en diagonale vers le haut</b> : avant de sortir, "
              "l’aimant s’incline. Et incliné, il n’occupe plus ses {diam} mm de diamètre "
              "mais sa diagonale, <b>√({diam}² + {alto}²) = {diag} mm</b>, qui ne tient "
              "pas dans le trou : il lui manque {falta} mm de jeu, donc il <b>se coince "
              "contre la paroi</b> au lieu de s’échapper. La même raison qui empêche une "
              "boîte haute de passer de biais par sa propre ouverture.",
        "de": "Sitzt der Magnet am Grund eines {prof} mm tiefen Lochs, zieht der Nachbar "
              "nicht seitlich, sondern <b>diagonal nach oben</b>: Bevor er heraus kann, "
              "kippt der Magnet. Gekippt braucht er nicht mehr seine {diam} mm Durchmesser, "
              "sondern seine Diagonale, <b>√({diam}² + {alto}²) = {diag} mm</b>, und die "
              "passt nicht ins Loch: {falta} mm Spiel fehlen, also <b>verklemmt er sich an "
              "der Wand</b>, statt zu entwischen. Genau wie eine hohe Kiste schräg nicht "
              "durch ihre eigene Öffnung geht.",
        "pt": "Com o ímã no fundo de um furo de {prof} mm, o vizinho não puxa na "
              "horizontal mas <b>na diagonal e para cima</b>: antes de sair, o ímã "
              "inclina-se. E inclinado deixa de ocupar os seus {diam} mm de diâmetro para "
              "ocupar a sua diagonal, <b>√({diam}² + {alto}²) = {diag} mm</b>, que não "
              "cabe no furo: faltam-lhe {falta} mm de folga, por isso <b>encrava contra a "
              "parede</b> em vez de escapar. É a mesma razão por que uma caixa alta não "
              "passa de lado pela sua própria abertura."},
    "common.ok": {"es": "Aceptar", "en": "OK", "zh": "确定", "ja": "OK",
                  "it": "OK", "fr": "OK", "de": "OK", "pt": "OK"},
    "common.cancel": {"es": "Cancelar", "en": "Cancel", "zh": "取消", "ja": "キャンセル",
                      "it": "Annulla", "fr": "Annuler", "de": "Abbrechen", "pt": "Cancelar"},
    "common.close": {"es": "Cerrar", "en": "Close", "zh": "关闭", "ja": "閉じる",
                     "it": "Chiudi", "fr": "Fermer", "de": "Schließen", "pt": "Fechar"},
}
