import streamlit as st
import pandas as pd
from supabase import create_client, Client
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

st.set_page_config(page_title="Rotas Confirmadas", layout="wide")

# Supabase config
url = "https://xhwotwefiqfwfabenwsi.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhod290d2VmaXFmd2ZhYmVud3NpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDgzNjc4NTMsImV4cCI6MjA2Mzk0Mzg1M30.3E2z-1SaABbCaV_HjQf0Rj8249mnPeGv7YkV4gOGhlg"
supabase: Client = create_client(url, key)

def formatar_brasileiro(valor):
    try:
        return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return valor

st.title("✅ Entregas Confirmadas por Rota")

try:
    df_confirmadas = pd.DataFrame(supabase.table("rotas_confirmadas").select("*").execute().data)

    if df_confirmadas.empty:
        st.info("Nenhuma entrega foi confirmada ainda.")
    else:
        rotas_unicas = sorted(df_confirmadas['Rota'].dropna().unique())

        for rota in rotas_unicas:
            st.markdown(f"## 🚛 Rota: {rota}")

            df_rota = df_confirmadas[df_confirmadas['Rota'] == rota]

            total_entregas = len(df_rota)
            peso_calculado = df_rota['Peso Calculado em Kg'].sum()
            peso_real = df_rota['Peso Real em Kg'].sum()
            valor_frete = df_rota['Valor do Frete'].sum()
            cubagem = df_rota['Cubagem em m³'].sum()
            volumes = df_rota['Quantidade de Volumes'].sum()

            st.markdown(f"""
            - **Quantidade de Entregas:** {total_entregas}  
            - **Peso Calculado (kg):** {formatar_brasileiro(peso_calculado)}  
            - **Peso Real (kg):** {formatar_brasileiro(peso_real)}  
            - **Valor do Frete:** R$ {formatar_brasileiro(valor_frete)}  
            - **Cubagem (m³):** {formatar_brasileiro(cubagem)}  
            - **Volumes:** {int(volumes) if pd.notnull(volumes) else 0}
            """)

            colunas_exibidas = [
                'Serie_Numero_CTRC', 'Cliente Pagador', 'Chave CT-e', 'Cliente Destinatario',
                'Cidade de Entrega', 'Bairro do Destinatario', 'Previsao de Entrega',
                'Numero da Nota Fiscal', 'Status', 'Entrega Programada', 'Particularidade',
                'Codigo da Ultima Ocorrencia', 'Peso Real em Kg', 'Peso Calculado em Kg',
                'Cubagem em m³', 'Quantidade de Volumes', 'Valor do Frete'
            ]
            colunas_exibidas = [col for col in colunas_exibidas if col in df_rota.columns]

            gb = GridOptionsBuilder.from_dataframe(df_rota[colunas_exibidas])
            gb.configure_default_column(resizable=True, minWidth=150)
            gb.configure_selection('multiple', use_checkbox=True)
            gb.configure_pagination(enabled=True)
            grid_options = gb.build()

            grid_response = AgGrid(
                df_rota[colunas_exibidas],
                gridOptions=grid_options,
                update_mode=GridUpdateMode.SELECTION_CHANGED,
                fit_columns_on_grid_load=True,
                height=400
            )

            selecionadas = grid_response.get("selected_rows", [])
            if selecionadas:
                st.warning(f"{len(selecionadas)} entrega(s) selecionada(s). Clique abaixo para remover da rota confirmada.")

                if st.button(f"❌ Remover selecionadas da Rota {rota}", key=f"remover_{rota}"):
                    try:
                        chaves_ctrc = [str(row['Serie_Numero_CTRC']) for row in selecionadas if 'Serie_Numero_CTRC' in row]
                        if chaves_ctrc:
                            for ctrc in chaves_ctrc:
                                supabase.table("rotas_confirmadas").delete().eq("Serie_Numero_CTRC", ctrc).execute()
                            st.success("Entregas removidas com sucesso!")
                            st.experimental_rerun()
                        else:
                            st.error("Nenhum CTRC válido selecionado.")
                    except Exception as e:
                        st.error(f"Erro ao remover entregas: {e}")

except Exception as e:
    st.error(f"Erro ao carregar rotas confirmadas: {e}")
