#sincronização, Pré Roterização e Rotas Confirmadas funcionando

import streamlit as st

st.set_page_config(page_title="Roterização", layout="wide")

import pandas as pd
import numpy as np
import io
import time
import uuid
import bcrypt
from datetime import datetime, timedelta, timezone
from datetime import datetime, date
import streamlit as st
import pandas as pd
from http.cookies import SimpleCookie
import os
from dotenv import load_dotenv
from pandas import Timestamp


from streamlit_cookies_manager import EncryptedCookieManager
from datetime import datetime
from supabase import create_client, Client
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from pathlib import Path
from st_aggrid.shared import JsCode


# ========== SUPABASE CONFIG ========== #
url = "https://xhwotwefiqfwfabenwsi.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhod290d2VmaXFmd2ZhYmVud3NpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDgzNjc4NTMsImV4cCI6MjA2Mzk0Mzg1M30.3E2z-1SaABbCaV_HjQf0Rj8249mnPeGv7YkV4gOGhlg"  # Substitua pela sua chave real

@st.cache_resource(show_spinner=False)
def init_supabase_client():
    try:
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro ao inicializar cliente Supabase: {e}")
        return None

supabase = init_supabase_client()
if supabase is None:
    st.stop()

# ========== SENHA COOKIES ========== #
load_dotenv()
COOKIE_PASSWORD = os.getenv("COOKIE_SECRET", "senha_padrao_insegura")

# ========== COOKIES ========== #
cookies = EncryptedCookieManager(
    password=COOKIE_PASSWORD,
    prefix="app_"
)

if not cookies.ready():
    st.stop()

# ========== UTILIDADES DE SENHA ========== #
def hash_senha(senha):
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()

def verificar_senha(senha_fornecida, senha_hash):
    return bcrypt.checkpw(senha_fornecida.encode(), senha_hash.encode())

# ========== AUTENTICAÇÃO ========== #
def autenticar_usuario(nome_usuario, senha):
    try:
        dados = supabase.table("usuarios").select("*").eq("nome_usuario", nome_usuario).execute()
        #st.write("🔍 Dados retornados:", dados.data)

        if dados.data:
            usuario = dados.data[0]
            hash_bruto = str(usuario["senha_hash"]).replace("\n", "").replace("\r", "").strip()

            #st.write("➡️ Comparando senha:", senha)
            #st.write("➡️ Hash corrigido:", hash_bruto)

            if verificar_senha(senha, hash_bruto):
                return usuario
        return None
    except Exception as e:
        st.error(f"Erro ao autenticar: {e}")
        return None

# ========== EXPIRAÇÃO ========== #
def is_cookie_expired(expiry_time_str):
    try:
        expiry = datetime.strptime(expiry_time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > expiry
    except Exception:
        return True
    
#================= MULTIPLA SELEÇÃO NO GRIDD ========================= 
def controle_selecao(chave_estado, df_todos, grid_key, grid_options):
    col1, col2 = st.columns([1, 1])

    # Botão para selecionar todas
    with col1:
        if st.button(f"🔘 Selecionar todas", key=f"btn_sel_{chave_estado}"):
            st.session_state[chave_estado] = "selecionar_tudo"

    # Botão para desmarcar todas
    with col2:
        if st.button(f"❌ Desmarcar todas", key=f"btn_desmarcar_{chave_estado}"):
            st.session_state[chave_estado] = "desmarcar_tudo"

    # ✅ Garantir scroll horizontal
    grid_options["domLayout"] = "normal"

    # Renderiza o grid com altura fixa
    grid_response = AgGrid(
        df_todos,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        height=600,
        allow_unsafe_jscode=True,
        key=grid_key
    )

    # Lógica de seleção
    if st.session_state.get(chave_estado) == "selecionar_tudo":
        return df_todos.copy()

    elif st.session_state.get(chave_estado) == "desmarcar_tudo":
        return pd.DataFrame([])

    else:
        return pd.DataFrame(grid_response.get("selected_rows", []))



#################################

# LOGIN

#################################
def login():
    login_cookie = cookies.get("login")
    username_cookie = cookies.get("username")
    is_admin_cookie = cookies.get("is_admin")
    expiry_time_cookie = cookies.get("expiry_time")

    if login_cookie and username_cookie and not is_cookie_expired(expiry_time_cookie):
        st.session_state.login = True
        st.session_state.username = username_cookie
        st.session_state.is_admin = is_admin_cookie == "True"
        return

    # Cria três colunas e usa a do meio
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 🔐 Login")
        nome = st.text_input("Usuário").strip()
        senha = st.text_input("Senha", type="password").strip()

        if st.button("Entrar"):
            usuario = autenticar_usuario(nome, senha)
            if usuario:
                cookies["login"] = "True"
                cookies["username"] = usuario["nome_usuario"]
                cookies["is_admin"] = str(usuario.get("is_admin", False))
                expiry = datetime.now(timezone.utc) + timedelta(hours=24)
                cookies["expiry_time"] = expiry.strftime("%Y-%m-%d %H:%M:%S")

                st.session_state.login = True
                st.session_state.username = usuario["nome_usuario"]
                st.session_state.is_admin = usuario.get("is_admin", False)

                if usuario.get("precisa_alterar_senha") is True:
                    st.warning("🔐 Você deve alterar sua senha antes de continuar.")
                    pagina_trocar_senha()
                    st.stop()

                st.success("✅ Login bem-sucedido!")
                st.rerun()
            else:
                st.error("🛑 Usuário ou senha incorretos.")

    st.stop()



# ========== PÁGINA: ALTERAR SENHA PRÓPRIA ========== #
def pagina_trocar_senha():
    st.title("🔐 Alterar Minha Senha")

    usuario_atual = st.session_state.get("username")
    if not usuario_atual:
        st.error("Usuário não autenticado.")
        return

    senha_atual = st.text_input("Senha atual", type="password")
    nova_senha = st.text_input("Nova senha", type="password")
    confirmar_senha = st.text_input("Confirmar nova senha", type="password")

    if st.button("Atualizar Senha"):
        usuario = autenticar_usuario(usuario_atual, senha_atual)
        if usuario:
            if nova_senha != confirmar_senha:
                st.warning("⚠️ A nova senha e a confirmação não coincidem.")
                return

            try:
                novo_hash = hash_senha(nova_senha)
                update_data = {"senha_hash": novo_hash}

                # Remove a flag de troca obrigatória (se existir)
                if usuario.get("precisa_alterar_senha") is True:
                    update_data["precisa_alterar_senha"] = False

                supabase.table("usuarios").update(update_data).eq("nome_usuario", usuario_atual).execute()
                st.success("✅ Senha alterada com sucesso!")
                st.rerun()

            except Exception as e:
                st.error(f"Erro ao atualizar senha: {e}")
        else:
            st.error("❌ Senha atual incorreta.")

# ========== PÁGINA: GERENCIAR USUÁRIOS (ADMIN) ========== #
def pagina_gerenciar_usuarios():
    if not st.session_state.get("is_admin", False):
        st.warning("Acesso negado.")
        return

    st.title("🔐 Gerenciamento de Usuários")

    usuarios = supabase.table("usuarios").select("*").execute().data
    df = pd.DataFrame(usuarios)
    if not df.empty:
        st.dataframe(df[["nome_usuario", "is_admin", "classe"]])

    st.subheader("➕ Criar novo usuário")
    novo_usuario = st.text_input("Novo nome de usuário")
    nova_senha = st.text_input("Senha", type="password")
    nova_classe = st.selectbox("Classe", ["colaborador", "aprovador"], key="classe_nova")
    novo_admin = st.checkbox("Tornar administrador")

    if st.button("Criar"):
        if novo_usuario and nova_senha:
            try:
                senha_hash = hash_senha(nova_senha)
                supabase.table("usuarios").insert({
                    "nome_usuario": novo_usuario,
                    "senha_hash": senha_hash,
                    "classe": nova_classe,
                    "is_admin": novo_admin,
                    # "precisa_alterar_senha": True
                }).execute()
                st.success("Usuário criado com sucesso!")
                st.session_state.pagina = "Gerenciar Usuários"
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao criar usuário: {e}")
        else:
            st.warning("Preencha todos os campos.")

    st.subheader("✏️ Atualizar usuário existente")
    if not df.empty:
        usuario_alvo = st.selectbox("Selecionar usuário", df["nome_usuario"].tolist())
        nova_senha_user = st.text_input("Nova senha (deixe em branco se não for alterar)")
        nova_classe_user = st.selectbox("Nova classe", ["colaborador", "aprovador"], key="classe_edit")
        novo_admin_status = st.checkbox("Administrador?", value=bool(df[df["nome_usuario"] == usuario_alvo]["is_admin"].iloc[0]))

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Atualizar", key="btn_atualizar"):
                update = {"classe": nova_classe_user, "is_admin": novo_admin_status}
                if nova_senha_user:
                    update["senha_hash"] = hash_senha(nova_senha_user)
                try:
                    supabase.table("usuarios").update(update).eq("nome_usuario", usuario_alvo).execute()
                    st.success("Usuário atualizado.")
                    st.session_state.pagina = "Gerenciar Usuários"
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao atualizar usuário: {e}")

        with col2:
            confirm_key = f"confirm_delete_{usuario_alvo}"

            # Apenas cria o checkbox com a chave, sem atribuir st.session_state diretamente
            confirm = st.checkbox(f"Confirmar exclusão do usuário '{usuario_alvo}'?", key=confirm_key)

            if confirm:
                if st.button("Deletar", key="btn_deletar"):
                    try:
                        supabase.table("usuarios").delete().eq("nome_usuario", usuario_alvo).execute()
                        st.success(f"Usuário '{usuario_alvo}' deletado com sucesso.")
                        st.session_state.pagina = "Gerenciar Usuários"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao deletar usuário: {e}")
            else:
                st.info("Marque a caixa para confirmar a exclusão.")

###############################################
# CONFIG BANCO
###############################################
# Supabase config
url = "https://xhwotwefiqfwfabenwsi.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhod290d2VmaXFmd2ZhYmVud3NpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDgzNjc4NTMsImV4cCI6MjA2Mzk0Mzg1M30.3E2z-1SaABbCaV_HjQf0Rj8249mnPeGv7YkV4gOGhlg"
TABLE_NAME = "fBaseroter"
EXCEL_SHEET_NAME = "Sheet1"
DELETE_FILTER_COLUMN = "Setor de Destino"



supabase = init_supabase_client()
if supabase is None:
    st.error("Não foi possível conectar ao Supabase. Verifique a URL e a chave de acesso.")
    st.stop()



def convert_value(v):
    """Converte valores para tipos JSON serializáveis e strings padrão para datas."""
    if v is None:
        return None
    if isinstance(v, float) and np.isnan(v):
        return None
    if isinstance(v, (Timestamp, datetime, date)):
        return v.strftime('%Y-%m-%d')
    if isinstance(v, np.generic):
        return v.item()
    return v

def clean_records(records):
    cleaned = []
    for record in records:
        cleaned_record = {k: convert_value(v) for k, v in record.items()}
        cleaned.append(cleaned_record)
    return cleaned
# Função de leitura e preparação dos dados
def load_and_prepare_data(uploaded_file):
    if uploaded_file is None:
        return None

    try:
        df = pd.read_excel(uploaded_file, sheet_name=EXCEL_SHEET_NAME)
        excel_to_supabase_col_map = {
            "Serie/Numero CTRC": "Serie_Numero_CTRC"
        }
        df.rename(columns=excel_to_supabase_col_map, inplace=True)


        st.success(f"Arquivo '{getattr(uploaded_file, 'name', 'desconhecido')}' lido com sucesso.")

        supabase_columns = [
            "Serie_Numero_CTRC", "Serie/Numero CT-e", "Tipo do Documento", "Unidade Emissora",
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

        primary_key = "Serie_Numero_CTRC"
        if primary_key in df.columns and df[primary_key].isnull().any():
            st.warning(f"Aviso: chave primária '{primary_key}' contém nulos.")
            df.dropna(subset=[primary_key], inplace=True)

            # ✅ GARANTE QUE CNPJ DESTINATARIO ESTEJA LIMPO E PREENCHIDO COMO STRING
        if "CNPJ Destinatario" in df.columns:
            df["CNPJ Destinatario"] = df["CNPJ Destinatario"].astype(str).str.strip()

        data_to_insert = df.to_dict(orient='records')

        cleaned_data = []
        for record in data_to_insert:
            cleaned_record = {k: convert_value(v) for k, v in record.items()}
            cleaned_data.append(cleaned_record)

        st.info(f"Dados preparados: {len(cleaned_data)} registros prontos para sincronizar.")
        return cleaned_data

    except Exception as e:
        st.error(f"Erro ao processar o Excel: {e}")
        return None
    


# 🔽 INSIRA AQUI
def criar_grid_destacado(df, key, selection_mode="multiple", page_size=500, altura=500):
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(
        resizable=True,
        sortable=True,
        filter=True,
        minWidth=150
    )
    gb.configure_selection(selection_mode, use_checkbox=True)
    gb.configure_pagination(enabled=True, paginationAutoPageSize=False)
    gb.configure_grid_options(paginationPageSize=page_size)

    # 🔶 Estilo condicional por linha (entrega com Status=Agendar e Entrega Programada vazia)
    js_code = """
    function(params) {
        if (
            params.data.Status?.toLowerCase() === 'agendar' &&
            (!params.data["Entrega Programada"] || params.data["Entrega Programada"].trim() === '')
        ) {
            return {
                'backgroundColor': '#fff3cd',
                'fontWeight': 'bold'
            }
        }
    }
    """

    gb.configure_grid_options(getRowStyle=js_code)

    grid_options = gb.build()

    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        fit_columns_on_grid_load=False,
        height=600,
        allow_unsafe_jscode=True,
        key=key
    )

    return grid_response



##############################
# Página de sincronização
##############################
def pagina_sincronizacao():
    st.title("🔄 Sincronização de Dados")
    st.subheader("1. Envie o arquivo Excel com os dados")

    uploaded_file = st.file_uploader("📂 Selecione o arquivo .xlsx", type=["xlsx"])

    if uploaded_file is None:
        st.warning("Por favor, importe o arquivo fBaseroter para continuar.")
        return

    data_to_sync = load_and_prepare_data(uploaded_file)

    def remover_colunas(df, colunas_para_remover):
        for col in colunas_para_remover:
            if col in df.columns:
                df = df.drop(columns=[col])
        return df

    def aplicar_rotas_e_particularidades(df):
        if df.empty:
            return df

        df['CNPJ Destinatario'] = df['CNPJ Destinatario'].astype(str).str.strip()
        df['Cidade de Entrega'] = df['Cidade de Entrega'].astype(str).str.strip().str.upper()
        df['Bairro do Destinatario'] = df['Bairro do Destinatario'].astype(str).str.strip().str.upper()

        # Carrega tabelas auxiliares
        agendadas = pd.DataFrame(supabase.table("Clientes_Entrega_Agendada").select("*").execute().data)
        particularidades = pd.DataFrame(supabase.table("Particularidades").select("*").execute().data)
        rotas = pd.DataFrame(supabase.table("Rotas").select("*").execute().data)
        rotas_poa = pd.DataFrame(supabase.table("RotasPortoAlegre").select("*").execute().data)

        if not agendadas.empty and {'CNPJ', 'Status de Agenda'}.issubset(agendadas.columns):
            agendadas['CNPJ'] = agendadas['CNPJ'].astype(str).str.strip()
            df = df.merge(
                agendadas[['CNPJ', 'Status de Agenda']],
                how='left',
                left_on='CNPJ Destinatario',
                right_on='CNPJ'
            ).rename(columns={'Status de Agenda': 'Status'})

        if 'Status' not in df.columns:
            df['Status'] = ''

        if not particularidades.empty and {'CNPJ', 'Particularidade'}.issubset(particularidades.columns):
            particularidades['CNPJ'] = particularidades['CNPJ'].astype(str).str.strip()
            df = df.merge(
                particularidades[['CNPJ', 'Particularidade']],
                how='left',
                left_on='CNPJ Destinatario',
                right_on='CNPJ'
            ).drop(columns=['CNPJ'], errors='ignore')

        # Aplicar rotas
        rotas['Cidade de Entrega'] = rotas['Cidade de Entrega'].astype(str).str.strip().str.upper()
        rotas['Bairro do Destinatario'] = rotas['Bairro do Destinatario'].astype(str).str.strip().str.upper()
        rotas_dict = dict(zip(rotas['Cidade de Entrega'], rotas['Rota']))

        rotas_poa['Cidade de Entrega'] = rotas_poa['Cidade de Entrega'].astype(str).str.strip().str.upper()
        rotas_poa['Bairro do Destinatario'] = rotas_poa['Bairro do Destinatario'].astype(str).str.strip().str.upper()
        rotas_poa_dict = dict(zip(rotas_poa['Bairro do Destinatario'], rotas_poa['Rota']))

        def definir_rota(row):
            if row.get('Cidade de Entrega') == 'PORTO ALEGRE':
                return rotas_poa_dict.get(row.get('Bairro do Destinatario'), '')
            return rotas_dict.get(row.get('Cidade de Entrega'), '')

        df['Rota'] = df.apply(definir_rota, axis=1)

        return df

    if data_to_sync is not None:
        st.subheader("2. Enviar para o Supabase")
        st.write("⚠️ As tabelas `pre_roterizacao` e `confirmadas_producao` serão substituídas. A tabela `fBaseroter` não será alterada.")

        if st.button("🚀 Sincronizar"):
            try:
                progress_bar = st.progress(0, text="Iniciando sincronização...")
                status_text = st.empty()
                log_area = st.expander("📄 Logs Detalhados", expanded=False)

                # ✅ ZERA TODAS AS TABELAS ENVOLVIDAS NO FLUXO
                tabelas_para_zerar = [
                    "aprovacao_custos",
                    "aprovacao_diretoria",
                    "cargas_aprovadas",
                    "cargas_geradas",
                    "confirmadas_producao",
                    "pre_roterizacao",
                    "rotas_confirmadas"
                ]
                for tabela in tabelas_para_zerar:
                    supabase.table(tabela).delete().neq("Serie_Numero_CTRC", "---NON_EXISTENT_VALUE---").execute()
                log_area.write("🧹 Tabelas auxiliares zeradas com sucesso.")

                df = pd.DataFrame(data_to_sync)

                status_text.info("💾 Enviando base completa para a tabela fBaseroter...")
                full_base_cleaned = clean_records(df.to_dict(orient="records"))
                supabase.table("fBaseroter").delete().neq("Serie_Numero_CTRC", "---NON_EXISTENT_VALUE---").execute()
                try:
                    insert_response = supabase.table("fBaseroter").insert(full_base_cleaned).execute()
                    log_area.write(f"✅ {len(full_base_cleaned)} registros inseridos na tabela `fBaseroter`.")
                except Exception as e:
                    st.error(f"❌ Falha ao inserir dados na tabela fBaseroter: {e}")
                    return


                df["Previsao de Entrega"] = pd.to_datetime(df["Previsao de Entrega"], errors='coerce')
                df["Entrega Programada"] = df["Entrega Programada"].fillna('').astype(str)

                # ✅ Conversão robusta de "Valor do Frete"
                df["Valor do Frete"] = (
                    df["Valor do Frete"]
                    .astype(str)
                    .str.replace(",", ".")
                    .str.strip()
                )
                df["Valor do Frete"] = pd.to_numeric(df["Valor do Frete"], errors="coerce")

                # ✅ Garante que 'Status' exista
                if 'Status' not in df.columns:
                    df['Status'] = ''

                d_mais_1 = datetime.now() + timedelta(days=1)



                colunas_necessarias = ["Previsao de Entrega", "Valor do Frete", "Status", "Entrega Programada"]
                faltando = [col for col in colunas_necessarias if col not in df.columns]

                if faltando:
                    st.error(f"❌ As seguintes colunas estão ausentes na base: {', '.join(faltando)}")
                    return  # ou st.stop()
                

                # ✅ Critérios obrigatórios
                # ✅ Aplica critérios obrigatórios
                obrigatorias = df[
                    (df["Previsao de Entrega"] < d_mais_1) |
                    (df["Valor do Frete"] >= 300) |
                    ((df["Status"].str.lower() == "agendar") & (df["Entrega Programada"].str.strip() == ''))
                ].copy()

                # ✅ Restantes = tudo que NÃO está em obrigatórias
                restantes = df[~df["Serie_Numero_CTRC"].isin(obrigatorias["Serie_Numero_CTRC"])].copy()

                # ✅ Garante que nenhuma entrega obrigatória já esteja na Confirmadas Produção
                confirmadas_existente = pd.DataFrame(
                    supabase.table("confirmadas_producao").select("Serie_Numero_CTRC").execute().data
                )
                if not confirmadas_existente.empty:
                    confirmadas_existente["Serie_Numero_CTRC"] = confirmadas_existente["Serie_Numero_CTRC"].astype(str).str.strip()
                    obrigatorias = obrigatorias[~obrigatorias["Serie_Numero_CTRC"].isin(confirmadas_existente["Serie_Numero_CTRC"])]

                # ✅ Garante que nenhuma entrega restante já esteja na Pré Roterização
                pre_roterizacao_existente = pd.DataFrame(
                    supabase.table("pre_roterizacao").select("Serie_Numero_CTRC").execute().data
                )
                if not pre_roterizacao_existente.empty:
                    pre_roterizacao_existente["Serie_Numero_CTRC"] = pre_roterizacao_existente["Serie_Numero_CTRC"].astype(str).str.strip()
                    restantes = restantes[~restantes["Serie_Numero_CTRC"].isin(pre_roterizacao_existente["Serie_Numero_CTRC"])]




                obrigatorias = obrigatorias.where(pd.notnull(obrigatorias), None)
                restantes = restantes.where(pd.notnull(restantes), None)

                # Colunas que não devem ir para o banco
                colunas_excluir_pre_roterizacao = [
                    'Adicional de Frete', 'Bairro', 'Chaves NF-es', 'Cliente Remetente',
                    'Codigo dos Correios', 'Compr. de Entrega Escaneado', 'Data da Entrega Realizada',
                    'Data da Ultima Ocorrencia', 'Data de Autorizacao', 'Data de Emissao',
                    'Data de inclusao da Ultima Ocorrencia', 'Data do Cancelamento', 'Data do Escaneamento',
                    'Descricao da Ultima Ocorrencia', 'Fone do Pagador', 'Frete Peso', 'Frete Valor',
                    'Hora do Escaneamento', 'Latitude da Ultima Ocorrencia', 'Local de Entrega',
                    'Longitude da Ultima Ocorrencia', 'Motivo do Cancelamento', 'Notas Fiscais',
                    'Numero da Capa de Remessa', 'Numero do Pacote de Arquivamento', 'Numero dos Pedidos',
                    'Quantidade de Dias de Atraso', 'Segmento do Pagador', 'Serie/Numero CT-e',
                    'Setor de Destino', 'TDA', 'TDE', 'Tipo do Documento', 'UF de Entrega',
                    'UF do Destinatario', 'UF do Expedidor', 'UF do Pagador', 'UF do Remetente',
                    'UF origem da prestacao', 'Unidade Emissora', 'Unidade Receptora',
                    'Unidade da Ultima Ocorrencia', 'Unnamed: 67', 'Usuario da Ultima Ocorrencia',
                    'Valor da Mercadoria', 'Valor do ICMS', 'Valor do ISS', 'Volume Cliente/Shipment'
                ]
                colunas_excluir_confirmadas = colunas_excluir_pre_roterizacao + ['Localizacao Atual']

                ## ✅ Aplica enriquecimento ANTES de remover colunas
                obrigatorias = aplicar_rotas_e_particularidades(obrigatorias)
                restantes = aplicar_rotas_e_particularidades(restantes)

                # 🔧 Remove colunas extras criadas por merge
                for df_temp in [obrigatorias, restantes]:
                    df_temp.drop(columns=[col for col in df_temp.columns if col.endswith('_x') or col.endswith('_y') or col == 'CNPJ'], inplace=True, errors='ignore')

                # Agora remove colunas desnecessárias
                obrigatorias = remover_colunas(obrigatorias, colunas_excluir_pre_roterizacao)
                restantes = remover_colunas(restantes, colunas_excluir_confirmadas)

                dados_pre_roterizacao = clean_records(obrigatorias.to_dict(orient="records"))
                dados_confirmadas_producao = clean_records(restantes.to_dict(orient="records"))
                df = df.replace([np.nan, pd.NaT, pd.NA, np.inf, -np.inf], None)

                status_text.info("🔄 Limpando tabelas `pre_roterizacao` e `confirmadas_producao`...")
                supabase.table("pre_roterizacao").delete().neq("Serie_Numero_CTRC", "---NON_EXISTENT_VALUE---").execute()
                supabase.table("confirmadas_producao").delete().neq("Serie_Numero_CTRC", "---NON_EXISTENT_VALUE---").execute()
                progress_bar.progress(25, text="Tabelas limpas.")

                if dados_pre_roterizacao:
                    supabase.table("pre_roterizacao").insert(dados_pre_roterizacao).execute()
                    log_area.write(f"{len(dados_pre_roterizacao)} entregas enviadas para `pre_roterizacao`.")
                progress_bar.progress(65, text="Entregas obrigatórias inseridas.")

                if dados_confirmadas_producao:
                    supabase.table("confirmadas_producao").insert(dados_confirmadas_producao).execute()
                    log_area.write(f"{len(dados_confirmadas_producao)} entregas enviadas para `confirmadas_producao`.")
                progress_bar.progress(100, text="Entregas restantes inseridas.")

                status_text.success("✅ Sincronização concluída com sucesso!")
                st.success(f"{len(data_to_sync)} registros processados.")
                st.cache_data.clear()
                time.sleep(1.5)
                st.rerun()

            except Exception as e:
                st.error(f"❌ Erro durante a sincronização: {e}")
                log_area.write(e)


#####################################
# PAGINA CONFIRMAR PRODUÇÃO
#####################################

def pagina_confirmar_producao():
    st.title("🏭 Confirmar Produção")

    def carregar_entregas_base():
        # Carregamento da tabela confirmadas_producao diretamente
        base = pd.DataFrame(supabase.table("confirmadas_producao").select("*").execute().data)

        # Função auxiliar para encontrar nomes de colunas semelhantes
        def encontrar_coluna_similar(df, nome_alvo):
            for col in df.columns:
                if col.strip().lower() == nome_alvo.strip().lower():
                    return col
            return None

        # Verificar e corrigir nome da coluna "Previsao de Entrega"
        col_previsao = encontrar_coluna_similar(base, "Previsao de Entrega")
        if not col_previsao:
            st.error("❌ A coluna 'Previsao de Entrega' está ausente da tabela 'confirmadas_producao'. Verifique os dados sincronizados.")
            return pd.DataFrame()

        base[col_previsao] = pd.to_datetime(base[col_previsao], errors='coerce')
        base.rename(columns={col_previsao: "Previsao de Entrega"}, inplace=True)

        # Remover entregas que já estão na aprovacao_diretoria
        aprovadas = pd.DataFrame(supabase.table("aprovacao_diretoria").select("Serie_Numero_CTRC").execute().data)
        if not aprovadas.empty:
            aprovadas["Serie_Numero_CTRC"] = aprovadas["Serie_Numero_CTRC"].astype(str).str.strip()
            base = base[~base["Serie_Numero_CTRC"].isin(aprovadas["Serie_Numero_CTRC"])]

        if base.empty:
            return base

        # Verificar se colunas essenciais estão presentes
        colunas_essenciais = [
            "Valor do Frete", "Status", "Entrega Programada",
            "CNPJ Destinatario", "Cidade de Entrega", "Bairro do Destinatario", "Cliente Pagador"
        ]
        faltando = [col for col in colunas_essenciais if col not in base.columns]
        if faltando:
            st.error(f"❌ As seguintes colunas estão ausentes da base: {', '.join(faltando)}")
            return pd.DataFrame()

        # Normalização de campos
        base['CNPJ Destinatario'] = base['CNPJ Destinatario'].astype(str).str.strip()
        base['Cidade de Entrega'] = base['Cidade de Entrega'].astype(str).str.strip().str.upper()
        base['Bairro do Destinatario'] = base['Bairro do Destinatario'].astype(str).str.strip().str.upper()
        base['Cliente Pagador'] = base['Cliente Pagador'].fillna("(Vazio)").astype(str).str.strip()

        if 'Codigo da Ultima Ocorrencia' not in base.columns:
            base['Codigo da Ultima Ocorrencia'] = None

        # Aplicar rotas
        rotas = pd.DataFrame(supabase.table("Rotas").select("*").execute().data)
        rotas_poa = pd.DataFrame(supabase.table("RotasPortoAlegre").select("*").execute().data)

        rotas['Cidade de Entrega'] = rotas['Cidade de Entrega'].astype(str).str.strip().str.upper()
        rotas['Bairro do Destinatario'] = rotas['Bairro do Destinatario'].astype(str).str.strip().str.upper()
        rotas_dict = dict(zip(rotas['Cidade de Entrega'], rotas['Rota']))

        rotas_poa['Cidade de Entrega'] = rotas_poa['Cidade de Entrega'].astype(str).str.strip().str.upper()
        rotas_poa['Bairro do Destinatario'] = rotas_poa['Bairro do Destinatario'].astype(str).str.strip().str.upper()
        rotas_poa_dict = dict(zip(rotas_poa['Bairro do Destinatario'], rotas_poa['Rota']))

        def definir_rota(row):
            if row.get('Cidade de Entrega') == 'PORTO ALEGRE':
                return rotas_poa_dict.get(row.get('Bairro do Destinatario'), '')
            return rotas_dict.get(row.get('Cidade de Entrega'), '')

        base['Rota'] = base.apply(definir_rota, axis=1)
        base['Indice'] = base.index



       # Garantir que não haja valores inválidos em 'Previsao de Entrega'
        base = base[pd.notnull(base['Previsao de Entrega'])]

        # Retornar tudo que não está na aprovacao_diretoria (já foi filtrado acima)
        return base.copy()




    # ✅ Carregar dados
    df = carregar_entregas_base()

    if df.empty:
        st.info("Nenhuma entrega pendente para confirmação.")
        return


    # Filtro por cliente
    clientes_filtrados = ["Todos"] + sorted(df["Cliente Pagador"].unique())
    cliente_selecionado = st.selectbox("🔎 Filtrar por Cliente", clientes_filtrados, key="filtro_cliente")
    if cliente_selecionado != "Todos":
        df = df[df["Cliente Pagador"] == cliente_selecionado]

    total_clientes = df["Cliente Pagador"].nunique()
    total_entregas = len(df)

    # Cards informativos
    st.markdown(f"""
    <div style="display: flex; gap: 10px; margin-bottom: 20px;">
        <div style="flex: 1; background-color: #2e2e2e; padding: 8px 16px; border-radius: 6px;">
            <span style="color: white; font-weight: bold; font-size: 18px;">Total de Clientes:</span>
            <span style="color: white; font-size: 24px;">{total_clientes}</span>
        </div>
        <div style="flex: 1; background-color: #2e2e2e; padding: 8px 16px; border-radius: 6px;">
            <span style="color: white; font-weight: bold; font-size: 18px;">Total de Entregas:</span>
            <span style="color: white; font-size: 24px;">{total_entregas}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Visão geral
    st.markdown("### 📊 Visão Geral por Cliente Pagador")
    df_grouped = df[df["Cliente Pagador"].notna()].groupby("Cliente Pagador").agg({
        "Peso Real em Kg": "sum",
        "Peso Calculado em Kg": "sum",
        "Cubagem em m³": "sum",
        "Quantidade de Volumes": "sum",
        "Valor do Frete": "sum",
        "Indice": "count"
    }).reset_index().rename(columns={"Indice": "Qtd Entregas"})
    st.dataframe(df_grouped.style.format(formatar_brasileiro), use_container_width=True)

    # Detalhamento por cliente
    st.markdown("### 📋 Entregas por Cliente")

    colunas_exibir = [
        "Serie_Numero_CTRC","Rota","Valor do Frete", "Cliente Pagador", "Chave CT-e", "Cliente Destinatario",
        "Cidade de Entrega", "Bairro do Destinatario", "Previsao de Entrega",
        "Numero da Nota Fiscal", "Status", "Entrega Programada",
        "Particularidade", "Codigo da Ultima Ocorrencia",
        "Peso Real em Kg", "Peso Calculado em Kg", "Cubagem em m³",
        "Quantidade de Volumes"
    ]

    for cliente in sorted(df["Cliente Pagador"].fillna("(Vazio)").unique()):
        st.markdown(f"<div style='background-color: #2e2e2e; padding: 10px 20px; border-radius: 6px; color: white; font-size: 22px; font-weight: bold; margin-top: 30px;'>Cliente: {cliente}</div>", unsafe_allow_html=True)
        df_cliente = df[df["Cliente Pagador"].fillna("(Vazio)") == cliente]

        col1, col2, col3, col4, col5, col6 = st.columns(6)
        col1.metric("Entregas", df_cliente.shape[0])
        col2.metric("Peso Calc. (Kg)", formatar_brasileiro(df_cliente["Peso Calculado em Kg"].sum()))
        col3.metric("Peso Real (Kg)", formatar_brasileiro(df_cliente["Peso Real em Kg"].sum()))
        col4.metric("Cubagem (m³)", formatar_brasileiro(df_cliente["Cubagem em m³"].sum()))
        col5.metric("Volumes", int(df_cliente["Quantidade de Volumes"].sum()))
        col6.metric("Valor Frete", f"R$ {formatar_brasileiro(df_cliente['Valor do Frete'].sum())}")

        df_formatado = df_cliente[[col for col in colunas_exibir if col in df_cliente.columns]].copy()

        for col in ["Peso Real em Kg", "Peso Calculado em Kg", "Cubagem em m³", "Quantidade de Volumes", "Valor do Frete"]:
            if col in df_formatado.columns:
                df_formatado[col] = pd.to_numeric(df_formatado[col], errors='coerce')
                df_formatado[col] = df_formatado[col].apply(formatar_brasileiro)

        linha_destacar = JsCode("""
        function(params) {
            if (params.data['Particularidade'] && params.data['Particularidade'].trim() !== '') {
                return {
                    'backgroundColor': '#808000',
                    'fontWeight': 'bold'
                }
            } else if (params.data['Status'] === 'AGENDAR' && 
                       (!params.data['Entrega Programada'] || params.data['Entrega Programada'].trim() === '')) {
                return {
                    'backgroundColor': '#8B4513',
                    'fontWeight': 'bold'
                }
            }
            return {};
        }
        """)

        gb = GridOptionsBuilder.from_dataframe(df_formatado)
        gb.configure_default_column(resizable=True, minWidth=150)
        gb.configure_selection('multiple', use_checkbox=True)
        #gb.configure_pagination(enabled=True, paginationAutoPageSize=False)
        gb.configure_grid_options(paginationPageSize=500)
        gb.configure_grid_options(getRowStyle=linha_destacar)


        
        grid_options = gb.build()

        grid_options["domLayout"] = "normal"  # ⬅️ Força o scroll horizontal



        selecionadas = controle_selecao(
            chave_estado=f"selecionar_tudo_cliente_{cliente}",
            df_todos=df_formatado,
            grid_key=f"grid_{cliente}",
            grid_options=grid_options
        )

        if not selecionadas.empty:
            st.success(f"{len(selecionadas)} entregas selecionadas para {cliente}.")

            if st.button(f"✅ Confirmar entregas de {cliente}", key=f"botao_{cliente}"):
                try:
                    # 🔒 Padronizar valores de chave
                    chaves = selecionadas["Serie_Numero_CTRC"].dropna().astype(str).str.strip().tolist()

                    # 🔒 Garantir que df_cliente também está padronizado
                    df_cliente["Serie_Numero_CTRC"] = df_cliente["Serie_Numero_CTRC"].astype(str).str.strip()

                    df_confirmar = df_cliente[df_cliente["Serie_Numero_CTRC"].isin(chaves)].copy()
                    colunas_validas = [col for col in colunas_exibir if col != "Serie_Numero_CTRC"]
                    df_confirmar = df_confirmar[["Serie_Numero_CTRC"] + colunas_validas]
                    df_confirmar = df_confirmar.replace([np.nan, np.inf, -np.inf], None)

                    # ✅ Converter datas para string
                    for col in df_confirmar.select_dtypes(include=['datetime64[ns]']).columns:
                        df_confirmar[col] = df_confirmar[col].dt.strftime('%Y-%m-%d %H:%M:%S')

                    # ⚠️ Verificações
                    if df_confirmar.empty:
                        st.warning("⚠️ Nenhuma entrega válida para confirmar.")
                        return

                    if "Serie_Numero_CTRC" not in df_confirmar.columns or df_confirmar["Serie_Numero_CTRC"].isnull().all():
                        st.warning("⚠️ Coluna 'Serie_Numero_CTRC' ausente ou com todos os valores nulos.")
                        return

                    # 🔒 Remover registros com chaves vazias
                    dados_confirmar = df_confirmar.to_dict(orient="records")
                    dados_confirmar = [d for d in dados_confirmar if d.get("Serie_Numero_CTRC")]

                    if not dados_confirmar:
                        st.warning("⚠️ Nenhum registro com 'Serie_Numero_CTRC' válido.")
                        return

                    # ✅ Inserir na aprovacao_diretoria
                    supabase.table("aprovacao_diretoria").insert(dados_confirmar).execute()
                    st.success("Entregas confirmadas e removidas com sucesso!")
                    

                    # ✅ Excluir da confirmadas_producao
                    delete_response = supabase.table("confirmadas_producao") \
                        .delete() \
                        .in_("Serie_Numero_CTRC", chaves) \
                        .execute()

                    # 🔍 Verificação: buscar os que eventualmente não foram deletados
                    check_response = supabase.table("confirmadas_producao") \
                        .select("Serie_Numero_CTRC") \
                        .in_("Serie_Numero_CTRC", chaves) \
                        .execute()

                    if check_response.data:
                        chaves_nao_removidas = [r["Serie_Numero_CTRC"] for r in check_response.data]
                        st.warning(f"⚠️ Algumas entregas não foram removidas da base: {chaves_nao_removidas}")
                    else:
                        st.success("Entregas confirmadas e removidas com sucesso!")
                        

                        # ✅ Resetar seleção do cliente após confirmação
                        st.session_state[f"selecionar_tudo_cliente_{cliente}"] = "desmarcar_tudo"

                        time.sleep(1.5)
                        st.rerun()

                except Exception as e:
                    st.error(f"Erro ao confirmar entregas: {e}")


###########################################

# PÁGINA APROVAÇÃO DIRETORIA

##########################################
def pagina_aprovacao_diretoria():
    st.title("📋 Aprovação da Diretoria")

    usuario = st.session_state.get("username")
    dados_usuario = supabase.table("usuarios").select("classe").eq("nome_usuario", usuario).execute().data
    if not dados_usuario or dados_usuario[0].get("classe") != "aprovador":
        st.warning("🔒 Apenas usuários com classe **aprovador** podem acessar esta página.")
        return

    df = pd.DataFrame(supabase.table("aprovacao_diretoria").select("*").execute().data)

    #st.write("🔍 Dados encontrados:", df.shape)
    if df.empty:
        st.info("Nenhuma entrega pendente para aprovação.")
        return

    df["Cliente Pagador"] = df["Cliente Pagador"].astype(str).str.strip().fillna("(Vazio)")

    clientes = ["Todos"] + sorted(df["Cliente Pagador"].unique())
    cliente_selecionado = st.selectbox("🔎 Filtrar por Cliente:", clientes)
    if cliente_selecionado != "Todos":
        df = df[df["Cliente Pagador"] == cliente_selecionado]

    total_clientes = df["Cliente Pagador"].nunique()
    total_entregas = len(df)

    col1, col2 = st.columns(2)
    col1.markdown(f"### Total de Clientes: **{total_clientes}**")
    col2.markdown(f"### Total de Entregas: **{total_entregas}**")

    st.markdown("---")

    df_grouped = df.groupby("Cliente Pagador").agg({
        "Peso Real em Kg": "sum",
        "Peso Calculado em Kg": "sum",
        "Cubagem em m³": "sum",
        "Quantidade de Volumes": "sum",
        "Valor do Frete": "sum",
        "Serie_Numero_CTRC": "count"
    }).reset_index().rename(columns={"Serie_Numero_CTRC": "Qtd Entregas"})

    st.markdown("### 📊 Resumo por Cliente")
    st.dataframe(df_grouped.style.format(formatar_brasileiro), use_container_width=True)

    st.markdown("### 📦 Entregas por Cliente")

    colunas_exibir = [
        "Serie_Numero_CTRC","Rota","Valor do Frete", "Cliente Pagador", "Chave CT-e", 
        "Cliente Destinatario","Cidade de Entrega", "Bairro do Destinatario", "Previsao de Entrega",
        "Numero da Nota Fiscal", "Status", "Entrega Programada",
        "Particularidade", "Codigo da Ultima Ocorrencia",
        "Peso Real em Kg", "Peso Calculado em Kg", "Cubagem em m³",
        "Quantidade de Volumes"
    ]

    for cliente in sorted(df["Cliente Pagador"].unique()):
        st.markdown(f"### Cliente: **{cliente}**")
        df_cliente = df[df["Cliente Pagador"] == cliente]

        col1, col2, col3, col4, col5, col6 = st.columns(6)
        col1.metric("Entregas", len(df_cliente))
        col2.metric("Peso Calc.", formatar_brasileiro(df_cliente["Peso Calculado em Kg"].sum()))
        col3.metric("Peso Real", formatar_brasileiro(df_cliente["Peso Real em Kg"].sum()))
        col4.metric("Cubagem", formatar_brasileiro(df_cliente["Cubagem em m³"].sum()))
        col5.metric("Volumes", int(df_cliente["Quantidade de Volumes"].sum()))
        col6.metric("Frete", f"R$ {formatar_brasileiro(df_cliente['Valor do Frete'].sum())}")

        df_formatado = df_cliente[colunas_exibir].copy()
        for col in ["Peso Real em Kg", "Peso Calculado em Kg", "Cubagem em m³", "Quantidade de Volumes", "Valor do Frete"]:
            if col in df_formatado.columns:
                df_formatado[col] = df_formatado[col].apply(formatar_brasileiro)

        # ✅ Aqui dentro do loop por cliente
        linha_destacar = JsCode("""
        function(params) {
            const status = params.data['Status'];
            const entrega = params.data['Entrega Programada'];

            if (
                status &&
                status.toUpperCase() === 'AGENDAR' &&
                (!entrega || entrega.toString().trim() === '')
            ) {
                return {
                    'backgroundColor': '#8B4513',
                    'color': 'white',
                    'fontWeight': 'bold'
                };
            }
            return {};
        }
        """)

        gb = GridOptionsBuilder.from_dataframe(df_formatado)
        gb.configure_default_column(resizable=True, minWidth=150)
        gb.configure_selection("multiple", use_checkbox=True)
        #gb.configure_pagination(enabled=True)
        gb.configure_grid_options(paginationPageSize=600)

        # Build e adicionar JsCode corretamente
        grid_options = gb.build()
        grid_options["getRowStyle"] = linha_destacar

        selecionadas = controle_selecao(
        chave_estado=f"selecionar_tudo_aprovacao_{cliente}",
        df_todos=df_formatado,
        grid_key=f"grid_{cliente}",
        grid_options=grid_options
    )


        if not selecionadas.empty:
            st.success(f"{len(selecionadas)} entregas selecionadas.")

            if st.button(f"✅ Aprovar entregas de {cliente}", key=f"btn_aprovar_{cliente}"):
                try:
                    aprovadas = selecionadas.copy()

                    # Corrigir campos numéricos
                    colunas_numericas = [
                        "Peso Real em Kg", "Peso Calculado em Kg", "Cubagem em m³",
                        "Quantidade de Volumes", "Valor do Frete"
                    ]
                    for col in colunas_numericas:
                        if col in aprovadas.columns:
                            aprovadas[col] = aprovadas[col].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False).astype(float)

                    if "Rota" not in aprovadas.columns:
                        st.warning("Coluna 'Rota' não encontrada nos dados selecionados.")
                        return

                    if "_selectedRowNodeInfo" in aprovadas.columns:
                        aprovadas.drop(columns=["_selectedRowNodeInfo"], inplace=True)

                    # Buscar CTRCs já presentes na pre_roterizacao
                    ctrcs_existentes = supabase.table("pre_roterizacao").select("Serie_Numero_CTRC").execute().data
                    ctrcs_existentes = {item["Serie_Numero_CTRC"] for item in ctrcs_existentes}

                    # Filtrar para não duplicar
                    aprovadas = aprovadas[~aprovadas["Serie_Numero_CTRC"].isin(ctrcs_existentes)]

                    # Se ainda houver entregas válidas
                    if not aprovadas.empty:
                        supabase.table("pre_roterizacao").insert(aprovadas.to_dict(orient="records")).execute()

                        ctrcs = aprovadas["Serie_Numero_CTRC"].astype(str).tolist()
                        supabase.table("aprovacao_diretoria").delete().in_("Serie_Numero_CTRC", ctrcs).execute()

                        st.success("✅ Entregas aprovadas e movidas para Pré Roteirização.")
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.info("Todas as entregas selecionadas já estavam na Pré-Roterização.")
                except Exception as e:
                    st.error(f"Erro ao aprovar entregas: {e}")



###########################################
# PÁGINA PRÉ ROTERIZAÇÃO
##########################################
def formatar_brasileiro(valor):
    try:
        if isinstance(valor, (int, float, np.float64)):
            return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return valor
    except:
        return valor

def carregar_base_supabase():
    try:
        base = pd.DataFrame(supabase.table("pre_roterizacao").select("*").execute().data)
        if base.empty:
            st.warning("⚠️ Nenhuma entrega encontrada na tabela `pre_roterizacao`.")
            return pd.DataFrame()

        agendadas = pd.DataFrame(supabase.table("Clientes_Entrega_Agendada").select("*").execute().data)
        particularidades = pd.DataFrame(supabase.table("Particularidades").select("*").execute().data)
        rotas = pd.DataFrame(supabase.table("Rotas").select("*").execute().data)
        rotas_poa = pd.DataFrame(supabase.table("RotasPortoAlegre").select("*").execute().data)
        confirmadas = pd.DataFrame(supabase.table("confirmadas_producao").select("*").execute().data)

        base['CNPJ Destinatario'] = base['CNPJ Destinatario'].astype(str).str.strip()
        if {'CNPJ', 'Status de Agenda'}.issubset(agendadas.columns):
            agendadas['CNPJ'] = agendadas['CNPJ'].astype(str).str.strip()
            base = base.merge(
                agendadas[['CNPJ', 'Status de Agenda']],
                how='left',
                left_on='CNPJ Destinatario',
                right_on='CNPJ'
            ).rename(columns={'Status de Agenda': 'Status'}).drop(columns=['CNPJ'], errors='ignore')
            
        if (
            'CNPJ Destinatario' in base.columns and
            not particularidades.empty and
            {'CNPJ', 'Particularidade'}.issubset(particularidades.columns)
        ):
            particularidades['CNPJ'] = particularidades['CNPJ'].astype(str).str.strip()
            base['CNPJ Destinatario'] = base['CNPJ Destinatario'].astype(str).str.strip()
            base = base.merge(
                particularidades[['CNPJ', 'Particularidade']],
                how='left',
                left_on='CNPJ Destinatario',
                right_on='CNPJ'
            ).drop(columns=['CNPJ'], errors='ignore')
        else:
            base['Particularidade'] = ''

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
            'Frete Peso', 'Frete Valor', 'TDA', 'TDE'
        ]
        for col in colunas_numericas:
            if col in base.columns:
                base[col] = pd.to_numeric(base[col], errors='coerce')

        base['Indice'] = base.index
        base = base.loc[:, ~base.columns.duplicated()]

        hoje = pd.Timestamp.today().normalize()
        d_mais_1 = hoje + pd.Timedelta(days=1)

        obrigatorias = base[
            (pd.to_datetime(base['Previsao de Entrega'], errors='coerce') < d_mais_1)
            |
            (base['Valor do Frete'] >= 300)
            |
            ((base['Status'] == 'Agendar') & (base['Entrega Programada'].isnull() | base['Entrega Programada'].eq('')))
        ].copy()

        if not confirmadas.empty:
            col_ctrc = 'Serie_Numero_CTRC'
            confirmadas[col_ctrc] = confirmadas[col_ctrc].astype(str).str.strip()
            obrigatorias = obrigatorias[~obrigatorias['Serie_Numero_CTRC'].isin(confirmadas[col_ctrc])]

        def deduplicar_colunas(df):
            cols = pd.Series(df.columns)
            for dup in cols[cols.duplicated()].unique():
                dup_idxs = cols[cols == dup].index.tolist()
                for i, idx in enumerate(dup_idxs):
                    cols[idx] = f"{dup}.{i}" if i > 0 else dup
            df.columns = cols
            return df

        confirmadas = deduplicar_colunas(confirmadas)
        obrigatorias = deduplicar_colunas(obrigatorias)

        confirmadas = confirmadas.loc[:, ~confirmadas.columns.duplicated()]
        obrigatorias = obrigatorias.loc[:, ~obrigatorias.columns.duplicated()]


        colunas_comuns = confirmadas.columns.intersection(obrigatorias.columns)
        confirmadas = confirmadas[colunas_comuns]
        obrigatorias = obrigatorias[colunas_comuns]

        df_final = obrigatorias.copy()
        df_final['Indice'] = df_final.index
        

        return df_final

    except Exception as e:
        st.error(f"Erro ao consultar as tabelas do Supabase: {e}")
        return pd.DataFrame()

def pagina_pre_roterizacao():
    st.title("Pré Roterização")

    df = carregar_base_supabase()

    df_pre_roterizacao = pd.DataFrame(supabase.table("pre_roterizacao").select("Serie_Numero_CTRC, Particularidade").execute().data)
    qtd_entregas_pre_roterizacao = len(df_pre_roterizacao)

    if df is None or df.empty:
        return

    dados_confirmados_raw = supabase.table("rotas_confirmadas").select("*").execute().data
    dados_confirmados = pd.DataFrame(dados_confirmados_raw)
    if not dados_confirmados.empty:
        df = df[~df["Serie_Numero_CTRC"].isin(dados_confirmados["Serie_Numero_CTRC"].astype(str))]

    rotas_opcoes = ["Todas"] + sorted(df["Rota"].dropna().unique())
    rota_selecionada = st.selectbox("🔎 Filtrar por Rota:", rotas_opcoes, key="filtro_rota")
    if rota_selecionada != "Todas":
        df = df[df["Rota"] == rota_selecionada]

    qtd_rotas = df["Rota"].nunique()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f"<div style='background:#2f2f2f;padding:8px;border-radius:8px'>"
            f"<span style='color:white;font-weight:bold;font-size:18px;'>Total de Rotas:</span>"
            f"<span style='color:white;font-size:24px;'> {qtd_rotas}</span></div>",
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            f"<div style='background:#2f2f2f;padding:8px;border-radius:8px'>"
            f"<span style='color:white;font-weight:bold;font-size:18px;'>Total de Entregas:</span>"
            f"<span style='color:white;font-size:24px;'> {qtd_entregas_pre_roterizacao}</span></div>",
            unsafe_allow_html=True
        )

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

    for rota in sorted(df["Rota"].dropna().unique()):
        df_rota = df[df["Rota"] == rota]
        st.markdown(f"<div style='font-size:22px;font-weight:bold;color:#f0f0f0;background:#2c2c2c;padding:10px;border-radius:8px'>Rota: {rota}</div>", unsafe_allow_html=True)

        col1, col2, col3, col4, col5, col6 = st.columns(6)
        col1.metric("Entregas", len(df_rota))
        col2.metric("Peso Calc. (Kg)", formatar_brasileiro(df_rota["Peso Calculado em Kg"].sum()))
        col3.metric("Peso Real (Kg)", formatar_brasileiro(df_rota["Peso Real em Kg"].sum()))
        col4.metric("Cubagem (m³)", formatar_brasileiro(df_rota["Cubagem em m³"].sum()))
        col5.metric("Volumes", int(df_rota["Quantidade de Volumes"].sum()))
        col6.metric("Valor Frete", f"R$ {formatar_brasileiro(df_rota['Valor do Frete'].sum())}")

        if 'Particularidade' not in df_rota.columns:
            df_rota['Particularidade'] = df_rota['Serie_Numero_CTRC'].map(
                dict(zip(df_pre_roterizacao['Serie_Numero_CTRC'], df_pre_roterizacao['Particularidade']))
            )

        colunas_exibir = [
            "Serie_Numero_CTRC", "Cliente Pagador", "Chave CT-e", "Cliente Destinatario",
            "Cidade de Entrega", "Bairro do Destinatario", "Previsao de Entrega",
            "Numero da Nota Fiscal", "Status", "Entrega Programada", "Particularidade",
            "Codigo da Ultima Ocorrencia", "Peso Real em Kg", "Peso Calculado em Kg",
            "Cubagem em m³", "Quantidade de Volumes", "Valor do Frete", "Rota"
        ]

        df_formatado = df_rota[[col for col in colunas_exibir if col in df_rota.columns]].copy()

        for col in ["Peso Real em Kg", "Peso Calculado em Kg", "Cubagem em m³", "Quantidade de Volumes", "Valor do Frete"]:
            if col in df_formatado.columns:
                df_formatado[col] = pd.to_numeric(df_formatado[col], errors='coerce')
                df_formatado[col] = df_formatado[col].apply(formatar_brasileiro)

        linha_destacar = JsCode("""
        function(params) {
            if (params.data['Particularidade'] && params.data['Particularidade'].trim() !== '') {
                return {
                    'backgroundColor': '#808000',
                    'fontWeight': 'bold'
                }
            } else if (params.data['Status'] === 'AGENDAR' && 
                       (!params.data['Entrega Programada'] || params.data['Entrega Programada'].trim() === '')) {
                return {
                    'backgroundColor': '#8B4513',
                    'fontWeight': 'bold'
                }
            }
            return {};
        }
        """)

        gb = GridOptionsBuilder.from_dataframe(df_formatado)
        gb.configure_default_column(resizable=True, minWidth=150)
        gb.configure_selection("multiple", use_checkbox=True)
        gb.configure_grid_options(getRowStyle=linha_destacar)
        gb.configure_grid_options(paginationPageSize=500)

        grid_options = gb.build()

        selecionadas = controle_selecao(
        chave_estado=f"selecionar_tudo_pre_rota_{rota}",
        df_todos=df_formatado,
        grid_key=f"grid_{rota}",
        grid_options=grid_options
        )

        if not selecionadas.empty:
            if "Serie_Numero_CTRC" not in selecionadas.columns:
                st.error("❌ A coluna 'Serie_Numero_CTRC' não foi retornada pelo AgGrid. Certifique-se de que ela está visível no grid.")
                return

            selecionadas = selecionadas[selecionadas["Serie_Numero_CTRC"].notnull()]

            chaves = selecionadas["Serie_Numero_CTRC"].dropna().astype(str).str.strip().tolist()
            df_selecionadas = df_rota[df_rota["Serie_Numero_CTRC"].isin(chaves)].copy()
            df_selecionadas["Rota"] = rota
            df_selecionadas.drop(columns=["Indice"], inplace=True, errors="ignore")
            df_selecionadas = df_selecionadas.replace([np.nan, np.inf, -np.inf], None)

            st.success(f"🔒 {len(df_selecionadas)} entregas selecionadas na rota **{rota}**.")
            chave_hash = "_" + str(hash("-".join(chaves)))[:6]
            col_conf, col_ret = st.columns(2)

            with col_conf:
                if st.button(f"✅ Confirmar Rota: {rota}", key=f"confirmar_{rota}{chave_hash}"):
                    try:
                        # Corrigir campos de data com string vazia para None
                        for col in df_selecionadas.columns:
                            if 'data' in col.lower() or 'entrega programada' in col.lower():
                                df_selecionadas[col] = df_selecionadas[col].replace("", None)

                        if "Serie_Numero_CTRC" not in df_selecionadas.columns:
                            st.error("❌ A coluna 'Serie_Numero_CTRC' está ausente nos dados selecionados.")
                            return

                        df_selecionadas = df_selecionadas[df_selecionadas["Serie_Numero_CTRC"].notnull()]

                        supabase.table("rotas_confirmadas").insert(df_selecionadas.to_dict(orient="records")).execute()
                        st.success(f"✅ {len(df_selecionadas)} entregas confirmadas com sucesso na rota **{rota}**!")
                        time.sleep(1.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro ao confirmar entregas: {e}")

            with col_ret:
                if st.button(f"❌ Retirar da Pré Rota: {rota}", key=f"retirar_{rota}{chave_hash}"):
                    try:
                        for ctrc in df_selecionadas["Serie_Numero_CTRC"]:
                            supabase.table("rotas_confirmadas").delete().eq("Serie_Numero_CTRC", ctrc).execute()
                        registros_confirmar = [{"Serie_Numero_CTRC": ctrc} for ctrc in df_selecionadas["Serie_Numero_CTRC"]]
                        supabase.table("confirmadas_producao").insert(registros_confirmar).execute()
                        st.success("🔄 Entregas retornadas para a etapa de produção com sucesso.")
                        time.sleep(1.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro ao retornar entregas: {e}")






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
                gb.configure_pagination(enabled=True, paginationAutoPageSize=False)
                gb.configure_grid_options(paginationPageSize=500)


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
                    height=600,
                    allow_unsafe_jscode=True
                )

                df_selecionadas = pd.DataFrame(grid_response.get("selected_rows", []))

                if not df_selecionadas.empty:
                    st.warning(f"{len(df_selecionadas)} entrega(s) selecionada(s). Clique abaixo para remover da rota confirmada.")

                    confirmar = st.checkbox("Confirmar remoção das entregas selecionadas", key=f"confirmar_remocao_{rota}")
                    if st.button(f"❌ Remover selecionadas da Rota {rota}", key=f"remover_{rota}") and confirmar:
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




# ========== EXECUÇÃO PRINCIPAL ========== #
login()  # Garante que o usuário esteja logado

# Mostrar welcome + botão sair no topo da sidebar
if st.session_state.get("login", False):
    col1, col2 = st.sidebar.columns([4, 1])
    with col1:
        st.markdown(f"👋 **Bem-vindo, {st.session_state.get('username','Usuário')}!**")
    with col2:
        if st.button("🔒 Sair"):
            for key in ["login", "username", "is_admin", "expiry_time"]:
                cookies[key] = ""
            st.session_state.login = False
            st.rerun()
    st.sidebar.markdown("---")  # linha separadora


login()  # Garante que o usuário esteja logado

# ========== INICIALIZA A PÁGINA SE NECESSÁRIO ==========
if "pagina" not in st.session_state:
    st.session_state.pagina = "Sincronização"

# ========== MENU UNIFICADO ==========
menu_principal = ["Sincronização", "Confirmar Produção", "Aprovação Diretoria", "Pré Roterização", "Rotas Confirmadas"]


menu_avancado = ["Alterar Senha"]
if st.session_state.get("is_admin", False):
    menu_avancado.append("Gerenciar Usuários")

# Linha separadora visual (não clicável)
separador = "────────────────────────"

# Menu completo com separador visual
menu_total = menu_principal + [separador] + menu_avancado

# Garante que a opção atual esteja na lista (evita erros ao abrir Gerenciar direto)
if st.session_state.pagina not in menu_total:
    st.session_state.pagina = "Sincronização"

# Define índice atual com base na página ativa
index_atual = menu_total.index(st.session_state.pagina)

# Radio unificado
escolha = st.sidebar.radio("📁 Menu", menu_total, index=index_atual)

# Impede seleção do separador
if escolha == separador:
    pass  # Ignora, mantém a página atual
elif escolha != st.session_state.pagina:
    st.session_state.pagina = escolha

# ========== ROTEAMENTO ==========
if st.session_state.pagina == "Sincronização":
    pagina_sincronizacao()
elif st.session_state.pagina == "Confirmar Produção":
    pagina_confirmar_producao()
elif st.session_state.pagina == "Aprovação Diretoria":
    pagina_aprovacao_diretoria()
elif st.session_state.pagina == "Pré Roterização":
    pagina_pre_roterizacao()
elif st.session_state.pagina == "Rotas Confirmadas":
    pagina_rotas_confirmadas()
elif st.session_state.pagina == "Alterar Senha":
    pagina_trocar_senha()
elif st.session_state.pagina == "Gerenciar Usuários":
    pagina_gerenciar_usuarios()







