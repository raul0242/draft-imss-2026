"""
DRAFT IMSS 2026 - Monitor de Plazas Disponibles
Version con Google Sheets + Panel Normativo

INSTRUCCIONES:
    pip install streamlit pandas gspread google-auth
    python -m streamlit run draft_imss_app.py
"""

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import traceback

# -----------------------------------------------
# CONFIGURACION
# -----------------------------------------------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

st.set_page_config(
    page_title="Draft IMSS 2026",
    page_icon="🏥",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# -----------------------------------------------
# CSS RESPONSIVE (mobile-first)
# -----------------------------------------------
st.markdown("""
<style>
    html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; }

    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-top: 1rem !important;
        max-width: 900px;
    }

    /* -- Header -- */
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

    /* -- KPI Cards -- */
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

    /* -- Tarjetas zona -- */
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

    /* -- Tarjetas especialidad -- */
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

    /* -- Botones tactiles -- */
    .stButton > button { min-height: 48px !important; font-size: 1rem !important; border-radius: 8px !important; }

    /* -- Ocultar sidebar toggle -- */
    [data-testid="collapsedControl"] { display: none !important; }

    /* -- Pantallas grandes -- */
    @media (min-width: 700px) {
        .kpi-grid  { grid-template-columns: repeat(4, 1fr); }
        .zona-grid { grid-template-columns: repeat(3, 1fr); }
        .app-header h1 { font-size: 1.8rem; }
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------
# FUNCIONES
# -----------------------------------------------

def get_gsheet_client():
    """Crea y retorna un cliente autenticado de Google Sheets."""
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), scopes=SCOPES
    )
    return gspread.authorize(creds)


@st.cache_data(ttl=60, show_spinner="Cargando datos desde Google Sheets...")
def cargar_datos_gsheet():
    client = get_gsheet_client()
    sh = client.open_by_key(st.secrets["spreadsheet_id"])

    # --- Hoja 1: Plazas ---
    ws_plazas = sh.worksheet("Plazas")
    records = ws_plazas.get_all_records()
    df = pd.DataFrame(records)

    for col in ["def_total", "int_total", "def_tomadas", "int_tomadas"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    df["def_disp"] = df["def_total"] - df["def_tomadas"]
    df["int_disp"] = df["int_total"] - df["int_tomadas"]
    df["total_disp"] = df["def_disp"] + df["int_disp"]

    # --- Hoja 2: Config ---
    ws_config = sh.worksheet("Config")
    config_data = ws_config.get_all_values()
    config = {}
    for row in config_data:
        if len(row) >= 2:
            config[row[0]] = row[1]

    return df, config


def actualizar_plaza_gsheet(zona, especialidad, def_tomadas, int_tomadas):
    """Actualiza las columnas def_tomadas e int_tomadas en Google Sheets."""
    client = get_gsheet_client()
    sh = client.open_by_key(st.secrets["spreadsheet_id"])
    ws = sh.worksheet("Plazas")

    # Buscar la fila que coincida con zona + especialidad
    all_data = ws.get_all_values()
    header = all_data[0]
    col_zona = header.index("zona")
    col_esp = header.index("especialidad")
    col_def_tom = header.index("def_tomadas")
    col_int_tom = header.index("int_tomadas")

    for i, row in enumerate(all_data[1:], start=2):
        if row[col_zona] == zona and row[col_esp] == especialidad:
            ws.update_cell(i, col_def_tom + 1, def_tomadas)
            ws.update_cell(i, col_int_tom + 1, int_tomadas)
            break

    # Actualizar timestamp en Config
    ws_config = sh.worksheet("Config")
    ws_config.update_cell(2, 2, datetime.now().strftime("%d/%m/%Y %H:%M:%S"))


def actualizar_dia_gsheet(dia_nuevo):
    """Actualiza el dia del evento en la hoja Config."""
    client = get_gsheet_client()
    sh = client.open_by_key(st.secrets["spreadsheet_id"])
    ws_config = sh.worksheet("Config")
    ws_config.update_cell(1, 2, dia_nuevo)


# -----------------------------------------------
# CARGA INICIAL
# -----------------------------------------------

try:
    df, config = cargar_datos_gsheet()
except Exception as e:
    st.error("Error al conectar con Google Sheets:")
    st.code(traceback.format_exc())
    st.stop()

dia = int(config.get("dia_evento", 1))
ultima = config.get("ultima_actualizacion", "Sin actualizaciones aun")
zonas = sorted(df["zona"].unique())

# -----------------------------------------------
# HEADER
# -----------------------------------------------
st.markdown(f"""
<div class="app-header">
    <h1>🏥 Draft IMSS 2026</h1>
    <p>Plazas Disponibles - OOAD Baja California</p>
    <p style="font-size:0.75rem; opacity:0.7">Dia {dia} del evento | Actualizado: {ultima}</p>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------
# KPIs
# -----------------------------------------------
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

# -----------------------------------------------
# TABS
# -----------------------------------------------
tab_plazas, tab_zonas, tab_normativo = st.tabs(["📋 Plazas", "🗺️ Por Zona", "🔐 Normativo"])


# ================================================
# TAB 1 - PLAZAS
# ================================================
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


# ================================================
# TAB 2 - POR ZONA
# ================================================
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


# ================================================
# TAB 3 - NORMATIVO (protegido con contrasena)
# ================================================
with tab_normativo:
    st.markdown("#### 🔐 Panel Normativo")
    st.info("Solo el equipo normativo debe operar esta seccion.")

    # --- Autenticacion simple ---
    if "normativo_auth" not in st.session_state:
        st.session_state.normativo_auth = False

    if not st.session_state.normativo_auth:
        pwd = st.text_input("Contrasena de acceso", type="password", key="pwd_input")
        if st.button("Ingresar", use_container_width=True):
            if pwd == st.secrets.get("normativo_password", "draft2026"):
                st.session_state.normativo_auth = True
                st.rerun()
            else:
                st.error("Contrasena incorrecta.")
    else:
        # --- Dia del evento ---
        dia_nuevo = st.number_input("📅 Dia del evento", min_value=1, max_value=10, value=dia, step=1)
        if dia_nuevo != dia:
            if st.button("Actualizar dia del evento", use_container_width=True):
                try:
                    actualizar_dia_gsheet(dia_nuevo)
                    st.cache_data.clear()
                    st.success(f"Dia actualizado a {dia_nuevo}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al actualizar dia: {e}")

        st.markdown("---")

        # --- Formulario de plazas tomadas ---
        zona_sel = st.selectbox("🗺️ Zona / OOAD", zonas, key="n_zona")
        espec_ops = sorted(df[df["zona"] == zona_sel]["especialidad"].unique())
        espec_sel = st.selectbox("🔬 Especialidad", espec_ops, key="n_espec")

        fila = df[(df["zona"] == zona_sel) & (df["especialidad"] == espec_sel)].iloc[0]

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Definitivas", int(fila["def_total"]))
            n_def = st.number_input("Tomadas (Def.)", 0, int(fila["def_total"]),
                                    int(fila["def_tomadas"]), key="n_def")
        with col2:
            st.metric("Total Interinas", int(fila["int_total"]))
            n_int = st.number_input("Tomadas (Int.)", 0, int(fila["int_total"]),
                                    int(fila["int_tomadas"]), key="n_int")

        disp_prev_def = int(fila["def_total"]) - n_def
        disp_prev_int = int(fila["int_total"]) - n_int
        st.markdown(f"> **Vista previa:** quedaran **{disp_prev_def}** definitivas y **{disp_prev_int}** interinas disponibles.")

        if st.button("💾 Guardar cambios", use_container_width=True, type="primary"):
            try:
                actualizar_plaza_gsheet(zona_sel, espec_sel, n_def, n_int)
                st.cache_data.clear()
                st.success(f"✅ Guardado: {zona_sel} · {espec_sel}")
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")

        st.markdown("---")
        if st.button("🔒 Cerrar sesion normativo", use_container_width=True):
            st.session_state.normativo_auth = False
            st.rerun()


# -----------------------------------------------
# FOOTER
# -----------------------------------------------
st.markdown("---")
st.caption("🏥 IMSS · Draft Médicos Especialistas 2026 · Delegación Baja California y Sonora")
