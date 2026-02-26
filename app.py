import streamlit as st
import pandas as pd
from datetime import datetime
import os

# ==========================
# CONFIGURACIÓN
# ==========================

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
# DEFINIR COLUMNAS
# ==========================

inventario_cols = ["ID", "Nombre", "Categoría", "Cantidad", "Ubicación", "Estado", "Fecha Ingreso"]

movimientos_cols = ["Fecha", "Tipo", "Material", "Cantidad", "Responsable"]

# ==========================
# CARGAR DATOS EN MEMORIA
# ==========================

if "inventario" not in st.session_state:
    st.session_state.inventario = cargar_csv(ARCHIVO_INVENTARIO, inventario_cols)

if "inventario" not in st.session_state:
    st.session_state.inventario = cargar_csv(ARCHIVO_INVENTARIO, inventario_cols)

    # 🔥 Si la columna no existe, crearla
    if "Fecha Ingreso" not in st.session_state.inventario.columns:
        st.session_state.inventario["Fecha Ingreso"] = ""


# ==========================
# TÍTULO
# ==========================

st.title("📦 Sistema de Inventario - Reinstalación")

# ==========================
# AGREGAR MATERIAL
# ==========================

st.subheader("➕ Agregar Material")

with st.form("form_agregar"):
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
        if nombre.strip() == "":
            st.warning("Debe ingresar un nombre")
        else:
            nuevo_id = 1
            if not st.session_state.inventario.empty:
                nuevo_id = int(st.session_state.inventario["ID"].max()) + 1

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
# REGISTRAR SALIDA
# ==========================

st.subheader("📤 Registrar Salida de Material")

if not st.session_state.inventario.empty:

    material_seleccionado = st.selectbox(
        "Seleccionar material",
        st.session_state.inventario["Nombre"].unique()
    )

    cantidad_salida = st.number_input("Cantidad a retirar", min_value=1, step=1)
    responsable = st.text_input("¿A quién se le entregó?")

    if st.button("Registrar Salida"):

        if responsable.strip() == "":
            st.warning("Debe indicar a quién se entregó")
        else:
            fila = st.session_state.inventario[
                st.session_state.inventario["Nombre"] == material_seleccionado
            ]

            if not fila.empty:

                idx = fila.index[0]
                stock_actual = st.session_state.inventario.loc[idx, "Cantidad"]

                if cantidad_salida <= stock_actual:

                    st.session_state.inventario.loc[idx, "Cantidad"] -= cantidad_salida

                    movimiento = {
                        "Fecha": datetime.now(),
                        "Tipo": "Salida",
                        "Material": material_seleccionado,
                        "Cantidad": cantidad_salida,
                        "Responsable": responsable
                    }

                    st.session_state.movimientos = pd.concat(
                        [st.session_state.movimientos, pd.DataFrame([movimiento])],
                        ignore_index=True
                    )

                    guardar_csv(st.session_state.inventario, ARCHIVO_INVENTARIO)
                    guardar_csv(st.session_state.movimientos, ARCHIVO_MOVIMIENTOS)

                    st.success("Salida registrada correctamente")

                else:
                    st.error("No hay suficiente stock disponible")

# ==========================
# INVENTARIO ACTUAL
# ==========================

st.subheader("📋 Inventario Actual")
st.dataframe(st.session_state.inventario, use_container_width=True)

# ==========================
# HISTORIAL DE MOVIMIENTOS
# ==========================

st.subheader("📜 Historial de Movimientos")
st.dataframe(st.session_state.movimientos, use_container_width=True)
# ==========================
# EXPORTAR DATOS
# ==========================

st.subheader("⬇ Exportar Datos")

col1, col2 = st.columns(2)

with col1:
    csv_inventario = st.session_state.inventario.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Descargar Inventario Actual",
        data=csv_inventario,
        file_name="inventario_actual.csv",
        mime="text/csv"
    )

with col2:
    # Solo exportar salidas
    salidas = st.session_state.movimientos[
        st.session_state.movimientos["Tipo"] == "Salida"
    ]

    csv_salidas = salidas.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Descargar Historial de Salidas",
        data=csv_salidas,
        file_name="historial_salidas.csv",
        mime="text/csv"
    )

# ==========================
# RESETEAR INVENTARIO MENSUAL
# ==========================

st.subheader("🔄 Resetear Inventario Mensual")

st.warning("⚠ Esta acción eliminará todo el inventario y el historial de movimientos.")

if st.button("Resetear Inventario"):

    # Reiniciar en memoria
    st.session_state.inventario = pd.DataFrame(columns=inventario_cols)
    st.session_state.movimientos = pd.DataFrame(columns=movimientos_cols)

    # Borrar archivos físicos si existen
    if os.path.exists(ARCHIVO_INVENTARIO):
        os.remove(ARCHIVO_INVENTARIO)

    if os.path.exists(ARCHIVO_MOVIMIENTOS):
        os.remove(ARCHIVO_MOVIMIENTOS)

    st.success("Inventario reiniciado correctamente. Ya puedes comenzar el nuevo mes.")

