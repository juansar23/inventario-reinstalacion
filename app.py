import streamlit as st
import pandas as pd
import io
from datetime import datetime

st.set_page_config(page_title="Sistema ITA - Trazabilidad Total", layout="wide")

# ==================================================
# 1. CARGA Y NORMALIZACIÓN DE DATOS
# ==================================================
st.title("🛡️ Panel de Control ITA: Trazabilidad Total")

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

            # Cargar Operarios
            if 'OPERARIOS' in xls.sheet_names:
                df_op = pd.read_excel(archivo, sheet_name='OPERARIOS')
                df_op.columns = ['OPERARIO', 'MATERIAL', 'CANTIDAD'] + list(df_op.columns[3:])
                st.session_state.data['OPERARIOS'] = df_op.groupby(['OPERARIO', 'MATERIAL'], as_index=False)['CANTIDAD'].sum()
            else:
                st.session_state.data['OPERARIOS'] = pd.DataFrame(columns=['OPERARIO', 'MATERIAL', 'CANTIDAD'])

            # Historial de Entregas (BODEGA -> OPERARIO)
            if 'HISTORIAL_ENTREGAS' in xls.sheet_names:
                st.session_state.data['H_ENTREGAS'] = pd.read_excel(archivo, sheet_name='HISTORIAL_ENTREGAS')
            else:
                st.session_state.data['H_ENTREGAS'] = pd.DataFrame(columns=['FECHA', 'OPERARIO', 'MATERIAL', 'CANTIDAD'])

            # Historial de Actas (OPERARIO -> OBRA)
            if 'HISTORIAL_ACTAS' in xls.sheet_names:
                st.session_state.data['H_ACTAS'] = pd.read_excel(archivo, sheet_name='HISTORIAL_ACTAS')
            else:
                st.session_state.data['H_ACTAS'] = pd.DataFrame(columns=['FECHA', 'NUM_ACTA', 'OPERARIO', 'MATERIAL', 'CANTIDAD'])

        except Exception as e:
            st.error(f"Error al cargar: {e}")
            st.stop()

    # ==================================================
    # 2. LÓGICA DE MOVIMIENTOS
    # ==================================================
    def registrar_entrega(mat_nombre, cant, op_destino):
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
                    # Guardar en HISTORIAL DE ENTREGAS
                    h_ent = pd.DataFrame([{'FECHA': datetime.now().strftime("%d/%m/%Y %H:%M"), 'OPERARIO': op_destino, 'MATERIAL': mat_nombre, 'CANTIDAD': cant}])
                    st.session_state.data['H_ENTREGAS'] = pd.concat([st.session_state.data['H_ENTREGAS'], h_ent], ignore_index=True)
                    return True
        return False

    # ==================================================
    # 3. INTERFAZ
    # ==================================================
    t1, t2, t3, t4, t5 = st.tabs(["🚚 Entregas (Bodega)", "📄 Actas (Instalación)", "👷 Saldos Operarios", "📜 Historiales", "💾 Exportar"])

    with t1:
        st.subheader("Salida de Bodega a Operario")
        with st.form("f_ent", clear_on_submit=True):
            col1, col2 = st.columns(2)
            ops = sorted(st.session_state.data['OPERARIOS']['OPERARIO'].unique())
            op_n = col1.selectbox("Operario", ["NUEVO..."] + [x for x in ops if str(x) != 'nan'])
            if op_n == "NUEVO...": op_n = col1.text_input("Nombre Completo").upper().strip()
            
            mats = pd.concat([st.session_state.data[b]['NOMBRE'] for b in ['MATERIALES', 'ACCESORIOS', 'TRIPLE_A']]).unique()
            m_sel = col2.selectbox("Material", sorted(mats))
            c_sel = col2.number_input("Cantidad", min_value=1, step=1)
            
            if st.form_submit_button("Registrar Entrega"):
                if op_n and registrar_entrega(m_sel, c_sel, op_n):
                    st.success("✅ Entrega registrada")
                    st.rerun()

    with t2:
        st.subheader("Consumo por Acta")
        df_op = st.session_state.data['OPERARIOS']
        if not df_op.empty:
            with st.form("f_acta", clear_on_submit=True):
                c1, c2 = st.columns(2)
                op_acta = c1.selectbox("Operario responsable", sorted(df_op['OPERARIO'].unique()))
                n_acta = c1.text_input("Número de Acta").upper().strip()
                mat_acta = c2.selectbox("Material usado", df_op[df_op['OPERARIO'] == op_acta]['MATERIAL'].unique())
                cant_acta = c2.number_input("Cantidad gastada", min_value=1, step=1)
                
                if st.form_submit_button("💾 Guardar Acta"):
                    mask = (df_op['OPERARIO'] == op_acta) & (df_op['MATERIAL'] == mat_acta)
                    if df_op.loc[mask, 'CANTIDAD'].values[0] >= cant_acta:
                        st.session_state.data['OPERARIOS'].loc[mask, 'CANTIDAD'] -= cant_acta
                        reg_acta = pd.DataFrame([{'FECHA': datetime.now().strftime("%d/%m/%Y %H:%M"), 'NUM_ACTA': n_acta, 'OPERARIO': op_acta, 'MATERIAL': mat_acta, 'CANTIDAD': cant_acta}])
                        st.session_state.data['H_ACTAS'] = pd.concat([st.session_state.data['H_ACTAS'], reg_acta], ignore_index=True)
                        st.success("✅ Acta guardada")
                        st.rerun()
                    else: st.error("El operario no tiene suficiente material")

    with t3:
        st.subheader("Stock actual en manos de operarios")
        st.dataframe(st.session_state.data['OPERARIOS'][st.session_state.data['OPERARIOS']['CANTIDAD'] > 0], use_container_width=True, hide_index=True)

    with t4:
        c1, c2 = st.columns(2)
        c1.subheader("📜 Historial de Entregas")
        c1.dataframe(st.session_state.data['H_ENTREGAS'], hide_index=True)
        c2.subheader("📜 Historial de Actas")
        c2.dataframe(st.session_state.data['H_ACTAS'], hide_index=True)

    with t5:
        st.subheader("Generar Archivo Maestro")
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            st.session_state.data['MATERIALES'].to_excel(writer, sheet_name='MATERIALES ITA', index=False)
            st.session_state.data['ACCESORIOS'].to_excel(writer, sheet_name='ACCESORIOS ITA', index=False)
            st.session_state.data['TRIPLE_A'].to_excel(writer, sheet_name='INVENTARIO TRIPLE A', index=False)
            st.session_state.data['OPERARIOS'].to_excel(writer, sheet_name='OPERARIOS', index=False)
            st.session_state.data['H_ENTREGAS'].to_excel(writer, sheet_name='HISTORIAL_ENTREGAS', index=False)
            st.session_state.data['H_ACTAS'].to_excel(writer, sheet_name='HISTORIAL_ACTAS', index=False)
        st.download_button("📥 Descargar Reporte Completo", buffer.getvalue(), "Inventario_ITA_PRO.xlsx")

else:
    st.info("👈 Sube tu archivo Excel para comenzar.")
