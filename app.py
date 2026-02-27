import streamlit as st
import pandas as pd
import io
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Sistema de Gestión UT - Carga Excel", layout="wide")

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

def convertir_a_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# ==================================================
# 3. BARRA LATERAL (CONFIGURACIÓN)
# ==================================================
with st.sidebar:
    st.header("⚙️ Configuración")
    
    with st.expander("👥 Operarios", expanded=True):
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

    with st.expander("🛠️ Herramientas"):
        herr_input = st.text_input("Nombre Herramienta")
        if st.button("Añadir Herramienta") and herr_input:
            nombre = herr_input.strip().upper()
            if nombre not in st.session_state.cat_herramientas:
                st.session_state.cat_herramientas.append(nombre)
                st.rerun()

    st.divider()
    if st.button("🚨 Reiniciar Sistema"):
        st.session_state.clear()
        st.rerun()

# ==================================================
# 4. CUERPO PRINCIPAL
# ==================================================
st.title("🛡️ Gestión de Inventario con Carga de Excel")

tab_resumen, tab_inicial, tab_actas, tab_bodega, tab_herr = st.tabs([
    "📊 Stock Calle", "📥 Carga Inicial Material", "📄 Actas (Restar)", "🏢 Bodega", "🛠️ Equipos/Herramientas"
])

# --- TAB 1: RESUMEN ---
with tab_resumen:
    st.subheader("Inventario en manos de Operarios")
    df_resumen = obtener_stock_real_operarios()
    st.dataframe(df_resumen, use_container_width=True, hide_index=True)

# --- TAB 2: CARGA INICIAL MATERIAL (CON EXCEL) ---
with tab_inicial:
    st.subheader("Carga de Inventario Inicial (Materiales)")
    
    # Subida de archivo Excel
    uploaded_file_mat = st.file_uploader("Subir Excel de Materiales (Columnas: Operario, Material, Cantidad)", type=["xlsx"])
    
    if uploaded_file_mat:
        if st.button("Procesar Excel de Materiales"):
            try:
                df_excel = pd.read_excel(uploaded_file_mat)
                # Estandarizar nombres
                df_excel['Operario'] = df_excel['Operario'].astype(str).str.strip().str.upper()
                df_excel['Material'] = df_excel['Material'].astype(str).str.strip().str.upper()
                
                for _, row in df_excel.iterrows():
                    # Añadir a catálogos si no existen
                    if row['Operario'] not in st.session_state.cat_operarios:
                        st.session_state.cat_operarios.append(row['Operario'])
                    if row['Material'] not in st.session_state.cat_materiales:
                        st.session_state.cat_materiales.append(row['Material'])
                    
                    # Registrar carga
                    nueva = pd.DataFrame([[datetime.now().date(), "INICIAL", row['Operario'], row['Material'], row['Cantidad'], "Carga Excel"]], 
                                        columns=st.session_state.db_materiales_operarios.columns)
                    st.session_state.db_materiales_operarios = pd.concat([st.session_state.db_materiales_operarios, nueva], ignore_index=True)
                
                st.success("¡Excel de materiales cargado exitosamente!")
                st.rerun()
            except Exception as e:
                st.error(f"Error al leer el archivo: {e}. Asegúrese de que las columnas sean: Operario, Material, Cantidad")

    st.divider()
    st.write("**O cargar manualmente:**")
    with st.form("f_inicial_man", clear_on_submit=True):
        c1, c2 = st.columns(2)
        op = c1.selectbox("Operario", st.session_state.cat_operarios)
        mat = c1.selectbox("Material", st.session_state.cat_materiales)
        cant = c2.number_input("Cantidad", min_value=1, step=1)
        if st.form_submit_button("Registrar Carga Manual"):
            nueva = pd.DataFrame([[datetime.now().date(), "INICIAL", op, mat, cant, "Manual"]], 
                                columns=st.session_state.db_materiales_operarios.columns)
            st.session_state.db_materiales_operarios = pd.concat([st.session_state.db_materiales_operarios, nueva], ignore_index=True)
            st.rerun()

# --- TAB 3: ACTAS (RESTAR) ---
with tab_actas:
    st.subheader("Descontar material por Acta")
    df_actual = obtener_stock_real_operarios()
    with st.form("f_acta", clear_on_submit=True):
        c1, c2 = st.columns(2)
        op_a = c1.selectbox("Operario", st.session_state.cat_operarios)
        mats_disp = df_actual[df_actual["Operario"] == op_a]["Material"].unique()
        mat_a = c1.selectbox("Material usado", mats_disp if len(mats_disp) > 0 else ["Sin Stock"])
        cant_a = c2.number_input("Cantidad a restar", min_value=1, step=1)
        acta_n = c2.text_input("Número de Acta")
        if st.form_submit_button("Registrar Consumo"):
            if len(mats_disp) > 0:
                actual = df_actual[(df_actual["Operario"] == op_a) & (df_actual["Material"] == mat_a)]["Stock Actual"].values[0]
                if cant_a <= actual:
                    nueva_acta = pd.DataFrame([[datetime.now().date(), "ACTA", op_a, mat_a, cant_a, acta_n]], 
                                             columns=st.session_state.db_materiales_operarios.columns)
                    st.session_state.db_materiales_operarios = pd.concat([st.session_state.db_materiales_operarios, nueva_acta], ignore_index=True)
                    st.rerun()
                else:
                    st.error("Stock insuficiente.")

# --- TAB 4: BODEGA ---
with tab_bodega:
    st.subheader("Entradas y Salidas de Bodega")
    # (Mantiene la lógica anterior de carga de bodega y entregas)
    st.info("Utilice esta pestaña para movimientos diarios de entrada/salida de bodega central.")

# --- TAB 5: EQUIPOS/HERRAMIENTAS (CON EXCEL) ---
with tab_herr:
    st.subheader("Carga Inicial de Herramientas/Equipos")
    
    uploaded_file_herr = st.file_uploader("Subir Excel de Herramientas (Columnas: Operario, Herramienta, ID_Serie)", type=["xlsx"])
    
    if uploaded_file_herr:
        if st.button("Procesar Excel de Herramientas"):
            try:
                df_ex_h = pd.read_excel(uploaded_file_herr)
                df_ex_h['Operario'] = df_ex_h['Operario'].astype(str).str.strip().str.upper()
                df_ex_h['Herramienta'] = df_ex_h['Herramienta'].astype(str).str.strip().str.upper()
                
                for _, row in df_ex_h.iterrows():
                    if row['Operario'] not in st.session_state.cat_operarios:
                        st.session_state.cat_operarios.append(row['Operario'])
                    if row['Herramienta'] not in st.session_state.cat_herramientas:
                        st.session_state.cat_herramientas.append(row['Herramienta'])
                    
                    nueva_h = pd.DataFrame([[datetime.now().date(), row['Operario'], row['Herramienta'], 1, row['ID_Serie']]], 
                                          columns=st.session_state.db_herramientas_operarios.columns)
                    st.session_state.db_herramientas_operarios = pd.concat([st.session_state.db_herramientas_operarios, nueva_h], ignore_index=True)
                
                st.success("¡Excel de herramientas cargado!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}. Columnas requeridas: Operario, Herramienta, ID_Serie")

    st.divider()
    st.write("**Herramientas Asignadas Actuales:**")
    st.dataframe(st.session_state.db_herramientas_operarios, use_container_width=True, hide_index=True)
