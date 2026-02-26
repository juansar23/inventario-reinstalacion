import streamlit as st
import pandas as pd
from datetime import datetime
import os

st.set_page_config(page_title="Inventario Reinstalación", layout="wide")

ARCHIVO_DATOS = "inventario.csv"

# ==========================
# FUNCIONES
# ==========================

def cargar_datos():
    if os.path.exists(ARCHIVO_DATOS):
        return pd.read_csv(ARCHIVO_DATOS)
    else:
        return pd.DataFrame(columns=[
            "ID",
            "Nombre",
            "Categoría",
            "Cantidad",
            "Ubicación",
            "Estado",
            "Fecha Registro"
        ])

def guardar_datos(df):
    df.to_csv(ARCHIVO_DATOS, index=False)

# ==========================
# CARGAR INVENTARIO
# ==========================

if "inventario" not in st.session_state:
    st.session_state.inventario = cargar_datos()

st.title("📦 Gestión de Inventario - Materiales de Reinstalación")

# ==========================
# FORMULARIO AGREGAR
# ==========================

st.subheader("➕ Agregar Material")

with st.form("form_material"):
    col1, col2 = st.columns(2)

    with col1:
        nombre = st.text_input("Nombre del material")
        categoria = st.selectbox("Categoría",
                                 ["Cableado", "Equipos", "Herramientas", "Conectores", "Otros"])
        cantidad = st.number_input("Cantidad", min_value=1, step=1)

    with col2:
        ubicacion = st.text_input("Ubicación")
        estado = st.selectbox("Estado", ["Nuevo", "Usado", "Dañado"])

    submitted = st.form_submit_button("Agregar")

    if submitted:
        if nombre:
            nuevo_id = 1
            if not st.session_state.inventario.empty:
                nuevo_id = st.session_state.inventario["ID"].max() + 1

            nuevo = {
                "ID": nuevo_id,
                "Nombre": nombre,
                "Categoría": categoria,
                "Cantidad": cantidad,
                "Ubicación": ubicacion,
                "Estado": estado,
                "Fecha Registro": datetime.now().strftime("%Y-%m-%d %H:%M")
            }

            st.session_state.inventario = pd.concat(
                [st.session_state.inventario, pd.DataFrame([nuevo])],
                ignore_index=True
            )

            guardar_datos(st.session_state.inventario)
            st.success("Material agregado correctamente")
        else:
            st.warning("Ingrese un nombre válido")

# ==========================
# BUSCADOR
# ==========================

st.subheader("🔎 Buscar Material")

buscar = st.text_input("Buscar por nombre")

df = st.session_state.inventario

if buscar:
    df = df[df["Nombre"].str.contains(buscar, case=False, na=False)]

# ==========================
# MÉTRICAS
# ==========================

col1, col2 = st.columns(2)
with col1:
    st.metric("Total de Ítems", len(st.session_state.inventario))
with col2:
    st.metric("Cantidad Total",
              int(st.session_state.inventario["Cantidad"].sum()) if not st.session_state.inventario.empty else 0)

# ==========================
# TABLA
# ==========================

st.subheader("📋 Inventario Actual")
st.dataframe(df, use_container_width=True)

# ==========================
# ELIMINAR
# ==========================

st.subheader("🗑 Eliminar Material")

id_eliminar = st.number_input("Ingrese ID a eliminar", min_value=1, step=1)

if st.button("Eliminar"):
    st.session_state.inventario = st.session_state.inventario[
        st.session_state.inventario["ID"] != id_eliminar
    ]

    guardar_datos(st.session_state.inventario)
    st.success("Material eliminado (si existía)")

# ==========================
# EXPORTAR
# ==========================

st.subheader("⬇ Exportar Inventario")

if not st.session_state.inventario.empty:
    csv = st.session_state.inventario.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Descargar como CSV",
        csv,
        "inventario_reinstalacion.csv",
        "text/csv"
    )
