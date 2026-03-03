import streamlit as st
import pandas as pd
import io
from datetime import datetime

st.set_page_config(page_title="Sistema ITA - Gestión Consolidada", layout="wide")

# ==================================================
# 1. CARGA Y CREACIÓN SEGURA DE DATOS
# ==================================================
st.title("🛡️ Panel de Control ITA")

archivo = st.sidebar.file_uploader("📂 Sube tu archivo Excel Maestro", type=["xlsx"])

if archivo:
    if 'data' not in st.session_state:
        try:
            xls = pd.ExcelFile(archivo)
            st.session_state.data = {}
            
            # --- CARGAR BODEGAS ---
            hojas_bodega = {'MATERIALES': 'MATERIALES ITA', 'ACCESORIOS': 'ACCESORIOS ITA', 'TRIPLE_A': 'INVENTARIO TRIPLE A'}
            for clave, nombre_hoja in hojas_bodega.items():
                if nombre_hoja in xls.sheet_names:
                    df = pd.read_excel(archivo, sheet_name=nombre_hoja)
                    df.columns = ['NOMBRE', 'CANTIDAD'] + list(df.columns[2:])
                    st.session_state.data[clave] = df

            # --- CARGAR OPERARIOS ---
            if 'OPERARIOS' in xls.sheet_names:
                df_op = pd.read_excel(archivo, sheet_name='OPERARIOS')
                # Forzamos los nombres de tus columnas: OPERARIO, MATERIAL, CANTIDAD
                df_op.columns = ['OPERARIO', 'MATERIAL', 'CANTIDAD'] + list(df_op.columns[3:])
                st.session_state.data['OPERARIOS'] = df_op
            else:
                st.session_state.data['OPERARIOS'] = pd.DataFrame(columns=['OPERARIO', 'MATERIAL', 'CANTIDAD'])

            # --- HISTORIALES ---
            if 'HISTORIAL_ENTREGAS' in xls.sheet_names:
                st.session_state.data['H_ENTREGAS'] = pd.read_excel(archivo, sheet_name='HISTORIAL_ENTREGAS')
            else:
                st.session_state.data['H_ENTREGAS'] = pd.DataFrame(columns=['FECHA', 'OPERARIO', 'MATERIAL', 'CANTIDAD'])

            if 'HISTORIAL_ACTAS' in xls.sheet_names:
                st.session_state.data['H_ACTAS'] = pd.read_excel(archivo, sheet_name='HISTORIAL_ACTAS')
            else:
                st.session_state.data['H_ACTAS'] = pd.DataFrame(columns=['FECHA', 'NUM_ACTA', 'OPERARIO', 'MATERIAL', 'CANTIDAD'])

            st.success("✅ Sistema Sincronizado")

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
                    st.session_state.data[b].loc[idx, 'CANTIDAD'] -= cant
                    
                    # Agregar al inventario del operario
                    nueva_entrega = pd.DataFrame([{'OPERARIO': op_destino, 'MATERIAL': mat_nombre, 'CANTIDAD': cant}])
                    st.session_state.data['OPERARIOS'] = pd.concat([st.session_state.data['OPERARIOS'], nueva_entrega], ignore_index=True)
                    
                    # Registro en historial
                    h_ent = pd.DataFrame([{'FECHA': datetime.now().strftime("%d/%m/%Y %H:%M"), 'OPERARIO': op_destino, 'MATERIAL': mat_nombre, 'CANTIDAD': cant}])
                    st.session_state.data['H_ENTREGAS'] = pd.concat([st.session_state.data['H_ENTREGAS'], h_ent], ignore_index=True)
                    return True
        return False

    # ==================================================
    # 3. INTERFAZ (TABS)
    # ==================================================
    t1, t2, t3, t4, t5 = st.tabs(["🚚 Entregas (Bodega)", "📄 Actas (Instalación)", "👷 Saldos Operarios", "📜 Historiales", "💾 Exportar"])

    with t1:
        st.subheader("Salida de Bodega a Operario")
        with st.form("f_ent", clear_on_submit=True):
            col1, col2 = st.columns(2)
            ops = sorted(st.session_state.data['OPERARIOS']['OPERARIO'].unique().tolist())
            op_n = col1.selectbox("Operario", ["NUEVO..."] + [str(x) for x in ops if str(x) != 'nan'])
            if op_n == "NUEVO...": op_n = col1.text_input("Nombre Operario").upper().strip()
            
            mats = pd.concat([st.session_state.data[b]['NOMBRE'] for b in ['MATERIALES', 'ACCESORIOS', 'TRIPLE_A']]).unique()
            m_sel = col2.selectbox("Material", sorted(mats))
            c_sel = col2.number_input("Cantidad", min_value=1, step=1)
            
            if st.form_submit_button("Registrar Entrega"):
                if op_n and registrar_entrega(m_sel, c_sel, op_n):
                    st.success("✅ Entrega registrada")
                    st.rerun()

    with t2:
        st.subheader("Consumo por Acta")
        # Aquí consolidamos temporalmente para saber cuánto tiene el operario en total
        df_temp = st.session_state.data['OPERARIOS'].groupby(['OPERARIO', 'MATERIAL'], as_index=False)['CANTIDAD'].sum()
        
        if not df_temp.empty:
            with st.form("f_acta", clear_on_submit=True):
                c1, c2 = st.columns(2)
                op_acta = c1.selectbox("Operario", sorted(df_temp['OPERARIO'].unique()))
                n_acta = c1.text_input("Número de Acta").upper().strip()
                mat_acta = c2.selectbox("Material", df_temp[df_temp['OPERARIO'] == op_acta]['MATERIAL'].unique())
                cant_acta = c2.number_input("Cantidad", min_value=1, step=1)
                
                if st.form_submit_button("💾 Guardar Acta"):
                    saldo_actual = df_temp[(df_temp['OPERARIO'] == op_acta) & (df_temp['MATERIAL'] == mat_acta)]['CANTIDAD'].values[0]
                    if saldo_actual >= cant_acta:
                        # Restamos creando una fila negativa (es más seguro para el historial)
                        resta = pd.DataFrame([{'OPERARIO': op_acta, 'MATERIAL': mat_acta, 'CANTIDAD': -cant_acta}])
                        st.session_state.data['OPERARIOS'] = pd.concat([st.session_state.data['OPERARIOS'], resta], ignore_index=True)
                        
                        # Guardar Historial Actas
                        reg_acta = pd.DataFrame([{'FECHA': datetime.now().strftime("%d/%m/%Y %H:%M"), 'NUM_ACTA': n_acta, 'OPERARIO': op_acta, 'MATERIAL': mat_acta, 'CANTIDAD': cant_acta}])
                        st.session_state.data['H_ACTAS'] = pd.concat([st.session_state.data['H_ACTAS'], reg_acta], ignore_index=True)
                        st.success("✅ Acta guardada")
                        st.rerun()
                    else: st.error("Saldo insuficiente")

    with t3:
        st.subheader("Saldos Consolidados por Operario")
        # --- AQUÍ ESTÁ EL TRUCO: AGRUPAMOS POR NOMBRE Y MATERIAL ANTES DE MOSTRAR ---
        df_saldos = st.session_state.data['OPERARIOS'].groupby(['OPERARIO', 'MATERIAL'], as_index=False)['CANTIDAD'].sum()
        # Solo mostrar lo que tiene cantidad mayor a 0
        df_saldos = df_saldos[df_saldos['CANTIDAD'] > 0]
        
        st.dataframe(df_saldos, use_container_width=True, hide_index=True)

    with t4:
        st.subheader("📜 Historial de Entregas")
        st.dataframe(st.session_state.data['H_ENTREGAS'], hide_index=True, use_container_width=True)
        st.subheader("📜 Historial de Actas")
        st.dataframe(st.session_state.data['H_ACTAS'], hide_index=True, use_container_width=True)

    with t5:
        st.subheader("Exportar")
        buffer = io.BytesIO()
        # Antes de exportar, consolidamos la hoja de operarios para que el Excel baje limpio
        df_final_ops = st.session_state.data['OPERARIOS'].groupby(['OPERARIO', 'MATERIAL'], as_index=False)['CANTIDAD'].sum()
        df_final_ops = df_final_ops[df_final_ops['CANTIDAD'] != 0]

        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            st.session_state.data['MATERIALES'].to_excel(writer, sheet_name='MATERIALES ITA', index=False)
            st.session_state.data['ACCESORIOS'].to_excel(writer, sheet_name='ACCESORIOS ITA', index=False)
            st.session_state.data['TRIPLE_A'].to_excel(writer, sheet_name='INVENTARIO TRIPLE A', index=False)
            df_final_ops.to_excel(writer, sheet_name='OPERARIOS', index=False)
            st.session_state.data['H_ENTREGAS'].to_excel(writer, sheet_name='HISTORIAL_ENTREGAS', index=False)
            st.session_state.data['H_ACTAS'].to_excel(writer, sheet_name='HISTORIAL_ACTAS', index=False)
        st.download_button("📥 Descargar Reporte", buffer.getvalue(), "Inventario_Final_ITA.xlsx")

else:
    st.info("👈 Sube tu archivo Excel para comenzar.")
