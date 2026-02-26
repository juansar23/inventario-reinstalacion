import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os

# =====================================
# CONFIGURACION
# =====================================

st.set_page_config(page_title="Sistema Inventario Reinstalacion", layout="wide")

ARCHIVO_INVENTARIO = "inventario.csv"
ARCHIVO_MOVIMIENTOS = "movimientos.csv"

ZONA = pytz.timezone("America/Bogota")

inventario_cols = ["ID", "Nombre", "Categoria", "Cantidad", "Ubicacion", "Estado", "Fecha_Ingreso", "Proveedor"]
movimientos_cols = ["Fecha", "Tipo", "Material", "Cantidad", "Responsable"]

# =====================================
# FUNCIONES
# =====================================

def cargar_csv(nombre, columnas):
    if os.path.exists(nombre):
        df = pd.read_csv(nombre)
    else:
        df = pd.DataFrame(columns=columnas)

    for col in columnas:
        if col not in df.columns:
            df[col] = ""

    return df

def guardar_csv(df, nombre):
    df.to_csv(nombre, index=False)

# =====================================
# CARGAR DATOS
# =====================================

if "inventario" not in st.session_state:
    st.session_state.inventario = cargar_csv(ARCHIVO_INVENTARIO, inventario_cols)

if "movimientos" not in st.session_state:
    st.session_state.movimientos = cargar_csv(ARCHIVO_MOVIMIENTOS, movimientos_cols)

# =====================================
# TITULO
# =====================================

st.title("Sistema de Inventario Reinstalacion")

# =====================================
# AGREGAR MATERIAL
# =====================================

st.subheader("Agregar Material")

with st.form("form_agregar"):
    col1, col2 = st.columns(2)

    with col1:
        nombre = st.text_input("Nombre del material")
        categoria = st.selectbox("Categoria",
                                 ["Cableado", "Equipos", "Herramientas", "Conectores", "Otros"])
        cantidad = st.number_input("Cantidad", min_value=1, step=1)

    with col2:
        ubicacion = st.text_input("Ubicacion")
        estado = st.selectbox("Estado", ["Nuevo", "Usado", "Danado"])
        proveedor = st.text_input("Quien entrego el material")

    submitted = st.form_submit_button("Agregar")

    if submitted:
        if nombre.strip() == "":
            st.warning("Debe ingresar un nombre")
        else:
            nuevo_id = 1
            if not st.session_state.inventario.empty:
                nuevo_id = int(st.session_state.inventario["ID"].max()) + 1

            fecha_actual = datetime.now(ZONA).strftime("%Y-%m-%d %H:%M")

            nuevo = {
                "ID": nuevo_id,
                "Nombre": nombre,
                "Categoria": categoria,
                "Cantidad": cantidad,
                "Ubicacion": ubicacion,
                "Estado": estado,
                "Fecha_Ingreso": fecha_actual,
                "Proveedor": proveedor
            }

            st.session_state.inventario = pd.concat(
                [st.session_state.inventario, pd.DataFrame([nuevo])],
                ignore_index=True
            )

            movimiento = {
                "Fecha": fecha_actual,
                "Tipo": "Entrada",
                "Material": nombre,
                "Cantidad": cantidad,
                "Responsable": proveedor
            }

            st.session_state.movimientos = pd.concat(
                [st.session_state.movimientos, pd.DataFrame([movimiento])],
                ignore_index=True
            )

            guardar_csv(st.session_state.inventario, ARCHIVO_INVENTARIO)
            guardar_csv(st.session_state.movimientos, ARCHIVO_MOVIMIENTOS)

            st.success("Material agregado correctamente")

# =====================================
# REGISTRAR SALIDA
# =====================================

st.subheader("Registrar Salida de Material")

if not st.session_state.inventario.empty:

    material_seleccionado = st.selectbox(
        "Seleccionar material",
        st.session_state.inventario["Nombre"].unique()
    )

    cantidad_salida = st.number_input("Cantidad a retirar", min_value=1, step=1)
    responsable = st.text_input("A quien se entrego")

    if st.button("Registrar Salida"):

        if responsable.strip() == "":
            st.warning("Debe indicar a quien se entrego")
        else:
            fila = st.session_state.inventario[
                st.session_state.inventario["Nombre"] == material_seleccionado
            ]

            if not fila.empty:

                idx = fila.index[0]
                stock_actual = st.session_state.inventario.loc[idx, "Cantidad"]

                if cantidad_salida <= stock_actual:

                    st.session_state.inventario.loc[idx, "Cantidad"] -= cantidad_salida

                    fecha_actual = datetime.now(ZONA).strftime("%Y-%m-%d %H:%M")

                    movimiento = {
                        "Fecha": fecha_actual,
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

# =====================================
# INVENTARIO ACTUAL
# =====================================

st.subheader("Inventario Actual")
st.dataframe(st.session_state.inventario, use_container_width=True)

# =====================================
# HISTORIAL
# =====================================

st.subheader("Historial de Movimientos")
st.dataframe(st.session_state.movimientos, use_container_width=True)

# =====================================
# EXPORTAR
# =====================================

st.subheader("Exportar Datos")

col1, col2 = st.columns(2)

with col1:
    csv_inventario = st.session_state.inventario.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Descargar Inventario",
        data=csv_inventario,
        file_name="inventario_actual.csv",
        mime="text/csv"
    )

with col2:
    salidas = st.session_state.movimientos[
        st.session_state.movimientos["Tipo"] == "Salida"
    ]

    csv_salidas = salidas.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Descargar Historial Salidas",
        data=csv_salidas,
        file_name="historial_salidas.csv",
        mime="text/csv"
    )

# =====================================
# RESETEAR INVENTARIO
# =====================================

st.subheader("Resetear Inventario Mensual")

confirmar = st.checkbox("Confirmo reiniciar el inventario completamente")

if confirmar:
    if st.button("Resetear Inventario"):

        st.session_state.inventario = pd.DataFrame(columns=inventario_cols)
        st.session_state.movimientos = pd.DataFrame(columns=movimientos_cols)

        if os.path.exists(ARCHIVO_INVENTARIO):
            os.remove(ARCHIVO_INVENTARIO)

        if os.path.exists(ARCHIVO_MOVIMIENTOS):
            os.remove(ARCHIVO_MOVIMIENTOS)

        st.success("Inventario reiniciado correctamente")
