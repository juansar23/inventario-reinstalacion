import streamlit as st
import pandas as pd
import io
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Control de Inventario Online", layout="wide")

# ==================================================
# 1. PERSISTENCIA DE DATOS (Session State)
# ==================================================
# Estas tablas actúan como tu "base de datos" mientras la app esté abierta
if 'db_entradas' not in st.session_state:
    st.session_state.db_entradas = pd.DataFrame(columns=["Fecha", "Material", "Cantidad", "Origen/Proveedor"])

if 'db_salidas' not in st.session_state:
    st.session_state.db_salidas = pd.DataFrame(columns=["Fecha", "Material", "Cantidad", "ID/Serie", "Entregado A", "Responsable"])

if 'lista_materiales' not in st.session_state:
    st.session_state.lista_materiales = []

# ==================================================
# 2. FUNCIONES DE LÓGICA
# ==================================================
def calcular_inventario():
    if not st.session_state.lista_materiales:
        return pd.DataFrame()
    
    # Agrupar entradas y salidas
    ent = st.session_state.db_entradas.groupby("Material")["Cantidad"].sum().reset_index()
    sal = st.session_state.db_salidas.groupby("Material")["Cantidad"].sum().reset_index()
    
    # Cruzar datos con el catálogo maestro
    df_inv = pd.DataFrame({"Material": st.session_state.lista_materiales})
    df_inv = pd.merge(df_inv, ent, on="Material", how="left").fillna(0)
    df_inv.rename(columns={"Cantidad": "Ingresos Total"}, inplace=True)
    
    df_inv = pd.merge(df_inv, sal, on="Material", how="left").fillna(0)
    df_inv.rename(columns={"Cantidad": "Salidas Total"}, inplace=True)
    
    df_inv["Stock Disponible"] = df_inv["Ingresos Total"] - df_inv["Salidas Total"]
    return df_inv

# ==================================================
# 3. INTERFAZ DE USUARIO
# ==================================================
st.title("📊 Sistema de Gestión de Inventario UT")
st.markdown("Crea materiales, registra lo que llega y controla lo que entregas en tiempo real.")

# --- BARRA LATERAL: CONFIGURACIÓN ---
with st.sidebar:
    st.header("⚙️ Configuración")
    st.subheader("Añadir nuevo tipo de material")
    nuevo_nombre = st.text_input("Nombre del material", placeholder="Ej: Cable Drop, Módem...")
    
    if st.button("➕ Registrar en Catálogo"):
        if nuevo_nombre:
            nombre_limpio = nuevo_nombre.strip().upper()
            if nombre_limpio not in st.session_state.lista_materiales:
                st.session_state.lista_materiales.append(nombre_limpio)
                st.success(f"Registrado: {nombre_limpio}")
                st.rerun()
            else:
                st.warning("El material ya existe en el catálogo.")
        else:
            st.error("Escribe un nombre válido.")

    st.divider()
    if st.button("🚨 Borrar todo el historial"):
        st.session_state.db_entradas = pd.DataFrame(columns=["Fecha", "Material", "Cantidad", "Origen/Proveedor"])
        st.session_state.db_salidas = pd.DataFrame(columns=["Fecha", "Material", "Cantidad", "ID/Serie", "Entregado A", "Responsable"])
        st.rerun()

# --- CUERPO PRINCIPAL: TABS ---
tab_resumen, tab_ingreso, tab_salida = st.tabs(["📋 Inventario", "📥 Entrada de Material", "📤 Registro de Salida"])

# TAB 1: RESUMEN DE STOCK
with tab_resumen:
    st.subheader("Estado Actual del Almacén")
    df_stock = calcular_inventario()
    
    if df_stock.empty:
        st.info("El catálogo está vacío. Usa la barra lateral para añadir materiales.")
    else:
        # Métricas rápidas
        c1, c2, c3 = st.columns(3)
        c1.metric("Items Registrados", len(st.session_state.lista_materiales))
        c2.metric("Total Unidades", int(df_stock["Stock Disponible"].sum()))
        c3.metric("Última Actualización", datetime.now().strftime("%H:%M"))
        
        st.dataframe(df_stock, use_container_width=True, hide_index=True)

# TAB 2: ENTRADA DE MATERIAL
with tab_ingreso:
    if not st.session_state.lista_materiales:
        st.warning("Debes registrar materiales en la barra lateral antes de cargar stock.")
    else:
        st.subheader("Registrar Ingreso (Entrada)")
        with st.form("form_ingreso", clear_on_submit=True):
            col1, col2 = st.columns(2)
            mat_e = col1.selectbox("Seleccione Material", st.session_state.lista_materiales)
            cant_e = col1.number_input("Cantidad que ingresa", min_value=1, step=1)
            orig_e = col2.text_input("Origen (Ej: Bodega Central, Compra)")
            fecha_e = col2.date_input("Fecha de Ingreso", datetime.now())
            
            if st.form_submit_button("Confirmar Ingreso"):
                nueva_fila = pd.DataFrame([[fecha_e, mat_e, cant_e, orig_e]], columns=st.session_state.db_entradas.columns)
                st.session_state.db_entradas = pd.concat([st.session_state.db_entradas, nueva_fila], ignore_index=True)
                st.success(f"Cargado: {cant_e} unidades de {mat_e}")
                st.rerun()

# TAB 3: REGISTRO DE SALIDA
with tab_salida:
    df_para_validar = calcular_inventario()
    
    if df_para_validar.empty:
        st.warning("No hay materiales en el inventario.")
    else:
        st.subheader("Entrega de Material a Personal")
        with st.form("form_salida", clear_on_submit=True):
            c1, c2 = st.columns(2)
            mat_s = c1.selectbox("Material a entregar", st.session_state.lista_materiales)
            
            # Verificación de stock en tiempo real
            stock_disp = df_para_validar.loc[df_para_validar["Material"] == mat_s, "Stock Disponible"].values[0]
            c1.info(f"Disponible: {int(stock_disp)} unidades")
            
            cant_s = c1.number_input("Cantidad a entregar", min_value=1, step=1)
            serie_s = c1.text_input("N° Serie / MAC / ID (Opcional)")
            
            receptor = c2.text_input("Nombre de quien recibe (Técnico)")
            resp_s = c2.text_input("Responsable que entrega")
            fecha_s = c2.date_input("Fecha de Salida", datetime.now())
            
            if st.form_submit_button("Confirmar Salida"):
                if cant_s > stock_disp:
                    st.error(f"❌ Error: Stock insuficiente. Solo tienes {int(stock_disp)}.")
                elif not receptor:
                    st.error("⚠️ Debes indicar quién recibe el material.")
                else:
                    nueva_sal = pd.DataFrame([[fecha_s, mat_s, cant_s, serie_s, receptor, resp_s]], columns=st.session_state.db_salidas.columns)
                    st.session_state.db_salidas = pd.concat([st.session_state.db_salidas, nueva_sal], ignore_index=True)
                    st.success(f"Entregado: {cant_s} {mat_s} a {receptor}")
                    st.rerun()

# ==================================================
# 4. EXPORTACIÓN DE DATOS
# ==================================================
st.divider()
st.subheader("📜 Historial de Movimientos")
ver_historial = st.toggle("Mostrar historial de salidas")

if ver_historial:
    if st.session_state.db_salidas.empty:
        st.write("No hay salidas registradas.")
    else:
        st.dataframe(st.session_state.db_salidas, use_container_width=True, hide_index=True)
        
        # Generar Excel para descarga
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state.db_salidas.to_excel(writer, index=False, sheet_name='Salidas')
        
        st.download_button(
            label="📥 Descargar Reporte de Salidas (Excel)",
            data=output.getvalue(),
            file_name=f"reporte_salidas_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
