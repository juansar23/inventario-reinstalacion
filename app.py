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
            
            # 1. Cargar Bodegas
            hojas_bodega = {
                'MATERIALES': 'MATERIALES ITA',
                'ACCESORIOS': 'ACCESORIOS ITA',
                'TRIPLE_A': 'INVENTARIO TRIPLE A'
            }
            
            for clave, nombre_hoja in hojas_bodega.items():
                if nombre_hoja in xls.sheet_names:
                    df = pd.read_excel(archivo, sheet_name=nombre_hoja)
                    df.columns = ['NOMBRE', 'CANTIDAD'] + list(df.columns[2:])
                    st.session_state.data[clave] = df
                else:
                    st.error(f"No se encontró la pestaña: {nombre_hoja}")
                    st.stop()

            # 2. Cargar Operarios (OPERARIO, MATERIAL, CANTIDAD)
            if 'OPERARIOS' in xls.sheet_names:
                df_op = pd.read_excel(archivo, sheet_name='OPERARIOS')
                df_op.columns = ['OPERARIO', 'MATERIAL', 'CANTIDAD'] + list(df_op.columns[3:])
                df_op['OPERARIO'] = df_op['OPERARIO'].astype(str).str.strip().str.upper()
                df_op['MATERIAL'] = df_op['MATERIAL'].astype(str).str.strip().str.upper()
                # Consolidamos al cargar
                st.session_state.data['OPERARIOS'] = df_op.groupby(['OPERARIO', 'MATERIAL'], as_index=False)['CANTIDAD'].sum()
            else:
                st.session_state.data['OPERARIOS'] = pd.DataFrame(columns=['OPERARIO', 'MATERIAL', 'CANTIDAD'])

            # 3. Cargar o Crear Historiales
            if 'HISTORIAL_ENTREGAS' in xls.sheet_names:
                st.session_state.data['H_ENTREGAS'] = pd.read_excel(archivo, sheet_name='HISTORIAL_ENTREGAS')
            else:
                st.session_state.data['H_ENTREGAS'] = pd.DataFrame(columns=['FECHA', 'OPERARIO', 'MATERIAL', 'CANTIDAD'])

            if 'HISTORIAL_ACTAS' in xls.sheet_names:
                st.session_state.data['H_ACTAS'] = pd.read_excel(archivo, sheet_name='HISTORIAL_ACTAS')
            else:
                st.session_state.data['H_ACTAS'] = pd.DataFrame(columns=['FECHA', 'NUM_ACTA', 'OPERARIO', 'MATERIAL', 'CANTIDAD'])

            st.success("✅ Datos cargados y normalizados")

        except Exception as e:
            st.error(f"Error al cargar: {e}")
            st.stop()

    # ==================================================
    # 2. LÓGICA DE MOVIMIENTOS
    # ==================================================
    def mover_a_operario(nombre_mat, cant, op_destino):
        for b in ['MATERIALES', 'ACCESORIOS', 'TRIPLE_A']:
            df_b = st.session_state.data[b]
            if nombre_mat in df_b['NOMBRE'].values:
                idx = df_b[df_b['NOMBRE'] == nombre_mat].index[0]
                if df_b.loc[idx, 'CANTIDAD'] >= cant:
                    # Descontar de bodega
                    st.session_state.data[b].loc[idx, 'CANTIDAD'] -= cant
                    
                    # Sumar a operario (Consolidando)
                    df_o = st.session_state.data['OPERARIOS']
                    mask = (df_o['OPERARIO'] == op_destino) & (df_o['MATERIAL'] == nombre_mat)
                    if mask.any():
                        st.session_state.data['OPERARIOS'].loc[mask, 'CANTIDAD'] += cant
                    else:
                        nueva = pd.DataFrame([{'OPERARIO': op_destino, 'MATERIAL': nombre_mat, 'CANTIDAD': cant}])
                        st.session_state.data['OPERARIOS'] = pd.concat([df_o, nueva], ignore_index=True)
                    
                    # Registrar Historial de Entrega
                    h_ent = pd.DataFrame([{'FECHA': datetime.now().strftime("%d/%m/%Y %H:%M"), 'OPERARIO': op_destino, 'MATERIAL': nombre_mat, 'CANTIDAD': cant}])
                    st.session_state.data['H_ENTREGAS'] = pd.concat([st.session_state.data['H_ENTREGAS'], h_ent], ignore_index=True)
                    return True
        return False

    # ==================================================
    # 3. INTERFAZ
    # ==================================================
    t1, t2, t3, t4, t5 = st.tabs(["🚚 Entregas", "📄 Registro Acta", "👷 Stock x Operario", "📜 Historiales", "💾 Exportar"])

    with t1:
        st.subheader("Entrega de Material (Bodega -> Operario)")
        with st.form("f_entrega", clear_on_submit=True):
            col1, col2 = st.columns(2)
            ops_actuales = sorted(st.session_state.data['OPERARIOS']['OPERARIO'].unique())
            op_nombre = col1.selectbox("Seleccione Operario", ["NUEVO..."] + [x for x in ops_actuales if str(x) != 'nan'])
            if op_nombre == "NUEVO...":
                op_nombre = col1.text_input("Nombre del operario").upper().strip()
            
            mats_bodega = pd.concat([st.session_state.data[b]['NOMBRE'] for b in ['MATERIALES', 'ACCESORIOS', 'TRIPLE_A']]).unique()
            mat_sel = col2.selectbox("Seleccione Material", sorted(mats_bodega))
            cant_sel = col2.number_input("Cantidad", min_value=1, step=1)
            
            if st.form_submit_button("Registrar Entrega"):
                if op_nombre and mover_a_operario(mat_sel, cant_sel, op_nombre):
                    st.success("✅ Entrega registrada")
                    st.rerun()

    with t2:
        st.subheader("Uso de Material (Operario -> Acta/Obra)")
        df_op_acta = st.session_state.data['OPERARIOS']
        if not df_op_acta.empty:
            with st.form("f_acta", clear_on_submit=True):
                c1, c2 = st.columns(2)
                op_sel_acta = c1.selectbox("Operario", sorted(df_op_acta['OPERARIO'].unique()))
                n_acta = c1.text_input("Número de Acta").upper().strip()
                
                mats_del_op = df_op_acta[df_op_acta['OPERARIO'] == op_sel_acta]['MATERIAL'].unique()
                mat_sel_acta = c2.selectbox("Material usado", mats_del_op)
                cant_sel_acta = c2.number_input("Cantidad utilizada", min_value=1, step=1)
                
                if st.form_submit_button("Guardar Acta"):
                    mask = (df_op_acta['OPERARIO'] == op_sel_acta) & (df_op_acta['MATERIAL'] == mat_sel_acta)
                    if df_op_acta.loc[mask, 'CANTIDAD'].values[0] >= cant_sel_acta:
                        # Descontar al operario
                        st.session_state.data['OPERARIOS'].loc[mask, 'CANTIDAD'] -= cant_sel_acta
                        # Registrar Historial Acta
                        h_acta = pd.DataFrame([{
                            'FECHA': datetime.now().strftime("%d/%m/%Y %H:%M"),
                            'NUM_ACTA': n_acta,
                            'OPERARIO': op_sel_acta,
                            'MATERIAL': mat_sel_acta,
                            'CANTIDAD': cant_sel_acta
                        }])
                        st.session_state.data['H_ACTAS'] = pd.concat([st.session_state.data['H_ACTAS'], h_acta], ignore_index=True)
                        st.success("✅ Acta registrada")
                        st.rerun()
                    else: st.error("El operario no tiene suficiente saldo de este material")

    with t3:
        st.subheader("Consulta de Inventario por Operario")
        df_view = st.session_state.data['OPERARIOS']
        if not df_view.empty:
            op_f = st.selectbox("Elegir Operario:", sorted(df_view['OPERARIO'].unique()))
            resumen = df_view[(df_view['OPERARIO'] == op_f) & (df_view['CANTIDAD'] > 0)]
            st.table(resumen[['MATERIAL', 'CANTIDAD']])
        else:
            st.info("No hay datos en la hoja de operarios.")

    with t4:
        st.subheader("📜 Historial de Entregas (Bodega)")
        st.dataframe(st.session_state.data['H_ENTREGAS'], hide_index=True, use_container_width=True)
        st.subheader("📜 Historial de Actas (Consumo)")
        st.dataframe(st.session_state.data['H_ACTAS'], hide_index=True, use_container_width=True)

    with t5:
        st.subheader("Descargar Resultados")
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            st.session_state.data['MATERIALES'].to_excel(writer, sheet_name='MATERIALES ITA', index=False)
            st.session_state.data['ACCESORIOS'].to_excel(writer, sheet_name='ACCESORIOS ITA', index=False)
            st.session_state.data['TRIPLE_A'].to_excel(writer, sheet_name='INVENTARIO TRIPLE A', index=False)
            st.session_state.data['OPERARIOS'].to_excel(writer, sheet_name='OPERARIOS', index=False)
            st.session_state.data['H_ENTREGAS'].to_excel(writer, sheet_name='HISTORIAL_ENTREGAS', index=False)
            st.session_state.data['H_ACTAS'].to_excel(writer, sheet_name='HISTORIAL_ACTAS', index=False)
        
        st.download_button("📥 Descargar Excel Actualizado", buffer.getvalue(), "Inventario_ITA_PRO.xlsx")

else:
    st.info("👈 Sube tu archivo Excel para activar el sistema.")
