
import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

st.set_page_config(layout="wide")

url = "https://xhwotwefiqfwfabenwsi.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhod290d2VmaXFmd2ZhYmVud3NpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDgzNjc4NTMsImV4cCI6MjA2Mzk0Mzg1M30.3E2z-1SaABbCaV_HjQf0Rj8249mnPeGv7YkV4gOGhlg"
supabase: Client = create_client(url, key)

def confirmar_entregas(entregas):
    if not entregas:
        return
    chaves = [entrega['serie_numero_ctrc'] for entrega in entregas]
    supabase.table("rotas_confirmadas").insert(entregas).execute()
    for chave in chaves:
        supabase.table("base_operacional").delete().eq("serie_numero_ctrc", chave).execute()

def mostrar_rotas():
    st.title("Pré Roterização")
    response = supabase.table("base_operacional").select("*").execute()
    df = pd.DataFrame(response.data)

    if df.empty:
        st.warning("Sem dados disponíveis.")
        return

    df['Peso Real em Kg'] = pd.to_numeric(df['peso_real'], errors='coerce')
    df['Peso Calculado em Kg'] = pd.to_numeric(df['peso_calculado'], errors='coerce')
    df['Cubagem em m3'] = pd.to_numeric(df['cubagem'], errors='coerce')
    df['Quantidade de Volumes'] = pd.to_numeric(df['volumes'], errors='coerce')
    df['Valor do Frete'] = pd.to_numeric(df['valor_frete'], errors='coerce')
    df['Rota'] = df['rota']

    st.markdown(f"**Total de Rotas:** {df['Rota'].nunique()}")
    st.markdown(f"**Total de Notas:** {len(df)}")

    rota_selecionada = st.selectbox("Selecionar rota para exibir (ou deixe em branco para todas):", options=["Todas"] + list(df['Rota'].dropna().unique()))

    rotas_para_exibir = df['Rota'].dropna().unique() if rota_selecionada == "Todas" else [rota_selecionada]

    for rota in rotas_para_exibir:
        rota_df = df[df['Rota'] == rota].copy()
        st.subheader(f"Rota: {rota}")
        st.markdown(f"""
        - **Notas**: {len(rota_df)}
        - **Peso Real**: {rota_df['Peso Real em Kg'].sum():,.2f} kg
        - **Peso Calculado**: {rota_df['Peso Calculado em Kg'].sum():,.2f} kg
        - **Cubagem**: {rota_df['Cubagem em m3'].sum():,.2f} m³
        - **Volumes**: {rota_df['Quantidade de Volumes'].sum():.0f}
        - **Frete**: R$ {rota_df['Valor do Frete'].sum():,.2f}
        """)

        gb = GridOptionsBuilder.from_dataframe(rota_df)
        gb.configure_default_column(resizable=True, filter=True, sortable=True)
        gb.configure_selection('multiple', use_checkbox=True)
        gb.configure_column("cliente_destinatario", header_name="Cliente", width=220)
        gb.configure_column("bairro_destinatario", header_name="Bairro", width=150)
        gb.configure_column("serie_numero_ctrc", header_name="CTRC", width=130)
        grid_options = gb.build()

        grid_response = AgGrid(
            rota_df,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            fit_columns_on_grid_load=False,
            theme="dark",
            height=300
        )

        selected_rows = grid_response['selected_rows']

        if isinstance(selected_rows, list) and len(selected_rows) > 0:
            if st.button(f"Confirmar Entregas da Rota {rota}", key=f"confirmar_{rota}"):
                confirmar_entregas(selected_rows)
                st.success(f"Entregas da Rota {rota} confirmadas!")
                st.experimental_rerun()

def mostrar_rotas_confirmadas():
    st.title("Rotas Confirmadas")
    response = supabase.table("rotas_confirmadas").select("*").execute()
    df = pd.DataFrame(response.data)

    if df.empty:
        st.warning("Nenhuma rota confirmada.")
        return

    df['Peso Real em Kg'] = pd.to_numeric(df['peso_real'], errors='coerce')
    df['Peso Calculado em Kg'] = pd.to_numeric(df['peso_calculado'], errors='coerce')
    df['Cubagem em m3'] = pd.to_numeric(df['cubagem'], errors='coerce')
    df['Quantidade de Volumes'] = pd.to_numeric(df['volumes'], errors='coerce')
    df['Valor do Frete'] = pd.to_numeric(df['valor_frete'], errors='coerce')
    df['Rota'] = df['rota']

    for rota in df['Rota'].dropna().unique():
        rota_df = df[df['Rota'] == rota].copy()
        st.subheader(f"Rota Confirmada: {rota}")
        st.markdown(f"""
        - **Notas**: {len(rota_df)}
        - **Peso Real**: {rota_df['Peso Real em Kg'].sum():,.2f} kg
        - **Peso Calculado**: {rota_df['Peso Calculado em Kg'].sum():,.2f} kg
        - **Cubagem**: {rota_df['Cubagem em m3'].sum():,.2f} m³
        - **Volumes**: {rota_df['Quantidade de Volumes'].sum():.0f}
        - **Frete**: R$ {rota_df['Valor do Frete'].sum():,.2f}
        """)

        gb = GridOptionsBuilder.from_dataframe(rota_df)
        gb.configure_default_column(resizable=True, filter=True, sortable=True)
        gb.configure_column("cliente_destinatario", header_name="Cliente", width=220)
        gb.configure_column("bairro_destinatario", header_name="Bairro", width=150)
        gb.configure_column("serie_numero_ctrc", header_name="CTRC", width=130)
        grid_options = gb.build()

        AgGrid(
            rota_df,
            gridOptions=grid_options,
            fit_columns_on_grid_load=False,
            theme="dark",
            height=300
        )

def main():
    aba = st.sidebar.radio("Navegação", ["Pré Roterização", "Rotas Confirmadas"])
    if aba == "Pré Roterização":
        mostrar_rotas()
    elif aba == "Rotas Confirmadas":
        mostrar_rotas_confirmadas()

if __name__ == '__main__':
    main()
