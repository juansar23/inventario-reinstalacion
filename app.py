import streamlit as st
import pandas as pd
import io
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Control de Inventario UT", layout="wide")

# ==================================================
# 1. PERSISTENCIA DE DATOS (Session State)
# ==================================================
if 'db_entradas' not in st.session_state:
    st.session_state.db_entradas = pd.DataFrame(columns=["Fecha", "Material", "Cantidad", "Origen/Proveedor"])

if 'db_salidas' not in st.session_state:
    st.session_state.db_salidas = pd.DataFrame(columns=["Fecha", "Material", "Cantidad", "ID/Serie", "Entregado A", "Responsable"])

if 'lista_materiales' not in st.session_state:
    st.session_state.lista_materiales = []

# ==================================================
# 2. FUNCIONES DE LÓGICA
# ==================================================
def calcular_inventario():
    if not st.session_state.lista_materiales:
        return pd.DataFrame()
    
    ent = st.session_state.db_entradas.groupby("Material")["Cantidad"].sum().reset_index()
    sal = st.session_state.db_salidas.groupby("Material")["Cantidad"].sum().reset_index()
    
    df_inv = pd.DataFrame({"Material": st.session_state.lista_materiales})
    df_inv = pd.merge(df_inv, ent, on="Material", how="left").fillna(0)
    df_inv.rename(columns={"Cantidad": "Ingresos Total"}, inplace=True)
    
    df_inv = pd.merge(df_inv, sal, on="Material", how="left").fillna(0)
    df_inv.rename(columns={"Cantidad": "Salidas Total"}, inplace=True)
    
    df_inv["Stock Disponible"] = df_inv["Ingresos Total"] - df_inv["Salidas Total"]
    return df_inv

# Función auxiliar para convertir dataframe a CSV
def convertir_a_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# ==================================================
# 3. INTERFAZ DE USUARIO
# ==================================================
st.title("📊 Gestión de Inventario UT - Control Manual")

with st.sidebar:
    st.header("⚙️ Configuración")
    nuevo_nombre = st.text_input("Nombre del material", placeholder="Ej: Módem, Cable Drop...")
    
    if st.button("➕ Añadir al Catálogo"):
        if nuevo_nombre:
            nombre_limpio = nuevo_nombre.strip().upper()
            if nombre_limpio not in st.session_state.lista_materiales:
                st.session_state.lista_materiales.append(nombre_limpio)
                st.success(f"Registrado: {nombre_limpio}")
                st.rerun()
            else:
                st.warning("Este material ya está en tu lista.")

    st.divider()
    if st.button("🚨 Reiniciar Todo"):
        st.session_state.db_entradas = pd.DataFrame(columns=["Fecha", "Material", "Cantidad", "Origen/Proveedor"])
        st.session_state.db_salidas = pd.DataFrame(columns=["Fecha", "Material", "Cantidad", "ID/Serie", "Entregado A", "Responsable"])
        st.session_state.lista_materiales = []
        st.rerun()

tab_resumen, tab_ingreso, tab_salida = st.tabs(["📋 Mi Stock Actual", "📥 Cargar Inventario", "📤 Registrar Salida"])

# TAB 1: RESUMEN DE STOCK + BOTÓN DESCARGA INVENTARIO
with tab_resumen:
    st.subheader("Estado de mi Inventario")
    df_stock = calcular_inventario()
    
    if df_stock.empty:
        st.info("Tu catálogo está vacío.")
    else:
        st.dataframe(df_stock, use_container_width=True, hide_index=True)
        
        # Botón de descarga para el Inventario Actual
        csv_inventario = convertir_a_csv(df_stock)
        st.download_button(
            label="📥 Descargar Inventario Actual (CSV)",
            data=csv_inventario,
            file_name=f"inventario_actual_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

# TAB 2: ENTRADA DE MATERIAL
with tab_ingreso:
    if not st.session_state.lista_materiales:
        st.warning("⚠️ Primero crea los materiales en la barra lateral.")
    else:
        st.subheader("Cargar Stock")
        with st.form("form_ingreso", clear_on_submit=True):
            col1, col2 = st.columns(2)
            mat_e = col1.selectbox("Material", st.session_state.lista_materiales)
            cant_e = col1.number_input("Cantidad", min_value=1, step=1)
            orig_e = col2.text_input("Origen/Nota")
            fecha_e = col2.date_input("Fecha", datetime.now())
            
            if st.form_submit_button("📥 Cargar"):
                nueva_fila = pd.DataFrame([[fecha_e, mat_e, cant_e, orig_e]], columns=st.session_state.db_entradas.columns)
                st.session_state.db_entradas = pd.concat([st.session_state.db_entradas, nueva_fila], ignore_index=True)
                st.success("Stock cargado.")
                st.rerun()

# TAB 3: REGISTRO DE SALIDA + BOTÓN DESCARGA SALIDAS
with tab_salida:
    df_para_validar = calcular_inventario()
    
    if df_para_validar.empty:
        st.warning("No hay stock.")
    else:
        st.subheader("Entrega de Material")
        with st.form("form_salida", clear_on_submit=True):
            c1, c2 = st.columns(2)
            mat_s = c1.selectbox("Material", st.session_state.lista_materiales)
            stock_disp = df_para_validar.loc[df_para_validar["Material"] == mat_s, "Stock Disponible"].values[0]
            c1.info(f"Disponible: {int(stock_disp)}")
            
            cant_s = c1.number_input("Cantidad", min_value=1, step=1)
            serie_s = c1.text_input("ID/Serie")
            
            receptor = c2.text_input("Recibe (Técnico)")
            resp_s = c2.text_input("Entrega (Tu nombre)")
            fecha_s = c2.date_input("Fecha", datetime.now())
            
            if st.form_submit_button("📤 Registrar Salida"):
                if cant_s > stock_disp:
                    st.error("Stock insuficiente.")
                elif not receptor:
                    st.error("Indica quién recibe.")
                else:
                    nueva_sal = pd.DataFrame([[fecha_s, mat_s, cant_s, serie_s, receptor, resp_s]], columns=st.session_state.db_salidas.columns)
                    st.session_state.db_salidas = pd.concat([st.session_state.db_salidas, nueva_sal], ignore_index=True)
                    st.success("Salida registrada.")
                    st.rerun()

    st.divider()
    if not st.session_state.db_salidas.empty:
        st.subheader("📜 Historial de Salidas")
        st.dataframe(st.session_state.db_salidas, use_container_width=True, hide_index=True)
        
        # Botón de descarga para las Salidas
        csv_salidas = convertir_a_csv(st.session_state.db_salidas)
        st.download_button(
            label="📥 Descargar Reporte de Salidas (CSV)",
            data=csv_salidas,
            file_name=f"reporte_salidas_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
