import streamlit as st
import pandas as pd
import io
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Sistema Integrado de Inventario UT", layout="wide")

# ==================================================
# 1. PERSISTENCIA DE DATOS (Session State)
# ==================================================
# Bases de datos de Materiales
if 'db_materiales_bodega' not in st.session_state:
    st.session_state.db_materiales_bodega = pd.DataFrame(columns=["Fecha", "Material", "Cantidad", "Origen"])
if 'db_materiales_operarios' not in st.session_state:
    # Incluye Inventario Inicial y Entregas desde Bodega
    st.session_state.db_materiales_operarios = pd.DataFrame(columns=["Fecha", "Tipo_Carga", "Operario", "Material", "Cantidad", "ID_Serie"])

# Bases de datos de Herramientas
if 'db_herramientas_bodega' not in st.session_state:
    st.session_state.db_herramientas_bodega = pd.DataFrame(columns=["Fecha", "Herramienta", "Cantidad", "Estado"])
if 'db_herramientas_operarios' not in st.session_state:
    st.session_state.db_herramientas_operarios = pd.DataFrame(columns=["Fecha", "Operario", "Herramienta", "Cantidad", "ID_Serie"])

# Listas de Catálogo (Tú las llenas)
if 'cat_materiales' not in st.session_state: st.session_state.cat_materiales = []
if 'cat_herramientas' not in st.session_state: st.session_state.cat_herramientas = []
if 'cat_operarios' not in st.session_state: st.session_state.cat_operarios = []

# ==================================================
# 2. FUNCIONES DE CÁLCULO
# ==================================================
def convertir_a_csv(df):
    return df.to_csv(index=False).encode('utf-8')

def obtener_stock_operarios(tipo="MATERIAL"):
    db = st.session_state.db_materiales_operarios if tipo == "MATERIAL" else st.session_state.db_herramientas_operarios
    if db.empty: return pd.DataFrame()
    return db.groupby(["Operario", "Material" if tipo=="MATERIAL" else "Herramienta"])["Cantidad"].sum().reset_index()

# ==================================================
# 3. INTERFAZ: CONFIGURACIÓN (BARRA LATERAL)
# ==================================================
with st.sidebar:
    st.header("⚙️ Configuración Maestra")
    
    # Registro de Operarios
    st.subheader("👥 Registro de Operarios")
    nuevo_op = st.text_input("Nombre del Operario")
    if st.button("Añadir Operario") and nuevo_op:
        op_nom = nuevo_op.strip().upper()
        if op_nom not in st.session_state.cat_operarios:
            st.session_state.cat_operarios.append(op_nom)
            st.rerun()

    # Registro de Materiales
    st.subheader("📦 Catálogo de Materiales")
    nuevo_mat = st.text_input("Nombre del Material")
    if st.button("Añadir Material") and nuevo_mat:
        mat_nom = nuevo_mat.strip().upper()
        if mat_nom not in st.session_state.cat_materiales:
            st.session_state.cat_materiales.append(mat_nom)
            st.rerun()

    # Registro de Herramientas
    st.subheader("🛠️ Catálogo de Herramientas")
    nueva_herr = st.text_input("Nombre de Herramienta")
    if st.button("Añadir Herramienta") and nueva_herr:
        herr_nom = nueva_herr.strip().upper()
        if herr_nom not in st.session_state.cat_herramientas:
            st.session_state.cat_herramientas.append(herr_nom)
            st.rerun()

    st.divider()
    if st.button("🚨 Borrar Todo"):
        st.session_state.clear()
        st.rerun()

# ==================================================
# 4. CUERPO PRINCIPAL (TABS)
# ==================================================
st.title("🛡️ Sistema de Control de Inventario y Herramientas")

tab_ops, tab_bodega, tab_herr = st.tabs(["👷 Inventario Operarios", "🏢 Bodega Materiales", "🛠️ Herramientas"])

# --- TAB: OPERARIOS (INVENTARIO INICIAL Y RESUMEN) ---
with tab_ops:
    col_a, col_b = st.columns([1, 2])
    
    with col_a:
        st.subheader("📥 Cargar Inventario Inicial")
        if not st.session_state.cat_operarios or not st.session_state.cat_materiales:
            st.warning("Primero registre operarios y materiales en la barra lateral.")
        else:
            with st.form("form_inv_inicial"):
                op_sel = st.selectbox("Operario", st.session_state.cat_operarios)
                mat_sel = st.selectbox("Material", st.session_state.cat_materiales)
                cant_ini = st.number_input("Cantidad Inicial", min_value=1, step=1)
                serie_ini = st.text_input("Serie/ID (Opcional)")
                if st.form_submit_button("Registrar Stock Inicial"):
                    nueva_data = pd.DataFrame([[datetime.now().date(), "INICIAL", op_sel, mat_sel, cant_ini, serie_ini]], 
                                             columns=st.session_state.db_materiales_operarios.columns)
                    st.session_state.db_materiales_operarios = pd.concat([st.session_state.db_materiales_operarios, nueva_data], ignore_index=True)
                    st.success("Cargado correctamente")
                    st.rerun()

    with col_b:
        st.subheader("📋 Resumen de Stock en Calle")
        resumen_op = obtener_stock_operarios("MATERIAL")
        if not resumen_op.empty:
            st.dataframe(resumen_op, use_container_width=True, hide_index=True)
            st.download_button("📥 Descargar Reporte Operarios CSV", convertir_a_csv(resumen_op), "inventario_operarios.csv")
        else:
            st.info("No hay datos registrados.")

# --- TAB: BODEGA MATERIALES ---
with tab_bodega:
    st.subheader("Gestión de Bodega Central")
    c1, c2 = st.columns(2)
    
    with c1:
        st.write("**Cargar entrada a bodega**")
        with st.form("ent_bodega", clear_on_submit=True):
            m_b = st.selectbox("Material", st.session_state.cat_materiales)
            c_b = st.number_input("Cantidad", min_value=1)
            o_b = st.text_input("Origen")
            if st.form_submit_button("📥 Ingresar a Bodega"):
                nueva_ent = pd.DataFrame([[datetime.now().date(), m_b, c_b, o_b]], columns=st.session_state.db_materiales_bodega.columns)
                st.session_state.db_materiales_bodega = pd.concat([st.session_state.db_materiales_bodega, nueva_ent], ignore_index=True)
                st.rerun()

    with c2:
        st.write("**Entregar desde bodega a operario**")
        with st.form("sal_bodega", clear_on_submit=True):
            op_s = st.selectbox("Operario Destino", st.session_state.cat_operarios)
            mat_s = st.selectbox("Material a Entregar", st.session_state.cat_materiales)
            cant_s = st.number_input("Cantidad", min_value=1)
            if st.form_submit_button("📤 Entregar Material"):
                # Lógica simplificada: Se registra en operarios como "BODEGA"
                nueva_sal = pd.DataFrame([[datetime.now().date(), "BODEGA", op_s, mat_s, cant_s, "N/A"]], 
                                         columns=st.session_state.db_materiales_operarios.columns)
                st.session_state.db_materiales_operarios = pd.concat([st.session_state.db_materiales_operarios, nueva_sal], ignore_index=True)
                # Restar de bodega (se registra como entrada negativa para el cálculo)
                restar_bod = pd.DataFrame([[datetime.now().date(), mat_s, -cant_s, f"Entrega a {op_s}"]], columns=st.session_state.db_materiales_bodega.columns)
                st.session_state.db_materiales_bodega = pd.concat([st.session_state.db_materiales_bodega, restar_bod], ignore_index=True)
                st.success("Entrega registrada")
                st.rerun()

# --- TAB: HERRAMIENTAS ---
with tab_herr:
    st.subheader("Control de Herramientas y Equipos")
    h_col1, h_col2 = st.columns(2)
    
    with h_col1:
        st.write("**Asignar Herramienta a Operario**")
        with st.form("form_herr"):
            op_h = st.selectbox("Operario", st.session_state.cat_operarios)
            herr_h = st.selectbox("Herramienta", st.session_state.cat_herramientas)
            cant_h = st.number_input("Cantidad", min_value=1, value=1)
            ser_h = st.text_input("Serie/Placa Herramienta")
            if st.form_submit_button("🛠️ Asignar Herramienta"):
                nueva_h = pd.DataFrame([[datetime.now().date(), op_h, herr_h, cant_h, ser_h]], 
                                      columns=st.session_state.db_herramientas_operarios.columns)
                st.session_state.db_herramientas_operarios = pd.concat([st.session_state.db_herramientas_operarios, nueva_h], ignore_index=True)
                st.success("Herramienta asignada")
                st.rerun()

    with h_col2:
        st.write("**Resumen de Herramientas por Operario**")
        resumen_herr = obtener_stock_operarios("HERRAMIENTA")
        if not resumen_herr.empty:
            st.dataframe(resumen_herr, use_container_width=True, hide_index=True)
            st.download_button("📥 Descargar CSV Herramientas", convertir_a_csv(resumen_herr), "herramientas_operarios.csv")
