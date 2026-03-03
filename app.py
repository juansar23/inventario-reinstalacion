import streamlit as st
import pandas as pd
import io
from datetime import datetime

st.set_page_config(page_title="Sistema ITA - Control Operarios", layout="wide")

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
            
            # 1. Cargar Bodegas (NOMBRE, CANTIDAD)
            hojas_bodega = {
                'MATERIALES': 'MATERIALES ITA',
                'ACCESORIOS': 'ACCESORIOS ITA',
                'TRIPLE_A': 'INVENTARIO TRIPLE A'
            }
            
            for clave, nombre_hoja in hojas_bodega.items():
                if nombre_hoja in xls.sheet_names:
                    df = pd.read_excel(archivo, sheet_name=nombre_hoja)
                    # Aseguramos nombres de columnas para bodega
                    df.columns = ['NOMBRE', 'CANTIDAD'] + list(df.columns[2:])
                    st.session_state.data[clave] = df
                else:
                    st.error(f"No se encontró la pestaña: {nombre_hoja}")
                    st.stop()

            # 2. Cargar Operarios (OPERARIO, MATERIAL, CANTIDAD)
            if 'OPERARIOS' in xls.sheet_names:
                df_op = pd.read_excel(archivo, sheet_name='OPERARIOS')
                # Forzamos los encabezados que tú tienes
                df_op.columns = ['OPERARIO', 'MATERIAL', 'CANTIDAD'] + list(df_op.columns[3:])
                
                # Limpieza: quitar espacios y convertir a mayúsculas
                df_op['OPERARIO'] = df_op['OPERARIO'].astype(str).str.strip().str.upper()
                df_op['MATERIAL'] = df_op['MATERIAL'].astype(str).str.strip().str.upper()
                
                # Consolidar: Si alguien aparece repetido con el mismo material, sumamos
                st.session_state.data['OPERARIOS'] = df_op.groupby(['OPERARIO', 'MATERIAL'], as_index=False)['CANTIDAD'].sum()
            else:
                st.session_state.data['OPERARIOS'] = pd.DataFrame(columns=['OPERARIO', 'MATERIAL', 'CANTIDAD'])

            st.session_state.data['HISTORIAL'] = pd.DataFrame(columns=['FECHA', 'OPERARIO', 'MATERIAL', 'CANTIDAD', 'NUM_ACTA'])
            st.success("✅ Excel cargado correctamente con encabezados: OPERARIO, MATERIAL, CANTIDAD")

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
                    
                    # Sumar a operario
                    df_o = st.session_state.data['OPERARIOS']
                    mask = (df_o['OPERARIO'] == op_destino) & (df_o['MATERIAL'] == nombre_mat)
                    
                    if mask.any():
                        st.session_state.data['OPERARIOS'].loc[mask, 'CANTIDAD'] += cant
                    else:
                        nueva = pd.DataFrame([{'OPERARIO': op_destino, 'MATERIAL': nombre_mat, 'CANTIDAD': cant}])
                        st.session_state.data['OPERARIOS'] = pd.concat([df_o, nueva], ignore_index=True)
                    return True
        return False

    # ==================================================
    # 3. INTERFAZ
    # ==================================================
    t1, t2, t3, t4 = st.tabs(["🚚 Entregas", "👷 Stock x Operario", "📦 Bodegas", "💾 Exportar"])

    with t1:
        st.subheader("Entrega de Material")
        with st.form("f_entrega", clear_on_submit=True):
            col1, col2 = st.columns(2)
            ops_actuales = sorted(st.session_state.data['OPERARIOS']['OPERARIO'].unique())
            op_nombre = col1.selectbox("Seleccione Operario", ["NUEVO..."] + [x for x in ops_actuales if x != 'NAN'])
            if op_nombre == "NUEVO...":
                op_nombre = col1.text_input("Escriba nombre del operario").upper().strip()
            
            # Unificar materiales de todas las bodegas para el buscador
            mats_bodega = pd.concat([st.session_state.data[b]['NOMBRE'] for b in ['MATERIALES', 'ACCESORIOS', 'TRIPLE_A']]).unique()
            mat_sel = col2.selectbox("Seleccione Material", sorted(mats_bodega))
            cant_sel = col2.number_input("Cantidad", min_value=1, step=1)
            
            if st.form_submit_button("Registrar Movimiento"):
                if op_nombre and mover_a_operario(mat_sel, cant_sel, op_nombre):
                    st.success("✅ Registrado con éxito")
                    st.rerun()

    with t2:
        st.subheader("Consulta de Inventario por Operario")
        df_view = st.session_state.data['OPERARIOS']
        if not df_view.empty:
            op_f = st.selectbox("Elegir Operario:", sorted(df_view['OPERARIO'].unique()))
            # Filtro por operario y mostramos columnas exactas: MATERIAL y CANTIDAD
            resumen = df_view[df_view['OPERARIO'] == op_f]
            st.table(resumen[['MATERIAL', 'CANTIDAD']])
        else:
            st.info("No hay datos en la hoja de operarios.")

    with t3:
        c1, c2, c3 = st.columns(3)
        c1.write("**Materiales ITA**"); c1.dataframe(st.session_state.data['MATERIALES'], hide_index=True)
        c2.write("**Accesorios ITA**"); c2.dataframe(st.session_state.data['ACCESORIOS'], hide_index=True)
        c3.write("**Inventario Triple A**"); c3.dataframe(st.session_state.data['TRIPLE_A'], hide_index=True)

    with t4:
        st.subheader("Descargar Resultados")
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            st.session_state.data['MATERIALES'].to_excel(writer, sheet_name='MATERIALES ITA', index=False)
            st.session_state.data['ACCESORIOS'].to_excel(writer, sheet_name='ACCESORIOS ITA', index=False)
            st.session_state.data['TRIPLE_A'].to_excel(writer, sheet_name='INVENTARIO TRIPLE A', index=False)
            st.session_state.data['OPERARIOS'].to_excel(writer, sheet_name='OPERARIOS', index=False)
        
        st.download_button("📥 Descargar Excel Actualizado", buffer.getvalue(), "Inventario_ITA_Final.xlsx")

else:
    st.info("👈 Sube tu archivo Excel para activar el sistema.")
