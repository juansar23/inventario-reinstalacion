import streamlit as st
import pandas as pd
from datetime import datetime
import os

st.set_page_config(page_title="Inventario Reinstalación", layout="wide")

ARCHIVO_INVENTARIO = "inventario.csv"
ARCHIVO_MOVIMIENTOS = "movimientos.csv"

# ==========================
# FUNCIONES
# ==========================

def cargar_csv(nombre, columnas):
    if os.path.exists(nombre):
        return pd.read_csv(nombre)
    else:
        return pd.DataFrame(columns=columnas)

def guardar_csv(df, nombre):
    df.to_csv(nombre, index=False)

# ==========================
# CARGAR DATOS
# ==========================

inventario_cols = ["ID", "Nombre", "Categoría", "Cantidad", "Ubicación", "Estado"]
movimientos_cols = ["Fecha", "Tipo", "Material", "Cantidad", "Responsable"]

if "inventario" not in st.session_state:
    st.session_state.inventario = cargar_csv(ARCHIVO_INVENTARIO, inventario_cols)

if "movimientos" not in st.session_state:
    st.session_state.movimientos = cargar_csv(ARCHIVO_MOVIMIENTOS, movimientos_cols)

st.title("📦 Sistema de Inventario - Reinstalación")

# ==========================
# AGREGAR MATERIAL
# ==========================

st.subheader("➕ Agregar Material")

with st.form("agregar"):
    nombre = st.text_input("Nombre")
    categoria = st.selectbox("Categoría", ["Cableado", "Equipos", "Herramientas", "Conectores", "Otros"])
    cantidad = st.number_input("Cantidad", min_value=1, step=1)
    ubicacion = st.text_input("Ubicación")
    estado = st.selectbox("Estado", ["Nuevo", "Usado", "Dañado"])

    submitted = st.form_submit_button("Agregar")

    if submitted and nombre:
        nuevo_id = 1
        if not st.session_state.inventario.empty:
            nuevo_id = st.session_state.inventario["ID"].max() + 1

        nuevo = {
            "ID": nuevo_id,
            "Nombre": nombre,
            "Categoría": categoria,
            "Cantidad": cantidad,
            "Ubicación": ubicacion,
            "Estado": estado
        }

        st.session_state.inventario = pd.concat(
            [st.session_state.inventario, pd.DataFrame([nuevo])],
            ignore_index=True
        )

        # Registrar movimiento entrada
        movimiento = {
            "Fecha": datetime.now(),
            "Tipo": "Entrada",
            "Material": nombre,
            "Cantidad": cantidad,
            "Responsable": "Sistema"
        }

        st.session_state.movimientos = pd.concat(
            [st.session_state.movimientos, pd.DataFrame([movimiento])],
            ignore_index=True
        )

        guardar_csv(st.session_state.inventario, ARCHIVO_INVENTARIO)
        guardar_csv(st.session_state.movimientos, ARCHIVO_MOVIMIENTOS)

        st.success("Material agregado correctamente")

# ==========================
# SALIDA DE MATERIAL
# ==========================

st.subheader("📤 Registrar Salida de Material")

if not st.session_state.inventario.empty:

    material_seleccionado = st.selectbox(
        "Seleccionar material",
        st.session_state.inventario["Nombre"]
    )

    cantidad_salida = st.number_input("Cantidad a retirar", min_value=1, step=1)
    responsable = st.text_input("¿A quién se le entregó?")

    if st.button("Registrar Salida"):

        idx = st.session_state.inventario[
            st.session_state.inve_
