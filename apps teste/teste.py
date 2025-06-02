import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime
from supabase import create_client, Client
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

st.set_page_config(layout="wide")

url = "https://xhwotwefiqfwfabenwsi.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhod290d2VmaXFmd2ZhYmVud3NpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDgzNjc4NTMsImV4cCI6MjA2Mzk0Mzg1M30.3E2z-1SaABbCaV_HjQf0Rj8249mnPeGv7YkV4gOGhlg"
supabase = create_client(url, key)

pasta = r'C:\Users\Rafael\OneDrive\Área de Trabalho\Roteriza' #pasta do projeto

arquivos = {
    'base': 'fBaseroter.xlsx',
    'agendadas': 'ClienteEntregaAgendada.xlsx',
    'regioes': 'EmbarqueporRegião.xlsx',
    'particularidades': 'Particularidades.xlsx',
    'rotas': 'Rotas.xlsx',
    'rotas_poa': 'RotasPortoAlegre.xlsx'
}

MAPEAMENTO_COLUNAS_SUPABASE = {
    'Serie/Numero CTRC': 'serie_numero_ctrc',
    'CNPJ Destinatario': 'cnpj_destinatario',
    'Cliente Destinatario': 'cliente_destinatario',
    'Cidade de Entrega': 'cidade_entrega',
    'Bairro do Destinatario': 'bairro_destinatario',
    'Previsão de Entrega': 'previsao_entrega',
    'Número da Nota Fiscal': 'numero_nota_fiscal',
    'Status': 'status',
    'Entrega Programada': 'entrega_programada',
    'Particularidade': 'particularidade',
    'Código da Última Ocorrência': 'codigo_ultima_ocorrencia',
    'Peso Calculado em Kg': 'peso_calculado',
    'Peso Real em Kg': 'peso_real',
    'Cubagem em m3': 'cubagem',
    'Quantidade de Volumes': 'volumes',
    'Valor do Frete': 'valor_frete'
}

def precisa_sincronizar():
    tabelas = ['base_operacional', 'Cliente_Entrega_Agendada', 'Embarque_por_Região',
               'Particularidades', 'Rota', 'Rotas_PortoAlegre']
    for tabela in tabelas:
        try:
            response = supabase.table(tabela).select("*").limit(1).execute()
            if not response.data:
                return True
        except:
            return True
    return False

@st.cache_data(ttl=600)
def carregar_planilhas():
    dados = {}
    for chave, nome in arquivos.items():
        caminho = os.path.join(pasta, nome)
        dados[chave] = pd.read_excel(caminho, dtype=str)
    return dados

def sincronizar_tabelas_auxiliares():
    dados = carregar_planilhas()
    df_agendadas = dados['agendadas'].where(pd.notnull(dados['agendadas']), None)
    df_regioes = dados['regioes'].where(pd.notnull(dados['regioes']), None)
    df_part = dados['particularidades'].where(pd.notnull(dados['particularidades']), None)
    df_rota = dados['rotas'].where(pd.notnull(dados['rotas']), None)
    df_rota_poa = dados['rotas_poa'].where(pd.notnull(dados['rotas_poa']), None)

    supabase.table("Cliente_Entrega_Agendada").delete().neq("CNPJ", "").execute()
    supabase.table("Cliente_Entrega_Agendada").insert(df_agendadas.to_dict(orient="records")).execute()

    supabase.table("Embarque_por_Região").delete().neq("CIDADE DESTINO", "").execute()
    supabase.table("Embarque_por_Região").insert(df_regioes.to_dict(orient="records")).execute()

    supabase.table("Particularidades").delete().neq("CNPJ", "").execute()
    supabase.table("Particularidades").insert(df_part.to_dict(orient="records")).execute()

    supabase.table("Rota").delete().neq("CidadeBairro", "").execute()
    supabase.table("Rota").insert(df_rota.to_dict(orient="records")).execute()

    supabase.table("Rotas_PortoAlegre").delete().neq("CidadeBairro", "").execute()
    supabase.table("Rotas_PortoAlegre").insert(df_rota_poa.to_dict(orient="records")).execute()

def integrar_dados(dados):
    base = dados['base']
    agendadas = dados['agendadas']
    particularidades = dados['particularidades']
    rotas = dados['rotas']
    rotas_poa = dados['rotas_poa']

    base['CNPJ Destinatario'] = base['CNPJ Destinatario'].str.strip()
    agendadas['CNPJ'] = agendadas['CNPJ'].str.strip()
    particularidades['CNPJ'] = particularidades['CNPJ'].str.strip()

    base = base.merge(agendadas[['CNPJ', 'Status de Agenda']], how='left', left_on='CNPJ Destinatario', right_on='CNPJ')
    if 'Status de Agenda' in base.columns:
        base = base.rename(columns={'Status de Agenda': 'Status'})

    base = base.merge(particularidades[['CNPJ', 'Particularidade']], how='left', left_on='CNPJ Destinatario', right_on='CNPJ')

    base['Cidade de Entrega'] = base['Cidade de Entrega'].str.strip().str.upper()
    base['Bairro do Destinatario'] = base['Bairro do Destinatario'].str.strip().str.upper()
    rotas['Cidade de Entrega'] = rotas['Cidade de Entrega'].str.strip().str.upper()
    rotas_poa['Bairro do Destinatario'] = rotas_poa['Bairro do Destinatario'].str.strip().str.upper()

    rotas_dict = dict(zip(rotas['Cidade de Entrega'], rotas['Rota']))
    rotas_poa_dict = dict(zip(rotas_poa['Bairro do Destinatario'], rotas_poa['Rota']))

    def definir_rota(row):
        if row['Cidade de Entrega'] == 'PORTO ALEGRE':
            return rotas_poa_dict.get(row['Bairro do Destinatario'], '')
        else:
            return rotas_dict.get(row['Cidade de Entrega'], '')

    base['rota'] = base.apply(definir_rota, axis=1)

    colunas_numericas = [
        'Peso Real em Kg', 'Peso Calculado em Kg', 'Cubagem em m3',
        'Quantidade de Volumes', 'Valor do Frete'
    ]
    for col in colunas_numericas:
        if col in base.columns:
            base[col] = base[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
            base[col] = pd.to_numeric(base[col], errors='coerce')

    base = base.rename(columns=MAPEAMENTO_COLUNAS_SUPABASE)
    base['data_sincronizacao'] = datetime.now().isoformat()

    # ✅ Apenas colunas esperadas
    colunas_validas = list(MAPEAMENTO_COLUNAS_SUPABASE.values()) + ['data_sincronizacao', 'rota']
    base = base[[col for col in base.columns if col in colunas_validas]]

    return base.where(pd.notnull(base), None)


def sincronizar_base_operacional():
    dados = carregar_planilhas()
    df_integrado = integrar_dados(dados)
    # Deleta com cláusula de segurança
    supabase.table("base_operacional").delete().neq("serie_numero_ctrc", "").execute()
    supabase.table("base_operacional").insert(df_integrado.to_dict(orient="records")).execute()


def sincronizar_tudo():
    sincronizar_tabelas_auxiliares()
    sincronizar_base_operacional()

def mostrar_rotas():
    response = supabase.table("base_operacional").select("*").execute()
    df = pd.DataFrame(response.data)
    st.title("Pré Roterização")
    if df.empty:
        st.warning("Sem dados disponíveis.")
        return
    df['Peso Real em Kg'] = pd.to_numeric(df['peso_real'], errors='coerce')
    df['Peso Calculado em Kg'] = pd.to_numeric(df['peso_calculado'], errors='coerce')
    df['Cubagem em m3'] = pd.to_numeric(df['cubagem'], errors='coerce')
    df['Quantidade de Volumes'] = pd.to_numeric(df['volumes'], errors='coerce')
    df['Valor do Frete'] = pd.to_numeric(df['valor_frete'], errors='coerce')
    df = df.rename(columns={'rota': 'Rota'})
    rotas = df['Rota'].dropna().unique()
    for rota in rotas:
        rota_df = df[df['Rota'] == rota].copy()
        st.subheader(f"Rota: {rota}")
        st.write(rota_df)

def confirmar_entregas(entregas):
    if not entregas:
        return

    chaves = [entrega['serie_numero_ctrc'] for entrega in entregas]

    # Insere na tabela de rotas confirmadas
    supabase.table("rotas_confirmadas").insert(entregas).execute()

    # Remove da base operacional
    for chave in chaves:
        supabase.table("base_operacional").delete().eq("serie_numero_ctrc", chave).execute()


def mostrar_rotas_confirmadas():
    response = supabase.table("rotas_confirmadas").select("*").execute()
    df = pd.DataFrame(response.data)

    st.title("Rotas Confirmadas")

    if df.empty:
        st.warning("Nenhuma rota confirmada.")
        return

    df['Peso Real em Kg'] = pd.to_numeric(df['peso_real'], errors='coerce')
    df['Peso Calculado em Kg'] = pd.to_numeric(df['peso_calculado'], errors='coerce')
    df['Cubagem em m3'] = pd.to_numeric(df['cubagem'], errors='coerce')
    df['Quantidade de Volumes'] = pd.to_numeric(df['volumes'], errors='coerce')
    df['Valor do Frete'] = pd.to_numeric(df['valor_frete'], errors='coerce')

    df['Rota'] = df['rota']
    rotas = df['Rota'].dropna().unique()

    for rota in rotas:
        st.subheader(f"Rota Confirmada: {rota}")
        rota_df = df[df['Rota'] == rota].copy()

        st.markdown(f"""
        - **Notas**: {len(rota_df)}
        - **Peso Real**: {rota_df['Peso Real em Kg'].sum():.2f} kg
        - **Peso Calculado**: {rota_df['Peso Calculado em Kg'].sum():.2f} kg
        - **Cubagem**: {rota_df['Cubagem em m3'].sum():.2f} m³
        - **Volumes**: {rota_df['Quantidade de Volumes'].sum():.0f}
        - **Frete Total**: R$ {rota_df['Valor do Frete'].sum():,.2f}
        """)

        AgGrid(
            rota_df,
            fit_columns_on_grid_load=True
        )


def main():
    st.title("Sistema de Roteirização de Entregas")
    if precisa_sincronizar():
        st.warning("🔁 É necessário sincronizar os dados com o Supabase antes de prosseguir.")
        if st.button("Sincronizar dados agora"):
            sincronizar_tudo()
            st.success("✅ Sincronização concluída com sucesso! Recarregue a página.")
            st.stop()
        else:
            st.stop()

    aba = st.sidebar.radio("Navegação", ["Pré Roterização", "Rotas Confirmadas"])
    if aba == "Pré Roterização":
        mostrar_rotas()
    elif aba == "Rotas Confirmadas":
        mostrar_rotas_confirmadas()

if __name__ == '__main__':
    main()
