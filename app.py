import streamlit as st
import pandas as pd
import io
from datetime import datetime

st.set_page_config(page_title="Sistema ITA - Gestión Integral", layout="wide")

# ==================================================
# 1. CARGA INICIAL DE DATOS
# ==================================================
if 'data' not in st.session_state:
    st.session_state.data = {
        'MATERIALES': pd.read_csv("INVENTARIO.xlsx - MATERIALES ITA.csv"),
        'ACCESORIOS': pd.read_csv("INVENTARIO.xlsx - ACCESORIOS ITA.csv"),
        'TRIPLE_A': pd.read_csv("INVENTARIO.xlsx - INVENTARIO TRIPLE A.csv"),
        'OPERARIOS': pd.DataFrame(columns=['OPERARIO', 'NOMBRE', 'CANTIDAD']),
        'HISTORIAL_ACTAS': pd.DataFrame(columns=['FECHA', 'OPERARIO', 'MATERIAL', 'CANTIDAD', 'NUM_ACTA'])
    }

# ==================================================
# 2. LÓGICA DE TRASLADOS Y CONSUMOS
# ==================================================
def transferir_a_operario(nombre_material, cant, operario_destino):
    for tabla in ['MATERIALES', 'ACCESORIOS', 'TRIPLE_A']:
        df = st.session_state.data[tabla]
        if nombre_material in df['NOMBRE'].values:
            idx = df[df['NOMBRE'] == nombre_material].index[0]
            if df.loc[idx, 'CANTIDAD'] >= cant:
                st.session_state.data[tabla].loc[idx, 'CANTIDAD'] -= cant
                df_op = st.session_state.data['OPERARIOS']
                mask = (df_op['OPERARIO'] == operario_destino) & (df_op['NOMBRE'] == nombre_material)
                if mask.any():
                    st.session_state.data['OPERARIOS'].loc[mask, 'CANTIDAD'] += cant
                else:
                    nueva = pd.DataFrame([{'OPERARIO': operario_destino, 'NOMBRE': nombre_material, 'CANTIDAD': cant}])
                    st.session_state.data['OPERARIOS'] = pd.concat([df_op, nueva], ignore_index=True)
                st.success(f"✅ Entregado: {cant} {nombre_material} a {operario_destino}")
                return
    st.error("No hay suficiente stock en bodega o el material no existe.")

# ==================================================
# 3. INTERFAZ DE USUARIO (TABS)
# ==================================================
st.title("🛡️ Panel de Control ITA: Inventario y Actas")

tabs = st.tabs(["🚚 Entregas", "📄 Registro de Actas", "👷 Stock Operarios", "📜 Historial Actas", "📦 Bodegas", "💾 Exportar"])

# --- TAB 1: ENTREGAS (BODEGA A OPERARIO) ---
with tabs[0]:
    st.subheader("Salida de Bodega -> Asignación a Operario")
    with st.form("f_entrega"):
        op_nom = st.text_input("Nombre del Operario (Ej: JUAN PEREZ)").upper()
        # Consolidar todos los nombres de materiales disponibles
        lista_bodega = pd.concat([st.session_state.data[t]['NOMBRE'] for t in ['MATERIALES', 'ACCESORIOS', 'TRIPLE_A']]).unique()
        mat_sel = st.selectbox("Seleccionar Material", sorted(lista_bodega))
        cant_e = st.number_input("Cantidad a entregar", min_value=1, step=1)
        if st.form_submit_button("Confirmar Entrega"):
            if op_nom:
                transferir_a_operario(mat_sel, cant_e, op_nom)
                st.rerun()
            else:
                st.warning("Escribe el nombre del operario.")

# --- TAB 2: ACTAS (CONSUMO) ---
with tabs[1]:
    st.subheader("Reporte de Material Instalado (Acta)")
    df_op = st.session_state.data['OPERARIOS']
    if not df_op.empty:
        with st.form("f_acta"):
            op_sel = st.selectbox("Operario que reporta", sorted(df_op['OPERARIO'].unique()))
            mats_op = df_op[df_op['OPERARIO'] == op_sel]['NOMBRE'].unique()
            mat_acta = st.selectbox("Material utilizado", mats_op)
            cant_a = st.number_input("Cantidad consumida", min_value=1, step=1)
            num_acta = st.text_input("Número de Acta / Orden de Trabajo").upper()
            
            if st.form_submit_button("Registrar Consumo"):
                mask = (df_op['OPERARIO'] == op_sel) & (df_op['NOMBRE'] == mat_acta)
                stock_op = df_op.loc[mask, 'CANTIDAD'].values[0]
                
                if stock_op >= cant_a:
                    # 1. Restar del stock del operario
                    st.session_state.data['OPERARIOS'].loc[mask, 'CANTIDAD'] -= cant_a
                    # 2. Guardar en el Historial de Actas
                    nuevo_h = pd.DataFrame([{
                        'FECHA': datetime.now().strftime("%d/%m/%Y %H:%M"),
                        'OPERARIO': op_sel,
                        'MATERIAL': mat_acta,
                        'CANTIDAD': cant_a,
                        'NUM_ACTA': num_acta
                    }])
                    st.session_state.data['HISTORIAL_ACTAS'] = pd.concat([st.session_state.data['HISTORIAL_ACTAS'], nuevo_h], ignore_index=True)
                    st.success(f"✅ Acta {num_acta} registrada. Se descontó del stock de {op_sel}")
                    st.rerun()
                else:
                    st.error(f"El operario solo tiene {stock_op} unidades disponibles.")
    else:
        st.info("No hay operarios con material asignado.")

# --- TAB 3: STOCK OPERARIOS ---
with tabs[2]:
    st.subheader("Inventario actual en poder de los operarios")
    # Limpiar filas con cantidad 0 para mejor visualización
    df_mostrar = st.session_state.data['OPERARIOS']
    st.dataframe(df_mostrar[df_mostrar['CANTIDAD'] > 0], use_container_width=True, hide_index=True)

# --- TAB 4: HISTORIAL DE ACTAS ---
with tabs[3]:
    st.subheader("Registro Histórico de Consumos")
    st.dataframe(st.session_state.data['HISTORIAL_ACTAS'], use_container_width=True, hide_index=True)

# --- TAB 5: BODEGAS ---
with tabs[4]:
    st.subheader("Estado de Bodegas Centrales")
    c1, c2, c3 = st.columns(3)
    c1.write("**Materiales ITA**"); c1.dataframe(st.session_state.data['MATERIALES'], hide_index=True)
    c2.write("**Accesorios ITA**"); c2.dataframe(st.session_state.data['ACCESORIOS'], hide_index=True)
    c3.write("**Inventario Triple A**"); c3.dataframe(st.session_state.data['TRIPLE_A'], hide_index=True)

# --- TAB 6: EXPORTAR ---
with tabs[5]:
    st.subheader("Descargar Inventario Maestro")
    st.write("Genera un archivo con todas las hojas actualizadas para tu respaldo.")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for name, df in st.session_state.data.items():
            df.to_excel(writer, sheet_name=name, index=False)
    
    st.download_button(
        label="📥 Descargar Excel Final",
        data=output.getvalue(),
        file_name=f"CONTROL_INVENTARIO_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
