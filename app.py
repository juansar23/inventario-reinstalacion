import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import io

# Configuración de la página
st.set_page_config(page_title="Sistema de Gestión UT - NUBE", layout="wide")

# ==================================================
# 1. CONEXIÓN Y FUNCIONES DE PERSISTENCIA (ANT-INVERSIÓN)
# ==================================================
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos_frescos(pestana):
    """Lee directamente de Google Sheets ignorando el caché (ttl=0)"""
    try:
        df = conn.read(worksheet=pestana, ttl=0)
        # Limpieza básica para evitar errores de tipos de datos
        return df.dropna(how='all')
    except Exception as e:
        columnas = {
            "materiales_operarios": ["Fecha", "Tipo_Movimiento", "Operario", "Material", "Cantidad", "Referencia/Acta"],
            "materiales_bodega": ["Fecha", "Material", "Cantidad", "Origen"],
            "herramientas": ["Fecha", "Operario", "Herramienta", "Cantidad", "ID_Serie"],
            "catalogos": ["Tipo", "Nombre"]
        }
        return pd.DataFrame(columns=columnas.get(pestana, []))

def guardar_en_nube(df, pestana):
    """Guarda en Google Sheets y limpia caché de Streamlit"""
    conn.update(worksheet=pestana, data=df)
    st.cache_data.clear()

# Inicialización de Session State (Solo si la app acaba de arrancar)
if 'db_catalogos' not in st.session_state:
    st.session_state.db_materiales_operarios = cargar_datos_frescos("materiales_operarios")
    st.session_state.db_herramientas_operarios = cargar_datos_frescos("herramientas")
    st.session_state.db_catalogos = cargar_datos_frescos("catalogos")

# --- FUNCIONES DE APOYO ---
def get_cat(tipo):
    df = st.session_state.db_catalogos
    return sorted(df[df['Tipo'] == tipo]['Nombre'].unique().tolist())

def add_to_cat(tipo, nombre):
    nombre = str(nombre).strip().upper()
    # Recargamos catálogos antes de guardar para no borrar lo que otro usuario subió
    df_actual = cargar_datos_frescos("catalogos")
    if nombre not in df_actual[df_actual['Tipo'] == tipo]['Nombre'].tolist():
        nueva_fila = pd.DataFrame([[tipo, nombre]], columns=["Tipo", "Nombre"])
        df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
        guardar_en_nube(df_final, "catalogos")
        st.session_state.db_catalogos = df_final

def generar_excel_respaldo():
    """Crea un archivo Excel en memoria con todas las pestañas"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        cargar_datos_frescos("materiales_operarios").to_excel(writer, sheet_name='Materiales', index=False)
        cargar_datos_frescos("herramientas").to_excel(writer, sheet_name='Herramientas', index=False)
        cargar_datos_frescos("catalogos").to_excel(writer, sheet_name='Catalogos', index=False)
    return output.getvalue()

# ==================================================
# 2. CÁLCULOS DE INVENTARIO
# ==================================================
def obtener_stock_real():
    # Siempre calculamos sobre datos frescos para evitar errores tras hibernación
    df = cargar_datos_frescos("materiales_operarios")
    if df.empty: 
        return pd.DataFrame(columns=["Operario", "Material", "Stock Actual"])
    
    df['Cantidad'] = pd.to_numeric(df['Cantidad'], errors='coerce').fillna(0)
    # Si es ACTA resta, si es INICIAL o BODEGA suma
    df['Cant_Neta'] = df.apply(lambda x: -x['Cantidad'] if x['Tipo_Movimiento'] == "ACTA" else x['Cantidad'], axis=1)
    
    resumen = df.groupby(["Operario", "Material"])["Cant_Neta"].sum().reset_index()
    resumen.rename(columns={"Cant_Neta": "Stock Actual"}, inplace=True)
    return resumen[resumen["Stock Actual"] >= 0] # Filtro preventivo

# ==================================================
# 3. BARRA LATERAL
# ==================================================
with st.sidebar:
    st.header("⚙️ Gestión y Backup")
    
    # Botón de Sincronización Manual
    if st.button("🔄 Forzar Sincronización Nube"):
        st.session_state.db_catalogos = cargar_datos_frescos("catalogos")
        st.rerun()

    st.divider()
    # Descarga de Excel
    excel_data = generar_excel_respaldo()
    st.download_button(
        label="📥 Descargar Respaldo Excel",
        data=excel_data,
        file_name=f"Backup_Inventario_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.divider()
    op_input = st.text_input("Añadir Operario")
    if st.button("Registrar Operario") and op_input:
        add_to_cat("OPERARIO", op_input)
        st.success(f"{op_input} registrado")
        st.rerun()

    mat_input = st.text_input("Añadir Material")
    if st.button("Registrar Material") and mat_input:
        add_to_cat("MATERIAL", mat_input)
        st.success(f"{mat_input} registrado")
        st.rerun()

    herr_input = st.text_input("Añadir Herramienta")
    if st.button("Registrar Herramienta") and herr_input:
        add_to_cat("HERRAMIENTA", herr_input)
        st.success(f"{herr_input} registrado")
        st.rerun()

# ==================================================
# 4. CUERPO PRINCIPAL
# ==================================================
st.title("🛡️ Control de Inventario UT")

tab_resumen, tab_inicial, tab_actas, tab_bodega, tab_herr = st.tabs([
    "📊 Resumen", "📥 Carga Inicial", "📄 Consumo (Actas)", "🏢 Bodega", "🛠️ Herramientas"
])

# --- TAB: RESUMEN ---
with tab_resumen:
    st.subheader("Estado Actual de Materiales por Operario")
    df_res = obtener_stock_real()
    st.dataframe(df_res, use_container_width=True, hide_index=True)

# --- TAB: CARGA INICIAL ---
with tab_inicial:
    st.subheader("Registrar Inventario Inicial")
    with st.form("form_inicial", clear_on_submit=True):
        col1, col2 = st.columns(2)
        op_i = col1.selectbox("Operario", get_cat("OPERARIO"), key="sel_op_i")
        mat_i = col1.selectbox("Material", get_cat("MATERIAL"), key="sel_mat_i")
        cant_i = col2.number_input("Cantidad Inicial", min_value=1, step=1)
        ref_i = col2.text_input("Referencia", "Inventario Inicial")
        
        if st.form_submit_button("Cargar Stock"):
            # Leer antes de escribir
            df_hist = cargar_datos_frescos("materiales_operarios")
            nueva_fila = pd.DataFrame([[str(datetime.now().date()), "INICIAL", op_i, mat_i, cant_i, ref_i]], 
                                     columns=df_hist.columns)
            guardar_en_nube(pd.concat([df_hist, nueva_fila], ignore_index=True), "materiales_operarios")
            st.success("Guardado en la nube")
            st.rerun()

# --- TAB: ACTAS ---
with tab_actas:
    st.subheader("📄 Registro de Consumo (Baja de Material)")
    df_val = obtener_stock_real()
    with st.form("form_acta", clear_on_submit=True):
        c1, c2 = st.columns(2)
        op_a = c1.selectbox("Operario", get_cat("OPERARIO"))
        
        mats_del_op = df_val[df_val["Operario"] == op_a]
        lista_mats = mats_del_op["Material"].tolist()
        
        mat_a = c1.selectbox("Material a descargar", lista_mats if lista_mats else ["Sin Stock"])
        
        actual = 0
        if not mats_del_op.empty and mat_a in lista_mats:
            actual = mats_del_op[mats_del_op["Material"] == mat_a]["Stock Actual"].values[0]
            c1.info(f"Stock disponible: {int(actual)}")
        
        cant_a = c2.number_input("Cantidad utilizada", min_value=1, step=1)
        num_acta = c2.text_input("Número de Acta/OT")
        
        if st.form_submit_button("🔥 Registrar Consumo"):
            if not lista_mats or cant_a > actual:
                st.error("Error: Cantidad excede el stock o el operario no tiene este material.")
            else:
                df_hist = cargar_datos_frescos("materiales_operarios")
                nueva_acta = pd.DataFrame([[str(datetime.now().date()), "ACTA", op_a, mat_a, cant_a, num_acta]], 
                                         columns=df_hist.columns)
                guardar_en_nube(pd.concat([df_hist, nueva_acta], ignore_index=True), "materiales_operarios")
                st.success("Consumo registrado correctamente")
                st.rerun()

# --- TAB: BODEGA ---
with tab_bodega:
    st.subheader("Entrega de Material de Bodega")
    with st.form("form_bodega"):
        st.write("Registrar salida de bodega central hacia operario")
        op_b = st.selectbox("Operario Destinatario", get_cat("OPERARIO"))
        mat_b = st.selectbox("Material entregado", get_cat("MATERIAL"))
        cant_b = st.number_input("Cantidad", min_value=1)
        
        if st.form_submit_button("Sincronizar Entrega"):
            df_hist = cargar_datos_frescos("materiales_operarios")
            n_ent = pd.DataFrame([[str(datetime.now().date()), "BODEGA", op_b, mat_b, cant_b, "Despacho Bodega"]], 
                                columns=df_hist.columns)
            guardar_en_nube(pd.concat([df_hist, n_ent], ignore_index=True), "materiales_operarios")
            st.success("Carga de bodega completada")
            st.rerun()

# --- TAB: HERRAMIENTAS ---
with tab_herr:
    st.subheader("Asignación de Herramientas")
    with st.form("f_herr"):
        col_h1, col_h2 = st.columns(2)
        op_h = col_h1.selectbox("Operario", get_cat("OPERARIO"))
        her_h = col_h1.selectbox("Herramienta", get_cat("HERRAMIENTA"))
        ser_h = col_h2.text_input("Número de Serie / ID")
        
        if st.form_submit_button("🛠️ Asignar Herramienta"):
            df_h_hist = cargar_datos_frescos("herramientas")
            n_h = pd.DataFrame([[str(datetime.now().date()), op_h, her_h, 1, ser_h]], 
                              columns=df_h_hist.columns)
            guardar_en_nube(pd.concat([df_h_hist, n_h], ignore_index=True), "herramientas")
            st.success("Herramienta asignada")
            st.rerun()
    
    st.divider()
    st.write("**Listado de Herramientas en Terreno**")
    st.dataframe(cargar_datos_frescos("herramientas"), use_container_width=True, hide_index=True)
