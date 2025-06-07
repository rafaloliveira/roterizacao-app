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
import streamlit as st
import pandas as pd
from http.cookies import SimpleCookie
import os
from dotenv import load_dotenv

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
        st.warning("Por favor, importe o arquivo fBaseroter para continuar.")
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



###########################################
# PÁGINA CONFIRMAR PRODUÇÃO
###########################################

def pagina_confirmar_producao():
    st.title("Confirmar Produção")

    def carregar_entregas_base():
        # Carregamento das tabelas principais
        base = pd.DataFrame(supabase.table("fBaseroter").select("*").execute().data)
        agendadas = pd.DataFrame(supabase.table("Clientes_Entrega_Agendada").select("*").execute().data)
        particularidades = pd.DataFrame(supabase.table("Particularidades").select("*").execute().data)

        base['CNPJ Destinatario'] = base['CNPJ Destinatario'].astype(str).str.strip()

        # Merge com tabela de agendamentos
        if not agendadas.empty and {'CNPJ', 'Status de Agenda'}.issubset(agendadas.columns):
            agendadas['CNPJ'] = agendadas['CNPJ'].astype(str).str.strip()
            base = base.merge(
                agendadas[['CNPJ', 'Status de Agenda']],
                how='left',
                left_on='CNPJ Destinatario',
                right_on='CNPJ'
            ).rename(columns={'Status de Agenda': 'Status'})

        # Merge com particularidades
        if not particularidades.empty and {'CNPJ', 'Particularidade'}.issubset(particularidades.columns):
            particularidades['CNPJ'] = particularidades['CNPJ'].astype(str).str.strip()
            base = base.merge(
                particularidades[['CNPJ', 'Particularidade']],
                how='left',
                left_on='CNPJ Destinatario',
                right_on='CNPJ'
            )

        if 'Codigo da Ultima Ocorrencia' not in base.columns:
            base['Codigo da Ultima Ocorrencia'] = None

        # Remover entregas já confirmadas
        confirmadas = pd.DataFrame(supabase.table("confirmadas_producao").select("Serie_Numero_CTRC").execute().data)
        if not confirmadas.empty:
            confirmadas["Serie_Numero_CTRC"] = confirmadas["Serie_Numero_CTRC"].astype(str).str.strip()
            base = base[~base["Serie/Numero CTRC"].astype(str).isin(confirmadas["Serie_Numero_CTRC"])]

        # Filtrar entregas obrigatórias
        hoje = pd.Timestamp.today().normalize()
        d_mais_1 = hoje + pd.Timedelta(days=1)

        base['Previsao de Entrega'] = pd.to_datetime(base['Previsao de Entrega'], errors='coerce')

        entregas_obrigatorias = base[
            (base['Previsao de Entrega'] < d_mais_1) |
            (base['Valor do Frete'] <= 300) |
            ((base['Status'] == "Agendar") & (base['Entrega Programada'].isnull() | base['Entrega Programada'].eq('')))
        ]["Serie/Numero CTRC"].astype(str).tolist()

        base = base[~base["Serie/Numero CTRC"].astype(str).isin(entregas_obrigatorias)]

        # Adiciona índice para controle
        base["Indice"] = base.index

        # Normalização de strings
        base['Cidade de Entrega'] = base['Cidade de Entrega'].astype(str).str.strip().str.upper()
        base['Bairro do Destinatario'] = base['Bairro do Destinatario'].astype(str).str.strip().str.upper()

        # Carregar e aplicar rotas
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
            else:
                return rotas_dict.get(row.get('Cidade de Entrega'), '')

        base['Rota'] = base.apply(definir_rota, axis=1)

        return base

    # Carrega a base e inicia o fluxo de exibição
    df = carregar_entregas_base()
    df["Cliente Pagador"] = df["Cliente Pagador"].astype(str).str.strip().fillna("(Vazio)")

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
            <span style="color: white; font-weight: bold; font-size: 18px;">Total de Rotas:</span>
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
        "Serie/Numero CTRC", "Cliente Pagador", "Chave CT-e", "Cliente Destinatario",
        "Cidade de Entrega", "Bairro do Destinatario", "Previsao de Entrega",
        "Numero da Nota Fiscal", "Status", "Entrega Programada",
        "Particularidade", "Codigo da Ultima Ocorrencia",
        "Peso Real em Kg", "Peso Calculado em Kg", "Cubagem em m³",
        "Quantidade de Volumes", "Valor do Frete", "Rota"
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

        gb = GridOptionsBuilder.from_dataframe(df_formatado)
        gb.configure_default_column(resizable=True, minWidth=150)
        gb.configure_selection('multiple', use_checkbox=True)
        gb.configure_pagination(enabled=True, paginationAutoPageSize=False)
        gb.configure_grid_options(paginationPageSize=500)

        grid = AgGrid(
            df_formatado,
            gridOptions=gb.build(),
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            height=500,
            allow_unsafe_jscode=True,
            key=f"grid_{cliente}"
        )

        selecionadas = pd.DataFrame(grid.get("selected_rows", []))

        if not selecionadas.empty:
            st.success(f"{len(selecionadas)} entregas selecionadas para {cliente}.")
            if st.button(f"✅ Confirmar entregas de {cliente}", key=f"botao_{cliente}"):
                try:
                    chaves = selecionadas["Serie/Numero CTRC"].astype(str).str.strip().tolist()
                    df_confirmar = df_cliente[df_cliente["Serie/Numero CTRC"].isin(chaves)].copy()
                    df_confirmar.rename(columns={"Serie/Numero CTRC": "Serie_Numero_CTRC"}, inplace=True)

                    colunas_validas = [col for col in colunas_exibir if col != "Serie/Numero CTRC"]
                    df_confirmar = df_confirmar[["Serie_Numero_CTRC"] + colunas_validas]
                    df_confirmar = df_confirmar.replace([np.nan, np.inf, -np.inf], None)

                    # Converter colunas datetime para string no formato ISO
                    for col in df_confirmar.select_dtypes(include=['datetime64[ns]']).columns:
                        df_confirmar[col] = df_confirmar[col].dt.strftime('%Y-%m-%d %H:%M:%S')


                    supabase.table("confirmadas_producao").insert(df_confirmar.to_dict(orient="records")).execute()

                    st.success("Entregas confirmadas com sucesso!")
                    time.sleep(1.5)
                    st.rerun()

                except Exception as e:
                    st.error(f"Erro ao confirmar entregas: {e}")


###########################################
# PÁGINA PRÉ ROTERIZAÇÃO
###########################################

# Aqui você pode adicionar os blocos das outras páginas (Pré Roterização, Rotas Confirmadas
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

            base['Indice'] = base.index

            confirmadas = pd.DataFrame(supabase.table("confirmadas_producao").select("*").execute().data)
            if not confirmadas.empty:
                confirmadas['Serie/Numero CTRC'] = confirmadas['Serie_Numero_CTRC'].astype(str).str.strip()

            hoje = pd.Timestamp.today().normalize()
            d_mais_1 = hoje + pd.Timedelta(days=1)

            obrigatorias = base[
                (pd.to_datetime(base['Previsao de Entrega'], errors='coerce') < d_mais_1)
                |
                (base['Valor do Frete'] <= 300)
                |
                ((base['Status'] == 'Agendar') & (base['Entrega Programada'].isnull() | base['Entrega Programada'].eq('')))
            ].copy()

            if not confirmadas.empty:
                obrigatorias = obrigatorias[~obrigatorias['Serie/Numero CTRC'].isin(confirmadas['Serie/Numero CTRC'])]

            df_final = pd.concat([confirmadas, obrigatorias], ignore_index=True)
            df_final['Indice'] = df_final.index

            return df_final

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

        qtd_rotas = df["Rota"].nunique()
        qtd_entregas = len(df)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                f"""
                <div style='background-color:#2f2f2f; padding:8px; border-radius:8px'>
                    <span style='color:white; font-weight:bold; font-size:18px;'>Total de Rotas: </span>
                    <span style='color:white; font-size:24px;'>{qtd_rotas}</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col2:
            st.markdown(
                f"""
                <div style='background-color:#2f2f2f; padding:8px; border-radius:8px'>
                    <span style='color:white; font-weight:bold; font-size:18px;'>Total de Entregas: </span>
                    <span style='color:white; font-size:24px;'>{qtd_entregas}</span>
                </div>
                """,
                unsafe_allow_html=True
            )

        if rota_selecionada != "Todas":
            df = df[df["Rota"] == rota_selecionada]

        colunas_exibidas = [
            'Serie/Numero CTRC', 'Cliente Pagador', 'Chave CT-e', 'Cliente Destinatario',
            'Cidade de Entrega', 'Bairro do Destinatario', 'Previsao de Entrega',
            'Numero da Nota Fiscal', 'Status', 'Entrega Programada', 'Particularidade',
            'Codigo da Ultima Ocorrencia', 'Peso Real em Kg', 'Peso Calculado em Kg',
            'Cubagem em m³', 'Quantidade de Volumes', 'Valor do Frete', 'Rota'
        ]

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

        

        for rota in sorted(df['Rota'].dropna().unique()):

            st.markdown(f"""
                <div style='
                    font-size: 22px;
                    font-weight: bold;
                    color: #f0f0f0;
                    margin-top: 30px;
                    background-color: #2c2c2c;
                    padding: 10px 15px;
                    border-radius: 8px;
                '>
                         Rota: {rota}
                </div>
            """, unsafe_allow_html=True)

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

            df_formatado = df_rota.copy()
            df_formatado = df_formatado[[col for col in colunas_exibidas if col in df_formatado.columns]]

            for col in ['Peso Real em Kg', 'Peso Calculado em Kg', 'Cubagem em m³', 'Quantidade de Volumes', 'Valor do Frete']:
                if col in df_formatado.columns:
                    df_formatado[col] = df_formatado[col].apply(formatar_brasileiro)

            gb = GridOptionsBuilder.from_dataframe(df_formatado)
            gb.configure_default_column(resizable=True, minWidth=150)
            gb.configure_selection('multiple', use_checkbox=True)
            gb.configure_pagination(enabled=True, paginationAutoPageSize=False)
            gb.configure_grid_options(paginationPageSize=500)
            grid_options = gb.build()

            grid_response = AgGrid(
                df_formatado,
                gridOptions=grid_options,
                update_mode=GridUpdateMode.SELECTION_CHANGED,
                fit_columns_on_grid_load=False,
                height=400,
                allow_unsafe_jscode=True,
                key=f"grid_{rota}"
            )

            rows = grid_response.get("selected_rows")
            selecionadas = pd.DataFrame(rows) if rows is not None and len(rows) > 0 else pd.DataFrame()

            if not selecionadas.empty and "Serie/Numero CTRC" in selecionadas.columns:
    # Obtemos as chaves das entregas selecionadas
                chaves = selecionadas["Serie/Numero CTRC"].dropna().astype(str).str.strip().tolist()
                df_selecionadas = df_rota[df_rota["Serie/Numero CTRC"].isin(chaves)].copy()

                # Prepara o DataFrame para inserção no Supabase
                df_selecionadas = df_selecionadas.copy()
                if "Serie/Numero CTRC" in df_selecionadas.columns:
                    df_selecionadas["Serie_Numero_CTRC"] = df_selecionadas["Serie/Numero CTRC"].astype(str).str.strip()
                    df_selecionadas.drop(columns=["Serie/Numero CTRC"], inplace=True, errors="ignore")

                df_selecionadas["Rota"] = rota
                df_selecionadas.drop(columns=["Indice"], inplace=True, errors="ignore")

                colunas_supabase = colunas_exibidas.copy()
                colunas_supabase[0] = "Serie_Numero_CTRC"
                df_selecionadas = df_selecionadas[[col for col in colunas_supabase if col in df_selecionadas.columns]]
                df_selecionadas = df_selecionadas.replace([np.nan, np.inf, -np.inf], None)

                st.success(f"🔒 {len(df_selecionadas)} entregas selecionadas na rota **{rota}**.")

                # Garante chaves únicas para evitar conflito de Streamlit
                chave_hash = "_" + str(hash("-".join(chaves)))[:6]

                col_conf, col_ret = st.columns(2)

                with col_conf:
                    if st.button(f"✅ Confirmar Rota: {rota}", key=f"confirmar_{rota}{chave_hash}"):
                        try:
                            supabase.table("rotas_confirmadas").insert(df_selecionadas.to_dict(orient="records")).execute()
                            st.success(f"✅ {len(df_selecionadas)} entregas confirmadas com sucesso na rota **{rota}**!")
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao confirmar entregas: {e}")

                with col_ret:
                    if st.button(f"❌ Retirar da Pré Rota: {rota}", key=f"retirar_{rota}{chave_hash}"):
                        try:
                            if "Serie_Numero_CTRC" in df_selecionadas.columns:
                                coluna_serie = df_selecionadas["Serie_Numero_CTRC"]
                                if isinstance(coluna_serie, pd.Series):
                                    chaves_ctrc = coluna_serie.dropna().astype(str).tolist()
                                else:
                                    raise ValueError("A coluna 'Serie_Numero_CTRC' não é uma Series válida.")

                                for ctrc in chaves_ctrc:
                                    supabase.table("rotas_confirmadas").delete().eq("Serie_Numero_CTRC", ctrc).execute()

                                registros_confirmar = [{"Serie_Numero_CTRC": ctrc} for ctrc in chaves_ctrc]
                                supabase.table("confirmadas_producao").insert(registros_confirmar).execute()

                                st.success("🔄 Entregas retornadas para a etapa de produção com sucesso.")
                                time.sleep(1.5)
                                st.rerun()
                            else:
                                st.error("❌ Coluna 'Serie_Numero_CTRC' não encontrada na seleção.")
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
menu_principal = ["Sincronização", "Confirmar Produção", "Pré Roterização", "Rotas Confirmadas"]
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
elif st.session_state.pagina == "Pré Roterização":
    pagina_pre_roterizacao()
elif st.session_state.pagina == "Rotas Confirmadas":
    pagina_rotas_confirmadas()
elif st.session_state.pagina == "Alterar Senha":
    pagina_trocar_senha()
elif st.session_state.pagina == "Gerenciar Usuários":
    pagina_gerenciar_usuarios()










##############################
# Página de Pré Roterização
##############################
def pagina_pre_roterizacao():
    st.title("🚚 Pré Roterização")

    # Filtro por Rota
    rotas = supabase.table("pre_roterizacao").select("Rota").execute().data
    rotas_unicas = sorted(list(set([r["Rota"] for r in rotas if r["Rota"] is not None])))
    filtro_rota = st.selectbox("Filtrar por Rota", ["Todas"] + rotas_unicas)

    # Carregar dados
    if filtro_rota == "Todas":
        dados_pre_roterizacao = supabase.table("pre_roterizacao").select("*").execute().data
    else:
        dados_pre_roterizacao = supabase.table("pre_roterizacao").select("*").eq("Rota", filtro_rota).execute().data

    df_pre_roterizacao = pd.DataFrame(dados_pre_roterizacao)

    if df_pre_roterizacao.empty:
        st.info("Nenhuma entrega encontrada para pré-roterização.")
        return

    # Markdowns de resumo
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"## Total de Rotas: {len(rotas_unicas)}")
    with col2:
        st.markdown(f"## Total de Entregas: {len(df_pre_roterizacao)}")

    # Resumo acima do Gridd
    total_entregas = len(df_pre_roterizacao)
    peso_calculado_total = df_pre_roterizacao["Peso Calculado em Kg"].sum()
    peso_real_total = df_pre_roterizacao["Peso Real em Kg"].sum()
    cubagem_total = df_pre_roterizacao["Cubagem em m³"].sum()
    volumes_total = df_pre_roterizacao["Quantidade de Volumes"].sum()
    valor_frete_total = df_pre_roterizacao["Valor do Frete"].sum()

    st.markdown(f"""
    ### Resumo Geral
    - **Total de Entregas:** {total_entregas}
    - **Peso Calculado Total:** {peso_calculado_total:.2f} Kg
    - **Peso Real Total:** {peso_real_total:.2f} Kg
    - **Cubagem Total:** {cubagem_total:.2f} m³
    - **Quantidade de Volumes Total:** {volumes_total}
    - **Valor do Frete Total:** R$ {valor_frete_total:.2f}
    """)

    # Visão Geral das Entregas por Rota
    st.subheader("Visão Geral das Entregas por Rota")
    visao_geral_rota = df_pre_roterizacao.groupby("Rota").agg(
        peso_total_kg=("Peso Real em Kg", "sum"),
        peso_calculado_kg=("Peso Calculado em Kg", "sum"),
        cubagem_m3=("Cubagem em m³", "sum"),
        quantidade_volumes=("Quantidade de Volumes", "sum"),
        valor_frete=("Valor do Frete", "sum"),
        quantidade_entregas=("id", "count")
    ).reset_index()
    st.dataframe(visao_geral_rota)

    # Aplicação dos critérios mandatórios
    data_atual = datetime.now().date()
    df_pre_roterizacao["Previsao de Entrega"] = pd.to_datetime(df_pre_roterizacao["Previsao de Entrega"], errors='coerce').dt.date
    df_pre_roterizacao["Entrega Programada"] = pd.to_datetime(df_pre_roterizacao["Entrega Programada"], errors='coerce').dt.date

    # Critério Data de embarque (D+1)
    df_pre_roterizacao["Flag_Data_Embarque"] = df_pre_roterizacao["Previsao de Entrega"].apply(
        lambda x: "🔴" if pd.notna(x) and x < (data_atual + timedelta(days=1)) else ""
    )

    # Critério valor: Frete a partir de R$ 300
    df_pre_roterizacao["Flag_Valor_Frete"] = df_pre_roterizacao["Valor do Frete"].apply(
        lambda x: "🔴" if pd.notna(x) and x >= 300 else ""
    )

    # Critério Status AGENDAR com Entrega Programada em branco ou nula
    df_pre_roterizacao["Flag_Agendar"] = df_pre_roterizacao.apply(
        lambda row: "🔴" if row["Status"] == "AGENDAR" and (pd.isna(row["Entrega Programada"]) or row["Entrega Programada"] == "") else "",
        axis=1
    )

    # Colunas a serem exibidas no grid
    colunas_grid = [
        "id", "Serie_Numero_CTRC", "Cliente Pagador", "Chave CT-e", "Cliente Destinatario",
        "Cidade de Entrega", "Bairro do Destinatario", "Previsao de Entrega", "Numero da Nota Fiscal",
        "Status", "Entrega Programada", "Particularidade", "Codigo da Ultima Ocorrencia",
        "Peso Real em Kg", "Peso Calculado em Kg", "Cubagem em m³", "Quantidade de Volumes",
        "Valor do Frete", "Rota", "Flag_Data_Embarque", "Flag_Valor_Frete", "Flag_Agendar"
    ]

    df_display = df_pre_roterizacao[colunas_grid].copy()

    # Configuração do AgGrid
    gb = GridOptionsBuilder.from_dataframe(df_display)
    gb.configure_selection("multiple", use_checkbox=True, groupSelectsChildren=True)
    gb.configure_grid_options(domLayout='normal')
    gridOptions = gb.build()

    st.subheader("Entregas para Pré Roterização")
    grid_response = AgGrid(
        df_display,
        gridOptions=gridOptions,
        data_return_mode='AS_INPUT',
        update_mode='MODEL_CHANGED',
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=True,  # Permite JS para checkboxes
        enable_enterprise_modules=True,
        height=350,
        width='100%',
        reload_data=True
    )

    selected_rows = grid_response['selected_rows']

    if selected_rows:
        st.write(f"Entregas selecionadas: {len(selected_rows)}")
        if st.button("Confirmar Entregas Selecionadas"):
            for row in selected_rows:
                try:
                    # Inserir na tabela rotas_confirmadas
                    supabase.table("rotas_confirmadas").insert(row).execute()
                    # Remover da tabela pre_roterizacao
                    supabase.table("pre_roterizacao").delete().eq("id", row["id"]).execute()
                except Exception as e:
                    st.error(f"Erro ao mover entrega {row['id']}: {e}")
            st.success("Entregas movidas para Rotas Confirmadas com sucesso!")
            st.rerun()







##############################
# Página de Pré Roterização
##############################
def pagina_pre_roterizacao():
    st.title("🚚 Pré Roterização")

    # Filtro por Rota
    rotas_disponiveis = ['Rota A', 'Rota B', 'Rota C', 'Todas'] # Exemplo, buscar do banco
    selected_rota = st.selectbox("Filtrar por Rota", rotas_disponiveis)

    # Mock de dados para demonstração
    data = [
        {'id': 1, 'Serie_Numero_CTRC': 'CTRC001', 'Cliente Pagador': 'Cliente X', 'Chave CT-e': 'CHAVE001', 'Cliente Destinatario': 'Destino 1', 'Cidade de Entrega': 'Cidade A', 'Bairro do Destinatario': 'Bairro A', 'Previsao de Entrega': '2025-06-06', 'Numero da Nota Fiscal': 'NF001', 'Status': 'AGENDAR', 'Entrega Programada': '2025-06-07', 'Particularidade': '', 'Codigo da Ultima Ocorrencia': 'OC001', 'Peso Real em Kg': 100, 'Peso Calculado em Kg': 120, 'Cubagem em m³': 0.5, 'Quantidade de Volumes': 2, 'Valor do Frete': 500, 'Rota': 'Rota A'},
        {'id': 2, 'Serie_Numero_CTRC': 'CTRC002', 'Cliente Pagador': 'Cliente Y', 'Chave CT-e': 'CHAVE002', 'Cliente Destinatario': 'Destino 2', 'Cidade de Entrega': 'Cidade B', 'Bairro do Destinatario': 'Bairro B', 'Previsao de Entrega': '2025-06-05', 'Numero da Nota Fiscal': 'NF002', 'Status': 'ENTREGUE', 'Entrega Programada': '2025-06-05', 'Particularidade': '', 'Codigo da Ultima Ocorrencia': 'OC002', 'Peso Real em Kg': 150, 'Peso Calculado em Kg': 180, 'Cubagem em m³': 0.7, 'Quantidade de Volumes': 3, 'Valor do Frete': 250, 'Rota': 'Rota B'},
        {'id': 3, 'Serie_Numero_CTRC': 'CTRC003', 'Cliente Pagador': 'Cliente X', 'Chave CT-e': 'CHAVE003', 'Cliente Destinatario': 'Destino 3', 'Cidade de Entrega': 'Cidade C', 'Bairro do Destinatario': 'Bairro C', 'Previsao de Entrega': '2025-06-08', 'Numero da Nota Fiscal': 'NF003', 'Status': 'AGENDAR', 'Entrega Programada': None, 'Particularidade': '', 'Codigo da Ultima Ocorrencia': 'OC003', 'Peso Real em Kg': 80, 'Peso Calculado em Kg': 90, 'Cubagem em m³': 0.3, 'Quantidade de Volumes': 1, 'Valor do Frete': 350, 'Rota': 'Rota A'},
    ]
    df = pd.DataFrame(data)

    # Aplicar filtro de rota
    if selected_rota != 'Todas':
        df = df[df['Rota'] == selected_rota]

    # Métricas de resumo
    total_entregas = len(df)
    peso_calculado_total = df['Peso Calculado em Kg'].sum()
    peso_real_total = df['Peso Real em Kg'].sum()
    cubagem_total = df['Cubagem em m³'].sum()
    volumes_total = df['Quantidade de Volumes'].sum()
    valor_frete_total = df['Valor do Frete'].sum()

    st.subheader("Resumo Geral")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Total de Entregas", total_entregas)
    col2.metric("Peso Calculado (Kg)", f"{peso_calculado_total:.2f}")
    col3.metric("Peso Real (Kg)", f"{peso_real_total:.2f}")
    col4.metric("Cubagem (m³)", f"{cubagem_total:.2f}")
    col5.metric("Volumes", volumes_total)
    col6.metric("Valor do Frete (R$)", f"{valor_frete_total:.2f}")

    st.subheader("Visão Geral das Entregas por Rota")
    # AgGrid para exibir os dados
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_selection('multiple', use_checkbox=True)
    gb.configure_column("Entrega Programada", type=["customDateTimeFormat"], custom_format_string='yyyy-MM-dd')
    gridOptions = gb.build()

    grid_response = AgGrid(
        df,
        gridOptions=gridOptions,
        data_return_mode='AS_INPUT',
        update_mode='MODEL_CHANGED',
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=True,  # Permite o uso de JavaScript personalizado
        enable_enterprise_modules=True,
        height=350,
        width='100%',
        reload_data=True
    )

    selected_rows = grid_response['selected_rows']

    if selected_rows:
        st.write("Entregas selecionadas para confirmação:")
        st.dataframe(pd.DataFrame(selected_rows))
        if st.button("Confirmar Entregas Selecionadas"):
            st.success("Entregas confirmadas e movidas para Rotas Confirmadas (funcionalidade a ser implementada).")
            # Lógica para mover para a tabela rotas_confirmadas


# ========== MAIN ========== #
if "login" not in st.session_state:
    st.session_state.login = False

if "pagina" not in st.session_state:
    st.session_state.pagina = "Login"

if st.session_state.login:
    st.sidebar.title(f"Bem-vindo, {st.session_state.username}!")
    if st.session_state.is_admin:
        st.sidebar.radio(
            "Navegação",
            ["Sincronização", "Pré Roterização", "Aprovação Diretoria", "Rotas Confirmadas", "Cargas Geradas", "Aprovação Custos", "Cargas Aprovadas", "Gerenciar Usuários", "Alterar Senha"],
            key="menu_admin",
            on_change=lambda: st.session_state.update(pagina=st.session_state.menu_admin)
        )
    else:
        st.sidebar.radio(
            "Navegação",
            ["Sincronização", "Pré Roterização", "Aprovação Diretoria", "Rotas Confirmadas", "Cargas Geradas", "Aprovação Custos", "Cargas Aprovadas", "Alterar Senha"],
            key="menu_user",
            on_change=lambda: st.session_state.update(pagina=st.session_state.menu_user)
        )

    if st.sidebar.button("Sair"):
        cookies["login"] = "False"
        cookies["username"] = ""
        cookies["is_admin"] = "False"
        cookies["expiry_time"] = ""
        st.session_state.login = False
        st.session_state.pagina = "Login"
        st.rerun()

    if st.session_state.pagina == "Sincronização":
        pagina_sincronizacao()
    elif st.session_state.pagina == "Gerenciar Usuários":
        pagina_gerenciar_usuarios()
    elif st.session_state.pagina == "Alterar Senha":
        pagina_trocar_senha()
    elif st.session_state.pagina == "Pré Roterização":
        pagina_pre_roterizacao()
    elif st.session_state.pagina == "Aprovação Diretoria":
        pagina_aprovacao_diretoria()
    elif st.session_state.pagina == "Rotas Confirmadas":
        pagina_rotas_confirmadas()
    elif st.session_state.pagina == "Cargas Geradas":
        pagina_cargas_geradas()
    elif st.session_state.pagina == "Aprovação Custos":
        pagina_aprovacao_custos()
    elif st.session_state.pagina == "Cargas Aprovadas":
        pagina_cargas_aprovadas()
else:
    login()





##############################
# Página de Aprovação Diretoria
##############################
def pagina_aprovacao_diretoria():
    if not st.session_state.get("is_admin", False): # Assumindo que aprovadores são admins por enquanto
        st.warning("Acesso negado. Somente usuários com classe 'aprovador' podem acessar esta página.")
        return

    st.title("✅ Aprovação Diretoria")

    # Mock de dados para demonstração
    data = [
        {'id': 101, 'Serie_Numero_CTRC': 'CTRC004', 'Cliente Pagador': 'Cliente A', 'Chave CT-e': 'CHAVE004', 'Cliente Destinatario': 'Destino 4', 'Cidade de Entrega': 'Cidade D', 'Bairro do Destinatario': 'Bairro D', 'Previsao de Entrega': '2025-06-09', 'Numero da Nota Fiscal': 'NF004', 'Status': 'PENDENTE', 'Entrega Programada': '2025-06-10', 'Particularidade': '', 'Codigo da Ultima Ocorrencia': 'OC004', 'Peso Real em Kg': 200, 'Peso Calculado em Kg': 220, 'Cubagem em m³': 1.0, 'Quantidade de Volumes': 5, 'Valor do Frete': 800, 'Rota': 'Rota X'},
        {'id': 102, 'Serie_Numero_CTRC': 'CTRC005', 'Cliente Pagador': 'Cliente B', 'Chave CT-e': 'CHAVE005', 'Cliente Destinatario': 'Destino 5', 'Cidade de Entrega': 'Cidade E', 'Bairro do Destinatario': 'Bairro E', 'Previsao de Entrega': '2025-06-10', 'Numero da Nota Fiscal': 'NF005', 'Status': 'PENDENTE', 'Entrega Programada': '2025-06-11', 'Particularidade': '', 'Codigo da Ultima Ocorrencia': 'OC005', 'Peso Real em Kg': 120, 'Peso Calculado em Kg': 130, 'Cubagem em m³': 0.6, 'Quantidade de Volumes': 2, 'Valor do Frete': 450, 'Rota': 'Rota Y'},
        {'id': 103, 'Serie_Numero_CTRC': 'CTRC006', 'Cliente Pagador': 'Cliente A', 'Chave CT-e': 'CHAVE006', 'Cliente Destinatario': 'Destino 6', 'Cidade de Entrega': 'Cidade F', 'Bairro do Destinatario': 'Bairro F', 'Previsao de Entrega': '2025-06-11', 'Numero da Nota Fiscal': 'NF006', 'Status': 'PENDENTE', 'Entrega Programada': '2025-06-12', 'Particularidade': '', 'Codigo da Ultima Ocorrencia': 'OC006', 'Peso Real em Kg': 90, 'Peso Calculado em Kg': 100, 'Cubagem em m³': 0.4, 'Quantidade de Volumes': 1, 'Valor do Frete': 300, 'Rota': 'Rota X'},
    ]
    df = pd.DataFrame(data)

    # Filtro por Cliente Pagador
    clientes_disponiveis = ["Todos"] + sorted(df["Cliente Pagador"].unique().tolist())
    selected_cliente = st.selectbox("Filtrar por Cliente Pagador", clientes_disponiveis)

    if selected_cliente != "Todos":
        df = df[df["Cliente Pagador"] == selected_cliente]

    # Métricas de resumo
    total_clientes = df["Cliente Pagador"].nunique()
    total_entregas = len(df)
    peso_calculado_total = df["Peso Calculado em Kg"].sum()
    peso_real_total = df["Peso Real em Kg"].sum()
    cubagem_total = df["Cubagem em m³"].sum()
    volumes_total = df["Quantidade de Volumes"].sum()
    valor_frete_total = df["Valor do Frete"].sum()

    st.subheader("Resumo Geral")
    col1, col2 = st.columns(2)
    col1.metric("Total de Clientes", total_clientes)
    col2.metric("Total de Entregas", total_entregas)

    st.subheader("Visão Geral das Entregas por Cliente Pagador")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Peso Calculado (Kg)", f"{peso_calculado_total:.2f}")
    col2.metric("Peso Real (Kg)", f"{peso_real_total:.2f}")
    col3.metric("Cubagem (m³)", f"{cubagem_total:.2f}")
    col4.metric("Volumes", volumes_total)
    col5.metric("Valor do Frete (R$)", f"{valor_frete_total:.2f}")

    # AgGrid para exibir os dados
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_selection("multiple", use_checkbox=True)
    gb.configure_column("Entrega Programada", type=["customDateTimeFormat"], custom_format_string=\'yyyy-MM-dd\')
    gridOptions = gb.build()

    grid_response = AgGrid(
        df,
        gridOptions=gridOptions,
        data_return_mode=\'AS_INPUT\',
        update_mode=\'MODEL_CHANGED\',
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=True,
        enable_enterprise_modules=True,
        height=350,
        width=\'100%\',
        reload_data=True
    )

    selected_rows = grid_response["selected_rows"]

    if selected_rows:
        st.write("Entregas selecionadas para aprovação:")
        st.dataframe(pd.DataFrame(selected_rows))
        if st.button("Aprovar Entregas Selecionadas"):
            st.success("Entregas aprovadas e movidas para Pré Roterização (funcionalidade a ser implementada).")
            # Lógica para mover para a tabela pre_roterizacao





##############################
# Página de Rotas Confirmadas
##############################
def pagina_rotas_confirmadas():
    st.title("🚚 Rotas Confirmadas")

    # Mock de dados para demonstração
    data = [
        {'id': 201, 'Serie_Numero_CTRC': 'CTRC007', 'Cliente Pagador': 'Cliente C', 'Chave CT-e': 'CHAVE007', 'Cliente Destinatario': 'Destino 7', 'Cidade de Entrega': 'Cidade G', 'Bairro do Destinatario': 'Bairro G', 'Previsao de Entrega': '2025-06-12', 'Numero da Nota Fiscal': 'NF007', 'Status': 'CONFIRMADO', 'Entrega Programada': '2025-06-13', 'Particularidade': '', 'Codigo da Ultima Ocorrencia': 'OC007', 'Peso Real em Kg': 300, 'Peso Calculado em Kg': 320, 'Cubagem em m³': 1.5, 'Quantidade de Volumes': 10, 'Valor do Frete': 1200, 'Rota': 'Rota A'},
        {'id': 202, 'Serie_Numero_CTRC': 'CTRC008', 'Cliente Pagador': 'Cliente D', 'Chave CT-e': 'CHAVE008', 'Cliente Destinatario': 'Destino 8', 'Cidade de Entrega': 'Cidade H', 'Bairro do Destinatario': 'Bairro H', 'Previsao de Entrega': '2025-06-13', 'Numero da Nota Fiscal': 'NF008', 'Status': 'CONFIRMADO', 'Entrega Programada': '2025-06-14', 'Particularidade': '', 'Codigo da Ultima Ocorrencia': 'OC008', 'Peso Real em Kg': 150, 'Peso Calculado em Kg': 160, 'Cubagem em m³': 0.8, 'Quantidade de Volumes': 3, 'Valor do Frete': 600, 'Rota': 'Rota B'},
        {'id': 203, 'Serie_Numero_CTRC': 'CTRC009', 'Cliente Pagador': 'Cliente C', 'Chave CT-e': 'CHAVE009', 'Cliente Destinatario': 'Destino 9', 'Cidade de Entrega': 'Cidade I', 'Bairro do Destinatario': 'Bairro I', 'Previsao de Entrega': '2025-06-14', 'Numero da Nota Fiscal': 'NF009', 'Status': 'CONFIRMADO', 'Entrega Programada': '2025-06-15', 'Particularidade': '', 'Codigo da Ultima Ocorrencia': 'OC009', 'Peso Real em Kg': 100, 'Peso Calculado em Kg': 110, 'Cubagem em m³': 0.5, 'Quantidade de Volumes': 2, 'Valor do Frete': 400, 'Rota': 'Rota A'},
    ]
    df = pd.DataFrame(data)

    # Filtro por Rota
    rotas_disponiveis = ["Todas"] + sorted(df["Rota"].unique().tolist())
    selected_rota = st.selectbox("Filtrar por Rota", rotas_disponiveis)

    if selected_rota != "Todas":
        df = df[df["Rota"] == selected_rota]

    # Métricas de resumo
    total_rotas = df["Rota"].nunique()
    total_entregas = len(df)
    peso_calculado_total = df["Peso Calculado em Kg"].sum()
    peso_real_total = df["Peso Real em Kg"].sum()
    cubagem_total = df["Cubagem em m³"].sum()
    volumes_total = df["Quantidade de Volumes"].sum()
    valor_frete_total = df["Valor do Frete"].sum()

    st.subheader("Resumo Geral")
    col1, col2 = st.columns(2)
    col1.metric("Total de Rotas", total_rotas)
    col2.metric("Total de Entregas", total_entregas)

    st.subheader("Visão Geral das Entregas por Rota")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Peso Calculado (Kg)", f"{peso_calculado_total:.2f}")
    col2.metric("Peso Real (Kg)", f"{peso_real_total:.2f}")
    col3.metric("Cubagem (m³)", f"{cubagem_total:.2f}")
    col4.metric("Volumes", volumes_total)
    col5.metric("Valor do Frete (R$)", f"{valor_frete_total:.2f}")
    col6.metric("Quantidade de Entregas", total_entregas)

    # AgGrid para exibir os dados
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_selection("multiple", use_checkbox=True)
    gb.configure_column("Entrega Programada", type=["customDateTimeFormat"], custom_format_string=\'yyyy-MM-dd\')
    gridOptions = gb.build()

    grid_response = AgGrid(
        df,
        gridOptions=gridOptions,
        data_return_mode=\'AS_INPUT\',
        update_mode=\'MODEL_CHANGED\',
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=True,
        enable_enterprise_modules=True,
        height=350,
        width=\'100%\',
        reload_data=True
    )

    selected_rows = grid_response["selected_rows"]

    if selected_rows:
        st.write("Entregas selecionadas para gerar carga:")
        st.dataframe(pd.DataFrame(selected_rows))
        if st.button("Gerar Carga com Entregas Selecionadas"):
            st.success("Carga gerada e movida para Cargas Geradas (funcionalidade a ser implementada).")
            # Lógica para mover para a tabela cargas_geradas





##############################
# Página de Cargas Geradas
##############################
def pagina_cargas_geradas():
    st.title("📦 Cargas Geradas")

    # Mock de dados para demonstração
    data = [
        {'id': 301, 'Serie_Numero_CTRC': 'CTRC010', 'Cliente Pagador': 'Cliente E', 'Chave CT-e': 'CHAVE010', 'Cliente Destinatario': 'Destino 10', 'Cidade de Entrega': 'Cidade J', 'Bairro do Destinatario': 'Bairro J', 'Previsao de Entrega': '2025-06-15', 'Numero da Nota Fiscal': 'NF010', 'Status': 'CARGA_GERADA', 'Entrega Programada': '2025-06-16', 'Particularidade': '', 'Codigo da Ultima Ocorrencia': 'OC010', 'Peso Real em Kg': 400, 'Peso Calculado em Kg': 420, 'Cubagem em m³': 2.0, 'Quantidade de Volumes': 15, 'Valor do Frete': 1500, 'Rota': 'Rota C', 'Sequencia_Carga': 'CARGA001', 'Valor_Contratacao': 1800, 'Micro_Regiao_por_data_embarque': 'Interior 1'},
        {'id': 302, 'Serie_Numero_CTRC': 'CTRC011', 'Cliente Pagador': 'Cliente F', 'Chave CT-e': 'CHAVE011', 'Cliente Destinatario': 'Destino 11', 'Cidade de Entrega': 'Cidade K', 'Bairro do Destinatario': 'Bairro K', 'Previsao de Entrega': '2025-06-16', 'Numero da Nota Fiscal': 'NF011', 'Status': 'CARGA_GERADA', 'Entrega Programada': '2025-06-17', 'Particularidade': '', 'Codigo da Ultima Ocorrencia': 'OC011', 'Peso Real em Kg': 250, 'Peso Calculado em Kg': 270, 'Cubagem em m³': 1.2, 'Quantidade de Volumes': 8, 'Valor do Frete': 900, 'Rota': 'Rota D', 'Sequencia_Carga': 'CARGA002', 'Valor_Contratacao': 1100, 'Micro_Regiao_por_data_embarque': 'POA CAPITAL'},
    ]
    df = pd.DataFrame(data)

    # Filtro por Sequência de Carga
    cargas_disponiveis = ["Todas"] + sorted(df["Sequencia_Carga"].unique().tolist())
    selected_carga = st.selectbox("Filtrar por Sequência de Carga", cargas_disponiveis)

    if selected_carga != "Todas":
        df = df[df["Sequencia_Carga"] == selected_carga]

    st.subheader("Informações da Carga")
    if not df.empty:
        st.write(f"**Sequência da Carga:** {df["Sequencia_Carga"].iloc[0]}")
        
        # Campo obrigatório para o usuário inserir o valor da contratação
        valor_contratacao_input = st.number_input("Valor da Contratação (R$)", value=float(df["Valor_Contratacao"].iloc[0]), format="%.2f")
        df["Valor_Contratacao"] = valor_contratacao_input

        # Cálculo do custo por região (mock)
        custo_maximo = {
            'Interior 1': 0.35,
            'Interior 2': 0.45,
            'POA CAPITAL': 0.30
        }
        df["Custo_Regiao"] = df.apply(lambda row: row["Valor do Frete"] * custo_maximo.get(row["Micro_Regiao_por_data_embarque"], 0), axis=1)
        st.metric("Custo por Região (R$)", f"{df["Custo_Regiao"].sum():.2f}")

        # Cálculo de Rentabilidade
        valor_total_frete_carga = df["Valor do Frete"].sum()
        rentabilidade = ((valor_contratacao_input - valor_total_frete_carga) / valor_contratacao_input) * 100 if valor_contratacao_input != 0 else 0
        st.metric("Rentabilidade da Carga (%)", f"{rentabilidade:.2f}%")

    # AgGrid para exibir os dados
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_selection("multiple", use_checkbox=True)
    gb.configure_column("Entrega Programada", type=["customDateTimeFormat"], custom_format_string=\'yyyy-MM-dd\
')
    gridOptions = gb.build()

    grid_response = AgGrid(
        df,
        gridOptions=gridOptions,
        data_return_mode=\'AS_INPUT\
',
        update_mode=\'MODEL_CHANGED\
',
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=True,
        enable_enterprise_modules=True,
        height=350,
        width=\'100%\
',
        reload_data=True
    )

    selected_rows = grid_response["selected_rows"]

    if selected_rows:
        st.write("Entregas selecionadas para aprovação de custo:")
        st.dataframe(pd.DataFrame(selected_rows))
        if st.button("Enviar Cargas para Aprovação de Custo"):
            st.success("Cargas enviadas para Aprovação de Custos (funcionalidade a ser implementada).")
            # Lógica para mover para a tabela aprovacao_custos





##############################
# Página de Aprovação Custos
##############################
def pagina_aprovacao_custos():
    st.title("💰 Aprovação Custos")

    # Mock de dados para demonstração
    data = [
        {'id': 401, 'Serie_Numero_CTRC': 'CTRC012', 'Cliente Pagador': 'Cliente G', 'Chave CT-e': 'CHAVE012', 'Cliente Destinatario': 'Destino 12', 'Cidade de Entrega': 'Cidade L', 'Bairro do Destinatario': 'Bairro L', 'Previsao de Entrega': '2025-06-17', 'Numero da Nota Fiscal': 'NF012', 'Status': 'AGUARDANDO_APROVACAO_CUSTO', 'Entrega Programada': '2025-06-18', 'Particularidade': '', 'Codigo da Ultima Ocorrencia': 'OC012', 'Peso Real em Kg': 500, 'Peso Calculado em Kg': 520, 'Cubagem em m³': 2.5, 'Quantidade de Volumes': 20, 'Valor do Frete': 2000, 'Rota': 'Rota E', 'Sequencia_Carga': 'CARGA001', 'Valor_Contratacao': 2200, 'Micro_Regiao_por_data_embarque': 'Interior 1'},
        {'id': 402, 'Serie_Numero_CTRC': 'CTRC013', 'Cliente Pagador': 'Cliente H', 'Chave CT-e': 'CHAVE013', 'Cliente Destinatario': 'Destino 13', 'Cidade de Entrega': 'Cidade M', 'Bairro do Destinatario': 'Bairro M', 'Previsao de Entrega': '2025-06-18', 'Numero da Nota Fiscal': 'NF013', 'Status': 'AGUARDANDO_APROVACAO_CUSTO', 'Entrega Programada': '2025-06-19', 'Particularidade': '', 'Codigo da Ultima Ocorrencia': 'OC013', 'Peso Real em Kg': 350, 'Peso Calculado em Kg': 370, 'Cubagem em m³': 1.8, 'Quantidade de Volumes': 12, 'Valor do Frete': 1300, 'Rota': 'Rota F', 'Sequencia_Carga': 'CARGA002', 'Valor_Contratacao': 1500, 'Micro_Regiao_por_data_embarque': 'Interior 2'},
    ]
    df = pd.DataFrame(data)

    # Filtro por Sequência de Carga
    cargas_disponiveis = ["Todas"] + sorted(df["Sequencia_Carga"].unique().tolist())
    selected_carga = st.selectbox("Filtrar por Sequência de Carga", cargas_disponiveis)

    if selected_carga != "Todas":
        df = df[df["Sequencia_Carga"] == selected_carga]

    # Métricas de resumo
    total_cargas = df["Sequencia_Carga"].nunique()
    total_entregas = len(df)

    st.subheader("Resumo Geral")
    col1, col2 = st.columns(2)
    col1.metric("Total de Cargas", total_cargas)
    col2.metric("Total de Entregas", total_entregas)

    st.subheader("Visão Geral das Entregas por Rota")
    # Agrupar por Rota para a visão geral
    df_grouped_by_rota = df.groupby("Rota").agg(
        peso_total_kg=("Peso Real em Kg", "sum"),
        peso_calculado_kg=("Peso Calculado em Kg", "sum"),
        cubagem_m3=("Cubagem em m³", "sum"),
        quantidade_volumes=("Quantidade de Volumes", "sum"),
        valor_frete=("Valor do Frete", "sum"),
        quantidade_entregas=("id", "count")
    ).reset_index()
    st.dataframe(df_grouped_by_rota)

    st.subheader("Resumo de Rentabilidade por Carga")
    df_rentabilidade = df.groupby("Sequencia_Carga").agg(
        valor_total_frete=("Valor do Frete", "sum"),
        valor_contratacao=("Valor_Contratacao", "first") # Assumindo que Valor_Contratacao é o mesmo para todas as entregas da carga
    ).reset_index()
    df_rentabilidade["Rentabilidade (%)"] = ((df_rentabilidade["valor_contratacao"] - df_rentabilidade["valor_total_frete"]) / df_rentabilidade["valor_contratacao"]) * 100
    st.dataframe(df_rentabilidade)

    # AgGrid para exibir os dados
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_selection("multiple", use_checkbox=True)
    gb.configure_column("Entrega Programada", type=["customDateTimeFormat"], custom_format_string=\'yyyy-MM-dd\')
    gridOptions = gb.build()

    grid_response = AgGrid(
        df,
        gridOptions=gridOptions,
        data_return_mode=\'AS_INPUT\',
        update_mode=\'MODEL_CHANGED\',
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=True,
        enable_enterprise_modules=True,
        height=350,
        width=\'100%\',
        reload_data=True
    )

    selected_rows = grid_response["selected_rows"]

    if selected_rows:
        st.write("Cargas selecionadas para aprovação:")
        st.dataframe(pd.DataFrame(selected_rows))
        if st.button("Aprovar Cargas Selecionadas"):
            st.success("Cargas aprovadas e movidas para Cargas Aprovadas (funcionalidade a ser implementada).")
            # Lógica para mover para a tabela cargas_aprovadas





##############################
# Página de Cargas Aprovadas
##############################
def pagina_cargas_aprovadas():
    st.title("✅ Cargas Aprovadas")

    # Mock de dados para demonstração
    data = [
        {'id': 501, 'Serie_Numero_CTRC': 'CTRC014', 'Cliente Pagador': 'Cliente I', 'Chave CT-e': 'CHAVE014', 'Cliente Destinatario': 'Destino 14', 'Cidade de Entrega': 'Cidade N', 'Bairro do Destinatario': 'Bairro N', 'Previsao de Entrega': '2025-06-19', 'Numero da Nota Fiscal': 'NF014', 'Status': 'APROVADO', 'Entrega Programada': '2025-06-20', 'Particularidade': '', 'Codigo da Ultima Ocorrencia': 'OC014', 'Peso Real em Kg': 600, 'Peso Calculado em Kg': 620, 'Cubagem em m³': 3.0, 'Quantidade de Volumes': 25, 'Valor do Frete': 2500, 'Rota': 'Rota G', 'Sequencia_Carga': 'CARGA001', 'Valor_Contratacao': 2700, 'Micro_Regiao_por_data_embarque': 'Interior 1'},
        {'id': 502, 'Serie_Numero_CTRC': 'CTRC015', 'Cliente Pagador': 'Cliente J', 'Chave CT-e': 'CHAVE015', 'Cliente Destinatario': 'Destino 15', 'Cidade de Entrega': 'Cidade O', 'Bairro do Destinatario': 'Bairro O', 'Previsao de Entrega': '2025-06-20', 'Numero da Nota Fiscal': 'NF015', 'Status': 'APROVADO', 'Entrega Programada': '2025-06-21', 'Particularidade': '', 'Codigo da Ultima Ocorrencia': 'OC015', 'Peso Real em Kg': 450, 'Peso Calculado em Kg': 470, 'Cubagem em m³': 2.2, 'Quantidade de Volumes': 18, 'Valor do Frete': 1800, 'Rota': 'Rota H', 'Sequencia_Carga': 'CARGA002', 'Valor_Contratacao': 2000, 'Micro_Regiao_por_data_embarque': 'POA CAPITAL'},
    ]
    df = pd.DataFrame(data)

    # Filtro por Sequência de Carga
    cargas_disponiveis = ["Todas"] + sorted(df["Sequencia_Carga"].unique().tolist())
    selected_carga = st.selectbox("Filtrar por Sequência de Carga", cargas_disponiveis)

    if selected_carga != "Todas":
        df = df[df["Sequencia_Carga"] == selected_carga]

    st.subheader("Cargas Aprovadas")
    if not df.empty:
        st.dataframe(df)

        st.subheader("Extrair Relatório")
        if st.button("Extrair Relatório de Entregas"):
            # Lógica para extrair relatório (ex: CSV, Excel)
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download Relatório CSV",
                data=csv,
                file_name="relatorio_cargas_aprovadas.csv",
                mime="text/csv",
            )
            st.success("Relatório gerado com sucesso!")

        st.subheader("Imprimir Cargas")
        if st.button("Imprimir Cargas Aprovadas"):
            st.info("Funcionalidade de impressão a ser implementada.")


