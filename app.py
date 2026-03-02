import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 1. ESTABLECER CONEXIÓN
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. FUNCIÓN PARA CARGAR DATOS (Persistencia Real)
def cargar_datos(pestana):
    try:
        # Intentamos leer la pestaña específica
        return conn.read(worksheet=pestana, ttl="0s") # ttl=0 para que no use caché y siempre esté actualizado
    except:
        # Si falla (hoja vacía), devolvemos el esquema base
        if pestana == "materiales_operarios":
            return pd.DataFrame(columns=["Fecha", "Tipo_Movimiento", "Operario", "Material", "Cantidad", "Referencia/Acta"])
        # ... añadir los demás según necesites
        return pd.DataFrame()

# 3. FUNCIÓN PARA GUARDAR DATOS
def guardar_datos(df, pestana):
    conn.update(worksheet=pestana, data=df)
    st.cache_data.clear() # Limpiamos caché para forzar recarga

# --- Al inicio de tu script ---
if 'db_materiales_operarios' not in st.session_state:
    st.session_state.db_materiales_operarios = cargar_datos("materiales_operarios")

# --- Ejemplo de cómo registrar un movimiento (Carga Inicial) ---
# Sustituye tus bloques de guardado por esto:
if st.form_submit_button("Cargar Stock Inicial"):
    nueva_fila = pd.DataFrame([[str(datetime.now().date()), "INICIAL", op_i, mat_i, cant_i, ref_i]], 
                               columns=st.session_state.db_materiales_operarios.columns)
    
    # Actualizamos el estado de la sesión
    st.session_state.db_materiales_operarios = pd.concat([st.session_state.db_materiales_operarios, nueva_fila], ignore_index=True)
    
    # GUARDADO REAL EN GOOGLE SHEETS
    guardar_datos(st.session_state.db_materiales_operarios, "materiales_operarios")
    
    st.success("Cargado y Guardado en la Nube")
    st.rerun()
