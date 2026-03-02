import streamlit as st
import pandas as pd
import io
from datetime import datetime

st.set_page_config(page_title="Sistema ITA - Control Total", layout="wide")

# ==================================================
# 1. CARGA DE ARCHIVO POR USUARIO
# ==================================================
st.title("🛡️ Panel de Control ITA")

# Selector de archivo en la barra lateral
archivo_subido = st.sidebar.file_uploader("Sube tu archivo Excel de Inventario", type=["xlsx"])

if archivo_subido:
    # Solo inicializamos si no están los datos cargados en la sesión
    if 'data' not in st.session_state:
        try:
            # Leer todas las hojas del Excel subido
            excel = pd.ExcelFile(archivo_subido)
            nombres_hojas = excel.sheet_names
            
            st.session_state.data = {}
            
            # Mapeo de hojas obligatorias (Asegúrate que coincidan con tus nombres de Excel)
            hojas_requeridas = {
                'MATERIALES': 'MATERIALES ITA',
                'ACCESORIOS': 'ACCESORIOS ITA',
                'TRIPLE_A': 'INVENTARIO TRIPLE A'
            }
            
            for clave, nombre_hoja in hojas_requeridas.items():
                if nombre_hoja in nombres_hojas:
                    st.session_state.data[clave] = pd.read_excel(archivo_subido, sheet_name=nombre_hoja)
                else:
                    st.error(f"⚠️ No se encontró la hoja: {nombre_hoja}")
                    st.stop()

            # Cargar u Operarios
            if 'OPERARIOS' in nombres_hojas:
                st.session_state.data['OPERARIOS'] = pd.read_excel(archivo_subido, sheet_name='OPERARIOS')
            else:
                st.session_state.data['OPERARIOS'] = pd.DataFrame(columns=['OPERARIO', 'NOMBRE', 'CANTIDAD'])
            
            # Cargar o crear Historial
            if 'HISTORIAL_ACTAS' in nombres_hojas:
                st.session_state.data['HISTORIAL_ACTAS'] = pd.read_excel(archivo_subido, sheet_name='HISTORIAL_ACTAS')
            else:
                st.session_state.data['HISTORIAL_ACTAS'] = pd.DataFrame(columns=['FECHA', 'OPERARIO', 'MATERIAL', 'CANTIDAD', 'NUM_ACTA'])

        except Exception as e:
            st.error(f"Error al procesar el Excel: {e}")
            st.stop()

    # ==================================================
    # 2. LÓGICA DE MOVIMIENTOS
    # ==================================================
    def transferir_a_operario(nombre_material, cant, operario_destino):
        for tabla in ['MATERIALES', 'ACCESORIOS', 'TRIPLE_A']:
            df = st.session_state.data[tabla]
            if nombre_material in df['NOMBRE'].values:
                idx = df[df['NOMBRE'] == nombre_material].index[0]
                if df.loc[idx, 'CANTIDAD'] >= cant:
                    # Descontar de bodega
                    st.session_state.data[tabla].loc[idx, 'CANTIDAD'] -= cant
                    
                    # Sumar a operario
                    df_op = st.session_state.data['OPERARIOS']
                    mask = (df_op['OPERARIO'] == operario_destino) & (df_op['NOMBRE'] == nombre_material)
                    if mask.any():
                        st.session_state.data['OPERARIOS'].loc[mask, 'CANTIDAD'] += cant
                    else:
                        nueva = pd.DataFrame([{'OPERARIO': operario_destino, 'NOMBRE': nombre_material, 'CANTIDAD': cant}])
                        st.session_state.data['OPERARIOS'] = pd.concat([df_op, nueva], ignore_index=True)
                    st.success(f"✅ Entregado: {cant} {nombre_material} a {operario_destino}")
                    return True
        st.error("Stock insuficiente o material no encontrado.")
        return False

    # ==================================================
    # 3. INTERFAZ (TABS)
    # ==================================================
    t1, t2, t3, t4, t5, t6 = st.tabs(["🚚 Entregas", "📄 Actas", "👷 Stock Operarios", "📜 Historial", "📦 Bodegas", "💾 Exportar"])

    with t1:
        st.subheader("Entregar de Bodega a Operario")
        with st.form("f_entrega", clear_on_submit=True):
            op_nom = st.text_input("Nombre del Operario").upper()
            lista_bodega = pd.concat([st.session_state.data[t]['NOMBRE'] for t in ['MATERIALES', 'ACCESORIOS', 'TRIPLE_A']]).unique()
            mat_sel = st.selectbox("Material", sorted(lista_bodega))
            cant = st.number_input("Cantidad a entregar", min_value=1, step=1)
            if st.form_submit_button("Ejecutar Entrega"):
                if op_nom:
                    transferir_a_operario(mat_sel, cant, op_nom)
                    st.rerun()
                else: st.warning("Escribe el nombre del operario")

    with t2:
        st.subheader("Registrar Acta de Consumo")
        df_op = st.session_state.data['OPERARIOS']
        if not df_op.empty:
            with st.form("f_acta", clear_on_submit=True):
                op_sel = st.selectbox("Operario", sorted(df_op['OPERARIO'].unique()))
                mats_op = df_op[df_op['OPERARIO'] == op_sel]['NOMBRE'].unique()
                mat_acta = st.selectbox("Material instalado", mats_op)
                cant_acta = st.number_input("Cantidad utilizada", min_value=1, step=1)
                n_acta = st.text_input("Número de Acta").upper()
                
                if st.form_submit_button("Registrar Acta"):
                    mask = (df_op['OPERARIO'] == op_sel) & (df_op['NOMBRE'] == mat_acta)
                    if df_op.loc[mask, 'CANTIDAD'].values[0] >= cant_acta:
                        # Restar a operario
                        st.session_state.data['OPERARIOS'].loc[mask, 'CANTIDAD'] -= cant_acta
                        # Guardar historial
                        nuevo_h = pd.DataFrame([{
                            'FECHA': datetime.now().strftime("%d/%m/%Y"),
                            'OPERARIO': op_sel, 'MATERIAL': mat_acta, 
                            'CANTIDAD': cant_acta, 'NUM_ACTA': n_acta
                        }])
                        st.session_state.data['HISTORIAL_ACTAS'] = pd.concat([st.session_state.data['HISTORIAL_ACTAS'], nuevo_h], ignore_index=True)
                        st.success("✅ Consumo registrado")
                        st.rerun()
                    else: st.error("El operario no tiene suficiente stock.")
        else: st.info("No hay operarios con materiales.")

    with t3:
        st.dataframe(st.session_state.data['OPERARIOS'], use_container_width=True, hide_index=True)

    with t4:
        st.dataframe(st.session_state.data['HISTORIAL_ACTAS'], use_container_width=True, hide_index=True)

    with t5:
        c1, c2, c3 = st.columns(3)
        c1.write("**Materiales**"); c1.dataframe(st.session_state.data['MATERIALES'], hide_index=True)
        c2.write("**Accesorios**"); c2.dataframe(st.session_state.data['ACCESORIOS'], hide_index=True)
        c3.write("**Triple A**"); c3.dataframe(st.session_state.data['TRIPLE_A'], hide_index=True)

    with t6:
        if st.button("Generar Archivo Actualizado"):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                st.session_state.data['MATERIALES'].to_excel(writer, sheet_name='MATERIALES ITA', index=False)
                st.session_state.data['ACCESORIOS'].to_excel(writer, sheet_name='ACCESORIOS ITA', index=False)
                st.session_state.data['TRIPLE_A'].to_excel(writer, sheet_name='INVENTARIO TRIPLE A', index=False)
                st.session_state.data['OPERARIOS'].to_excel(writer, sheet_name='OPERARIOS', index=False)
                st.session_state.data['HISTORIAL_ACTAS'].to_excel(writer, sheet_name='HISTORIAL_ACTAS', index=False)
            st.download_button("📥 Descargar Inventario Maestro", output.getvalue(), "Inventario_Actualizado.xlsx")

else:
    st.info("👋 Sube el archivo Excel en la barra lateral para comenzar.")
    if st.sidebar.button("Limpiar Sesión"):
        st.session_state.clear()
        st.rerun()
