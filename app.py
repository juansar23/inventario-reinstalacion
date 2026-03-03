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
                # Agrupamos para que no haya filas repetidas al cargar
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
    # 2. INTERFAZ (TABS)
    # ==================================================
    t1, t2, t3, t4, t5 = st.tabs(["🚚 Entregas", "📄 Registro Acta", "👷 Stock x Operario", "📜 Historiales", "💾 Exportar"])

    with t1:
        st.subheader("Bodega -> Operario")
        with st.form("f_ent", clear_on_submit=True):
            col1, col2 = st.columns(2)
            ops = sorted(st.session_state.data['OPERARIOS']['OPERARIO'].unique())
            op_n = col1.selectbox("Operario Destino", ["NUEVO..."] + [x for x in ops if str(x) != 'nan'])
            if op_n == "NUEVO...": op_n = col1.text_input("Nombre Operario").upper().strip()
            
            mats_bod = pd.concat([st.session_state.data[b]['NOMBRE'] for b in ['MATERIALES', 'ACCESORIOS', 'TRIPLE_A']]).unique()
            m_sel = col2.selectbox("Material de Bodega", sorted(mats_bod))
            c_sel = col2.number_input("Cantidad a Entregar", min_value=1, step=1)
            
            if st.form_submit_button("Registrar Entrega"):
                # Lógica de entrega directa
                exito = False
                for b in ['MATERIALES', 'ACCESORIOS', 'TRIPLE_A']:
                    df_b = st.session_state.data[b]
                    if m_sel in df_b['NOMBRE'].values:
                        idx = df_b[df_b['NOMBRE'] == m_sel].index[0]
                        if df_b.loc[idx, 'CANTIDAD'] >= c_sel:
                            st.session_state.data[b].loc[idx, 'CANTIDAD'] -= c_sel
                            df_o = st.session_state.data['OPERARIOS']
                            mask = (df_o['OPERARIO'] == op_n) & (df_o['MATERIAL'] == m_sel)
                            if mask.any():
                                st.session_state.data['OPERARIOS'].loc[mask, 'CANTIDAD'] += c_sel
                            else:
                                nueva = pd.DataFrame([{'OPERARIO': op_n, 'MATERIAL': m_sel, 'CANTIDAD': c_sel}])
                                st.session_state.data['OPERARIOS'] = pd.concat([df_o, nueva], ignore_index=True)
                            
                            h_ent = pd.DataFrame([{'FECHA': datetime.now().strftime("%d/%m/%Y %H:%M"), 'OPERARIO': op_n, 'MATERIAL': m_sel, 'CANTIDAD': c_sel}])
                            st.session_state.data['H_ENTREGAS'] = pd.concat([st.session_state.data['H_ENTREGAS'], h_ent], ignore_index=True)
                            exito = True
                            break
                if exito: st.success("✅ Entrega registrada"); st.rerun()
                else: st.error("No hay stock suficiente en bodega")

    with t2:
        st.subheader("Registro de Acta (Gasto del Operario)")
        df_inv = st.session_state.data['OPERARIOS']
        ops_actas = sorted(df_inv[df_inv['CANTIDAD'] > 0]['OPERARIO'].unique())
        
        if ops_actas:
            # Seleccionar operario fuera del form para actualizar la lista de materiales dinámicamente
            op_acta_sel = st.selectbox("1. Seleccione Operario responsable", ops_actas)
            
            # Filtrar materiales que tiene ese operario específico
            mats_op_disp = df_inv[(df_inv['OPERARIO'] == op_acta_sel) & (df_inv['CANTIDAD'] > 0)]['MATERIAL'].unique()
            
            with st.form("f_registro_acta", clear_on_submit=True):
                c1, c2 = st.columns(2)
                # Aquí está la clave: usamos la lista filtrada de materiales de ESE operario
                mat_acta_sel = c1.selectbox("2. Material que instaló", sorted(mats_op_disp))
                cant_acta_sel = c1.number_input("3. Cantidad utilizada", min_value=1, step=1)
                n_acta_val = c2.text_input("4. Número de Acta").upper().strip()
                
                if st.form_submit_button("💾 Guardar y Descontar del Operario"):
                    if n_acta_val:
                        # Buscamos la fila exacta usando el nombre del operario Y el nombre del material
                        df_real = st.session_state.data['OPERARIOS']
                        mask = (df_real['OPERARIO'] == op_acta_sel) & (df_real['MATERIAL'] == mat_acta_sel)
                        
                        if mask.any():
                            saldo = df_real.loc[mask, 'CANTIDAD'].values[0]
                            if saldo >= cant_acta_sel:
                                # DESCUENTO REAL
                                st.session_state.data['OPERARIOS'].loc[mask, 'CANTIDAD'] -= cant_acta_sel
                                
                                # GUARDAR HISTORIAL
                                nueva_acta = pd.DataFrame([{
                                    'FECHA': datetime.now().strftime("%d/%m/%Y %H:%M"),
                                    'NUM_ACTA': n_acta_val,
                                    'OPERARIO': op_acta_sel,
                                    'MATERIAL': mat_acta_sel,
                                    'CANTIDAD': cant_acta_sel
                                }])
                                st.session_state.data['H_ACTAS'] = pd.concat([st.session_state.data['H_ACTAS'], nueva_acta], ignore_index=True)
                                st.success(f"✅ Se descontaron {cant_acta_sel} unidades de '{mat_acta_sel}' a {op_acta_sel}")
                                st.rerun()
                            else:
                                st.error(f"El operario solo tiene {saldo} de este material.")
                    else:
                        st.warning("Debe ingresar un número de acta.")
        else:
            st.info("No hay operarios con stock disponible.")

    with t3:
        st.subheader("Saldos Actuales por Operario")
        df_v = st.session_state.data['OPERARIOS']
        if not df_v.empty:
            op_f = st.selectbox("Consultar Operario:", sorted(df_v['OPERARIO'].unique()))
            resumen = df_v[(df_v['OPERARIO'] == op_f) & (df_v['CANTIDAD'] > 0)]
            st.table(resumen[['MATERIAL', 'CANTIDAD']])
        else:
            st.info("Sin datos.")

    with t4:
        st.subheader("📜 Historiales")
        col_h1, col_h2 = st.columns(2)
        col_h1.write("Entregas de Bodega")
        col_h1.dataframe(st.session_state.data['H_ENTREGAS'], hide_index=True)
        col_h2.write("Registro de Actas")
        col_h2.dataframe(st.session_state.data['H_ACTAS'], hide_index=True)

    with t5:
        st.subheader("Exportar Excel")
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            st.session_state.data['MATERIALES'].to_excel(writer, sheet_name='MATERIALES ITA', index=False)
            st.session_state.data['ACCESORIOS'].to_excel(writer, sheet_name='ACCESORIOS ITA', index=False)
            st.session_state.data['TRIPLE_A'].to_excel(writer, sheet_name='INVENTARIO TRIPLE A', index=False)
            # Solo guardamos los que tienen saldo
            df_ops_save = st.session_state.data['OPERARIOS']
            df_ops_save[df_ops_save['CANTIDAD'] > 0].to_excel(writer, sheet_name='OPERARIOS', index=False)
            st.session_state.data['H_ENTREGAS'].to_excel(writer, sheet_name='HISTORIAL_ENTREGAS', index=False)
            st.session_state.data['H_ACTAS'].to_excel(writer, sheet_name='HISTORIAL_ACTAS', index=False)
        st.download_button("📥 Descargar Reporte Final", buffer.getvalue(), "Inventario_ITA.xlsx")

else:
    st.info("👈 Sube tu archivo Excel para comenzar.")
