import streamlit as st
import pandas as pd
import io
from datetime import datetime

st.set_page_config(page_title="Control de Salidas UT", layout="wide")

# ==================================================
# 1. BASE DE DATOS (Persistencia)
# ==================================================
if 'inventario_base' not in st.session_state:
    # Columnas: Material, Stock Inicial
    st.session_state.inventario_base = pd.DataFrame(columns=["Material", "Cantidad_Inicial"])

if 'db_salidas' not in st.session_state:
    st.session_state.db_salidas = pd.DataFrame(columns=["Fecha", "Material", "Cantidad", "Entregado A", "Responsable"])

# ==================================================
# 2. LÓGICA DE CÁLCULO
# ==================================================
def calcular_stock_final():
    if st.session_state.inventario_base.empty:
        return pd.DataFrame(columns=["Material", "Disponible"])
    
    df_resumen = st.session_state.inventario_base.copy()
    
    # Restar salidas
    if not st.session_state.db_salidas.empty:
        salidas_agrupadas = st.session_state.db_salidas.groupby("Material")["Cantidad"].sum()
        df_resumen = df_resumen.set_index("Material")
        df_resumen["Cantidad_Salidas"] = salidas_agrupadas
        df_resumen["Cantidad_Salidas"] = df_resumen["Cantidad_Salidas"].fillna(0)
        df_resumen["Disponible"] = df_resumen["Cantidad_Inicial"] - df_resumen["Cantidad_Salidas"]
        df_resumen = df_resumen.reset_index()
    else:
        df_resumen["Disponible"] = df_resumen["Cantidad_Inicial"]
        
    return df_resumen

# ==================================================
# 3. INTERFAZ
# ==================================================
st.title("📦 Control Directo de Salidas UT")

col_a, col_b = st.columns([1, 2])

# PANEL IZQUIERDO: CONFIGURAR MATERIALES
with col_a:
    st.subheader("⚙️ Catálogo de Materiales")
    with st.form("nuevo_mat"):
        nombre_mat = st.text_input("Nombre del Material")
        cant_inicial = st.number_input("Cantidad Inicial", min_value=0, step=1)
        if st.form_submit_button("Agregar al Inventario"):
            if nombre_mat:
                nueva_fila = pd.DataFrame([[nombre_mat.upper(), cant_inicial]], columns=["Material", "Cantidad_Inicial"])
                st.session_state.inventario_base = pd.concat([st.session_state.inventario_base, nueva_fila], ignore_index=True)
                st.rerun()

# PANEL DERECHO: REGISTRAR SALIDA
with col_b:
    st.subheader("📤 Registrar Salida")
    df_stock = calcular_stock_final()
    
    if df_stock.empty:
        st.info("Agrega materiales en el panel izquierdo para empezar.")
    else:
        with st.form("form_salida", clear_on_submit=True):
            mat_sel = st.selectbox("Seleccionar Material", df_stock["Material"].tolist())
            disp = df_stock.loc[df_stock["Material"] == mat_sel, "Disponible"].values[0]
            st.write(f"Stock disponible: **{int(disp)}**")
            
            cant_salida = st.number_input("Cantidad a entregar", min_value=1, max_value=int(disp), step=1)
            receptor = st.text_input("¿Quién recibe el material?")
            responsable = st.text_input("Responsable de la entrega")
            
            if st.form_submit_button("Registrar Entrega"):
                nueva_sal = pd.DataFrame([[datetime.now().date(), mat_sel, cant_salida, receptor, responsable]], 
                                         columns=st.session_state.db_salidas.columns)
                st.session_state.db_salidas = pd.concat([st.session_state.db_salidas, nueva_sal], ignore_index=True)
                st.success(f"¡Salida de {cant_salida} {mat_sel} registrada!")
                st.rerun()

# TABLA DE STOCK
st.divider()
st.subheader("📊 Inventario Actualizado")
st.dataframe(df_stock, use_container_width=True)

# HISTORIAL
if st.checkbox("Ver Historial de Salidas"):
    st.table(st.session_state.db_salidas)
