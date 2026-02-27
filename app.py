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
    "Ubicacion", "Estado", "Fecha_Ingreso"
]

movimientos_cols = [
    "Fecha", "Tipo", "Material", "Cantidad", "Responsable"
]

# =====================================================
# FUNCIONES
# =====================================================

def cargar_csv(nombre, columnas):
    if os.path.exists(nombre):
        return pd.read_csv(nombre)
    return pd.DataFrame(columns=columnas)

def guardar_csv(df, nombre):
    df.to_csv(nombre, index=False)

def fecha_actual():
    return datetime.now(ZONA).strftime("%Y-%m-%d %H:%M")

# =====================================================
# CARGA INICIAL
# =====================================================

if "inventario" not in st.session_state:
    st.session_state.inventario = cargar_csv(ARCHIVO_INVENTARIO, inventario_cols)

if "movimientos" not in st.session_state:
    st.session_state.movimientos = cargar_csv(ARCHIVO_MOVIMIENTOS, movimientos_cols)

# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.title("Menu")

opcion = st.sidebar.selectbox(
    "Seleccionar opcion",
    [
        "Inventario Bodega",
        "Asignar a Operario",
        "Ver Inventario Completo",
        "Herramientas",
        "Exportar Datos"
    ]
)

# =====================================================
# 1️⃣ INVENTARIO INICIAL (BODEGA)
# =====================================================

if opcion == "Inventario Bodega":

    st.title("Cargar Inventario Inicial - Bodega")

    with st.form("form_bodega"):

        nombre = st.text_input("Nombre del material")
        categoria = st.selectbox("Categoria",
                                 ["Cableado", "Equipos", "Herramientas", "Conectores", "Otros"])
        cantidad = st.number_input("Cantidad", min_value=1, step=1)
        precio = st.number_input("Precio unitario", min_value=0.0, step=0.01)

        submitted = st.form_submit_button("Agregar a Bodega")

        if submitted:

            fecha = fecha_actual()

            nuevo_id = 1
            if not st.session_state.inventario.empty:
                nuevo_id = int(st.session_state.inventario["ID"].max()) + 1

            nuevo = {
                "ID": nuevo_id,
                "Nombre": nombre,
                "Categoria": categoria,
                "Cantidad": cantidad,
                "Precio_Unitario": precio,
                "Valor_Total": cantidad * precio,
                "Ubicacion": "Bodega",
                "Estado": "Disponible",
                "Fecha_Ingreso": fecha
            }

            st.session_state.inventario = pd.concat(
                [st.session_state.inventario, pd.DataFrame([nuevo])],
                ignore_index=True
            )

            guardar_csv(st.session_state.inventario, ARCHIVO_INVENTARIO)

            st.success("Material agregado a Bodega")

# =====================================================
# 2️⃣ ASIGNAR A OPERARIO
# =====================================================

elif opcion == "Asignar a Operario":

    st.title("Asignar Material a Operario")

    inventario_bodega = st.session_state.inventario[
        st.session_state.inventario["Ubicacion"] == "Bodega"
    ]

    if inventario_bodega.empty:
        st.warning("No hay stock en bodega")
    else:

        material = st.selectbox("Seleccionar material", inventario_bodega["Nombre"])
        cantidad = st.number_input("Cantidad a asignar", min_value=1, step=1)
        operario = st.text_input("Nombre del operario")

        if st.button("Asignar"):

            fila = inventario_bodega[
                inventario_bodega["Nombre"] == material
            ]

            idx = fila.index[0]
            stock = st.session_state.inventario.loc[idx, "Cantidad"]

            if cantidad > stock:
                st.error("Stock insuficiente en bodega")
            else:

                # Descontar de bodega
                st.session_state.inventario.loc[idx, "Cantidad"] -= cantidad
                precio_unit = st.session_state.inventario.loc[idx, "Precio_Unitario"]

                st.session_state.inventario.loc[idx, "Valor_Total"] = (
                    st.session_state.inventario.loc[idx, "Cantidad"] * precio_unit
                )

                # Agregar registro al operario
                nuevo_id = int(st.session_state.inventario["ID"].max()) + 1

                nuevo = {
                    "ID": nuevo_id,
                    "Nombre": material,
                    "Categoria": fila["Categoria"].values[0],
                    "Cantidad": cantidad,
                    "Precio_Unitario": precio_unit,
                    "Valor_Total": cantidad * precio_unit,
                    "Ubicacion": operario,
                    "Estado": "Asignado",
                    "Fecha_Ingreso": fecha_actual()
                }

                st.session_state.inventario = pd.concat(
                    [st.session_state.inventario, pd.DataFrame([nuevo])],
                    ignore_index=True
                )

                guardar_csv(st.session_state.inventario, ARCHIVO_INVENTARIO)

                st.success("Material asignado correctamente")

# =====================================================
# 3️⃣ VER INVENTARIO COMPLETO
# =====================================================

elif opcion == "Ver Inventario Completo":

    st.title("Inventario General")

    st.dataframe(st.session_state.inventario, use_container_width=True)

    valor_total = st.session_state.inventario["Valor_Total"].astype(float).sum()

    st.markdown(f"### Valor Total General: ${valor_total:,.2f}")

# =====================================================
# 4️⃣ HERRAMIENTAS
# =====================================================

elif opcion == "Herramientas":

    st.title("Inventario de Herramientas")

    herramientas = st.session_state.inventario[
        st.session_state.inventario["Categoria"] == "Herramientas"
    ]

    st.dataframe(herramientas, use_container_width=True)

# =====================================================
# 5️⃣ EXPORTAR
# =====================================================

elif opcion == "Exportar Datos":

    st.title("Exportar Datos")

    csv_inv = st.session_state.inventario.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Descargar Inventario Completo",
        data=csv_inv,
        file_name="inventario_completo.csv",
        mime="text/csv"
    )
