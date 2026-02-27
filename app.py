import streamlit as st
import pandas as pd
import io
from datetime import datetime

st.set_page_config(page_title="Control de Inventario Online", layout="wide")

# ==================================================
# 1. BASE DE DATOS VIRTUAL (Session State)
# ==================================================
# Inicializamos las tablas si no existen en la sesión
if 'db_entradas' not in st.session_state:
    st.session_state.db_entradas = pd.DataFrame(columns=["Fecha", "Material", "Cantidad", "Proveedor"])

if 'db_salidas' not in st.session_state:
    st.session_state.db_salidas = pd.DataFrame(columns=["Fecha", "Material", "Cantidad", "Entregado A", "Responsable"])

# Lista de materiales predefinidos (puedes editarlos aquí)
if 'lista_materiales' not in st.session_state:
    st.session_state.lista_materiales = ["Cable UTP", "Módem", "Router", "Conectores RJ45", "Splitter"]

# ==================================================
# 2. LÓGICA DE CÁLCULO DE STOCK
# ==================================================
def obtener_stock_actual():
    # Sumar todas las entradas por material
    entradas = st.session_state.db_entradas.groupby("Material")["Cantidad"].sum().reset_index()
    # Sumar todas las salidas por material
    salidas = st.session_state.db_salidas.groupby("Material")["Cantidad"].sum().reset_index()
    
    # Crear tabla de inventario
    df_inventario = pd.DataFrame({"Material": st.session_state.lista_materiales})
    df_inventario = pd.merge(df_inventario, entradas, on="Material", how="left").fillna(0)
    df_inventario.rename(columns={"Cantidad": "Total Entradas"}, inplace=True)
    
    df_inventario = pd.merge(df_inventario, salidas, on="Material", how="left").fillna(0)
    df_inventario.rename(columns={"Cantidad": "Total Salidas"}, inplace=True)
    
    df_inventario["Stock Disponible"] = df_inventario["Total Entradas"] - df_inventario["Total Salidas"]
    return df_inventario

# ==================================================
# 3. INTERFAZ DE USUARIO (TABS)
# ==================================================
st.title("📦 Sistema de Inventario en Línea")

tab_stock, tab_entrada, tab_salida, tab_admin = st.tabs([
    "📊 Stock Actual", 
    "📥 Registrar Entrada", 
    "📤 Registrar Salida",
    "⚙️ Configuración"
])

# --- TAB: STOCK ACTUAL ---
with tab_stock:
    st.subheader("Estado del Inventario")
    df_stock = obtener_stock_actual()
    
    # Métricas clave
    c1, c2, c3 = st.columns(3)
    c1.metric("Items en Catálogo", len(st.session_state.lista_materiales))
    c2.metric("Total Unidades Stock", int(df_stock["Stock Disponible"].sum()))
    c3.metric("Último Movimiento", datetime.now().strftime("%H:%M:%S"))
    
    st.dataframe(df_stock, use_container_width=True)

# --- TAB: REGISTRAR ENTRADA (Carga de inventario) ---
with tab_entrada:
    st.subheader("Añadir Stock al Sistema")
    with st.form("form_entrada", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            m_entrada = st.selectbox("Material que ingresa", st.session_state.lista_materiales)
            c_entrada = st.number_input("Cantidad", min_value=1, step=1)
        with col2:
            prov = st.text_input("Proveedor / Origen", value="Bodega Central")
            f_entrada = st.date_input("Fecha de Ingreso", datetime.now())
        
        btn_ent = st.form_submit_button("📥 Registrar Ingreso")
        
        if btn_ent:
            nueva_ent = pd.DataFrame([[f_entrada, m_entrada, c_entrada, prov]], 
                                     columns=["Fecha", "Material", "Cantidad", "Proveedor"])
            st.session_state.db_entradas = pd.concat([st.session_state.db_entradas, nueva_ent], ignore_index=True)
            st.success(f"Se cargaron {c_entrada} unidades de {m_entrada}")
            st.rerun()

# --- TAB: REGISTRAR SALIDA (Entrega a técnicos) ---
with tab_salida:
    st.subheader("Entrega de Material")
    df_stock_validar = obtener_stock_actual()
    
    with st.form("form_salida", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            m_salida = st.selectbox("Material a entregar", st.session_state.lista_materiales)
            
            # Validar stock disponible
            disp = df_stock_validar.loc[df_stock_validar["Material"] == m_salida, "Stock Disponible"].values[0]
            st.info(f"Disponible actualmente: {int(disp)} unidades")
            
            c_salida = st.number_input("Cantidad a entregar", min_value=1, step=1)
        
        with col2:
            receptor = st.text_input("Nombre de quien recibe (Técnico/Cliente)")
            responsable = st.text_input("Persona que entrega")
            f_salida = st.date_input("Fecha de Salida", datetime.now())
        
        btn_sal = st.form_submit_button("📤 Confirmar Entrega")
        
        if btn_sal:
            if c_salida > disp:
                st.error(f"❌ Error: Stock insuficiente. Solo hay {int(disp)} disponibles.")
            elif not receptor:
                st.warning("⚠️ Debes indicar quién recibe el material.")
            else:
                nueva_sal = pd.DataFrame([[f_salida, m_salida, c_salida, receptor, responsable]], 
                                         columns=["Fecha", "Material", "Cantidad", "Entregado A", "Responsable"])
                st.session_state.db_salidas = pd.concat([st.session_state.db_salidas, nueva_sal], ignore_index=True)
                st.success(f"Salida registrada: {c_salida} {m_salida} entregados a {receptor}")
                st.rerun()

# --- TAB: CONFIGURACIÓN (Añadir nuevos tipos de materiales) ---
with tab_admin:
    st.subheader("Administrar Catálogo")
    nuevo_item = st.text_input("Nombre del nuevo material (ej: Cinta aislante)")
    if st.button("➕ Añadir al Catálogo"):
        if nuevo_item and nuevo_item not in st.session_state.lista_materiales:
            st.session_state.lista_materiales.append(nuevo_item)
            st.success(f"'{nuevo_item}' añadido correctamente.")
            st.rerun()
    
    st.divider()
    if st.button("🗑️ Limpiar Todo el Inventario (Reset)"):
        st.session_state.db_entradas = pd.DataFrame(columns=["Fecha", "Material", "Cantidad", "Proveedor"])
        st.session_state.db_salidas = pd.DataFrame(columns=["Fecha", "Material", "Cantidad", "Entregado A", "Responsable"])
        st.rerun()
