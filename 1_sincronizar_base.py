import streamlit as st
import pandas as pd
from supabase import create_client, Client
import numpy as np
from pathlib import Path
import io

st.set_page_config(page_title="Sincronizar Base", layout="wide")

SUPABASE_URL = "https://xhwotwefiqfwfabenwsi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhod290d2VmaXFmd2ZhYmVud3NpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDgzNjc4NTMsImV4cCI6MjA2Mzk0Mzg1M30.3E2z-1SaABbCaV_HjQf0Rj8249mnPeGv7YkV4gOGhlg"
TABLE_NAME = "fBaseroter"
EXCEL_SHEET_NAME = "Sheet1"
DELETE_FILTER_COLUMN = "Setor de Destino"


#########################################
            #SINCRONIZADOR
#########################################
@st.cache_resource
def init_supabase_client():
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return supabase
    except Exception as e:
        st.error(f"Erro ao inicializar cliente Supabase: {e}")
        return None

supabase = init_supabase_client()

if supabase:
   
    st.warning("A tabela 'fBaseroter' não contém dados ou não foi encontrada.")


def load_and_prepare_data(uploaded_file):
    if uploaded_file is None:
        return None

    try:
        df = pd.read_excel(uploaded_file, sheet_name=EXCEL_SHEET_NAME)
        st.success(f"Ficheiro '{uploaded_file.name}' lido com sucesso (aba '{EXCEL_SHEET_NAME}').")

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
            "Volume Cliente/Shipment", "Unnamed: 67", "Peso Real em Kg", "Cubagem em m³", 
            "Quantidade de Volumes", "Valor da Mercadoria", "Valor do Frete", "Valor do ICMS", 
            "Valor do ISS", "Peso Calculado em Kg", "Frete Peso", "Frete Valor", "TDA", "TDE", 
            "Adicional de Frete", "Codigo da Ultima Ocorrencia", "Latitude da Ultima Ocorrencia",
            "Longitude da Ultima Ocorrencia", "Quantidade de Dias de Atraso", "Quantidade de Volumes", 
            "Codigo da Ultima Ocorrencia", "Quantidade de Dias de Atraso"
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
        # Remove colunas duplicadas preservando a ordem
        seen = set()
        final_columns = []
        for col in supabase_columns:
            if col in df.columns and col not in seen:
                final_columns.append(col)
                seen.add(col)

        df = df[final_columns]

        for col in numeric_columns:
            if col in df.columns:
                df[col] = df[col].apply(
                    lambda x: str(x).replace(',', '.').strip() if pd.notnull(x) else None
                )
                df[col] = pd.to_numeric(df[col], errors='coerce')
                if col in int_cols:
                    df[col] = df[col].astype('Int64')




        for col in numeric_columns:
            if col in df.columns:
                # Converte para string apenas os valores válidos e aplica substituições
                df[col] = df[col].apply(lambda x: str(x).replace(',', '.').strip() if pd.notnull(x) else x)
                df[col] = pd.to_numeric(df[col], errors='coerce')
                if col in int_cols:
                    df[col] = df[col].astype('Int64')

        if boolean_column in df.columns:
            bool_map = {'S': True, 'Sim': True, '1': True, 1: True, True: True,
                        'N': False, 'Não': False, '0': False, 0: False, False: False}
            df[boolean_column] = df[boolean_column].map(bool_map).astype('boolean')

        for col in date_columns:
            if col in df.columns:
                try:
                    df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')
                    df[col] = df[col].dt.strftime('%Y-%m-%d')  # converte para string ISO
                except Exception as e:
                    st.warning(f"Erro ao converter coluna de data '{col}': {e}")


        df = df.replace({np.nan: None, pd.NaT: None, pd.NA: None})

        primary_key = "Serie/Numero CTRC"
        if primary_key in df.columns and df[primary_key].isnull().any():
            st.warning(f"Aviso: A coluna chave primária '{primary_key}' contém valores nulos. Linhas com chave primária nula serão ignoradas.")
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




        st.info(f"Dados preparados com sucesso ({len(cleaned_data)} registos).")
        return cleaned_data

    except Exception as e:
        st.error(f"Erro ao ler ou preparar o ficheiro Excel: {e}")
        return None

##########################################################################################################################

st.subheader("1. Sincronizar automaticamente arquivo local")

# Caminho fixo para o arquivo Excel
file_path = Path("C:/Users/Rafael/OneDrive/Área de Trabalho/Roteriza/fBaseroter.xlsx")

if not file_path.exists():
    st.error(f"Arquivo não encontrado: {file_path}")
    st.stop()

with open(file_path, "rb") as f:
    uploaded_file = io.BytesIO(f.read())
    uploaded_file.name = "fBaseroter.xlsx"

# Carregar dados
data_to_sync = load_and_prepare_data(uploaded_file)

if data_to_sync is not None:
    st.subheader("2. Sincronizar com Supabase")
    st.write(f"A aplicação irá **deletar todos** os dados existentes na tabela `{TABLE_NAME}` e depois inserir os {len(data_to_sync)} registros preparados do arquivo local.")
    #st.warning("⚠️ **Atenção:** Esta operação é irreversível e utiliza uma chave 'anon' que pode não ter permissão para deletar.")

    if st.button("Sincronizar"):
        progress_bar = st.progress(0, text="Iniciando sincronização...")
        status_text = st.empty()
        log_area = st.expander("Logs Detalhados", expanded=False)

        try:
            status_text.info(f"Deletando dados da tabela '{TABLE_NAME}'...")
            delete_response = supabase.table(TABLE_NAME).delete().neq(DELETE_FILTER_COLUMN, '---NON_EXISTENT_VALUE---').execute()
            log_area.write(f"Resposta da deleção: {delete_response}")

            progress_bar.progress(33, text="Inserindo novos dados...")
            total_inserted = 0
            batch_size = 500
            total_records = len(data_to_sync)
            num_batches = (total_records + batch_size - 1) // batch_size

            for i in range(num_batches):
                batch = data_to_sync[i * batch_size : (i + 1) * batch_size]
                insert_response = supabase.table(TABLE_NAME).insert(batch).execute()
                log_area.write(f"Lote {i+1}: {len(batch)} registros inseridos.")
                total_inserted += len(batch)
                progress_bar.progress(33 + int((i + 1) / num_batches * 67), text=f"Inserindo lote {i+1}/{num_batches}...")

            progress_bar.progress(100, text="Sincronização finalizada.")
            status_text.success(f"Sincronização concluída com {total_inserted} registros.")
            st.success("✅ Arquivo sincronizado com sucesso!")

            # Mostrar botão para ir à próxima página
            st.markdown("### 👉 Próximo passo:")
            if st.button("Ir para Pré-Roterização 🚚"):
                st.markdown("""
                    <script>
                        window.location.href = window.location.origin + "/#2_pre_roterizacao";
                    </script>
                """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Erro durante a sincronização: {e}")
            log_area.write(f"Exceção: {e}")


        st.success("✅ Arquivo sincronizado com sucesso!")

        


