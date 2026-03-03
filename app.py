import streamlit as st
import pandas as pd
import io
from datetime import datetime

st.set_page_config(page_title="Sistema ITA - Control Total", layout="wide")

# ==================================================
# 1. CARGA Y NORMALIZACIÓN DE DATOS
# ==================================================
st.title("🛡️ Panel de Control ITA")

archivo = st.sidebar.file_uploader("📂 Sube tu archivo Excel Maestro", type=["xlsx"])

if archivo:
    if 'data' not in st.session_state:
        try:
            xls = pd.ExcelFile(archivo)
            st.session_state.data = {}
            
            # Cargar Bodegas
            hojas_bodega = {'MATERIALES': 'MATERIALES ITA', 'ACCESORIOS': 'ACCESORIOS ITA', 'TRIPLE_A': 'INVENTARIO TRIPLE A'}
            for clave, nombre_hoja in hojas_bodega.items():
                if nombre_hoja in xls.sheet_names:
                    df = pd.read_excel(archivo, sheet_name=nombre_hoja)
                    df.columns = ['NOMBRE', 'CANTIDAD'] + list(df.columns[2:])
                    st.session_state.data[clave] = df

            # Cargar Operarios (OPERARIO, MATERIAL, CANTIDAD)
            if 'OPERARIOS' in xls.sheet_names:
                df_op = pd.read_excel(archivo, sheet_name='OPERARIOS')
                df_op.columns = ['OPERARIO', 'MATERIAL', 'CANTIDAD'] + list(df_op.columns[3:])
                df_op['OPERARIO'] = df_op['OPERARIO'].astype(str).str.strip().str.upper()
                df_op['MATERIAL'] = df_op['MATERIAL'].astype(str).str.strip().str.upper()
                # Consolidamos duplicados al inicio
                st.session_state.data['OPERARIOS'] = df_op.groupby(['OPERARIO', 'MATERIAL'], as_index=False)['CANTIDAD'].sum()
            else:
                st.session_state.data['OPERARIOS'] = pd.DataFrame(columns=['OPERARIO', 'MATERIAL', 'CANTIDAD'])

            # Historiales
            st.session_state.data['H_ENTREGAS'] = pd.read_excel(archivo, sheet_name='HISTORIAL_ENTREGAS') if 'HISTORIAL_ENTREGAS' in xls.sheet_names else pd.DataFrame(columns=['FECHA', 'OPERARIO', 'MATERIAL', 'CANTIDAD'])
            st.session_state.data['H_ACTAS'] = pd.read_excel(archivo, sheet_name='HISTORIAL_ACTAS') if 'HISTORIAL_ACTAS' in xls.sheet_names else pd.DataFrame(columns=['FECHA', 'NUM_ACTA', 'OPERARIO', 'MATERIAL', 'CANTIDAD'])

            st.success("✅ Datos cargados correctamente")

        except Exception as e:
            st.error(f"Error al cargar: {e}")
            st.stop()

    # ==================================================
    # 2. FUNCIONES DE MOVIMIENTO
    # ==================================================
    def registrar_entrega_bodega(mat_nombre, cant, op_destino):
        for b in ['MATERIALES', 'ACCESORIOS', 'TRIPLE_A']:
            df_b = st.session_state.data[b]
            if mat_nombre in df_b['NOMBRE'].values:
                idx = df_b[df_b['NOMBRE'] == mat_nombre].index[0]
                if df_b.loc[idx, 'CANTIDAD'] >= cant:
                    # Restar de bodega
                    st.session_state.data[b].loc[idx, 'CANTIDAD'] -= cant
                    # Sumar a operario
                    df_o = st.session_state.data['OPERARIOS']
                    mask = (df_o['OPERARIO'] == op_destino) & (df_o['MATERIAL'] == mat_nombre)
                    if mask.any():
                        st.session_state.data['OPERARIOS'].loc[mask, 'CANTIDAD'] += cant
                    else:
                        nueva = pd.DataFrame([{'OPERARIO': op_destino, 'MATERIAL': mat_nombre, 'CANTIDAD': cant}])
                        st.session_state.data['OPERARIOS'] = pd.concat([df_o, nueva], ignore_index=True)
                    # Historial entrega
                    h_ent = pd.DataFrame([{'FECHA': datetime.now().strftime("%d/%m/%Y %H:%M"), 'OPERARIO': op_destino, 'MATERIAL': mat_nombre, 'CANTIDAD': cant}])
                    st.session_state.data['H_ENTREGAS'] = pd.concat([st.session_state.data['H_ENTREGAS'], h_ent], ignore_index=True)
                    return True
        return False

    # ==================================================
    # 3. INTERFAZ
    # ==================================================
    t1, t2, t3, t4, t5 = st.tabs(["🚚 Entregas", "📄 Registro Acta", "👷 Stock x Operario", "📜 Historiales", "💾 Exportar"])

    with t1:
        st.subheader("Bodega -> Operario")
        with st.form("f_ent", clear_on_submit=True):
            col1, col2 = st.columns(2)
            ops = sorted(st.session_state.data['OPERARIOS']['OPERARIO'].unique())
            op_n = col1.selectbox("Operario", ["NUEVO..."] + [x for x in ops if str(x) != 'nan'])
            if op_n == "NUEVO...": op_n = col1.text_input("Nombre Operario").upper().strip()
            mats_bod = pd.concat([st.session_state.data[b]['NOMBRE'] for b in ['MATERIALES', 'ACCESORIOS', 'TRIPLE_A']]).unique()
            m_sel = col2.selectbox("Material", sorted(mats_bod))
            c_sel = col2.number_input("Cantidad", min_value=1, step=1)
            if st.form_submit_button("Registrar Entrega"):
                if op_n and registrar_entrega_bodega(m_sel, c_sel, op_n):
                    st.success("✅ Entrega registrada")
                    st.rerun()

    with t2:
        st.subheader("Registro de Acta (Gasto del Operario)")
        df_operarios = st.session_state.data['OPERARIOS']
        # Filtramos solo los que tienen algo para mostrar en el select
        ops_con_stock = sorted(df_operarios[df_operarios['CANTIDAD'] > 0]['OPERARIO'].unique())
        
        if ops_con_stock:
            with st.form("f_acta", clear_on_submit=True):
                c1, c2 = st.columns(2)
                op_acta = c1.selectbox("Operario responsable", ops_con_stock)
                n_acta = c1.text_input("Número de Acta").upper().strip()
                mats_disp = df_operarios[(df_operarios['OPERARIO'] == op_acta) & (df_operarios['CANTIDAD'] > 0)]['MATERIAL'].unique()
                mat_acta = c2.selectbox("Material instalado", mats_disp)
                cant_acta = c2.number_input("Cantidad utilizada", min_value=1, step=1)
                
                if st.form_submit_button("💾 Guardar Acta"):
                    # BUSCAR LA FILA EXACTA EN LA BASE DE DATOS REAL
                    mask = (st.session_state.data['OPERARIOS']['OPERARIO'] == op_acta) & (st.session_state.data['OPERARIOS']['MATERIAL'] == mat_acta)
                    saldo_actual = st.session_state.data['OPERARIOS'].loc[mask, 'CANTIDAD'].values[0]
                    
                    if saldo_actual >= cant_acta:
                        # --- DESCUENTO REAL ---
                        st.session_state.data['OPERARIOS'].loc[mask, 'CANTIDAD'] -= cant_acta
                        
                        # Guardar Historial
                        h_acta = pd.DataFrame([{'FECHA': datetime.now().strftime("%d/%m/%Y %H:%M"), 'NUM_ACTA': n_acta, 'OPERARIO': op_acta, 'MATERIAL': mat_acta, 'CANTIDAD': cant_acta}])
                        st.session_state.data['H_ACTAS'] = pd.concat([st.session_state.data['H_ACTAS'], h_acta], ignore_index=True)
                        st.success(f"✅ Acta {n_acta} guardada. Saldo actualizado.")
                        st.rerun()
                    else:
                        st.error(f"Error: El operario solo tiene {saldo_actual} unidades.")
        else:
            st.info("No hay operarios con materiales asignados.")

    with t3:
        st.subheader("Inventario actual por Operario")
        df_view = st.session_state.data['OPERARIOS']
        if not df_view.empty:
            op_f = st.selectbox("Elegir Operario:", sorted(df_view['OPERARIO'].unique()))
            resumen = df_view[(df_view['OPERARIO'] == op_f) & (df_view['CANTIDAD'] > 0)]
            st.table(resumen[['MATERIAL', 'CANTIDAD']])
        else:
            st.info("No hay materiales en manos de operarios.")

    with t4:
        st.subheader("📜 Historial de Entregas")
        st.dataframe(st.session_state.data['H_ENTREGAS'], hide_index=True, use_container_width=True)
        st.subheader("📜 Historial de Actas")
        st.dataframe(st.session_state.data['H_ACTAS'], hide_index=True, use_container_width=True)

    with t5:
        st.subheader("Exportar")
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            st.session_state.data['MATERIALES'].to_excel(writer, sheet_name='MATERIALES ITA', index=False)
            st.session_state.data['ACCESORIOS'].to_excel(writer, sheet_name='ACCESORIOS ITA', index=False)
            st.session_state.data['TRIPLE_A'].to_excel(writer, sheet_name='INVENTARIO TRIPLE A', index=False)
            # Guardamos operarios quitando los que quedaron en 0 para limpiar el excel
            df_op_final = st.session_state.data['OPERARIOS']
            df_op_final[df_op_final['CANTIDAD'] > 0].to_excel(writer, sheet_name='OPERARIOS', index=False)
            st.session_state.data['H_ENTREGAS'].to_excel(writer, sheet_name='HISTORIAL_ENTREGAS', index=False)
            st.session_state.data['H_ACTAS'].to_excel(writer, sheet_name='HISTORIAL_ACTAS', index=False)
        st.download_button("📥 Descargar Reporte Final", buffer.getvalue(), "Inventario_ITA.xlsx")

else:
    st.info("👈 Sube tu archivo Excel para comenzar.")
