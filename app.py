import streamlit as st
import pandas as pd
import io
from datetime import datetime

st.set_page_config(page_title="Sistema ITA - Control Total", layout="wide")

# ==================================================
# 1. CARGA INICIAL
# ==================================================
if 'data' not in st.session_state:
    st.session_state.data = {
        'MATERIALES': pd.read_csv("INVENTARIO.xlsx - MATERIALES ITA.csv"),
        'ACCESORIOS': pd.read_csv("INVENTARIO.xlsx - ACCESORIOS ITA.csv"),
        'TRIPLE_A': pd.read_csv("INVENTARIO.xlsx - INVENTARIO TRIPLE A.csv"),
        'OPERARIOS': pd.DataFrame(columns=['OPERARIO', 'NOMBRE', 'CANTIDAD'])
    }

# ==================================================
# 2. LÓGICA DE MOVIMIENTOS
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
            else:
                st.error("Stock insuficiente en bodega.")
                return

# ==================================================
# 3. INTERFAZ
# ==================================================
st.title("🛡️ Panel de Control ITA")
t1, t2, t3, t4, t5 = st.tabs(["🚚 Entregas (Bodega->Op)", "📄 Actas (Consumo)", "👷 Stock Operarios", "📦 Bodegas", "💾 Exportar"])

# --- ENTREGAS ---
with t1:
    st.subheader("Entregar de Bodega a Operario")
    with st.form("f_entrega"):
        op_nom = st.text_input("Nombre del Operario").upper()
        lista_bodega = pd.concat([st.session_state.data[t]['NOMBRE'] for t in ['MATERIALES', 'ACCESORIOS', 'TRIPLE_A']]).unique()
        mat_sel = st.selectbox("Material", lista_bodega)
        cant = st.number_input("Cantidad a entregar", min_value=1)
        if st.form_submit_button("Ejecutar Entrega"):
            transferir_a_operario(mat_sel, cant, op_nom)
            st.rerun()

# --- ACTAS (CONSUMO) ---
with t2:
    st.subheader("Registrar Acta (Consumo de Operario)")
    with st.form("f_acta"):
        df_op = st.session_state.data['OPERARIOS']
        op_sel = st.selectbox("Operario", df_op['OPERARIO'].unique())
        mats_op = df_op[df_op['OPERARIO'] == op_sel]['NOMBRE'].unique()
        mat_acta = st.selectbox("Material instalado", mats_op)
        cant_acta = st.number_input("Cantidad utilizada", min_value=1)
        
        if st.form_submit_button("Registrar Acta de Consumo"):
            mask = (df_op['OPERARIO'] == op_sel) & (df_op['NOMBRE'] == mat_acta)
            if df_op.loc[mask, 'CANTIDAD'].values[0] >= cant_acta:
                st.session_state.data['OPERARIOS'].loc[mask, 'CANTIDAD'] -= cant_acta
                st.success("✅ Material descontado del inventario del operario.")
                st.rerun()
            else:
                st.error("Cantidad mayor al stock del operario.")

# --- STOCK OPERARIOS ---
with t3:
    st.dataframe(st.session_state.data['OPERARIOS'], use_container_width=True)

# --- BODEGAS ---
with t4:
    c1, c2, c3 = st.columns(3)
    with c1: st.write("Materiales"); st.dataframe(st.session_state.data['MATERIALES'])
    with c2: st.write("Accesorios"); st.dataframe(st.session_state.data['ACCESORIOS'])
    with c3: st.write("Triple A"); st.dataframe(st.session_state.data['TRIPLE_A'])

# --- EXPORTAR ---
with t5:
    if st.button("Generar Excel Maestro"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            for name, df in st.session_state.data.items():
                df.to_excel(writer, sheet_name=name, index=False)
        st.download_button("Descargar", output.getvalue(), "Inventario_Final_ITA.xlsx")
