import streamlit as st
import pandas as pd
import io
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Procesador de Inventario UT", layout="wide")

# ==================================================
# 1. GESTIÓN DE DATOS EN MEMORIA VOLÁTIL
# ==================================================
# Usamos session_state para mantener los cambios mientras la pestaña esté abierta
if 'db_movs' not in st.session_state:
    st.session_state.db_movs = pd.DataFrame(columns=["Fecha", "Tipo_Movimiento", "Operario", "Material", "Cantidad", "Referencia/Acta"])

# ==================================================
# 2. FUNCIONES DE CÁLCULO
# ==================================================
def obtener_stock_real(df):
    if df.empty:
        return pd.DataFrame(columns=["Operario", "Material", "Stock Actual"])
    
    temp_df = df.copy()
    # Las ACTAS restan, el resto (INICIAL, BODEGA) suman
    temp_df['Cantidad_Neta'] = temp_df.apply(
        lambda x: -x['Cantidad'] if x['Tipo_Movimiento'] == "ACTA" else x['Cantidad'], axis=1
    )
    
    resumen = temp_df.groupby(["Operario", "Material"])["Cantidad_Neta"].sum().reset_index()
    resumen.rename(columns={"Cantidad_Neta": "Stock Actual"}, inplace=True)
    return resumen

def exportar_excel(df_movimientos):
    # Crea un archivo Excel en memoria para descargar
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_movimientos.to_excel(writer, index=False, sheet_name='Historial_Movimientos')
        # También incluimos el resumen calculado para conveniencia
        obtener_stock_real(df_movimientos).to_excel(writer, index=False, sheet_name='Resumen_Stock')
    return output.getvalue()

# ==================================================
# 3. INTERFAZ PRINCIPAL
# ==================================================
st.title("📑 Procesador de Inventario y Actas")
st.info("Paso 1: Sube tu archivo actual. Paso 2: Registra movimientos. Paso 3: Descarga el resultado.")

# --- SECCIÓN DE CARGA ---
with st.expander("📂 CARGAR BASE DE DATOS ACTUAL", expanded=st.session_state.db_movs.empty):
    archivo_subido = st.file_uploader("Sube tu archivo Excel o CSV de movimientos", type=["xlsx", "csv"])
    if archivo_subido:
        if archivo_subido.name.endswith('.csv'):
            df_input = pd.read_csv(archivo_subido)
        else:
            df_input = pd.read_excel(archivo_subido)
        
        if st.button("Confirmar Carga de Datos"):
            st.session_state.db_movs = df_input
            st.success("¡Datos cargados correctamente!")
            st.rerun()

# --- SI HAY DATOS CARGADOS, MOSTRAR HERRAMIENTAS ---
if not st.session_state.db_movs.empty:
    tab_resumen, tab_registro, tab_descarga = st.tabs(["📊 Stock Actual", "📝 Registrar Salida (Acta)", "💾 Descargar Cambios"])

    with tab_resumen:
        st.subheader("Estado de Inventario en Calle")
        df_actual = obtener_stock_real(st.session_state.db_movs)
        st.dataframe(df_actual, use_container_width=True, hide_index=True)

    with tab_registro:
        st.subheader("Registrar Nueva Acta de Consumo")
        df_val = obtener_stock_real(st.session_state.db_movs)
        
        with st.form("form_salida", clear_on_submit=True):
            col1, col2 = st.columns(2)
            # Extraemos operarios y materiales de los datos subidos
            ops_disponibles = sorted(st.session_state.db_movs["Operario"].unique())
            op_sel = col1.selectbox("Operario", ops_disponibles)
            
            mats_op = df_val[df_val["Operario"] == op_sel]["Material"].unique()
            mat_sel = col1.selectbox("Material a reportar", mats_op if len(mats_op)>0 else ["Sin stock"])
            
            # Mostrar stock disponible en tiempo real
            if len(mats_op) > 0:
                actual = df_val[(df_val["Operario"] == op_sel) & (df_val["Material"] == mat_sel)]["Stock Actual"].values[0]
                col1.warning(f"Stock disponible: {int(actual)}")
            
            cant_salida = col2.number_input("Cantidad utilizada", min_value=1, step=1)
            n_acta = col2.text_input("Número de Acta / Orden de Trabajo")
            
            if st.form_submit_button("Añadir Movimiento"):
                if len(mats_op) == 0:
                    st.error("Este operario no tiene material.")
                elif cant_salida > actual:
                    st.error("No puedes restar más de lo que el operario tiene.")
                else:
                    # Crear nueva fila de movimiento
                    nueva_fila = pd.DataFrame([{
                        "Fecha": datetime.now().strftime("%Y-%m-%d"),
                        "Tipo_Movimiento": "ACTA",
                        "Operario": op_sel,
                        "Material": mat_sel,
                        "Cantidad": cant_salida,
                        "Referencia/Acta": n_acta
                    }])
                    st.session_state.db_movs = pd.concat([st.session_state.db_movs, nueva_fila], ignore_index=True)
                    st.success("Movimiento añadido a la lista temporal.")
                    st.rerun()

    with tab_descarga:
        st.subheader("Finalizar y Guardar")
        st.write("Haz clic abajo para generar el nuevo archivo Excel con todos los movimientos agregados.")
        
        excel_data = exportar_excel(st.session_state.db_movs)
        nombre_archivo = f"Inventario_Actualizado_{datetime.now().strftime('%d_%m_%Y')}.xlsx"
        
        st.download_button(
            label="📥 Descargar Excel Actualizado",
            data=excel_data,
            file_name=nombre_archivo,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        if st.button("🚨 Limpiar sesión (Borrar todo para empezar de cero)"):
            st.session_state.clear()
            st.rerun()
else:
    st.warning("⚠️ Por favor, sube un archivo Excel para comenzar a trabajar.")
