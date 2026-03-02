import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Sistema de Gestión UT - NUBE", layout="wide")

# ==================================================
# 1. CONEXIÓN Y FUNCIONES DE PERSISTENCIA
# ==================================================
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos(pestana):
    try:
        # ttl="0s" obliga a leer los datos frescos de la nube siempre
        return conn.read(worksheet=pestana, ttl="0s")
    except:
        # Estructuras por defecto si la hoja está vacía
        columnas = {
            "materiales_operarios": ["Fecha", "Tipo_Movimiento", "Operario", "Material", "Cantidad", "Referencia/Acta"],
            "materiales_bodega": ["Fecha", "Material", "Cantidad", "Origen"],
            "herramientas": ["Fecha", "Operario", "Herramienta", "Cantidad", "ID_Serie"],
            "catalogos": ["Tipo", "Nombre"]
        }
        return pd.DataFrame(columns=columnas.get(pestana, []))

def guardar_datos(df, pestana):
    conn.update(worksheet=pestana, data=df)
    st.cache_data.clear()

# Inicialización de Session State desde la Nube
if 'db_materiales_operarios' not in st.session_state:
    st.session_state.db_materiales_operarios = cargar_datos("materiales_operarios")
if 'db_materiales_bodega' not in st.session_state:
    st.session_state.db_materiales_bodega = cargar_datos("materiales_bodega")
if 'db_herramientas_operarios' not in st.session_state:
    st.session_state.db_herramientas_operarios = cargar_datos("herramientas")
if 'db_catalogos' not in st.session_state:
    st.session_state.db_catalogos = cargar_datos("catalogos")

# Funciones auxiliares para catálogos
def get_cat(tipo):
    df = st.session_state.db_catalogos
    return df[df['Tipo'] == tipo]['Nombre'].tolist()

def add_to_cat(tipo, nombre):
    nombre = nombre.strip().upper()
    if nombre not in get_cat(tipo):
        nueva_fila = pd.DataFrame([[tipo, nombre]], columns=["Tipo", "Nombre"])
        st.session_state.db_catalogos = pd.concat([st.session_state.db_catalogos, nueva_fila], ignore_index=True)
        guardar_datos(st.session_state.db_catalogos, "catalogos")

# ==================================================
# 2. FUNCIONES DE CÁLCULO
# ==================================================
def obtener_stock_real_operarios():
    df = st.session_state.db_materiales_operarios
    if df.empty: return pd.DataFrame(columns=["Operario", "Material", "Stock Actual"])
    
    df_temp = df.copy()
    df_temp['Cantidad'] = pd.to_numeric(df_temp['Cantidad'])
    df_temp['Cantidad_Neta'] = df_temp.apply(lambda x: -x['Cantidad'] if x['Tipo_Movimiento'] == "ACTA" else x['Cantidad'], axis=1)
    resumen = df_temp.groupby(["Operario", "Material"])["Cantidad_Neta"].sum().reset_index()
    resumen.rename(columns={"Cantidad_Neta": "Stock Actual"}, inplace=True)
    return resumen

# ==================================================
# 3. BARRA LATERAL (CONFIGURACIÓN)
# ==================================================
with st.sidebar:
    st.header("⚙️ Configuración")
    
    op_input = st.text_input("Añadir Operario")
    if st.button("Registrar Operario") and op_input:
        add_to_cat("OPERARIO", op_input)
        st.rerun()

    mat_input = st.text_input("Añadir Material")
    if st.button("Registrar Material") and mat_input:
        add_to_cat("MATERIAL", mat_input)
        st.rerun()

    herr_input = st.text_input("Añadir Herramienta")
    if st.button("Registrar Herramienta") and herr_input:
        add_to_cat("HERRAMIENTA", herr_input)
        st.rerun()

# ==================================================
# 4. CUERPO PRINCIPAL
# ==================================================
st.title("🛡️ Control de Inventario UT (Sincronizado)")

tab_resumen, tab_inicial, tab_actas, tab_bodega, tab_herr = st.tabs([
    "📊 Resumen", "📥 Carga Inicial", "📄 Consumo (Actas)", "🏢 Bodega", "🛠️ Herramientas"
])

# --- TAB: CARGA INICIAL (Tú desde tu PC) ---
with tab_inicial:
    st.subheader("Registrar Inventario Inicial")
    with st.form("form_inicial", clear_on_submit=True):
        col1, col2 = st.columns(2)
        op_i = col1.selectbox("Operario", get_cat("OPERARIO"))
        mat_i = col1.selectbox("Material", get_cat("MATERIAL"))
        cant_i = col2.number_input("Cantidad Inicial", min_value=1, step=1)
        ref_i = col2.text_input("Referencia", "Inventario Inicial")
        
        if st.form_submit_button("Cargar Stock Inicial"):
            nueva_fila = pd.DataFrame([[str(datetime.now().date()), "INICIAL", op_i, mat_i, cant_i, ref_i]], 
                                     columns=st.session_state.db_materiales_operarios.columns)
            st.session_state.db_materiales_operarios = pd.concat([st.session_state.db_materiales_operarios, nueva_fila], ignore_index=True)
            guardar_datos(st.session_state.db_materiales_operarios, "materiales_operarios")
            st.success("Guardado en la nube")
            st.rerun()

# --- TAB: ACTAS (Supervisor desde su PC) ---
with tab_actas:
    st.subheader("📄 Registro de Consumo")
    df_val = obtener_stock_real_operarios()
    with st.form("form_acta", clear_on_submit=True):
        c1, c2 = st.columns(2)
        op_a = c1.selectbox("Operario que reporta", get_cat("OPERARIO"))
        mats_op = df_val[df_val["Operario"] == op_a]["Material"].unique()
        mat_a = c1.selectbox("Material utilizado", mats_op if len(mats_op)>0 else ["Sin stock"])
        
        actual = 0
        if len(mats_op) > 0:
            actual = df_val[(df_val["Operario"] == op_a) & (df_val["Material"] == mat_a)]["Stock Actual"].values[0]
            c1.info(f"Stock disponible: {int(actual)}")
        
        cant_a = c2.number_input("Cantidad utilizada", min_value=1, step=1)
        num_acta = c2.text_input("Número de Acta")
        
        if st.form_submit_button("🔥 Registrar Consumo"):
            if len(mats_op) == 0 or cant_a > actual:
                st.error("Cantidad no válida o sin stock")
            else:
                nueva_acta = pd.DataFrame([[str(datetime.now().date()), "ACTA", op_a, mat_a, cant_a, num_acta]], 
                                         columns=st.session_state.db_materiales_operarios.columns)
                st.session_state.db_materiales_operarios = pd.concat([st.session_state.db_materiales_operarios, nueva_acta], ignore_index=True)
                guardar_datos(st.session_state.db_materiales_operarios, "materiales_operarios")
                st.success("Consumo registrado")
                st.rerun()

# --- TAB: BODEGA ---
with tab_bodega:
    st.subheader("Movimientos de Bodega")
    with st.form("b_sal"):
        st.write("**Entrega Bodega -> Operario**")
        op_d = st.selectbox("Operario Destino", get_cat("OPERARIO"))
        mat_d = st.selectbox("Material", get_cat("MATERIAL"))
        cant_d = st.number_input("Cantidad", min_value=1)
        if st.form_submit_button("Entregar Material"):
            # Registro en Operarios
            n_ent = pd.DataFrame([[str(datetime.now().date()), "BODEGA", op_d, mat_d, cant_d, "Entrega Bodega"]], 
                                columns=st.session_state.db_materiales_operarios.columns)
            st.session_state.db_materiales_operarios = pd.concat([st.session_state.db_materiales_operarios, n_ent], ignore_index=True)
            guardar_datos(st.session_state.db_materiales_operarios, "materiales_operarios")
            st.success("Entrega sincronizada")
            st.rerun()

# --- TAB: RESUMEN Y HERRAMIENTAS ---
with tab_resumen:
    st.dataframe(obtener_stock_real_operarios(), use_container_width=True, hide_index=True)

with tab_herr:
    with st.form("f_herr"):
        op_h = st.selectbox("Operario", get_cat("OPERARIO"))
        her_h = st.selectbox("Herramienta", get_cat("HERRAMIENTA"))
        ser_h = st.text_input("Serie")
        if st.form_submit_button("🛠️ Asignar"):
            n_h = pd.DataFrame([[str(datetime.now().date()), op_h, her_h, 1, ser_h]], 
                              columns=st.session_state.db_herramientas_operarios.columns)
            st.session_state.db_herramientas_operarios = pd.concat([st.session_state.db_herramientas_operarios, n_h], ignore_index=True)
            guardar_datos(st.session_state.db_herramientas_operarios, "herramientas")
            st.rerun()
    st.dataframe(st.session_state.db_herramientas_operarios, use_container_width=True)
