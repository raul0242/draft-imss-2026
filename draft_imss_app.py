"""
╔══════════════════════════════════════════════════════════════╗
║        DRAFT IMSS 2026 – Monitor de Plazas Disponibles       ║
║        Desarrollado para IMSS / Normativo Nacional           ║
╚══════════════════════════════════════════════════════════════╝

INSTRUCCIONES DE USO:
1. Instala dependencias (solo la primera vez):
       pip install streamlit pandas openpyxl

2. Coloca este archivo y el Excel en la misma carpeta.

3. Ejecuta la app:
       streamlit run draft_imss_app.py

4. Se abre automáticamente en tu navegador en http://localhost:8501
   Comparte esa URL en tu red local para que otros la consulten.
"""

import streamlit as st
import pandas as pd
import openpyxl
import json
import os
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURACIÓN GENERAL
# ─────────────────────────────────────────────
EXCEL_PATH = "PLAZAS_DRAFT_2026_X_ZONA.xlsx"   # <-- pon el nombre de tu archivo aquí
ESTADO_PATH = "estado_draft.json"               # archivo donde se guarda el avance

st.set_page_config(
    page_title="Draft IMSS 2026 – Plazas Disponibles",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# ESTILOS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    .main-title {
        font-size: 2rem; font-weight: 700; color: #003087;
        text-align: center; margin-bottom: 0;
    }
    .sub-title {
        text-align: center; color: #666; margin-bottom: 1.5rem;
    }
    .metric-disponible {
        background: #e8f5e9; border-left: 5px solid #2e7d32;
        padding: 10px 15px; border-radius: 6px; margin: 5px 0;
    }
    .metric-tomada {
        background: #ffebee; border-left: 5px solid #c62828;
        padding: 10px 15px; border-radius: 6px; margin: 5px 0;
    }
    .badge-zona {
        background: #003087; color: white; padding: 3px 10px;
        border-radius: 12px; font-size: 0.8rem; font-weight: 600;
    }
    .update-time {
        color: #888; font-size: 0.8rem; text-align: right;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# FUNCIONES DE CARGA Y ESTADO
# ─────────────────────────────────────────────

@st.cache_data(show_spinner="Cargando catálogo de plazas...")
def cargar_catalogo(path: str) -> pd.DataFrame:
    """Lee el Excel y devuelve un DataFrame plano con todas las plazas."""
    wb = openpyxl.load_workbook(path)
    ws = wb.active
    registros = []
    zona_actual = None
    for row in ws.iter_rows(values_only=True):
        a, b, c = row
        if a is not None and b is None and c is None:
            zona_actual = str(a).strip()
        elif a is not None and zona_actual and str(a).strip().upper() not in ("DEFINITIVA", "INTERINA"):
            definitivas = int(b) if b else 0
            interinas   = int(c) if c else 0
            if definitivas > 0 or interinas > 0:
                registros.append({
                    "zona":        zona_actual,
                    "especialidad": str(a).strip(),
                    "def_total":   definitivas,
                    "int_total":   interinas,
                })
    return pd.DataFrame(registros)


def cargar_estado() -> dict:
    """Carga el estado de plazas tomadas desde el JSON persistente."""
    if os.path.exists(ESTADO_PATH):
        with open(ESTADO_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"tomadas": {}, "ultima_actualizacion": None, "dia_evento": 1}


def guardar_estado(estado: dict):
    """Persiste el estado en disco."""
    estado["ultima_actualizacion"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    with open(ESTADO_PATH, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)


def clave(zona: str, especialidad: str) -> str:
    return f"{zona}||{especialidad}"


# ─────────────────────────────────────────────
# CARGA INICIAL
# ─────────────────────────────────────────────

if not os.path.exists(EXCEL_PATH):
    st.error(f"❌ No se encontró el archivo **{EXCEL_PATH}**. Colócalo en la misma carpeta que este script.")
    st.stop()

df = cargar_catalogo(EXCEL_PATH)
estado = cargar_estado()
tomadas: dict = estado.get("tomadas", {})


# ─────────────────────────────────────────────
# SIDEBAR – PANEL DE NORMATIVO
# ─────────────────────────────────────────────

st.sidebar.image(
    "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9b/IMSS_logo.svg/200px-IMSS_logo.svg.png",
    width=140,
)
st.sidebar.markdown("## 🔐 Panel Normativo")
st.sidebar.markdown("Actualiza diariamente las plazas tomadas.")

dia_evento = st.sidebar.number_input(
    "📅 Día del evento", min_value=1, max_value=10,
    value=estado.get("dia_evento", 1), step=1
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Registrar plazas tomadas")

zonas        = sorted(df["zona"].unique())
zona_sel     = st.sidebar.selectbox("Zona / OOAD", zonas)
espec_opciones = sorted(df[df["zona"] == zona_sel]["especialidad"].unique())
espec_sel    = st.sidebar.selectbox("Especialidad", espec_opciones)

fila = df[(df["zona"] == zona_sel) & (df["especialidad"] == espec_sel)].iloc[0]
k    = clave(zona_sel, espec_sel)
tomadas_actual = tomadas.get(k, {"def": 0, "int": 0})

st.sidebar.markdown(f"""
**Total ofertadas:**
- Definitivas: `{fila['def_total']}`
- Interinas: `{fila['int_total']}`
""")

nuevas_def = st.sidebar.number_input(
    "Definitivas TOMADAS", min_value=0,
    max_value=int(fila["def_total"]),
    value=int(tomadas_actual["def"]), step=1
)
nuevas_int = st.sidebar.number_input(
    "Interinas TOMADAS", min_value=0,
    max_value=int(fila["int_total"]),
    value=int(tomadas_actual["int"]), step=1
)

if st.sidebar.button("💾 Guardar cambios", use_container_width=True, type="primary"):
    tomadas[k] = {"def": nuevas_def, "int": nuevas_int}
    estado["tomadas"]    = tomadas
    estado["dia_evento"] = dia_evento
    guardar_estado(estado)
    st.sidebar.success("✅ Guardado correctamente")
    st.rerun()

if estado.get("ultima_actualizacion"):
    st.sidebar.markdown(f"<p class='update-time'>Última actualización:<br>{estado['ultima_actualizacion']}</p>",
                        unsafe_allow_html=True)

st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Reiniciar todo el estado", use_container_width=True):
    if os.path.exists(ESTADO_PATH):
        os.remove(ESTADO_PATH)
    st.rerun()


# ─────────────────────────────────────────────
# CONSTRUIR DATAFRAME CON DISPONIBILIDAD
# ─────────────────────────────────────────────

def disponibles(row):
    k = clave(row["zona"], row["especialidad"])
    t = tomadas.get(k, {"def": 0, "int": 0})
    return pd.Series({
        "def_tomadas":  t["def"],
        "int_tomadas":  t["int"],
        "def_disp":     row["def_total"] - t["def"],
        "int_disp":     row["int_total"] - t["int"],
        "total_disp":   (row["def_total"] - t["def"]) + (row["int_total"] - t["int"]),
    })

df = df.join(df.apply(disponibles, axis=1))


# ─────────────────────────────────────────────
# VISTA PRINCIPAL
# ─────────────────────────────────────────────

st.markdown(f"<h1 class='main-title'>🏥 Draft IMSS 2026 — Plazas Disponibles</h1>", unsafe_allow_html=True)
st.markdown(f"<p class='sub-title'>Día {dia_evento} del evento · Delegación Baja California y Sonora</p>",
            unsafe_allow_html=True)

# ── KPIs Globales ──
total_def  = df["def_total"].sum()
total_int  = df["int_total"].sum()
tom_def    = df["def_tomadas"].sum()
tom_int    = df["int_tomadas"].sum()
disp_def   = df["def_disp"].sum()
disp_int   = df["int_disp"].sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric("📋 Total Plazas",   int(total_def + total_int))
col2.metric("✅ Disponibles",    int(disp_def + disp_int),
            delta=f"-{int(tom_def + tom_int)} tomadas", delta_color="inverse")
col3.metric("🎓 Definitivas disp.", int(disp_def))
col4.metric("📄 Interinas disp.",  int(disp_int))

st.markdown("---")

# ── Filtros de vista ──
col_f1, col_f2, col_f3 = st.columns([2, 2, 2])
with col_f1:
    zona_filtro = st.multiselect("🗺️ Filtrar por Zona", options=zonas, default=[])
with col_f2:
    solo_disponibles = st.checkbox("Mostrar solo con plazas disponibles", value=True)
with col_f3:
    tipo_plaza = st.radio("Tipo de plaza", ["Ambas", "Solo Definitivas", "Solo Interinas"], horizontal=True)

# Aplicar filtros
vista = df.copy()
if zona_filtro:
    vista = vista[vista["zona"].isin(zona_filtro)]
if solo_disponibles:
    vista = vista[vista["total_disp"] > 0]
if tipo_plaza == "Solo Definitivas":
    vista = vista[vista["def_disp"] > 0]
elif tipo_plaza == "Solo Interinas":
    vista = vista[vista["int_disp"] > 0]

# ── Tabla principal ──
st.markdown(f"### 📊 Plazas — {len(vista)} registros encontrados")

if vista.empty:
    st.info("No hay plazas disponibles con los filtros seleccionados.")
else:
    tabla = vista[["zona", "especialidad", "def_total", "def_tomadas", "def_disp",
                   "int_total", "int_tomadas", "int_disp", "total_disp"]].copy()
    tabla.columns = [
        "Zona/OOAD", "Especialidad",
        "Def. Total", "Def. Tomadas", "Def. Disponibles",
        "Int. Total", "Int. Tomadas", "Int. Disponibles",
        "Total Disponibles"
    ]

    st.dataframe(
        tabla.style
            .applymap(lambda v: "background-color: #c8e6c9; font-weight:bold"
                      if isinstance(v, int) and v > 0 and tabla.columns[tabla.columns.tolist().index(tabla.columns[tabla.eq(v).any()].tolist()[0]) if False else 0] in ["Def. Disponibles", "Int. Disponibles", "Total Disponibles"] else "",
                      subset=["Def. Disponibles", "Int. Disponibles", "Total Disponibles"])
            .format({"Def. Total": "{:.0f}", "Def. Tomadas": "{:.0f}", "Def. Disponibles": "{:.0f}",
                     "Int. Total": "{:.0f}", "Int. Tomadas": "{:.0f}", "Int. Disponibles": "{:.0f}",
                     "Total Disponibles": "{:.0f}"}),
        use_container_width=True,
        height=500,
    )

    # Botón de exportar
    csv = tabla.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="⬇️ Descargar reporte CSV",
        data=csv,
        file_name=f"plazas_disponibles_dia{dia_evento}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
    )

# ── Vista por Zona ──
st.markdown("---")
st.markdown("### 🗺️ Resumen por Zona")

zonas_vista = zona_filtro if zona_filtro else zonas
cols = st.columns(min(len(zonas_vista), 3))

for idx, zona in enumerate(zonas_vista):
    df_zona = df[df["zona"] == zona]
    disp_z  = int(df_zona["total_disp"].sum())
    tom_z   = int((df_zona["def_tomadas"] + df_zona["int_tomadas"]).sum())
    tot_z   = int((df_zona["def_total"] + df_zona["int_total"]).sum())

    with cols[idx % 3]:
        color = "#e8f5e9" if disp_z > 0 else "#ffebee"
        icon  = "✅" if disp_z > 0 else "🔴"
        st.markdown(f"""
        <div style="background:{color}; padding:12px; border-radius:8px; margin-bottom:10px;">
            <b>{icon} {zona}</b><br>
            <span style="font-size:1.4rem; font-weight:700; color:#003087">{disp_z}</span>
            <span style="color:#666"> / {tot_z} disponibles</span><br>
            <small style="color:#888">{tom_z} plazas tomadas</small>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")
st.caption("Sistema desarrollado para IMSS · Draft de Médicos Especialistas 2026 · Delegación BC y Sonora")
