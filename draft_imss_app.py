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
from io import BytesIO
import base64
from pathlib import Path

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

    /* -- Ocultar barra superior de Streamlit -- */
    header[data-testid="stHeader"] { display: none !important; }

    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-top: 0.5rem !important;
        max-width: 900px;
    }

    /* -- Barra institucional de logos -- */
    .inst-logo-bar {
        background: white;
        padding: 12px 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 20px;
        border-radius: 12px 12px 0 0;
        border-bottom: 3px solid #691C32;
    }
    .inst-logo-bar img { height: 48px; max-width: 180px; object-fit: contain; }

    /* -- Header -- */
    .app-header {
        background: linear-gradient(135deg, #006B5E 0%, #13322B 100%);
        color: white;
        padding: 10px 16px;
        border-radius: 0 0 12px 12px;
        margin-bottom: 12px;
        text-align: center;
    }
    .app-header-standalone {
        border-radius: 12px;
    }
    .app-header h1 { font-size: 1.15rem; margin: 0; font-weight: 700; }
    .app-header p  { font-size: 0.78rem; margin: 2px 0 0; opacity: 0.85; }

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
    .kpi-total .kpi-value { color: #13322B; }
    .kpi-disp  .kpi-value { color: #006B5E; }
    .kpi-def   .kpi-value { color: #006B5E; }
    .kpi-int   .kpi-value { color: #691C32; }

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
    .zona-card.disponible { background: #e8f5e9; border-left: 5px solid #006B5E; }
    .zona-card.agotada    { background: #fce4ec; border-left: 5px solid #691C32; }
    .zona-nombre { font-weight: 700; font-size: 0.82rem; color: #333; margin-bottom: 6px; }
    .zona-numero { font-size: 1.8rem; font-weight: 800; line-height: 1; }
    .zona-sub    { font-size: 0.75rem; color: #777; margin-top: 2px; }
    .disponible .zona-numero { color: #006B5E; }
    .agotada    .zona-numero { color: #691C32; }

    /* -- Tarjetas especialidad -- */
    .esp-card {
        background: white; border: 1px solid #e0e0e0;
        border-radius: 8px; padding: 12px; margin-bottom: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .esp-card.disponible { border-left: 4px solid #006B5E; }
    .esp-card.agotada    { border-left: 4px solid #691C32; opacity: 0.55; }
    .esp-nombre { font-weight: 600; font-size: 0.9rem; color: #222; }
    .esp-zona   { font-size: 0.75rem; color: #888; margin-bottom: 6px; }
    .esp-badges { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 6px; }
    .badge {
        padding: 3px 10px; border-radius: 12px;
        font-size: 0.75rem; font-weight: 600;
    }
    .badge-def  { background: #e0f2f1; color: #006B5E; }
    .badge-int  { background: #fce4ec; color: #691C32; }
    .badge-tom  { background: #f5f5f5; color: #9B2335; }

    /* -- Botones tactiles -- */
    .stButton > button { min-height: 48px !important; font-size: 1rem !important; border-radius: 8px !important; }

    /* -- Ocultar sidebar toggle -- */
    [data-testid="collapsedControl"] { display: none !important; }

    /* -- Footer institucional -- */
    .inst-footer {
        border-top: 3px solid #691C32;
        padding-top: 12px;
        margin-top: 8px;
        text-align: center;
    }
    .inst-footer p {
        font-size: 0.75rem;
        color: #A7A9AC;
        margin: 2px 0;
    }

    /* -- Pantallas grandes -- */
    @media (min-width: 700px) {
        .kpi-grid  { grid-template-columns: repeat(4, 1fr); }
        .zona-grid { grid-template-columns: repeat(3, 1fr); }
        .app-header h1 { font-size: 1.8rem; }
        .inst-logo-bar img { height: 56px; }
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------
# FUNCIONES
# -----------------------------------------------

def img_to_base64(relative_path):
    """Convierte imagen local a base64 para embedding en HTML."""
    file_path = Path(__file__).parent / relative_path
    if file_path.exists():
        return base64.b64encode(file_path.read_bytes()).decode()
    return None


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
logo_gob_b64 = img_to_base64("assets/logo_gobierno.png")
logo_imss_b64 = img_to_base64("assets/logo_imss.png")

has_logos = logo_gob_b64 or logo_imss_b64

if has_logos:
    logos_html = '<div class="inst-logo-bar">'
    if logo_gob_b64:
        logos_html += f'<img src="data:image/png;base64,{logo_gob_b64}" alt="Gobierno de México">'
    if logo_imss_b64:
        logos_html += f'<img src="data:image/png;base64,{logo_imss_b64}" alt="IMSS">'
    logos_html += '</div>'
    st.markdown(logos_html, unsafe_allow_html=True)

header_extra_class = "" if has_logos else "app-header-standalone"
st.markdown(f"""
<div class="app-header {header_extra_class}">
    <h1>Draft IMSS 2026</h1>
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

        # --- Descargar Excel ---
        st.markdown("#### 📥 Descargar reporte Excel")
        tabla_excel = df[["zona", "especialidad", "def_total", "int_total",
                          "def_tomadas", "int_tomadas", "def_disp", "int_disp", "total_disp"]].copy()
        tabla_excel.columns = ["Zona", "Especialidad", "Def.Total", "Int.Total",
                               "Def.Tomadas", "Int.Tomadas", "Def.Disponibles", "Int.Disponibles", "Total Disp."]
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            tabla_excel.to_excel(writer, index=False, sheet_name="Plazas")
        st.download_button(
            "📥 Descargar Excel",
            data=buffer.getvalue(),
            file_name=f"plazas_dia{dia}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

        st.markdown("---")
        if st.button("🔒 Cerrar sesion normativo", use_container_width=True):
            st.session_state.normativo_auth = False
            st.rerun()


# -----------------------------------------------
# FOOTER
# -----------------------------------------------
st.markdown("""
<div class="inst-footer">
    <p><strong>Instituto Mexicano del Seguro Social</strong></p>
    <p>Draft Médicos Especialistas 2026 · Delegación Baja California y San Luis Rio Colorado Sonora</p>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------
# SWIPE ENTRE TABS (movil)
# -----------------------------------------------
import streamlit.components.v1 as components
components.html("""
<script>
(function() {
    const doc = window.parent.document;
    let startX = 0, startY = 0;
    doc.addEventListener('touchstart', function(e) {
        startX = e.changedTouches[0].screenX;
        startY = e.changedTouches[0].screenY;
    });
    doc.addEventListener('touchend', function(e) {
        const diffX = startX - e.changedTouches[0].screenX;
        const diffY = startY - e.changedTouches[0].screenY;
        if (Math.abs(diffX) < 60 || Math.abs(diffY) > Math.abs(diffX)) return;
        const tabs = doc.querySelectorAll('[role="tab"]');
        if (!tabs.length) return;
        let active = -1;
        tabs.forEach(function(t, i) { if (t.getAttribute('aria-selected') === 'true') active = i; });
        if (diffX > 0 && active < tabs.length - 1) tabs[active + 1].click();
        else if (diffX < 0 && active > 0) tabs[active - 1].click();
    });
})();
</script>
""", height=0)

