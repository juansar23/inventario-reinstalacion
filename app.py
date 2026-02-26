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
    "ID", "Mes", "Nombre", "Categoria", "Cantidad",
    "Precio_Unitario", "Valor_Total",
    "Ubicacion", "Estado", "Fecha_Ingreso", "Proveedor"
]

movimientos_cols = [
    "Fecha", "Mes", "Tipo", "Material", "Cantidad", "Responsable"
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


def mes_actual():
    return datetime.now(ZONA).strftime("%Y-%m")

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

mes_act = mes_actual()

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

        fecha_actual = datetime.now(ZONA).strftime("%Y-%m-%d %H:%M")

        nuevo_id = 1
        if not st.session_state.inventario.empty:
            nuevo_id = int(st.session_state.inventario["ID"].max()) + 1

        nuevo = {
            "ID": nuevo_id,
            "Mes": mes_act,
            "Nombre": nombre,
            "Categoria": categoria,
            "Cantidad": cantidad,
            "Precio_Unitario": precio,
            "Valor_Total": cantidad * precio,
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
            "Mes": mes_act,
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
# PESTAÑAS POR MES
# =====================================================

meses = sorted(st.session_state.inventario["Mes"].dropna().unique())

if len(meses) == 0:
    st.info("No hay datos registrados aun")
else:

    tabs = st.tabs(meses)

    for i, mes in enumerate(meses):

        with tabs[i]:

            st.subheader(f"Inventario del mes {mes}")

            inv_mes = st.session_state.inventario[
                st.session_state.inventario["Mes"] == mes
            ]

            st.dataframe(inv_mes, use_container_width=True)

            valor_total = inv_mes["Valor_Total"].astype(float).sum()
            st.markdown(f"### Valor Total Mes {mes}: ${valor_total:,.2f}")

            st.subheader("Movimientos del mes")

            mov_mes = st.session_state.movimientos[
                st.session_state.movimientos["Mes"] == mes
            ]

            st.dataframe(mov_mes, use_container_width=True)

            col1, col2 = st.columns(2)

            with col1:
                csv_inv = inv_mes.to_csv(index=False).encode("utf-8")
                st.download_button(
                    f"Descargar Inventario {mes}",
                    data=csv_inv,
                    file_name=f"inventario_{mes}.csv",
                    mime="text/csv"
                )

            with col2:
                csv_mov = mov_mes.to_csv(index=False).encode("utf-8")
                st.download_button(
                    f"Descargar Movimientos {mes}",
                    data=csv_mov,
                    file_name=f"movimientos_{mes}.csv",
                    mime="text/csv"
                )
