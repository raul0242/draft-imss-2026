"""
╔══════════════════════════════════════════════════════════════╗
║        DRAFT IMSS 2026 – Monitor de Plazas Disponibles       ║
║        Versión Mobile-Friendly                               ║
╚══════════════════════════════════════════════════════════════╝

INSTRUCCIONES:
    pip install streamlit pandas openpyxl
    streamlit run draft_imss_app.py
"""

import streamlit as st
import pandas as pd
import openpyxl
import json
import os
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
EXCEL_PATH  = "PLAZAS_DRAFT_2026_X_ZONA.xlsx"
ESTADO_PATH = "estado_draft.json"

st.set_page_config(
    page_title="Draft IMSS 2026",
    page_icon="🏥",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# CSS RESPONSIVE (mobile-first)
# ─────────────────────────────────────────────
st.markdown("""
<style>
    html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; }

    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-top: 1rem !important;
        max-width: 900px;
    }

    /* ── Header ── */
    .app-header {
        background: linear-gradient(135deg, #003087 0%, #0050b3 100%);
        color: white;
        padding: 16px 20px;
        border-radius: 12px;
        margin-bottom: 16px;
        text-align: center;
    }
    .app-header h1 { font-size: 1.4rem; margin: 0; font-weight: 700; }
    .app-header p  { font-size: 0.85rem; margin: 4px 0 0; opacity: 0.85; }

    /* ── KPI Cards ── */
    .kpi-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
        margin-bottom: 16px;
    }
    .kpi-card {
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 14px 12px;
        text-align: center;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    .kpi-card .kpi-value {
        font-size: 2rem; font-weight: 800; line-height: 1;
    }
    .kpi-card .kpi-label {
        font-size: 0.72rem; color: #666; margin-top: 4px;
        text-transform: uppercase; letter-spacing: 0.03em;
    }
    .kpi-total .kpi-value { color: #003087; }
    .kpi-disp  .kpi-value { color: #2e7d32; }
    .kpi-def   .kpi-value { color: #1565c0; }
    .kpi-int   .kpi-value { color: #6a1b9a; }

    /* ── Tarjetas zona ── */
    .zona-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
        margin-top: 12px;
    }
    .zona-card {
        border-radius: 10px; padding: 14px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }
    .zona-card.disponible { background: #f1f8e9; border-left: 5px solid #558b2f; }
    .zona-card.agotada    { background: #fce4ec; border-left: 5px solid #c62828; }
    .zona-nombre { font-weight: 700; font-size: 0.82rem; color: #333; margin-bottom: 6px; }
    .zona-numero { font-size: 1.8rem; font-weight: 800; line-height: 1; }
    .zona-sub    { font-size: 0.75rem; color: #777; margin-top: 2px; }
    .disponible .zona-numero { color: #2e7d32; }
    .agotada    .zona-numero { color: #c62828; }

    /* ── Tarjetas especialidad ── */
    .esp-card {
        background: white; border: 1px solid #e0e0e0;
        border-radius: 8px; padding: 12px; margin-bottom: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .esp-card.disponible { border-left: 4px solid #2e7d32; }
    .esp-card.agotada    { border-left: 4px solid #e53935; opacity: 0.55; }
    .esp-nombre { font-weight: 600; font-size: 0.9rem; color: #222; }
    .esp-zona   { font-size: 0.75rem; color: #888; margin-bottom: 6px; }
    .esp-badges { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 6px; }
    .badge {
        padding: 3px 10px; border-radius: 12px;
        font-size: 0.75rem; font-weight: 600;
    }
    .badge-def  { background: #e3f2fd; color: #1565c0; }
    .badge-int  { background: #ede7f6; color: #6a1b9a; }
    .badge-tom  { background: #ffebee; color: #c62828; }

    /* ── Inputs táctiles ── */
    .stButton > button { min-height: 48px !important; font-size: 1rem !important; border-radius: 8px !important; }

    /* ── Ocultar sidebar toggle ── */
    [data-testid="collapsedControl"] { display: none !important; }

    /* ── Pantallas grandes ── */
    @media (min-width: 700px) {
        .kpi-grid  { grid-template-columns: repeat(4, 1fr); }
        .zona-grid { grid-template-columns: repeat(3, 1fr); }
        .app-header h1 { font-size: 1.8rem; }
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# FUNCIONES
# ─────────────────────────────────────────────

@st.cache_data(show_spinner="Cargando catálogo...")
def cargar_catalogo(path):
    wb = openpyxl.load_workbook(path)
    ws = wb.active
    registros, zona_actual = [], None
    for row in ws.iter_rows(values_only=True):
        a, b, c = row
        if a is not None and b is None and c is None:
            zona_actual = str(a).strip()
        elif a is not None and zona_actual and str(a).strip().upper() not in ("DEFINITIVA", "INTERINA"):
            d = int(b) if b else 0
            i = int(c) if c else 0
            if d > 0 or i > 0:
                registros.append({"zona": zona_actual, "especialidad": str(a).strip(),
                                   "def_total": d, "int_total": i})
    return pd.DataFrame(registros)


def cargar_estado():
    if os.path.exists(ESTADO_PATH):
        with open(ESTADO_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"tomadas": {}, "ultima_actualizacion": None, "dia_evento": 1}


def guardar_estado(estado):
    estado["ultima_actualizacion"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    with open(ESTADO_PATH, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)


def clave(zona, especialidad):
    return f"{zona}||{especialidad}"


def calcular_disponibles(df, tomadas):
    def _row(row):
        t = tomadas.get(clave(row["zona"], row["especialidad"]), {"def": 0, "int": 0})
        return pd.Series({
            "def_tomadas": t["def"], "int_tomadas": t["int"],
            "def_disp":    row["def_total"] - t["def"],
            "int_disp":    row["int_total"] - t["int"],
            "total_disp":  (row["def_total"] - t["def"]) + (row["int_total"] - t["int"]),
        })
    return df.join(df.apply(_row, axis=1))


# ─────────────────────────────────────────────
# CARGA INICIAL
# ─────────────────────────────────────────────

if not os.path.exists(EXCEL_PATH):
    st.error(f"❌ Archivo no encontrado: **{EXCEL_PATH}**")
    st.stop()

df_base = cargar_catalogo(EXCEL_PATH)
estado  = cargar_estado()
tomadas = estado.get("tomadas", {})
dia     = estado.get("dia_evento", 1)
df      = calcular_disponibles(df_base, tomadas)
zonas   = sorted(df["zona"].unique())

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
ultima = estado.get("ultima_actualizacion") or "Sin actualizaciones aún"
st.markdown(f"""
<div class="app-header">
    <h1>🏥 Draft IMSS 2026</h1>
    <p>Plazas Disponibles · Día {dia} del evento</p>
    <p style="font-size:0.75rem; opacity:0.7">Última actualización: {ultima}</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# KPIs
# ─────────────────────────────────────────────
total = int(df["def_total"].sum() + df["int_total"].sum())
disp  = int(df["def_disp"].sum()  + df["int_disp"].sum())
def_d = int(df["def_disp"].sum())
int_d = int(df["int_disp"].sum())

st.markdown(f"""
<div class="kpi-grid">
    <div class="kpi-card kpi-total"><div class="kpi-value">{total}</div><div class="kpi-label">📋 Total Plazas</div></div>
    <div class="kpi-card kpi-disp"> <div class="kpi-value">{disp}</div> <div class="kpi-label">✅ Disponibles</div></div>
    <div class="kpi-card kpi-def">  <div class="kpi-value">{def_d}</div><div class="kpi-label">🎓 Definitivas</div></div>
    <div class="kpi-card kpi-int">  <div class="kpi-value">{int_d}</div><div class="kpi-label">📄 Interinas</div></div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────
tab_plazas, tab_zonas, tab_normativo = st.tabs(["📋 Plazas", "🗺️ Por Zona", "🔐 Normativo"])


# ══════════════════════════════════════════════
# TAB 1 – PLAZAS
# ══════════════════════════════════════════════
with tab_plazas:
    zona_filtro = st.multiselect("Filtrar por Zona", options=zonas)
    col_a, col_b = st.columns(2)
    with col_a:
        solo_disp = st.checkbox("Solo disponibles", value=True)
    with col_b:
        tipo = st.selectbox("Tipo", ["Ambas", "Definitivas", "Interinas"], label_visibility="collapsed")

    vista = df.copy()
    if zona_filtro:
        vista = vista[vista["zona"].isin(zona_filtro)]
    if solo_disp:
        vista = vista[vista["total_disp"] > 0]
    if tipo == "Definitivas":
        vista = vista[vista["def_disp"] > 0]
    elif tipo == "Interinas":
        vista = vista[vista["int_disp"] > 0]

    st.caption(f"{len(vista)} especialidades encontradas")

    if vista.empty:
        st.info("No hay plazas disponibles con estos filtros.")
    else:
        for _, row in vista.iterrows():
            css = "disponible" if row["total_disp"] > 0 else "agotada"
            badges = ""
            if row["def_disp"] > 0:
                badges += f'<span class="badge badge-def">🎓 {int(row["def_disp"])} Def.</span>'
            if row["int_disp"] > 0:
                badges += f'<span class="badge badge-int">📄 {int(row["int_disp"])} Int.</span>'
            tom = int(row["def_tomadas"] + row["int_tomadas"])
            if tom > 0:
                badges += f'<span class="badge badge-tom">❌ {tom} tomadas</span>'
            st.markdown(f"""
            <div class="esp-card {css}">
                <div class="esp-nombre">{row['especialidad']}</div>
                <div class="esp-zona">{row['zona']}</div>
                <div class="esp-badges">{badges}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("")
        tabla_exp = vista[["zona","especialidad","def_disp","int_disp","total_disp","def_tomadas","int_tomadas"]].copy()
        tabla_exp.columns = ["Zona","Especialidad","Def.Disponibles","Int.Disponibles","Total Disp.","Def.Tomadas","Int.Tomadas"]
        csv = tabla_exp.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ Descargar CSV", data=csv,
            file_name=f"plazas_dia{dia}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv", use_container_width=True)


# ══════════════════════════════════════════════
# TAB 2 – POR ZONA
# ══════════════════════════════════════════════
with tab_zonas:
    cards_html = '<div class="zona-grid">'
    for zona in zonas:
        dz     = df[df["zona"] == zona]
        disp_z = int(dz["total_disp"].sum())
        tom_z  = int((dz["def_tomadas"] + dz["int_tomadas"]).sum())
        tot_z  = int((dz["def_total"] + dz["int_total"]).sum())
        css    = "disponible" if disp_z > 0 else "agotada"
        icon   = "✅" if disp_z > 0 else "🔴"
        cards_html += f"""
        <div class="zona-card {css}">
            <div class="zona-nombre">{icon} {zona}</div>
            <div class="zona-numero">{disp_z}</div>
            <div class="zona-sub">de {tot_z} disponibles</div>
            <div class="zona-sub">{tom_z} tomadas</div>
        </div>"""
    cards_html += "</div>"
    st.markdown(cards_html, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### Detalle por zona")
    for zona in zonas:
        dz = df[df["zona"] == zona]
        dz_disp = dz[dz["total_disp"] > 0]
        n = len(dz_disp)
        with st.expander(f"{'✅' if n > 0 else '🔴'} {zona}  —  {n} especialidades disponibles"):
            if dz_disp.empty:
                st.warning("Sin plazas disponibles en esta zona.")
            else:
                for _, r in dz_disp.iterrows():
                    st.markdown(f"**{r['especialidad']}** — 🎓 `{int(r['def_disp'])}` def. · 📄 `{int(r['int_disp'])}` int.")


# ══════════════════════════════════════════════
# TAB 3 – NORMATIVO
# ══════════════════════════════════════════════
with tab_normativo:
    st.markdown("#### 🔐 Actualización de plazas tomadas")
    st.info("Solo el equipo normativo debe operar esta sección.")

    dia_nuevo = st.number_input("📅 Día del evento", min_value=1, max_value=10, value=dia, step=1)
    st.markdown("---")

    zona_sel  = st.selectbox("🗺️ Zona / OOAD", zonas, key="n_zona")
    espec_ops = sorted(df[df["zona"] == zona_sel]["especialidad"].unique())
    espec_sel = st.selectbox("🔬 Especialidad", espec_ops, key="n_espec")

    fila  = df[(df["zona"] == zona_sel) & (df["especialidad"] == espec_sel)].iloc[0]
    k_sel = clave(zona_sel, espec_sel)
    act   = tomadas.get(k_sel, {"def": 0, "int": 0})

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Definitivas", int(fila["def_total"]))
        n_def = st.number_input("Tomadas (Def.)", 0, int(fila["def_total"]), int(act["def"]), key="n_def")
    with col2:
        st.metric("Total Interinas", int(fila["int_total"]))
        n_int = st.number_input("Tomadas (Int.)", 0, int(fila["int_total"]), int(act["int"]), key="n_int")

    disp_prev_def = int(fila["def_total"]) - n_def
    disp_prev_int = int(fila["int_total"]) - n_int
    st.markdown(f"> **Vista previa:** quedarán **{disp_prev_def}** definitivas y **{disp_prev_int}** interinas disponibles.")

    if st.button("💾 Guardar cambios", use_container_width=True, type="primary"):
        tomadas[k_sel]       = {"def": n_def, "int": n_int}
        estado["tomadas"]    = tomadas
        estado["dia_evento"] = dia_nuevo
        guardar_estado(estado)
        st.success(f"✅ Guardado: {zona_sel} · {espec_sel}")
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    with st.expander("⚠️ Zona de peligro"):
        if st.button("🗑️ Reiniciar TODO el estado del evento", use_container_width=True):
            if os.path.exists(ESTADO_PATH):
                os.remove(ESTADO_PATH)
            st.cache_data.clear()
            st.rerun()

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown("---")
st.caption("🏥 IMSS · Draft Médicos Especialistas 2026 · Delegación Baja California y Sonora")
