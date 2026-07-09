import re, shutil

html_path = r'templates/index.html'
backup_path = r'templates/index.html.i18n_bak'

with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

shutil.copy2(html_path, backup_path)
print(f"Backup: {backup_path}")

ok, fail = [], []

def rp(old, new, label=None, use_re=False, count=1):
    global html
    tag = label or (old[:60] if not use_re else old[:40])
    if use_re:
        result, n = re.subn(old, new, html)
        if n > 0:
            html = result; ok.append(f"RE  {tag} ({n}x)")
        else:
            fail.append(f"RE  {tag}")
    else:
        if old in html:
            html = html.replace(old, new, count); ok.append(f"STR {tag}")
        else:
            fail.append(f"STR {tag}")

# --- 1. LANGUAGE SELECTOR ---
LANG_SEL = """
    <!-- Language selector -->
    <div class="nav-item dropdown ms-3 me-2">
      <a class="nav-link dropdown-toggle py-1 px-2" href="#"
         id="langDropdown" data-bs-toggle="dropdown" aria-expanded="false">
        <span id="lang-flag">🇪🇸</span>
        <span id="lang-name" class="ms-1">Español</span>
      </a>
      <ul class="dropdown-menu dropdown-menu-end">
        <li><a class="dropdown-item lang-item" href="#" data-lang="es">🇪🇸 Español</a></li>
        <li><a class="dropdown-item lang-item" href="#" data-lang="en">🇬🇧 English</a></li>
      </ul>
    </div>
"""
rp('    <!-- Status text -->', LANG_SEL + '    <!-- Status text -->', 'lang selector')

# --- 2. NAVBAR BRAND ---
rp('<span class="navbar-brand fw-bold">',
   '<span class="navbar-brand fw-bold" data-i18n="nav.brand">', 'brand')

# --- 3. ARCHIVO DROPDOWN ---
rp('<a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">\n          <i class="bi bi-folder2-open me-1"></i>Archivo',
   '<a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown" data-i18n="nav.file">\n          <i class="bi bi-folder2-open me-1"></i>Archivo', 'archivo dropdown')

# --- 4. MENU ITEMS ---
rp('<a class="dropdown-item" href="#" id="btn-new">',
   '<a class="dropdown-item" href="#" id="btn-new" data-i18n="nav.new">', 'btn-new')
rp('<a class="dropdown-item" href="#" id="btn-load">',
   '<a class="dropdown-item" href="#" id="btn-load" data-i18n="nav.load">', 'btn-load')
rp('<a class="dropdown-item" href="#" id="btn-saveas">',
   '<a class="dropdown-item" href="#" id="btn-saveas" data-i18n="nav.saveas">', 'btn-saveas')
rp('<a class="dropdown-item" href="#" id="btn-preview">',
   '<a class="dropdown-item" href="#" id="btn-preview" data-i18n="nav.preview">', 'btn-preview')

# --- 5. SECCIONES DROPDOWN ---
rp('<a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">\n          <i class="bi bi-layout-text-sidebar-reverse me-1"></i>Secciones',
   '<a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown" data-i18n="nav.sections">\n          <i class="bi bi-layout-text-sidebar-reverse me-1"></i>Secciones', 'secciones dropdown')

# --- 6. SECTION LINKS ---
rp('data-section="sec-general">\n              <i class="bi bi-gear me-2"></i>Configuración General',
   'data-section="sec-general" data-i18n="nav.sec_general">\n              <i class="bi bi-gear me-2"></i>Configuración General', 'sec-general link')
rp('data-section="sec-geometry">\n              <i class="bi bi-grid-3x3 me-2"></i>Definición Geométrica y Espacial',
   'data-section="sec-geometry" data-i18n="nav.sec_geometry">\n              <i class="bi bi-grid-3x3 me-2"></i>Definición Geométrica y Espacial', 'sec-geometry link')
rp('data-section="sec-materials">\n              <i class="bi bi-layers me-2"></i>Materiales y Flujo',
   'data-section="sec-materials" data-i18n="nav.sec_materials">\n              <i class="bi bi-layers me-2"></i>Materiales y Flujo', 'sec-materials link')
rp('data-section="sec-temporal">\n              <i class="bi bi-clock-history me-2"></i>Historial Temporal',
   'data-section="sec-temporal" data-i18n="nav.sec_temporal">\n              <i class="bi bi-clock-history me-2"></i>Historial Temporal', 'sec-temporal link')
rp('data-section="sec-uncertainties"\n               title="Requiere IUNC = 1 (Block #1)">',
   'data-section="sec-uncertainties"\n               title="Requiere IUNC = 1 (Block #1)" data-i18n="nav.sec_uncertainties" data-i18n-title="nav.sec_unc_tip">', 'sec-unc link')

# --- 7. SECTION TABS ---
rp('id="tab-general-btn"\n              data-bs-toggle="tab" data-bs-target="#sec-general"\n              type="button" role="tab">',
   'id="tab-general-btn"\n              data-bs-toggle="tab" data-bs-target="#sec-general"\n              type="button" role="tab" data-i18n="tabs.general">', 'tab-general')
rp('id="tab-geometry-btn"\n              data-bs-toggle="tab" data-bs-target="#sec-geometry"\n              type="button" role="tab">',
   'id="tab-geometry-btn"\n              data-bs-toggle="tab" data-bs-target="#sec-geometry"\n              type="button" role="tab" data-i18n="tabs.geometry">', 'tab-geometry')
rp('id="tab-materials-btn"\n              data-bs-toggle="tab" data-bs-target="#sec-materials"\n              type="button" role="tab">',
   'id="tab-materials-btn"\n              data-bs-toggle="tab" data-bs-target="#sec-materials"\n              type="button" role="tab" data-i18n="tabs.materials">', 'tab-materials')
rp('id="tab-temporal-btn"\n              data-bs-toggle="tab" data-bs-target="#sec-temporal"\n              type="button" role="tab">',
   'id="tab-temporal-btn"\n              data-bs-toggle="tab" data-bs-target="#sec-temporal"\n              type="button" role="tab" data-i18n="tabs.temporal">', 'tab-temporal')
rp('id="tab-uncertainties-btn"\n              data-bs-toggle="tab" data-bs-target="#sec-uncertainties"\n              type="button" role="tab"\n              title="Requiere IUNC = 1 (Block #1)">',
   'id="tab-uncertainties-btn"\n              data-bs-toggle="tab" data-bs-target="#sec-uncertainties"\n              type="button" role="tab"\n              title="Requiere IUNC = 1 (Block #1)" data-i18n="tabs.uncertainties" data-i18n-title="tabs.unc_tip">', 'tab-uncertainties')

# --- 8. BLOCK PILL SUBTITLES ---
pill_subs = [
    ('Parámetros generales', 'pill.b1_sub'),
    ('Reinicio', 'pill.b4_sub'),
    ('Error y normalización', 'pill.b9_sub'),
    ('Productos de fisión', 'pill.b10_sub'),
    ('Malla y salida', 'pill.b2_sub'),
    ('Flujo neutrónico', 'pill.b3_sub'),
    ('Composición inicial', 'pill.b5_sub'),
    ('Alimentación continua', 'pill.b6_sub'),
    ('Historial temporal', 'pill.b78_sub'),
    ('Control de ejecución', 'pill.b11_sub'),
    ('Control de salida', 'pill.b13_sub'),
]
for text, key in pill_subs:
    rp(f'<div class="small text-muted lh-1">{text}</div>',
       f'<div class="small text-muted lh-1" data-i18n="{key}">{text}</div>', f'pill {key}')

# --- 9. COMMENT AREA ---
rp(r'(<i class="bi bi-chat-left-quote me-1"></i>)(Comentario para )(Block[^<\n]+)',
   r'\1<span data-i18n="cmt.prefix">\2</span>\3',
   'cmt prefix wrap', use_re=True)

# --- 10. COMMENT NOTE SPANS ---
rp('<span class="fw-normal text-muted">(se escribe como <code>&lt;</code> texto en el fichero)</span>',
   '<span class="fw-normal text-muted" data-i18n-html="cmt.note">(se escribe como <code>&lt;</code> texto en el fichero)</span>',
   'cmt note', count=0)

# --- 11. COMMENT PLACEHOLDERS ---
rp('placeholder="Comentario opcional…"',
   'placeholder="Comentario opcional…" data-i18n-ph="cmt.placeholder"',
   'cmt placeholder', count=0)

# --- 12. HELP BUTTONS ---
rp(r'(data-bs-toggle="collapse" data-bs-target="#help-b[^"]+")>',
   r'\1 data-i18n="help.btn">',
   'help buttons', use_re=True)

# --- 13. CARD HEADERS ---
card_headers = [
    ('Card #1 &mdash; Título del experimento', 'b1.card1_h'),
    ('Card #2 &mdash; Tipo de ejecución', 'b1.card2_h'),
    ('Card #3 &mdash; Librería, geometría y salida (21 parámetros)', 'b1.card3_h'),
    ('Card #1 &mdash; Opción de reinicio (IREST)', 'b4.card1_h'),
    ('Card #1 &mdash; Error de truncamiento y normalización de flujo', 'b9.card1_h'),
    ('Card #1 &mdash; Inventario de productos de fisión', 'b10.card1_h'),
    ('Card #1 &mdash; XRR &mdash; Límites de intervalos / Volúmenes de zona', 'b2.card1_h'),
    ('Card #2 &mdash; YZT &mdash; Límites de 2ª dimensión', 'b2.card2_h'),
    ('Card #3 &mdash; MA &mdash; Identificación de zona por intervalo espacial', 'b2.card3_h'),
    ('Card #4 &mdash; NUCZO &mdash; Número de especies iniciales por zona', 'b2.card4_h'),
    ('Card #5 &mdash; ISOZO &mdash; Número de especies de alimentación por zona', 'b2.card5_h'),
    ('Card #6 &mdash; EGRP &mdash; Límites de grupos de energía gamma (MeV)', 'b2.card6_h'),
    ('Card #7 &mdash; CUTOFF &mdash; Umbrales de truncamiento para tablas de salida', 'b2.card7_h'),
    ('Card #8 &mdash; NTO &mdash; Selección de tablas de salida (18 indicadores)', 'b2.card8_h'),
    ('Card #1 &mdash; FLUX &mdash; Flujos escalares multigrupo de neutrones y gammas', 'b3.card1_h'),
    ('Generador de Historial Temporal', 'b78.card_gen_h'),
    ('Vista previa &mdash; Blocks #7/#8', 'b78.card_prev_h'),
    ('Card #1 &mdash; Tipo de cálculo y funciones de respuesta', 'b11.card1_h'),
    ('Card #2 &mdash; Tasas de dosis a calcular', 'b11.card2_h'),
    ('Card #6 &mdash; Estructura temporal (ciclos y conjuntos)', 'b11.card6_h'),
    ('Card #7 &mdash; FVAR &mdash; Factores de escala de flujo', 'b11.card7_h'),
    ('Card #8 &mdash; NMULT &mdash; Escritura periódica de ciclos', 'b11.card8_h'),
    ('Card #1 &mdash; Control de ciclos y series finales', 'b13.card1_h'),
    ('Card #2 &mdash; ICYO &mdash; Ciclos seleccionados', 'b13.card2_h'),
    ('Card #3 &mdash; ITSO &mdash; Selección de conjuntos para salida', 'b13.card3_h'),
    ('Block #14 &mdash; Cálculo de incertidumbres (Monte Carlo)', 'b14.card_h'),
]
for text, key in card_headers:
    rp(text, f'<span data-i18n="{key}">{text}</span>', f'card header {key}')

# --- 14. GROUP HEADINGS ---
group_headings = [
    ('Tamaños de librería', 'b1.grp_lib'),
    ('Tablas de salida', 'b1.grp_tables'),
    ('Composición inicial y alimentación', 'b1.grp_comp'),
    ('Grupos de energía', 'b1.grp_energy'),
    ('Geometría', 'b1.grp_geom'),
    ('Flujo y opciones de salida adicionales', 'b1.grp_flux'),
    ('Fase de irradiación', 'b78.grp_irr'),
    ('Fase de enfriamiento', 'b78.grp_cool'),
    ('Funciones de respuesta adicionales', 'b11.grp_response'),
]
for text, key in group_headings:
    rp(f'</i>{text}\n                  </h6>',
       f'</i><span data-i18n="{key}">{text}</span>\n                  </h6>', f'group {key}')
    rp(f'</i>{text}\n                </h6>',
       f'</i><span data-i18n="{key}">{text}</span>\n                </h6>', f'group2 {key}')

# --- 15. B14 group headings ---
b14_h6 = [
    ('Card #1 &mdash; Parámetros generales', 'b14.card1_h'),
    ('Card #3 &mdash; ITSU &mdash; Tiempos de interés por conjunto', 'b14.card3_h'),
    ('Card #4 &mdash; ITIMEU &mdash; Índices de pasos temporales', 'b14.card4_h'),
    ('Card #5 &mdash; INUCU &mdash; Identificadores de nucléidos', 'b14.card5_h'),
]
for text, key in b14_h6:
    rp(f'<h6 class="group-heading">{text}</h6>',
       f'<h6 class="group-heading" data-i18n="{key}">{text}</h6>', f'b14 h6 {key}')
    rp(f'<h6 class="group-heading mt-3">{text}</h6>',
       f'<h6 class="group-heading mt-3" data-i18n="{key}">{text}</h6>', f'b14 h6 mt3 {key}')

# --- 16. FORM HINTS (form-text) ---
form_hints = [
    ('Nucleidos en la librería de desintegración', 'b1.itmax_hint'),
    ('Elementos no nulos en la Matriz de Transición', 'b1.izmax_hint'),
    ('Guías de concentración radiactiva', 'b1.mpctab_hint'),
    ('Elementos de la Matriz de Transición', 'b1.ir_hint'),
    ('Selección de tablas de salida', 'b1.jto_hint'),
    ('Filtro de isótopos en tablas', 'b1.ntable_hint'),
    ('Índice de paso temporal para selección', 'b1.mstar_hint'),
    ('Tipo de concentración inicial (Block #5)', 'b1.inpt_hint'),
    ('Tipo de alimentación continua', 'b1.infd_hint'),
    ('Grupos de energía gamma', 'b1.nogg_hint'),
    ('Grupos de energía neutrónica', 'b1.ngrp_hint'),
    ('Grupos gamma del transporte', 'b1.igrp_hint'),
    ('Tipo de geometría', 'b1.ige_hint'),
    ('Nº de zonas de material', 'b1.izm_hint'),
    ('Intervalos espaciales (1D) / 1ª dim. (2D)', 'b1.im_hint'),
    ('2ª dimensión (2D); 0 para 1D/3D', 'b1.jm_hint'),
    ('Fuente del flujo neutrónico', 'b1.iflu_hint'),
    ('Imprimir flujos neutrónico', 'b1.iprt_hint'),
    ('Imprimir producción de fotones', 'b1.ilib_hint'),
    ('Concentraciones durante irradiación', 'b1.irad_hint'),
    ('Generar fichero de tasas de emisión gamma', 'b1.ipun_hint'),
    ('Activar inventario de productos de fisión', 'b10.igfp_hint'),
    ('Método de cálculo del rendimiento de fisión', 'b10.iwfyd_hint'),
    ('Fichero fuente de rendimientos de fisión', 'b10.ifort96_hint'),
    ('Repeticiones de la unidad. 0 = sin repetición.', 'b11.nopul_hint'),
    ('Total de conjuntos (<150).', 'b11.notts_hint'),
    ('0=no, N=nº distancias (OFFSIDO.dat)', 'b11.ioffsd_hint'),
    ('Escribe inventario en UNIT 48 cada NMULT ciclos. 0 = no generar.', 'b11.nmult_hint'),
    ('Ciclos con salida (0 si NOPUL=0).', 'b13.ncyo_hint'),
    ('Nº de historias Monte Carlo.', 'b14.nmohi_hint'),
    ('Nº de tiempos de interés.', 'b14.ntimes_hint'),
    ('Ciclos con tiempos de interés. 0 si NOPUL = 0.', 'b14.ncyu_hint'),
    ('Nº de nucléidos con incertidumbre en concentración.', 'b14.nnucu_hint'),
    ('IZM valores (uno por zona de material).', 'b2.nuczo_hint'),
    ('Número de elementos o isótopos de alimentación continua por zona (Block #6). Omitir si INFD = 0.', 'b2.isozo_hint'),
]
for text, key in form_hints:
    rp(f'<div class="form-text">{text}</div>',
       f'<div class="form-text" data-i18n="{key}">{text}</div>', f'hint {key}')

rp('<div class="form-text">Conjuntos por unidad. Si NOPUL=0 \u2192 0.</div>',
   '<div class="form-text" data-i18n="b11.ntseq_hint">Conjuntos por unidad. Si NOPUL=0 \u2192 0.</div>', 'ntseq_hint')

# --- 17. B78 GENERATOR LABELS ---
rp('<label class="form-label" for="b78-iunit">IUNIT &mdash; Unidad de tiempo</label>',
   '<label class="form-label" for="b78-iunit" data-i18n="b78.iunit_lbl">IUNIT &mdash; Unidad de tiempo</label>', 'b78 iunit lbl')
rp('<label class="form-label">Opciones de salida por conjunto</label>',
   '<label class="form-label" data-i18n="b78.out_lbl">Opciones de salida por conjunto</label>', 'b78 out_lbl')
rp('<label class="form-check-label small" for="b78-iout">IOUT = 1 (por intervalo)</label>',
   '<label class="form-check-label small" for="b78-iout" data-i18n="b78.iout_lbl">IOUT = 1 (por intervalo)</label>', 'b78 iout')
rp('<label class="form-check-label small" for="b78-iplot">IPLOT = 1 (datos para gráfica)</label>',
   '<label class="form-check-label small" for="b78-iplot" data-i18n="b78.iplot_lbl">IPLOT = 1 (datos para gráfica)</label>', 'b78 iplot')
rp('<div class="form-text">Aplica a todos los conjuntos del historial.</div>',
   '<div class="form-text" data-i18n="b78.iunit_hint">Aplica a todos los conjuntos del historial.</div>', 'b78 iunit_hint')

rp('<th>Tiempo final acumulado <span class="fw-normal text-muted">(unidad IUNIT)</span></th>',
   '<th data-i18n="b78.irr_th_time">Tiempo final acumulado <span class="fw-normal text-muted" data-i18n="b78.irr_th_iunit">(unidad IUNIT)</span></th>', 'b78 irr th time')
rp('<th style="width:3rem">#</th>\n                        <th>Tiempo final acumulado <span class="fw-normal text-muted">(desde fin de irradiación)</span></th>',
   '<th style="width:3rem">#</th>\n                        <th data-i18n="b78.irr_th_time">Tiempo final acumulado <span class="fw-normal text-muted" data-i18n="b78.cool_th_note">(desde fin de irradiación)</span></th>', 'b78 cool th time')
rp('<th style="width:10rem">Pasos (1&ndash;10)</th>\n                        <th style="width:3rem"></th>\n                      </tr>\n                    </thead>\n                    <tbody id="b78-irr-tbody">',
   '<th style="width:10rem" data-i18n="b78.irr_th_steps">Pasos (1\u201310)</th>\n                        <th style="width:3rem"></th>\n                      </tr>\n                    </thead>\n                    <tbody id="b78-irr-tbody">', 'b78 irr steps 1')
rp('<th style="width:10rem">Pasos (1&ndash;10)</th>\n                        <th style="width:3rem"></th>\n                      </tr>\n                    </thead>\n                    <tbody id="b78-cool-tbody">',
   '<th style="width:10rem" data-i18n="b78.irr_th_steps">Pasos (1\u201310)</th>\n                        <th style="width:3rem"></th>\n                      </tr>\n                    </thead>\n                    <tbody id="b78-cool-tbody">', 'b78 cool steps 1')

rp('<i class="bi bi-plus-lg me-1"></i>Añadir tramo de irradiación\n                  </button>',
   '<i class="bi bi-plus-lg me-1"></i><span data-i18n="b78.btn_add_irr">Añadir tramo de irradiación</span>\n                  </button>', 'b78 add irr')
rp('<i class="bi bi-plus-lg me-1"></i>Añadir tramo de enfriamiento\n                  </button>',
   '<i class="bi bi-plus-lg me-1"></i><span data-i18n="b78.btn_add_cool">Añadir tramo de enfriamiento</span>\n                  </button>', 'b78 add cool')
rp('<i class="bi bi-gear-fill me-1"></i>Generar y actualizar datos\n                    </button>',
   '<i class="bi bi-gear-fill me-1"></i><span data-i18n="b78.btn_gen">Generar y actualizar datos</span>\n                    </button>', 'b78 btn gen')
rp('<i class="bi bi-check-circle-fill me-1"></i>Historial generado y actualizado.\n                    </span>',
   '<i class="bi bi-check-circle-fill me-1"></i><span data-i18n="b78.ok_msg">Historial generado y actualizado.</span>\n                    </span>', 'b78 ok msg')
rp('placeholder="Pulsa «Generar y actualizar datos» para ver el código…"',
   'placeholder="Pulsa «Generar y actualizar datos» para ver el código…" data-i18n-ph="b78.preview_ph"', 'b78 preview ph')

# --- 18. B11 LABELS ---
rp('<label class="form-label" for="b11-IWP">IWP &mdash; Tipo de ejecución</label>',
   '<label class="form-label" for="b11-IWP" data-i18n="b11.iwp_lbl">IWP &mdash; Tipo de ejecución</label>', 'b11 iwp lbl')
rp('<label class="form-label" for="b11-IMTX">IMTX &mdash; Matriz de transición</label>',
   '<label class="form-label" for="b11-IMTX" data-i18n="b11.imtx_lbl">IMTX &mdash; Matriz de transición</label>', 'b11 imtx lbl')
rp('<label class="form-label" for="b11-IWDR">IWDR &mdash; Residuos</label>',
   '<label class="form-label" for="b11-IWDR" data-i18n="b11.iwdr_lbl">IWDR &mdash; Residuos</label>', 'b11 iwdr lbl')
rp('<label class="form-label" for="b11-IDOSE">IDOSE &mdash; Tasa de dosis</label>',
   '<label class="form-label" for="b11-IDOSE" data-i18n="b11.idose_lbl">IDOSE &mdash; Tasa de dosis</label>', 'b11 idose lbl')
rp('<label class="form-label" for="b11-IDHEAT">IDHEAT &mdash; Calor desint.</label>',
   '<label class="form-label" for="b11-IDHEAT" data-i18n="b11.idheat_lbl">IDHEAT &mdash; Calor desint.</label>', 'b11 idheat lbl')
rp('<label class="form-label" for="b11-ICEDE">ICEDE &mdash; CEDE</label>',
   '<label class="form-label" for="b11-ICEDE" data-i18n="b11.icede_lbl">ICEDE &mdash; CEDE</label>', 'b11 icede lbl')
rp('<label class="form-label" for="b11-INEMISS">INEMISS &mdash; Emisiones n</label>',
   '<label class="form-label" for="b11-INEMISS" data-i18n="b11.inemiss_lbl">INEMISS &mdash; Emisiones n</label>', 'b11 inemiss lbl')
rp('<label class="form-label" for="b11-IDAMAGE">IDAMAGE &mdash; DPA</label>',
   '<label class="form-label" for="b11-IDAMAGE" data-i18n="b11.idamage_lbl">IDAMAGE &mdash; DPA</label>', 'b11 idamage lbl')
rp('<label class="form-label" for="b11-dose-PH">PH &mdash; Fotónica (Sv/h)</label>',
   '<label class="form-label" for="b11-dose-PH" data-i18n="b11.ph_lbl">PH &mdash; Fotónica (Sv/h)</label>', 'b11 ph lbl')
rp('<label class="form-label" for="b11-dose-BREM">BREM &mdash; Bremsstrahlung</label>',
   '<label class="form-label" for="b11-dose-BREM" data-i18n="b11.brem_lbl">BREM &mdash; Bremsstrahlung</label>', 'b11 brem lbl')
rp('<label class="form-label" for="b11-dose-TOT">TOT &mdash; Fotón+Brem.</label>',
   '<label class="form-label" for="b11-dose-TOT" data-i18n="b11.tot_lbl">TOT &mdash; Fotón+Brem.</label>', 'b11 tot lbl')
rp('<label class="form-label" for="b11-dose-RHOR">RHOR &mdash; Capa delgada</label>',
   '<label class="form-label" for="b11-dose-RHOR" data-i18n="b11.rhor_lbl">RHOR &mdash; Capa delgada</label>', 'b11 rhor lbl')

# --- 19. MODAL CONTENT ---
rp('<i class="bi bi-eye me-1"></i>Vista previa &mdash; fichero inp.5',
   '<i class="bi bi-eye me-1"></i><span data-i18n="modal.preview_title">Vista previa &mdash; fichero inp.5</span>', 'modal preview title')
rp('<span class="ms-2 text-muted">Generando…</span>',
   '<span class="ms-2 text-muted" data-i18n="modal.preview_gen">Generando…</span>', 'modal gen')
rp('placeholder="Pulsa \'Vista previa del fichero\' en el menú Archivo para generar la vista previa…"',
   'placeholder="Pulsa \'Vista previa del fichero\' en el menú Archivo para generar la vista previa…" data-i18n-ph="modal.preview_ph"', 'modal preview ph')
rp('<i class="bi bi-clipboard me-1"></i>Copiar al portapapeles\n        </button>',
   '<i class="bi bi-clipboard me-1"></i><span data-i18n="modal.preview_copy">Copiar al portapapeles</span>\n        </button>', 'modal copy btn')
rp('data-bs-dismiss="modal">Cerrar</button>',
   'data-bs-dismiss="modal" data-i18n="modal.preview_close">Cerrar</button>', 'modal close')
rp('<i class="bi bi-floppy me-1"></i>Guardar como…\n        </h5>',
   '<i class="bi bi-floppy me-1"></i><span data-i18n="modal.saveas_title">Guardar como…</span>\n        </h5>', 'saveas title')
rp('<label class="form-label" for="save-filename">Nombre del fichero</label>',
   '<label class="form-label" for="save-filename" data-i18n="modal.saveas_lbl">Nombre del fichero</label>', 'saveas lbl')
rp('data-bs-dismiss="modal">Cancelar</button>',
   'data-bs-dismiss="modal" data-i18n="modal.saveas_cancel">Cancelar</button>', 'saveas cancel')
rp('<i class="bi bi-floppy me-1"></i>Guardar\n        </button>',
   '<i class="bi bi-floppy me-1"></i><span data-i18n="modal.saveas_save">Guardar</span>\n        </button>', 'saveas save')

# --- 20. FOOTER ---
rp('<span>Trabajo de Fin de Grado &mdash; Ingeniería de la Energía &nbsp;|&nbsp; 2026</span>',
   '<span data-i18n="footer.tfg">Trabajo de Fin de Grado &mdash; Ingeniería de la Energía &nbsp;|&nbsp; 2026</span>', 'footer tfg')
rp('<span class="text-secondary">Escuela Universitaria de Minas y Energía &mdash; Universidad Politécnica de Madrid</span>',
   '<span class="text-secondary" data-i18n="footer.center">Escuela Universitaria de Minas y Energía &mdash; Universidad Politécnica de Madrid</span>', 'footer center')

# --- 21. FILE STATUS initial text ---
rp('<span class="navbar-text small" id="file-status">\n      <i class="bi bi-circle text-secondary me-1"></i>Sin fichero cargado\n    </span>',
   '<span class="navbar-text small" id="file-status" data-i18n="status.no_file">\n      <i class="bi bi-circle text-secondary me-1"></i>Sin fichero cargado\n    </span>', 'file status')

# --- 22. SEC-UNCERTAINTIES warning ---
rp('Este bloque solo se activa cuando <strong>IUNC = 1</strong> en Block #1.\n          Si IUNC cambia a un valor distinto de 1, esta sección quedará deshabilitada.',
   '<span data-i18n="b14.iunc_warn">Este bloque solo se activa cuando <strong>IUNC = 1</strong> en Block #1.\n          Si IUNC cambia a un valor distinto de 1, esta sección quedará deshabilitada.</span>', 'b14 iunc warn')

# --- 23. B3 IFLU warning ---
rp('IFLU ≠ 1 en Block #1 &mdash; este bloque no se escribirá en el fichero de salida.',
   '<span data-i18n="b3.iflu_warn">IFLU ≠ 1 en Block #1 &mdash; este bloque no se escribirá en el fichero de salida.</span>', 'b3 iflu warn')

# --- 24. B5/B6 static text ---
rp('Define zonas en <strong>NUCZO</strong> (Block #2) para activar la edición de composiciones.',
   '<span data-i18n="b5.empty_msg">Define zonas en <strong>NUCZO</strong> (Block #2) para activar la edición de composiciones.</span>', 'b5 empty msg')
rp('Establece <strong>INFD &gt; 0</strong> (Block #1) and define <strong>ISOZO</strong> (Block #2)\n                  para activar la alimentación continua.',
   '<span data-i18n="b6.empty_msg">Establece <strong>INFD &gt; 0</strong> (Block #1) and define <strong>ISOZO</strong> (Block #2)\n                  para activar la alimentación continua.</span>', 'b6 empty msg')

# --- WRITE ---
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\nWritten: {html_path}")
print(f"   {len(ok)} replacements applied")
print(f"   {len(fail)} failed")
if fail:
    print("\nFailed:")
    for f in fail:
        print(f"  {f}")
