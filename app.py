import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os

# =====================================================
# CONFIGURACION
# =====================================================

st.set_page_config(page_title="Sistema Inventario Reinstalacion", layout="wide")

ARCHIVO_INVENTARIO = "inventario.csv"
ARCHIVO_MOVIMIENTOS = "movimientos.csv"

ZONA = pytz.timezone("America/Bogota")

inventario_cols = [
    "ID", "Nombre", "Categoria", "Cantidad",
    "Precio_Unitario", "Valor_Total",
    "Ubicacion", "Estado", "Fecha_Ingreso", "Proveedor"
]

movimientos_cols = [
    "Fecha", "Tipo", "Material", "Cantidad", "Responsable"
]

# =====================================================
# FUNCIONES
# =====================================================

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


# =====================================================
# CARGA INICIAL
# =====================================================

if "inventario" not in st.session_state:
    st.session_state.inventario = cargar_csv(ARCHIVO_INVENTARIO, inventario_cols)

if "movimientos" not in st.session_state:
    st.session_state.movimientos = cargar_csv(ARCHIVO_MOVIMIENTOS, movimientos_cols)


# =====================================================
# TITULO
# =====================================================

st.title("Sistema de Inventario Reinstalacion")


# =====================================================
# AGREGAR MATERIAL
# =====================================================

st.subheader("Agregar Material")

with st.form("form_agregar"):

    col1, col2 = st.columns(2)

    with col1:
        nombre = st.text_input("Nombre del material")
        categoria = st.selectbox("Categoria",
                                 ["Cableado", "Equipos", "Herramientas", "Conectores", "Otros"])
        cantidad = st.number_input("Cantidad", min_value=1, step=1)
        precio = st.number_input("Precio unitario", min_value=0.0, step=0.01)

    with col2:
        ubicacion = st.text_input("Ubicacion")
        estado = st.selectbox("Estado", ["Nuevo", "Usado", "Danado"])
        proveedor = st.text_input("Proveedor")

    submitted = st.form_submit_button("Registrar Entrada")

    if submitted:

        if nombre.strip() == "":
            st.warning("Debe ingresar un nombre")
        else:

            fecha_actual = datetime.now(ZONA).strftime("%Y-%m-%d %H:%M")

            existe = st.session_state.inventario[
                st.session_state.inventario["Nombre"].str.lower() == nombre.lower()
            ]

            if not existe.empty:
                idx = existe.index[0]
                st.session_state.inventario.loc[idx, "Cantidad"] += cantidad
                st.session_state.inventario.loc[idx, "Precio_Unitario"] = precio
            else:
                nuevo_id = 1
                if not st.session_state.inventario.empty:
                    nuevo_id = int(st.session_state.inventario["ID"].max()) + 1

                nuevo = {
                    "ID": nuevo_id,
                    "Nombre": nombre,
                    "Categoria": categoria,
                    "Cantidad": cantidad,
                    "Precio_Unitario": precio,
                    "Valor_Total": 0,
                    "Ubicacion": ubicacion,
                    "Estado": estado,
                    "Fecha_Ingreso": fecha_actual,
                    "Proveedor": proveedor
                }

                st.session_state.inventario = pd.concat(
                    [st.session_state.inventario, pd.DataFrame([nuevo])],
                    ignore_index=True
                )

            # Recalcular valor total
            st.session_state.inventario["Valor_Total"] = (
                st.session_state.inventario["Cantidad"].astype(float) *
                st.session_state.inventario["Precio_Unitario"].astype(float)
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

            st.success("Entrada registrada correctamente")


# =====================================================
# REGISTRAR SALIDA
# =====================================================

st.subheader("Registrar Salida")

if not st.session_state.inventario.empty:

    material = st.selectbox(
        "Seleccionar material",
        st.session_state.inventario["Nombre"]
    )

    cantidad_salida = st.number_input("Cantidad a retirar", min_value=1, step=1)
    responsable = st.text_input("A quien se entrego")

    if st.button("Registrar Salida"):

        fila = st.session_state.inventario[
            st.session_state.inventario["Nombre"] == material
        ]

        idx = fila.index[0]
        stock_actual = st.session_state.inventario.loc[idx, "Cantidad"]

        if cantidad_salida > stock_actual:
            st.error("No hay suficiente stock")
        else:

            st.session_state.inventario.loc[idx, "Cantidad"] -= cantidad_salida

            # Recalcular valor total
            st.session_state.inventario["Valor_Total"] = (
                st.session_state.inventario["Cantidad"].astype(float) *
                st.session_state.inventario["Precio_Unitario"].astype(float)
            )

            fecha_actual = datetime.now(ZONA).strftime("%Y-%m-%d %H:%M")

            movimiento = {
                "Fecha": fecha_actual,
                "Tipo": "Salida",
                "Material": material,
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


# =====================================================
# INVENTARIO ACTUAL
# =====================================================

st.subheader("Inventario Actual")

st.dataframe(st.session_state.inventario, use_container_width=True)

# Valor total general
valor_total_inventario = st.session_state.inventario["Valor_Total"].astype(float).sum()

st.markdown(f"## Valor Total del Inventario: ${valor_total_inventario:,.2f}")


# =====================================================
# HISTORIAL
# =====================================================

st.subheader("Historial de Movimientos")
st.dataframe(st.session_state.movimientos, use_container_width=True)
