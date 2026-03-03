import streamlit as st
import pandas as pd
import io
from datetime import datetime

# ==================================================
# CONFIGURACIÓN Y CARGA SEGURA
# ==================================================
st.set_page_config(page_title="ITA - Procesador Profesional", layout="wide")
st.title("⚙️ Procesador de Inventario ITA")

archivo = st.sidebar.file_uploader("Subir Excel Maestro", type=["xlsx"])

if archivo:
    if 'data' not in st.session_state:
        # Cargamos el Excel y estandarizamos nombres
        xls = pd.ExcelFile(archivo)
        st.session_state.data = {
            'MATERIALES': pd.read_excel(archivo, sheet_name='MATERIALES ITA'),
            'ACCESORIOS': pd.read_excel(archivo, sheet_name='ACCESORIOS ITA'),
            'TRIPLE_A': pd.read_excel(archivo, sheet_name='INVENTARIO TRIPLE A')
        }
        
        # Carga o creación de OPERARIOS (Garantiza que no haya duplicados al cargar)
        if 'OPERARIOS' in xls.sheet_names:
            df_op = pd.read_excel(archivo, sheet_name='OPERARIOS')
            # Consolidamos por si el archivo ya venía con nombres repetidos
            st.session_state.data['OPERARIOS'] = df_op.groupby(['OPERARIO', 'NOMBRE'], as_index=False)['CANTIDAD'].sum()
        else:
            st.session_state.data['OPERARIOS'] = pd.DataFrame(columns=['OPERARIO', 'NOMBRE', 'CANTIDAD'])

    # ==================================================
    # LÓGICA DE ACTUALIZACIÓN (ELIMINA REPETIDOS)
    # ==================================================
    def mover_material(mat_nombre, cant, destino_op):
        for bodega in ['MATERIALES', 'ACCESORIOS', 'TRIPLE_A']:
            df_b = st.session_state.data[bodega]
            if mat_nombre in df_b['NOMBRE'].values:
                idx = df_b[df_b['NOMBRE'] == mat_nombre].index[0]
                if df_b.loc[idx, 'CANTIDAD'] >= cant:
                    # 1. Restar de Bodega
                    st.session_state.data[bodega].loc[idx, 'CANTIDAD'] -= cant
                    
                    # 2. Sumar a Operario (BUSCAR EXISTENTE O CREAR)
                    df_o = st.session_state.data['OPERARIOS']
                    condicion = (df_o['OPERARIO'] == destino_op) & (df_o['NOMBRE'] == mat_nombre)
                    
                    if condicion.any():
                        st.session_state.data['OPERARIOS'].loc[condicion, 'CANTIDAD'] += cant
                    else:
                        nueva_fila = pd.DataFrame([{'OPERARIO': destino_op, 'NOMBRE': mat_nombre, 'CANTIDAD': cant}])
                        st.session_state.data['OPERARIOS'] = pd.concat([df_o, nueva_fila], ignore_index=True)
                    return True
        return False

    # ==================================================
    # INTERFAZ ORGANIZADA
    # ==================================================
    tab1, tab2, tab3 = st.tabs(["🔄 Movimientos", "👤 Consulta Operarios", "💾 Finalizar"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Entregar Material")
            with st.form("form_entrega", clear_on_submit=True):
                # Menu desplegable de operarios existentes para no escribir mal el nombre
                ops_existentes = sorted(st.session_state.data['OPERARIOS']['OPERARIO'].unique())
                op_nombre = st.selectbox("Operario Destino", ["NUEVO..."] + ops_existentes)
                if op_nombre == "NUEVO...":
                    op_nombre = st.text_input("Escriba nombre del nuevo operario").upper().strip()
                
                mats = pd.concat([st.session_state.data[b]['NOMBRE'] for b in ['MATERIALES', 'ACCESORIOS', 'TRIPLE_A']]).unique()
                mat_nombre = st.selectbox("Material", sorted(mats))
                cantidad = st.number_input("Cantidad", min_value=1, step=1)
                
                if st.form_submit_button("Registrar Entrega"):
                    if op_nombre and mover_material(mat_nombre, cantidad, op_nombre):
                        st.success("Movimiento registrado con éxito")
                        st.rerun()
                    else: st.error("Error en stock o nombre vacío")

    with tab2:
        st.subheader("Inventario por Persona")
        df_inv = st.session_state.data['OPERARIOS']
        if not df_inv.empty:
            op_sel = st.selectbox("Seleccione para ver detalle", df_inv['OPERARIO'].unique())
            detalle = df_inv[df_inv['OPERARIO'] == op_sel]
            st.table(detalle[['NOMBRE', 'CANTIDAD']])
        else:
            st.info("No hay materiales asignados.")

    with tab3:
        st.subheader("Exportar a Excel")
        # Botón para descargar
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            st.session_state.data['MATERIALES'].to_excel(writer, sheet_name='MATERIALES ITA', index=False)
            st.session_state.data['ACCESORIOS'].to_excel(writer, sheet_name='ACCESORIOS ITA', index=False)
            st.session_state.data['TRIPLE_A'].to_excel(writer, sheet_name='INVENTARIO TRIPLE A', index=False)
            st.session_state.data['OPERARIOS'].to_excel(writer, sheet_name='OPERARIOS', index=False)
        
        st.download_button(
            label="📥 Descargar Inventario Actualizado",
            data=buffer.getvalue(),
            file_name=f"Inventario_ITA_{datetime.now().strftime('%d_%m')}.xlsx",
            mime="application/vnd.ms-excel"
        )
else:
    st.warning("Por favor, sube el archivo Excel en la barra lateral.")
