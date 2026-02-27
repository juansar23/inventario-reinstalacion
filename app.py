import streamlit as st
import pandas as pd
import io
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Gestión de Inventario UT - Carga Masiva", layout="wide")

# ==================================================
# 1. PERSISTENCIA DE DATOS (Session State)
# ==================================================
if 'db_materiales_operarios' not in st.session_state:
    st.session_state.db_materiales_operarios = pd.DataFrame(
        columns=["Fecha", "Tipo_Movimiento", "Operario", "Material", "Cantidad", "Referencia"]
    )

if 'db_materiales_bodega' not in st.session_state:
    st.session_state.db_materiales_bodega = pd.DataFrame(columns=["Fecha", "Material", "Cantidad", "Origen"])

if 'db_herramientas_operarios' not in st.session_state:
    st.session_state.db_herramientas_operarios = pd.DataFrame(
        columns=["Fecha", "Operario", "Herramienta", "Cantidad", "ID_Serie"]
    )

if 'cat_materiales' not in st.session_state: st.session_state.cat_materiales = []
if 'cat_herramientas' not in st.session_state: st.session_state.cat_herramientas = []
if 'cat_operarios' not in st.session_state: st.session_state.cat_operarios = []

# ==================================================
# 2. FUNCIONES DE LÓGICA
# ==================================================
def obtener_stock_real_operarios():
    if st.session_state.db_materiales_operarios.empty:
        return pd.DataFrame(columns=["Operario", "Material", "Stock Actual"])
    df = st.session_state.db_materiales_operarios.copy()
    df['Cantidad_Neta'] = df.apply(lambda x: -x['Cantidad'] if x['Tipo_Movimiento'] == "ACTA" else x['Cantidad'], axis=1)
    resumen = df.groupby(["Operario", "Material"])["Cantidad_Neta"].sum().reset_index()
    resumen.rename(columns={"Cantidad_Neta": "Stock Actual"}, inplace=True)
    return resumen

def obtener_stock_bodega():
    if st.session_state.db_materiales_bodega.empty:
        return pd.DataFrame(columns=["Material", "Stock Bodega"])
    resumen = st.session_state.db_materiales_bodega.groupby("Material")["Cantidad"].sum().reset_index()
    resumen.rename(columns={"Cantidad": "Stock Bodega"}, inplace=True)
    return resumen

def convertir_a_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# ==================================================
# 3. BARRA LATERAL (CONFIGURACIÓN)
# ==================================================
with st.sidebar:
    st.header("⚙️ Configuración")
    
    with st.expander("👥 Operarios"):
        op_input = st.text_input("Nombre Operario")
        if st.button("Añadir Operario") and op_input:
            nombre = op_input.strip().upper()
            if nombre not in st.session_state.cat_operarios:
                st.session_state.cat_operarios.append(nombre)
                st.rerun()

    with st.expander("📦 Materiales"):
        mat_input = st.text_input("Nombre Material")
        if st.button("Añadir Material") and mat_input:
            nombre = mat_input.strip().upper()
            if nombre not in st.session_state.cat_materiales:
                st.session_state.cat_materiales.append(nombre)
                st.rerun()

    st.divider()
    if st.button("🚨 Reiniciar Sistema"):
        st.session_state.clear()
        st.rerun()

# ==================================================
# 4. CUERPO PRINCIPAL
# ==================================================
st.title("🛡️ Sistema de Gestión de Inventario")

tab_resumen, tab_inicial_op, tab_actas, tab_bodega, tab_herr = st.tabs([
    "📊 Resumen", "📥 Inicial Operarios", "📄 Actas", "🏢 Bodega", "🛠️ Herramientas"
])

# --- TAB 1: RESUMEN ---
with tab_resumen:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Stock en Bodega")
        st.dataframe(obtener_stock_bodega(), use_container_width=True, hide_index=True)
    with col2:
        st.subheader("Stock en Calle (Operarios)")
        st.dataframe(obtener_stock_real_operarios(), use_container_width=True, hide_index=True)

# --- TAB 2: CARGA INICIAL OPERARIOS ---
with tab_inicial_op:
    st.subheader("Carga Inicial Materiales a Operarios (Excel)")
    uploaded_file_mat = st.file_uploader("Excel: Operario, Material, Cantidad", type=["xlsx"], key="up_op")
    if uploaded_file_mat:
        if st.button("Cargar Materiales a Operarios"):
            df_ex = pd.read_excel(uploaded_file_mat)
            for _, row in df_ex.iterrows():
                m, o, c = str(row['Material']).upper(), str(row['Operario']).upper(), row['Cantidad']
                if m not in st.session_state.cat_materiales: st.session_state.cat_materiales.append(m)
                if o not in st.session_state.cat_operarios: st.session_state.cat_operarios.append(o)
                nueva = pd.DataFrame([[datetime.now().date(), "INICIAL", o, m, c, "Carga Excel"]], columns=st.session_state.db_materiales_operarios.columns)
                st.session_state.db_materiales_operarios = pd.concat([st.session_state.db_materiales_operarios, nueva], ignore_index=True)
            st.success("Carga de operarios lista")
            st.rerun()

# --- TAB 3: ACTAS ---
with tab_actas:
    st.subheader("Registrar Consumo por Acta")
    # Lógica de resta de material (mantiene la funcionalidad previa)
    # ... (Código de actas aquí)

# --- TAB 4: BODEGA (CON SU PROPIO BOTÓN EXCEL) ---
with tab_bodega:
    st.subheader("Gestión de Bodega Central")
    
    # NUEVA SECCIÓN: CARGA INICIAL BODEGA
    st.markdown("### 📥 Carga Inicial de Bodega")
    uploaded_file_bod = st.file_uploader("Subir Excel de Bodega (Columnas: Material, Cantidad)", type=["xlsx"], key="up_bod")
    
    if uploaded_file_bod:
        if st.button("🚀 Procesar Inventario Inicial Bodega"):
            try:
                df_bod = pd.read_excel(uploaded_file_bod)
                # Estandarizar
                df_bod['Material'] = df_bod['Material'].astype(str).str.strip().str.upper()
                
                for _, row in df_bod.iterrows():
                    # Añadir al catálogo si no existe
                    if row['Material'] not in st.session_state.cat_materiales:
                        st.session_state.cat_materiales.append(row['Material'])
                    
                    # Registrar en la base de bodega
                    nueva_b = pd.DataFrame([[datetime.now().date(), row['Material'], row['Cantidad'], "Inventario Inicial"]], 
                                          columns=st.session_state.db_materiales_bodega.columns)
                    st.session_state.db_materiales_bodega = pd.concat([st.session_state.db_materiales_bodega, nueva_b], ignore_index=True)
                
                st.success("¡Inventario de bodega cargado correctamente!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: Verifique que el Excel tenga las columnas 'Material' y 'Cantidad'.")

    st.divider()
    # Entregas diarias Bodega -> Operario
    st.markdown("### 📤 Entrega Diaria a Operario")
    with st.form("entrega_diaria"):
        c1, c2 = st.columns(2)
        op_dest = c1.selectbox("Operario", st.session_state.cat_operarios)
        mat_dest = c1.selectbox("Material", st.session_state.cat_materiales)
        cant_dest = c2.number_input("Cantidad", min_value=1)
        if st.form_submit_button("Confirmar Entrega"):
            # Restar de bodega y sumar a operario
            st.rerun()

# --- TAB 5: HERRAMIENTAS ---
with tab_herr:
    st.subheader("Carga Inicial de Herramientas (Excel)")
    uploaded_file_herr = st.file_uploader("Excel: Operario, Herramienta, ID_Serie", type=["xlsx"], key="up_herr")
    # ... (Lógica de herramientas aquí)
