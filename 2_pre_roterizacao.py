#sincronização, Pré Roterização e Rotas Confirmadas funcionando

import streamlit as st

st.set_page_config(page_title="Roterização", layout="wide")

import pandas as pd
from datetime import datetime
from supabase import create_client, Client
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import numpy as np
from pathlib import Path
import io
import time
from st_aggrid.shared import JsCode

# Supabase config
url = "https://xhwotwefiqfwfabenwsi.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhod290d2VmaXFmd2ZhYmVud3NpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDgzNjc4NTMsImV4cCI6MjA2Mzk0Mzg1M30.3E2z-1SaABbCaV_HjQf0Rj8249mnPeGv7YkV4gOGhlg"
TABLE_NAME = "fBaseroter"
EXCEL_SHEET_NAME = "Sheet1"
DELETE_FILTER_COLUMN = "Setor de Destino"

# Inicializar Supabase
@st.cache_resource(show_spinner=False)
def init_supabase_client():
    try:
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro ao inicializar cliente Supabase: {e}")
        return None

supabase = init_supabase_client()
if supabase is None:
    st.error("Não foi possível conectar ao Supabase. Verifique a URL e a chave de acesso.")
    st.stop()

# Função de leitura e preparação dos dados
def load_and_prepare_data(uploaded_file):
    if uploaded_file is None:
        return None

    try:
        df = pd.read_excel(uploaded_file, sheet_name=EXCEL_SHEET_NAME)
        st.success(f"Arquivo '{getattr(uploaded_file, 'name', 'desconhecido')}' lido com sucesso.")

        supabase_columns = [
            "Serie/Numero CTRC", "Serie/Numero CT-e", "Tipo do Documento", "Unidade Emissora",
            "Data de Emissao", "Data de Autorizacao", "Chave CT-e", "Cliente Remetente",
            "UF do Remetente", "UF do Expedidor", "Cliente Pagador", "UF do Pagador",
            "Fone do Pagador", "Segmento do Pagador", "CNPJ Destinatario", "Cliente Destinatario",
            "Bairro do Destinatario", "Setor de Destino", "UF do Destinatario", "Local de Entrega",
            "Bairro", "Cidade de Entrega", "UF de Entrega", "Unidade Receptora",
            "Numero da Nota Fiscal", "Peso Real em Kg", "Cubagem em m³", "Quantidade de Volumes",
            "Valor da Mercadoria", "Valor do Frete", "Valor do ICMS", "Valor do ISS",
            "Peso Calculado em Kg", "Frete Peso", "Frete Valor", "TDA", "TDE",
            "Adicional de Frete", "UF origem da prestacao", "Codigo da Ultima Ocorrencia",
            "Data de inclusao da Ultima Ocorrencia", "Data da Ultima Ocorrencia",
            "Usuario da Ultima Ocorrencia", "Unidade da Ultima Ocorrencia",
            "Descricao da Ultima Ocorrencia", "Latitude da Ultima Ocorrencia",
            "Longitude da Ultima Ocorrencia", "Previsao de Entrega", "Entrega Programada",
            "Data da Entrega Realizada", "Quantidade de Dias de Atraso", "Localizacao Atual",
            "Data do Cancelamento", "Motivo do Cancelamento", "Codigo dos Correios",
            "Numero da Capa de Remessa", "Numero do Pacote de Arquivamento",
            "Compr. de Entrega Escaneado", "Data do Escaneamento", "Hora do Escaneamento",
            "Notas Fiscais", "Numero dos Pedidos", "Chaves NF-es",
            "Volume Cliente/Shipment", "Unnamed: 67"
        ]

        column_mapping = {
            'Cubagem em m3': 'Cubagem em m³'
        }

        date_columns = [
            "Data de Emissao", "Data de Autorizacao", "Data de inclusao da Ultima Ocorrencia",
            "Data da Ultima Ocorrencia", "Previsao de Entrega", "Entrega Programada",
            "Data da Entrega Realizada", "Data do Cancelamento", "Data do Escaneamento"
        ]

        numeric_columns = [
            "Peso Real em Kg", "Cubagem em m³", "Valor da Mercadoria", "Valor do Frete",
            "Valor do ICMS", "Valor do ISS", "Peso Calculado em Kg", "Frete Peso",
            "Frete Valor", "TDA", "TDE", "Adicional de Frete"
        ]

        int_cols = []
        boolean_column = "Compr. de Entrega Escaneado"

        df.rename(columns=column_mapping, inplace=True)

        seen = set()
        final_columns = []
        for col in supabase_columns:
            if col in df.columns and col not in seen:
                final_columns.append(col)
                seen.add(col)
        df = df[final_columns]

        for col in numeric_columns:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: str(x).replace(',', '.').strip() if pd.notnull(x) else None)
                df[col] = pd.to_numeric(df[col], errors='coerce')
                if col in int_cols:
                    df[col] = df[col].astype('Int64')

        if boolean_column in df.columns:
            bool_map = {'S': True, 'Sim': True, '1': True, 1: True, True: True,
                        'N': False, 'Não': False, '0': False, 0: False, False: False}
            df[boolean_column] = df[boolean_column].map(bool_map).astype('boolean')

        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')
                df[col] = df[col].dt.strftime('%Y-%m-%d')

        df = df.replace({np.nan: None, pd.NaT: None, pd.NA: None})

        primary_key = "Serie/Numero CTRC"
        if primary_key in df.columns and df[primary_key].isnull().any():
            st.warning(f"Aviso: chave primária '{primary_key}' contém nulos.")
            df.dropna(subset=[primary_key], inplace=True)

        data_to_insert = df.to_dict(orient='records')

        cleaned_data = []
        for record in data_to_insert:
            cleaned_record = {}
            for k, v in record.items():
                if v is None or (isinstance(v, float) and np.isnan(v)):
                    cleaned_record[k] = None
                elif k in int_cols:
                    try:
                        cleaned_record[k] = int(v)
                    except:
                        cleaned_record[k] = None
                else:
                    cleaned_record[k] = v
            cleaned_data.append(cleaned_record)

        st.info(f"Dados preparados: {len(cleaned_data)} registros prontos para sincronizar.")
        return cleaned_data

    except Exception as e:
        st.error(f"Erro ao processar o Excel: {e}")
        return None

##############################
# Página de sincronização
##############################
def pagina_sincronizacao(): 
    st.title("📁 Sincronização de Dados")
    st.subheader("1. Envie o arquivo Excel com os dados")

    # Upload manual do arquivo .xlsx
    uploaded_file = st.file_uploader("📂 Selecione o arquivo .xlsx", type=["xlsx"])

    if uploaded_file is None:
        st.warning("Por favor, selecione um arquivo Excel para continuar.")
        return

    # Processar o arquivo enviado
    data_to_sync = load_and_prepare_data(uploaded_file)

    if data_to_sync is not None:
        st.subheader("2. Enviar para o Supabase")
        st.write(f"⚠️ Todos os dados da tabela `{TABLE_NAME}` serão apagados antes da nova inserção.")

        if st.button("🚀 Sincronizar"):
            progress_bar = st.progress(0, text="Iniciando...")
            status_text = st.empty()
            log_area = st.expander("📄 Logs Detalhados", expanded=False)

            try:
                status_text.info("Deletando dados antigos...")
                delete_response = supabase.table(TABLE_NAME).delete().neq(DELETE_FILTER_COLUMN, '---NON_EXISTENT_VALUE---').execute()
                log_area.write(f"Deleção: {delete_response}")
                progress_bar.progress(33, text="Inserindo novos dados...")

                batch_size = 500
                total = len(data_to_sync)
                for i in range(0, total, batch_size):
                    batch = data_to_sync[i:i+batch_size]
                    supabase.table(TABLE_NAME).insert(batch).execute()
                    progresso = 33 + int((i+batch_size)/total * 67)
                    progress_bar.progress(min(progresso, 100), text=f"Inserindo {i+1}-{min(i+batch_size, total)}...")

                status_text.success(f"✅ {total} registros sincronizados com sucesso!")
                st.cache_data.clear()

            except Exception as e:
                st.error(f"❌ Erro na sincronização: {e}")
                log_area.write(e)




# Aqui você pode adicionar os blocos das outras páginas (Pré Roterização, Rotas Confirmadas
###########################################
# PÁGINA PRÉ ROTERIZAÇÃO
##########################################
def formatar_brasileiro(valor):
    try:
        return f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return valor

def pagina_pre_roterizacao():
    st.title("Pré Roterização")

    def carregar_base_supabase():
        try:
            base = pd.DataFrame(supabase.table("fBaseroter").select("*").execute().data)
            if supabase is None:
                st.error("Erro: conexão com o Supabase falhou.")
                return None
            agendadas = pd.DataFrame(supabase.table("Clientes_Entrega_Agendada").select("*").execute().data)
            particularidades = pd.DataFrame(supabase.table("Particularidades").select("*").execute().data)
            rotas = pd.DataFrame(supabase.table("Rotas").select("*").execute().data)
            rotas_poa = pd.DataFrame(supabase.table("RotasPortoAlegre").select("*").execute().data)

            base['CNPJ Destinatario'] = base['CNPJ Destinatario'].astype(str).str.strip()

            if {'CNPJ', 'Status de Agenda'}.issubset(agendadas.columns):
                agendadas['CNPJ'] = agendadas['CNPJ'].astype(str).str.strip()
                base = base.merge(
                    agendadas[['CNPJ', 'Status de Agenda']],
                    how='left',
                    left_on='CNPJ Destinatario',
                    right_on='CNPJ'
                ).rename(columns={'Status de Agenda': 'Status'})

            if {'CNPJ', 'Particularidade'}.issubset(particularidades.columns):
                particularidades['CNPJ'] = particularidades['CNPJ'].astype(str).str.strip()
                base = base.merge(
                    particularidades[['CNPJ', 'Particularidade']],
                    how='left',
                    left_on='CNPJ Destinatario',
                    right_on='CNPJ'
                )

            for col in ['Cidade de Entrega', 'Bairro do Destinatario']:
                if col in base.columns:
                    base[col] = base[col].astype(str).str.strip().str.upper()

            rotas['Cidade de Entrega'] = rotas['Cidade de Entrega'].astype(str).str.strip().str.upper()
            rotas['Bairro do Destinatario'] = rotas['Bairro do Destinatario'].astype(str).str.strip().str.upper()
            rotas_dict = dict(zip(rotas['Cidade de Entrega'], rotas['Rota']))

            rotas_poa['Cidade de Entrega'] = rotas_poa['Cidade de Entrega'].astype(str).str.strip().str.upper()
            rotas_poa['Bairro do Destinatario'] = rotas_poa['Bairro do Destinatario'].astype(str).str.strip().str.upper()
            rotas_poa_dict = dict(zip(rotas_poa['Bairro do Destinatario'], rotas_poa['Rota']))

            def definir_rota(row):
                if row.get('Cidade de Entrega') == 'PORTO ALEGRE':
                    return rotas_poa_dict.get(row.get('Bairro do Destinatario'), '')
                else:
                    return rotas_dict.get(row.get('Cidade de Entrega'), '')

            base['Rota'] = base.apply(definir_rota, axis=1)

            colunas_numericas = [
                'Peso Real em Kg', 'Cubagem em m³', 'Quantidade de Volumes', 'Valor da Mercadoria',
                'Valor do Frete', 'Valor do ICMS', 'Valor do ISS', 'Peso Calculado em Kg',
                'Frete Peso', 'Frete Valor', 'TDA', 'TDE', 'Adicional de Frete'
            ]

            for col in colunas_numericas:
                if col in base.columns:
                    base[col] = pd.to_numeric(base[col], errors='coerce')
                else:
                    st.warning(f"Coluna '{col}' não encontrada na base.")

            base['Indice'] = base.index
            return base

        except Exception as e:
            st.error(f"Erro ao consultar as tabelas do Supabase: {e}")
            return None

    df = carregar_base_supabase()
    if df is not None:
        dados_confirmados_raw = supabase.table("rotas_confirmadas").select("*").execute().data
        dados_confirmados = pd.DataFrame(dados_confirmados_raw)

        if not dados_confirmados.empty and "Serie_Numero_CTRC" in dados_confirmados.columns and "Serie/Numero CTRC" in df.columns:
            df["Serie/Numero CTRC"] = df["Serie/Numero CTRC"].astype(str).str.strip()
            dados_confirmados["Serie_Numero_CTRC"] = dados_confirmados["Serie_Numero_CTRC"].astype(str).str.strip()
            ctrcs_confirmados = dados_confirmados["Serie_Numero_CTRC"].dropna().unique().tolist()
            df = df[~df["Serie/Numero CTRC"].isin(ctrcs_confirmados)]

        rotas_disponiveis = sorted(df["Rota"].dropna().unique())
        rotas_opcoes = ["Todas"] + rotas_disponiveis
        rota_selecionada = st.selectbox("🔎 Filtrar por Rota:", rotas_opcoes, key="filtro_rota")

        if rota_selecionada != "Todas":
            df = df[df["Rota"] == rota_selecionada]

        total_rotas = df["Rota"].nunique()
        total_entregas = len(df)

        st.markdown(f"""
        <div style="display: flex; gap: 20px; margin-bottom: 20px;">
            <div style="background-color: #2e2e2e; padding: 16px 24px; border-radius: 8px; color: white; text-align: center;">
                <h4 style="margin: 0 0 6px 0;">Total de Rotas</h4>
                <div style="font-size: 22px; font-weight: bold;">{total_rotas}</div>
            </div>
            <div style="background-color: #2e2e2e; padding: 16px 24px; border-radius: 8px; color: white; text-align: center;">
                <h4 style="margin: 0 0 6px 0;">Total de Entregas</h4>
                <div style="font-size: 22px; font-weight: bold;">{total_entregas}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### 📊 Visão Geral das Entregas por Rota")
        df_grouped = df.groupby('Rota').agg({
            'Peso Real em Kg': 'sum',
            'Peso Calculado em Kg': 'sum',
            'Cubagem em m³': 'sum',
            'Quantidade de Volumes': 'sum',
            'Valor do Frete': 'sum',
            'Indice': 'count'
        }).reset_index().rename(columns={'Indice': 'Qtd Entregas'})
        st.dataframe(df_grouped.style.format(formatar_brasileiro), use_container_width=True)

        st.markdown("### 📋 Entregas por Rota")
        rotas_unicas = sorted(df['Rota'].dropna().unique())

        for rota in rotas_unicas:
            st.markdown(f"<div style='background-color: #2e2e2e; padding: 10px 20px; border-radius: 6px; color: white; font-size: 22px; font-weight: bold; margin-top: 30px;'>Rota: {rota}</div>", unsafe_allow_html=True)

            df_rota = df[df['Rota'] == rota]

            total_entregas = len(df_rota)
            peso_calculado = df_rota['Peso Calculado em Kg'].sum()
            peso_real = df_rota['Peso Real em Kg'].sum()
            valor_frete = df_rota['Valor do Frete'].sum()
            cubagem = df_rota['Cubagem em m³'].sum()
            volumes = df_rota['Quantidade de Volumes'].sum()

            col1, col2, col3, col4, col5, col6 = st.columns(6)
            col1.metric("Entregas", total_entregas)
            col2.metric("Peso Calc. (Kg)", formatar_brasileiro(peso_calculado))
            col3.metric("Peso Real (Kg)", formatar_brasileiro(peso_real))
            col4.metric("Cubagem (m³)", formatar_brasileiro(cubagem))
            col5.metric("Volumes", int(volumes) if pd.notnull(volumes) else 0)
            col6.metric("Valor Frete", f"R$ {formatar_brasileiro(valor_frete)}")

            # Corrigido: usar coluna real que vem da base
            colunas_exibidas = [
                'Serie/Numero CTRC', 'Cliente Pagador', 'Chave CT-e', 'Cliente Destinatario',
                'Cidade de Entrega', 'Bairro do Destinatario', 'Previsao de Entrega',
                'Numero da Nota Fiscal', 'Status', 'Entrega Programada', 'Particularidade',
                'Codigo da Ultima Ocorrencia', 'Peso Real em Kg', 'Peso Calculado em Kg',
                'Cubagem em m³', 'Quantidade de Volumes', 'Valor do Frete'
            ]
            colunas_exibidas = [col for col in colunas_exibidas if col in df_rota.columns]

            df_formatado = df_rota[colunas_exibidas].copy()

            colunas_formatar = [
                'Peso Real em Kg', 'Peso Calculado em Kg', 'Cubagem em m³',
                'Quantidade de Volumes', 'Valor do Frete'
            ]
            for col in colunas_formatar:
                if col in df_formatado.columns:
                    df_formatado[col] = df_formatado[col].apply(formatar_brasileiro)

            gb = GridOptionsBuilder.from_dataframe(df_formatado)
            gb.configure_default_column(resizable=True, minWidth=150)
            gb.configure_selection('multiple', use_checkbox=True)
            gb.configure_pagination(enabled=True)
            grid_options = gb.build()

            grid_response = AgGrid(
                df_formatado,
                gridOptions=grid_options,
                update_mode=GridUpdateMode.SELECTION_CHANGED,
                fit_columns_on_grid_load=True,
                height=400,
                allow_unsafe_jscode=True,
                key=f"grid_{rota}"
            )

           # Captura linhas selecionadas com segurança
            rows = grid_response.get("selected_rows")
            selecionadas = pd.DataFrame(rows) if rows is not None and len(rows) > 0 else pd.DataFrame()

            if not selecionadas.empty and "Serie/Numero CTRC" in selecionadas.columns:
                # Extrai os identificadores das entregas selecionadas
                chaves = selecionadas["Serie/Numero CTRC"].dropna().astype(str).str.strip().tolist()

                # Busca os dados originais com base nas chaves
                df_selecionadas = df_rota[df_rota["Serie/Numero CTRC"].isin(chaves)].copy()
                df_selecionadas.rename(columns={"Serie/Numero CTRC": "Serie_Numero_CTRC"}, inplace=True)
                df_selecionadas["Rota"] = rota
                df_selecionadas.drop(columns=["Indice"], inplace=True, errors="ignore")

                # ✅ MANTENHA APENAS AS COLUNAS QUE EXISTEM NO SUPABASE
                colunas_supabase = [
                    'Serie_Numero_CTRC', 'Cliente Pagador', 'Chave CT-e', 'Cliente Destinatario',
                    'Cidade de Entrega', 'Bairro do Destinatario', 'Previsao de Entrega',
                    'Numero da Nota Fiscal', 'Status', 'Entrega Programada', 'Particularidade',
                    'Codigo da Ultima Ocorrencia', 'Peso Real em Kg', 'Peso Calculado em Kg',
                    'Cubagem em m³', 'Quantidade de Volumes', 'Valor do Frete', 'Rota'
                ]
                df_selecionadas = df_selecionadas[[col for col in colunas_supabase if col in df_selecionadas.columns]]

                # ✅ SUBSTITUIR NaN e inf por None (compatível com JSON)
                df_selecionadas = df_selecionadas.replace([np.nan, np.inf, -np.inf], None)

                # 📢 Mostrar a quantidade de entregas selecionadas
                st.success(f"🔒 {len(df_selecionadas)} entregas selecionadas para confirmação na rota **{rota}**.")

                if st.button(f"✅ Confirmar Rota: {rota}", key=f"confirmar_{rota}"):
                    try:
                        supabase.table("rotas_confirmadas").insert(df_selecionadas.to_dict(orient="records")).execute()
                        st.success(f"✅ {len(df_selecionadas)} entregas confirmadas com sucesso na rota **{rota}**!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro ao confirmar entregas: {e}")
            else:
                st.info("Nenhuma entrega selecionada nesta rota.")











################################
# Página de Rotas Confirmadas
################################
def pagina_rotas_confirmadas():
    st.title("✅ Entregas Confirmadas por Rota")

    try:
        df_confirmadas = pd.DataFrame(supabase.table("rotas_confirmadas").select("*").execute().data)

        if df_confirmadas.empty:
            st.info("Nenhuma entrega foi confirmada ainda.")
        else:
            # ▶️ Novidade: Totais no topo
            total_rotas = df_confirmadas['Rota'].nunique()
            total_entregas = len(df_confirmadas)

            st.markdown(f"""
            <div style="display: flex; gap: 20px; margin-bottom: 20px;">
                <div style="background-color: #2e2e2e; padding: 16px 24px; border-radius: 8px; color: white; text-align: center;">
                    <h4 style="margin: 0 0 6px 0;">Total de Rotas</h4>
                    <div style="font-size: 22px; font-weight: bold;">{total_rotas}</div>
                </div>
                <div style="background-color: #2e2e2e; padding: 16px 24px; border-radius: 8px; color: white; text-align: center;">
                    <h4 style="margin: 0 0 6px 0;">Total de Entregas</h4>
                    <div style="font-size: 22px; font-weight: bold;">{total_entregas}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Continua como antes
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

                    # Função JS para formatar valores no estilo brasileiro (2 casas decimais)
                formatter_brasileiro = JsCode("""
                function(params) {
                    if (!params.value) return '';
                    return Number(params.value).toLocaleString('pt-BR', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                    });
                }
                """)

                formatter_tonelada = JsCode("""
                function(params) {
                    if (!params.value) return '';
                    return (Number(params.value) / 1000).toLocaleString('pt-BR', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                    }) + ' t';
                }
                """)

                gb = GridOptionsBuilder.from_dataframe(df_rota[colunas_exibidas])
                gb.configure_default_column(resizable=True, minWidth=150)
                gb.configure_selection('multiple', use_checkbox=True)
                gb.configure_pagination(enabled=True)

                # Aplica o formatador nas colunas numéricas
                colunas_formatadas = [
                    'Peso Real em Kg', 'Peso Calculado em Kg', 'Cubagem em m³',
                    'Quantidade de Volumes', 'Valor do Frete'
                ]
                for col in colunas_formatadas:
                    if col in df_rota.columns:
                        if col in ['Peso Real em Kg', 'Peso Calculado em Kg']:
                            gb.configure_column(col, type=["numericColumn"], valueFormatter=formatter_tonelada)
                        else:
                            gb.configure_column(col, type=["numericColumn"], valueFormatter=formatter_brasileiro)


                grid_options = gb.build()

                grid_response = AgGrid(
                    df_rota[colunas_exibidas],
                    gridOptions=grid_options,
                    update_mode=GridUpdateMode.SELECTION_CHANGED,
                    fit_columns_on_grid_load=True,
                    height=400,
                    allow_unsafe_jscode=True
                )

                df_selecionadas = pd.DataFrame(grid_response.get("selected_rows", []))

                if not df_selecionadas.empty:
                    st.warning(f"{len(df_selecionadas)} entrega(s) selecionada(s). Clique abaixo para remover da rota confirmada.")

                    if st.button(f"❌ Remover selecionadas da Rota {rota}", key=f"remover_{rota}"):
                        try:
                            if "Serie_Numero_CTRC" in df_selecionadas.columns:
                                chaves_ctrc = df_selecionadas["Serie_Numero_CTRC"].dropna().astype(str).tolist()
                                for ctrc in chaves_ctrc:
                                    supabase.table("rotas_confirmadas").delete().eq("Serie_Numero_CTRC", ctrc).execute()
                                st.success("✅ Entregas removidas com sucesso!")
                                st.rerun()
                            else:
                                st.error("Coluna 'Serie_Numero_CTRC' não encontrada nos dados selecionados.")
                        except Exception as e:
                            st.error(f"Erro ao remover entregas: {e}")

    except Exception as e:
        st.error(f"Erro ao carregar rotas confirmadas: {e}")



# Menu lateral
opcao = st.sidebar.radio("Menu", ["Sincronização", "Pré Roterização", "Rotas Confirmadas"], key="menu_lateral")

# Renderizar a página correspondente
if opcao == "Sincronização":
    pagina_sincronizacao()
elif opcao == "Pré Roterização":
    pagina_pre_roterizacao()
elif opcao == "Rotas Confirmadas":
    pagina_rotas_confirmadas()
