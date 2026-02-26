# ==========================
# SALIDA DE MATERIAL
# ==========================

st.subheader("📤 Registrar Salida de Material")

if not st.session_state.inventario.empty:

    material_seleccionado = st.selectbox(
        "Seleccionar material",
        st.session_state.inventario["Nombre"].unique()
    )

    cantidad_salida = st.number_input("Cantidad a retirar", min_value=1, step=1)
    responsable = st.text_input("¿A quién se le entregó?")

    if st.button("Registrar Salida"):

        fila = st.session_state.inventario[
            st.session_state.inventario["Nombre"] == material_seleccionado
        ]

        if not fila.empty:

            idx = fila.index[0]
            stock_actual = st.session_state.inventario.loc[idx, "Cantidad"]

            if cantidad_salida <= stock_actual:

                st.session_state.inventario.loc[idx, "Cantidad"] -= cantidad_salida

                movimiento = {
                    "Fecha": datetime.now(),
                    "Tipo": "Salida",
                    "Material": material_seleccionado,
                    "Cantidad": cantidad_salida,
                    "Responsable": responsable
                }

                st.session_state.movimientos = pd.concat(
                    [st.session_state.movimientos, pd.DataFrame([movimiento])],
                    ignore_index=True
                )

                guardar_csv(st.session_state.inventario, ARCHIVO_INVENTARIO)
                guardar_csv(st.session_state.movimientos, ARCHIVO_MOVIMIENTOS)

                st.success("Salida registrada correctamente")

            else:
                st.error("No hay suficiente stock disponible")
