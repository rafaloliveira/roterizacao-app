#sincronização, Pré Roterização e Rotas Confirmadas funcionando

import streamlit as st
st.set_page_config(page_title="Roterização", layout="wide")
import pandas as pd
import numpy as np
import io
import re
import json
import time
import hashlib
import uuid
import bcrypt
import streamlit as st
import pandas as pd
import os
import uuid
import time
import numpy as np
import pandas as pd
import streamlit as st

from zoneinfo import ZoneInfo
from datetime import datetime, timedelta, timezone
from datetime import datetime, date
from http.cookies import SimpleCookie
from st_aggrid.shared import GridUpdateMode
from st_aggrid.shared import AgGridTheme
from dotenv import load_dotenv
from pandas import Timestamp
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from streamlit_cookies_manager import EncryptedCookieManager
from datetime import datetime
from supabase import create_client, Client
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from pathlib import Path
from st_aggrid.shared import JsCode




def aplicar_zoom_personalizado(percent=85):
    escala = percent / 100
    largura = 100 / escala  # Ex: para 85%, usamos 117% de largura

    st.markdown(
        f"""
        <style>
        .appview-container .main {{
            transform: scale({escala});
            transform-origin: top left;
            width: {largura}%;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )



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
        

        if dados.data:
            usuario = dados.data[0]
            hash_bruto = str(usuario["senha_hash"]).replace("\n", "").replace("\r", "").strip()

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
        return True # Se houver erro na data, considera expirado
    
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
    fit_columns_on_grid_load=False,
    height=470,  # ⬅️ AUMENTE AQUI
    use_container_width=True,
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
    classe_cookie = cookies.get("classe") # Pega a classe do cookie

    # Verifica se já está logado via cookie e se o cookie não expirou
    if login_cookie and username_cookie and not is_cookie_expired(expiry_time_cookie):
        st.session_state.login = True
        st.session_state.username = username_cookie
        st.session_state.is_admin = is_admin_cookie == "True"
        st.session_state.classe = classe_cookie # Define a classe no session_state a partir do cookie
        return # Sai da função, usuário já logado

    # Cria três colunas e usa a do meio para o formulário de login
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 🔐 Login")
        nome = st.text_input("Usuário").strip()
        senha = st.text_input("Senha", type="password").strip()

        # ... (dentro da função login) ...

        if st.button("Entrar"):
            usuario = autenticar_usuario(nome, senha)
            if usuario:
                # Armazena as informações no cookie
                cookies["login"] = "True"
                cookies["username"] = usuario["nome_usuario"]
                cookies["is_admin"] = str(usuario.get("is_admin", False))
                cookies["classe"] = usuario.get("classe", "colaborador") # <<< ADIÇÃO AQUI: Armazena a classe no cookie
                
                # Define o tempo de expiração do cookie (24 horas)
                expiry = datetime.now(timezone.utc) + timedelta(hours=24)
                cookies["expiry_time"] = expiry.strftime("%Y-%m-%d %H:%M:%S")

                # Armazena as informações no st.session_state
                st.session_state.login = True
                st.session_state.username = usuario["nome_usuario"]
                st.session_state.is_admin = usuario.get("is_admin", False)
                st.session_state.classe = usuario.get("classe", "colaborador") # <<< ADIÇÃO AQUI: Armazena a classe no session_state

                # Verifica se o usuário precisa alterar a senha (se houver essa flag no banco)
                if usuario.get("precisa_alterar_senha") is True:
                    st.warning("🔐 Você deve alterar sua senha antes de continuar.")
                    pagina_trocar_senha() # Chama a página de troca de senha
                    st.stop() # Interrompe a execução para forçar a troca de senha

                st.success("✅ Login bem-sucedido!")
                st.rerun() # Força um rerun para que a interface atualize e mostre as páginas principais
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
        # ATUALIZAR: Adicionar "classe" à exibição do dataframe
        st.dataframe(df[["nome_usuario", "is_admin", "classe"]]) # ATUALIZE ESTA LINHA

    st.subheader("➕ Criar novo usuário")
    novo_usuario = st.text_input("Novo nome de usuário")
    nova_senha = st.text_input("Senha", type="password")
    # ATUALIZAR: Adicionar selectbox para classe na criação
    nova_classe = st.selectbox("Classe", ["colaborador", "aprovador"], key="classe_nova_criar") # ATUALIZE ESTA LINHA
    novo_admin = st.checkbox("Tornar administrador")

    if st.button("Criar"):
        if novo_usuario and nova_senha:
            try:
                senha_hash = hash_senha(nova_senha)
                supabase.table("usuarios").insert({
                    "nome_usuario": novo_usuario,
                    "senha_hash": senha_hash,
                    "classe": nova_classe, # ATUALIZE ESTA LINHA
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
        # Recuperar informações do usuário selecionado para preencher os campos
        usuario_info = df[df["nome_usuario"] == usuario_alvo].iloc[0]

        nova_senha_user = st.text_input("Nova senha (deixe em branco se não for alterar)")
        # NOVO: Selectbox para atualizar a classe do usuário existente
        # Preenche o valor padrão com a classe atual do usuário selecionado
        nova_classe_user = st.selectbox(
            "Nova classe",
            ["colaborador", "aprovador"],
            index=["colaborador", "aprovador"].index(usuario_info["classe"]), # Preenche com a classe atual
            key=f"classe_edit_{usuario_alvo}" # Chave única para cada selectbox
        )
        novo_admin_status = st.checkbox("Administrador?", value=bool(usuario_info["is_admin"])) # ATUALIZE ESTA LINHA para usar usuario_info

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Atualizar", key=f"btn_atualizar_{usuario_alvo}"): # Chave única para o botão
                update = {
                    "classe": nova_classe_user, # ATUALIZE ESTA LINHA
                    "is_admin": novo_admin_status
                }
                if nova_senha_user:
                    update["senha_hash"] = hash_senha(nova_senha_user)
                try:
                    supabase.table("usuarios").update(update).eq("nome_usuario", usuario_alvo).execute()
                    st.success("Usuário atualizado.")
                    st.session_state.pagina = "Gerenciar Usuários"
                    # CRUCIAL: Recarregar a página para que as mudanças reflitam no DF e no Supabase.
                    # Isso também limpará o cache do Supabase para a tabela de usuários se você a tiver.
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao atualizar usuário: {e}")

        with col2:
            confirm_key = f"confirm_delete_{usuario_alvo}"
            confirm = st.checkbox(f"Confirmar exclusão do usuário '{usuario_alvo}'?", key=confirm_key)

            if confirm:
                if st.button("Deletar", key=f"btn_deletar_{usuario_alvo}"): # Chave única para o botão
                    try:
                        supabase.table("usuarios").delete().eq("nome_usuario", usuario_alvo).execute()
                        st.success(f"Usuário '{usuario_alvo}' deletado com sucesso.")
                        st.session_state.pagina = "Gerenciar Usuários"
                        # CRUCIAL: Recarregar a página após a deleção
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



# Fuso horário padrão do Brasil (São Paulo)
FUSO_BRASIL = ZoneInfo("America/Sao_Paulo")
def data_hora_brasil_iso():
    return datetime.now(FUSO_BRASIL).isoformat()
def data_hora_brasil_str():
    return datetime.now(FUSO_BRASIL).strftime("%Y-%m-%d %H:%M:%S")

def formatar_data_hora_br(data_iso):
    """
    Converte string ou datetime para 'dd-mm-yyyy HH:MM:SS' no fuso de São Paulo.
    """
    if isinstance(data_iso, str):
        try:
            dt = datetime.fromisoformat(data_iso)
        except Exception:
            return data_iso
    else:
        dt = data_iso

    # Se vier sem timezone, assume que é UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc).astimezone(FUSO_BRASIL)
    else:
        dt = dt.astimezone(FUSO_BRASIL)

    return dt.strftime("%d-%m-%Y %H:%M:%S")



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
            "Volume Cliente/Shipment", "Unnamed: 67","CEP de Entrega","CEP do Destinatario" 
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
                df[col] = pd.to_datetime(df[col], format='%d-%m-%Y', errors='coerce')
                df[col] = df[col].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) else None)


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
    gb.configure_grid_options(onGridReady=GRID_RESIZE_JS_CODE) # <<< ADICIONADO AQUI

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
        height=650,
        allow_unsafe_jscode=True,
        key=key
    )

    return grid_response

# NO ARQUIVO: 02-07-9.txt
# FUNÇÃO: def formatar_brasileiro(valor): (Esta função fica geralmente no final do arquivo)

def formatar_brasileiro(valor):
    """
    Formata um valor numérico para o padrão monetário/numérico brasileiro (milhares com '.' e decimal com ',').
    Garanti que ele sempre retorna o formato BR, mesmo que o locale do Python seja diferente.
    """
    try:
        # Se o valor for None ou NaN, retorne "0,00" ou ""
        if valor is None or (isinstance(valor, (float, np.float64)) and np.isnan(valor)):
            return "0,00"
        
        # Garante que o valor é numérico para formatação
        if not isinstance(valor, (int, float, np.float64)):
            valor = pd.to_numeric(valor, errors='coerce')
            if pd.isna(valor):
                return "0,00"

        # 1. Formata o número usando o formato padrão (geralmente US: 1,234.56)
        formatted_us = "{:,.2f}".format(valor)
        
        # 2. Troca os separadores para o padrão brasileiro
        # - Troca o ponto (separador decimal US) por um caractere temporário (ex: 'X')
        # - Troca a vírgula (separador de milhar US) por ponto
        # - Troca o caractere temporário por vírgula
        formatted_br = formatted_us.replace('.', 'TEMP').replace(',', '.').replace('TEMP', ',')
        
        return formatted_br
    except Exception:
        # Retorna a string original ou uma representação simples em caso de erro de formatação
        return str(valor)

# ========== FIM DA FUNÇÃO formatar_brasileiro ==========

def carregar_base_supabase():
    try:
        base = pd.DataFrame(supabase.table("pre_roterizacao").select("*").execute().data)
        if base.empty:
            st.warning("⚠️ Nenhuma entrega encontrada na tabela pre_roterizacao.")
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

        df_final = base.copy()
        df_final['Indice'] = df_final.index
        

        return df_final

    except Exception as e:
        st.error(f"Erro ao consultar as tabelas do Supabase: {e}")
        return pd.DataFrame()
    


def gerar_proximo_numero_carga(supabase):
    try:
        hoje = datetime.now(FUSO_BRASIL).strftime("%Y%m%d")  # AGORA USA O FUSO HORÁRIO DO BRASIL
        prefixo = f"{hoje}-"

        # ⚠️ Supabase-py não suporta .like diretamente como usado antes
        cargas = supabase.table("cargas_geradas") \
            .select("numero_carga") \
            .execute().data

        numeros_existentes = []
        for c in cargas:
            numero = str(c.get("numero_carga", ""))
            if numero.startswith(prefixo):
                sufixo = numero[len(prefixo):]
                if sufixo.isdigit():
                    numeros_existentes.append(int(sufixo))

        proximo_numero = max(numeros_existentes) + 1 if numeros_existentes else 1
        return f"{prefixo}{str(proximo_numero).zfill(6)}"

    except Exception as e:
        st.error(f"Erro ao gerar número da carga: {e}")
        return f"{datetime.now().strftime('%Y%m%d')}-000001"


GRID_RESIZE_JS_CODE = JsCode("""
function(params) {
    const gridApi = params.api;
    const gridDiv = params.eGridDiv; // O elemento DOM raiz do grid

    const resizeColumns = () => {
        // FORÇA O NAVEGADOR A RECALCULAR O LAYOUT DO ELEMENTO.
        // Ao acessar uma propriedade como offsetWidth, o navegador é obrigado
        // a garantir que o elemento tenha seu layout mais atualizado.
        gridDiv.offsetWidth; // <--- ADICIONADO AQUI!

        gridApi.sizeColumnsToFit();
        // gridApi.onGridSizeChanged(); // Esta chamada pode ser um complemento se sizeColumnsToFit() não for suficiente sozinho
    };

    // Mantemos um pequeno atraso para a chamada inicial para dar tempo
    // à estrutura DOM do Streamlit se assentar.
    setTimeout(resizeColumns, 200); // Reduzindo o atraso para 200ms, pois o reflow é mais rápido.

    const resizeObserver = new ResizeObserver(entries => {
        for (let entry of entries) {
            // Força o reflow antes de redimensionar novamente para futuras mudanças
            entry.target.offsetWidth; // <--- ADICIONADO AQUI também para o observer!
            resizeColumns();
        }
    });

    resizeObserver.observe(gridDiv);
}
""");

def badge(label):
    """
    Retorna uma string HTML formatada como um 'badge' estilizado.
    Usado para exibir resumos de informações de forma visualmente agrupada.
    """
    return f"<span style='background:#eef2f7;border-radius:12px;padding:6px 12px;margin:4px;color:inherit;display:inline-block;'>{label}</span>"

formatter = JsCode("""
    function(params) {
        if (params.value === null || typeof params.value === 'undefined') return ''; // Retorna vazio para nulos
        // Inclui 0 como valor válido, formata como "0,00"
        if (params.value === 0) return '0,00';
        
        // Aplica formatação monetária (com R$) para colunas de valor
        if (params.colDef.field === 'valor_contratacao' || params.colDef.field === 'Valor do Frete') {
            return Number(params.value).toLocaleString('pt-BR', {
                style: 'currency',
                currency: 'BRL',
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
        }
        // Aplica formatação numérica geral (milhares com ., decimais com ,)
        return Number(params.value).toLocaleString('pt-BR', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }
""")

    
##############################
# Página de sincronização
##############################
# --- Inicializações no topo do script (fora de qualquer função) ---
# Mantenha estas linhas exatamente como estão no topo do seu script
if "sync_triggered" not in st.session_state:
    st.session_state.sync_triggered = False
if "uploaded_sync_file_hash" not in st.session_state:
    st.session_state.uploaded_sync_file_hash = None
if "df_for_sync_cache" not in st.session_state:
    st.session_state.df_for_sync_cache = None
if 'file_uploader_key' not in st.session_state:
    st.session_state.file_uploader_key = 0
# --- Fim das inicializações ---


def pagina_sincronizacao():
    st.title("🔄 Sincronização de Dados")
    
    st.markdown("### 1. Carregar Planilha Excel")
        
    # Usa a chave dinâmica para forçar o reset visual do uploader
    arquivo_excel = st.file_uploader(
        "Selecione a planilha da fBaseroter:", 
        type=["xlsx"], 
        key=f"sync_file_uploader_{st.session_state.file_uploader_key}"
    )

    current_file_hash = None
    if arquivo_excel:
        # CORREÇÃO AQUI: de .heigest() para .hexdigest()
        current_file_hash = hashlib.md5(arquivo_excel.getvalue()).hexdigest()

    # Detecta se um novo arquivo foi carregado ou se o anterior foi limpo/removido
    if current_file_hash != st.session_state.uploaded_sync_file_hash:
        st.session_state.uploaded_sync_file_hash = current_file_hash
        st.session_state.sync_triggered = False # Reseta o gatilho se o arquivo muda
        st.session_state.df_for_sync_cache = None # Limpa o cache do DF

    # Exibe a interface inicial de upload ou o botão de sincronização
    if arquivo_excel:
        try:
            if st.session_state.df_for_sync_cache is None:
                # Lê o arquivo apenas uma vez e armazena em cache
                df_raw = pd.read_excel(arquivo_excel)
                df_raw.columns = df_raw.columns.str.strip()
                st.session_state.df_for_sync_cache = df_raw

            st.success(f"Arquivo '{arquivo_excel.name}' carregado com sucesso!")
            st.write("Clique em 'Iniciar Sincronização' para começar o processo.")

            # Botão para iniciar a sincronização (desabilitado se já estiver rodando)
            if st.button("🚀 Iniciar Sincronização", key="start_sync_button", disabled=st.session_state.sync_triggered):
                st.session_state.sync_triggered = True
                st.rerun() # Força um rerun para que a lógica de sincronização seja executada

        except Exception as e:
            st.error(f"Erro ao ler o arquivo Excel: {e}")
            st.session_state.uploaded_sync_file_hash = None # Resetar em caso de erro na leitura
            st.session_state.sync_triggered = False
            st.session_state.df_for_sync_cache = None

    elif not arquivo_excel and st.session_state.uploaded_sync_file_hash:
        # Caso em que o arquivo foi limpo pelo usuário ou resetado
        st.session_state.uploaded_sync_file_hash = None
        st.session_state.df_for_sync_cache = None
        st.session_state.sync_triggered = False
        st.info("Nenhum arquivo carregado. Faça o upload de um novo arquivo Excel para sincronizar.")
        return # Sai da função se não há arquivo para processar

    else: # Primeiro acesso ou nenhum arquivo carregado ainda
        st.info("Aguardando o upload de um arquivo Excel para iniciar a sincronização.")
        return # Sai da função se não há arquivo para processar


    # --- Bloco de Sincronização (executado SOMENTE se sync_triggered for True) ---
    if st.session_state.sync_triggered:
        st.markdown("---") # Separador visual para o bloco de sincronização
        
        # Apenas a barra de progresso, sem placeholder para mensagens textuais adicionais
        progress_bar = st.progress(0)
        
        try:
            # Passo 1: Limpando e inserindo dados em fBaseroter
            progress_bar.progress(10) # 10%
            
            df_to_process = st.session_state.df_for_sync_cache.copy() 
            
            # 🔧 Remove colunas indesejadas (mesma lógica do seu 02-07.txt)
            colunas_para_remover = ['Capa de Canhoto de NF','Unnamed: 70']
            colunas_existentes_para_remover = [col for col in colunas_para_remover if col in df_to_process.columns]
            if colunas_existentes_para_remover:
                df_to_process.drop(columns=colunas_existentes_para_remover, inplace=True)

            # 🔄 Renomeia colunas (mesma lógica do seu 02-07.txt)
            renomear_colunas = {
                'Cubagem em m3': 'Cubagem em m³',
                'Serie/Numero CTRC': 'Serie_Numero_CTRC'
            }
            colunas_renomeadas = {k: v for k, v in renomear_colunas.items() if k in df_to_process.columns}
            if colunas_renomeadas:
                df_to_process.rename(columns=colunas_renomeadas, inplace=True)
            
            df_to_process = corrigir_tipos(df_to_process) # Garanta que esta função está no seu código

            supabase.table("fBaseroter").delete().neq("Serie_Numero_CTRC", "").execute()
            inserir_em_lote("fBaseroter", df_to_process) # Garanta que esta função está no seu código
            
            progress_bar.progress(30) # 30%

            # Passo 2: Limpando tabelas dependentes
            progress_bar.progress(50) # 50%
            limpar_tabelas_relacionadas() # Garanta que esta função está no seu código
            
            progress_bar.progress(70) # 70%

            # Passo 3: Aplicando regras de negócio
            progress_bar.progress(90) # 90%
            aplicar_regras_e_preencher_tabelas() # Garanta que esta função está no seu código
            
            progress_bar.progress(95) # 95%

            # Passo 4: Invalidando caches (essencial, manter)
            st.session_state["reload_confirmadas_producao"] = True
            st.session_state.pop("df_confirmadas_cache", None)

            st.session_state["reload_aprovacao_diretoria"] = True 

            st.session_state["reload_pre_roterizacao"] = True
            st.session_state.pop("df_pre_roterizacao_cache", None)
            st.session_state.pop("dados_confirmados_cache", None) 
            
            st.session_state["reload_rotas_confirmadas"] = True
            st.session_state.pop("df_rotas_confirmadas_cache", None)

            st.session_state["reload_cargas_geradas"] = True
            st.session_state.pop("df_cargas_cache", None)
        
            st.session_state["reload_aprovacao_custos"] = True
            st.session_state.pop("df_aprovacao_custos_cache", None)
        
            st.session_state["reload_cargas_aprovadas"] = True
            st.session_state.pop("df_cargas_aprovadas_cache", None)
            
            
            progress_bar.progress(100) # 100%

            # --- TRECHO PARA MENSAGEM DE SUCESSO E BALÕES ---
            st.success("✅ Sincronização concluída com sucesso!")
            st.balloons() 
            
            # CRUCIAL: Adicione um pequeno atraso para que o Streamlit possa renderizar os balões e a mensagem
            time.sleep(3) # Espera 2 segundos (ajuste conforme necessário)
            # --- FIM DO TRECHO ---

            # --- CRUCIAL PARA RETORNAR AO ESTADO INICIAL ---
            st.session_state.sync_triggered = False  # Reseta o gatilho
            st.session_state.uploaded_sync_file_hash = None # Remove o hash do arquivo anterior
            st.session_state.df_for_sync_cache = None # Limpa o DataFrame cacheado
            st.session_state.file_uploader_key += 1 # Incrementa a chave para RESETAR o file_uploader visualmente

            st.rerun() # Dispara um rerun para recarregar a página no estado inicial

        except Exception as e:
            st.error(f"❌ Ocorreu um erro durante a sincronização: {e}")
            # Certifique-se de que o uploader e o estado sejam resetados mesmo em caso de erro
            st.session_state.sync_triggered = False
            st.session_state.uploaded_sync_file_hash = None
            st.session_state.df_for_sync_cache = None
            st.session_state.file_uploader_key += 1 # Resetar uploader em erro também
            st.rerun() # Dispara um rerun para recarregar a página após o erro

#___________________________________________________________________________________
def corrigir_tipos(df):
    # Definições dos tipos conforme seu mapeamento
    colunas_texto = [
        "Unnamed", "Serie/Numero CT-e", "Numero da Nota Fiscal",
        "Codigo da Ultima Ocorrencia", "Quantidade de Dias de Atraso",
        "CEP de Entrega","CEP do Destinatario","CEP do Remetente"
    ]

    colunas_numero = [
        "Adicional de Frete", "Cubagem em m³", "Frete Peso", "Frete Valor",
        "Peso Calculado em Kg", "Peso Real em Kg", "Quantidade de Volumes",
        "TDA", "TDE", "Valor da Mercadoria", "Valor do Frete",
        "Valor do ICMS", "Valor do ISS"
    ]

    colunas_data = [
        "Data da Ultima Ocorrencia", "Data de inclusao da Ultima Ocorrencia",
        "Entrega Programada", "Previsao de Entrega",
        "Data de Emissao", "Data de Autorizacao", "Data do Cancelamento", "Data do Escaneamento",
        "Data da Entrega Realizada"
    ]

    # Converter para texto (string)
    for col in colunas_texto:
        if col in df.columns:
            df[col] = df[col].astype(str).replace({'nan': None, 'NaT': None})

    # Converter para numérico
    for col in colunas_numero:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Converter para datetime
    for col in colunas_data:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)

    return df


#_______________________________________________________________________________________________________
def inserir_em_lote(nome_tabela, df, lote=100, tentativas=3, pausa=0.2):
    # Defina as colunas de data do jeito que você já conhece
    colunas_data = [
        "Data da Ultima Ocorrencia", "Data de inclusao da Ultima Ocorrencia",
        "Entrega Programada", "Previsao de Entrega",
        "Data de Emissao", "Data de Autorizacao", "Data do Cancelamento",
        "Data do Escaneamento", "Data da Entrega Realizada"
    ]

    for col in df.columns:
        # Formatar para string só se for coluna de data e coluna existir no df
        if col in colunas_data:
            try:
                df[col] = pd.to_datetime(df[col], errors='coerce')
                df[col] = df[col].dt.strftime('%Y-%m-%d')
            except Exception:
                pass

    # st.write("[DEBUG] Quantidade de NaNs por coluna (antes do applymap):", df.isna().sum()) # REMOVIDO

    def limpar_valores(obj):
        if pd.isna(obj):
            return None
        return obj

    dados = df.applymap(limpar_valores).to_dict(orient="records")

    if dados:
        # st.write("[DEBUG] Primeira linha do lote limpo:", dados[0]) # REMOVIDO
        pass # Mantido para evitar erro se 'dados' for vazio e a linha acima estivesse sozinha

    for i in range(0, len(dados), lote):
        sublote = dados[i:i + lote]
        for tentativa in range(tentativas):
            try:
                supabase.table(nome_tabela).insert(sublote).execute()
                # st.info(f"[DEBUG] Inseridos {len(sublote)} registros na tabela '{nome_tabela}' (lote {i}–{i + len(sublote) - 1}).") # REMOVIDO
                break
            except Exception as e:
                st.warning(f"[TENTATIVA {tentativa + 1}] Erro ao inserir lote {i}–{i + len(sublote) - 1}: {e}")
                time.sleep(1)
        else:
            st.error(f"[ERRO] Falha final ao inserir lote {i}–{i + len(sublote) - 1} na tabela '{nome_tabela}'.")
        time.sleep(pausa)


#------------------------------------------------------------------------------
def limpar_tabelas_relacionadas():
    tabelas = [
        "confirmadas_producao", "aprovacao_diretoria", "pre_roterizacao",
        "rotas_confirmadas", "cargas_geradas", "aprovacao_custos", "cargas_aprovadas"
    ]

    for tabela in tabelas:
        try:
            res = supabase.table(tabela).select("*").limit(1).execute()
            if res.data:
                chave = list(res.data[0].keys())[0]
                valor_exclusao = "00000000-0000-0000-0000-000000000000" if "uuid" in str(type(res.data[0][chave])).lower() else "0"

                # Executa o delete com filtro válido
                supabase.table(tabela).delete().neq(chave, valor_exclusao).execute()

                # st.warning(f"[DEBUG] Dados da tabela '{tabela}' foram apagados.") # REMOVIDO
            else:
                # st.info(f"[DEBUG] Tabela '{tabela}' já estava vazia.") # REMOVIDO
                pass # Mantido para evitar erro se 'else' for vazio
        except Exception as e:
            st.error(f"[ERRO] Ao limpar tabela '{tabela}': {e}")

# ------------------------#############-------------------------------------------
def adicionar_entregas_a_carga(chaves_cte):
    if not chaves_cte:
        st.warning("⚠️ Nenhuma chave CT-e foi informada.")
        return

    numero_carga = gerar_proximo_numero_carga(supabase)
    entregas_coletadas = []

    for tabela in ["rotas_confirmadas", "pre_roterizacao"]:
        try:
            resposta = supabase.table(tabela).select("*").in_("Chave CT-e", chaves_cte).execute()
            if resposta.data:
                entregas_coletadas.extend(resposta.data)
        except Exception as e:
            st.error(f"Erro ao consultar tabela '{tabela}': {e}")
            return

    if not entregas_coletadas:
        st.warning("⚠️ Nenhuma entrega encontrada para as chaves informadas.")
        return

    # Remove entregas das tabelas de origem
    for tabela in ["rotas_confirmadas", "pre_roterizacao"]:
        try:
            supabase.table(tabela).delete().in_("Chave CT-e", chaves_cte).execute()
        except Exception as e:
            st.error(f"Erro ao remover da tabela '{tabela}': {e}")

    # Insere entregas na tabela `cargas_geradas`
    now = data_hora_brasil_iso()
    for entrega in entregas_coletadas:
        entrega["numero_carga"] = numero_carga
        entrega["Data_Hora_Gerada"] = now

    try:
        supabase.table("cargas_geradas").insert(entregas_coletadas).execute()
        st.success(f"✅ {len(entregas_coletadas)} entrega(s) adicionada(s) à Carga {numero_carga}")
    except Exception as e:
        st.error(f"Erro ao inserir na tabela 'cargas_geradas': {e}")




# ------------------------#############-------------------------------------------
def aplicar_regras_e_preencher_tabelas():
    #st.subheader("🔍 Aplicando Regras de Negócio")

    try:
        # Carrega dados base
        df = supabase.table("fBaseroter").select("*").execute().data
        if not df:
            st.error("Tabela fBaseroter está vazia.")
            return

        df = pd.DataFrame(df)
        df.columns = df.columns.str.strip()

        df['Previsao de Entrega'] = pd.to_datetime(df.get('Previsao de Entrega'), errors='coerce')
        df['Entrega Programada'] = pd.to_datetime(df.get('Entrega Programada'), errors='coerce')

        # st.text(f"[DEBUG] {len(df)} registros carregados de fBaseroter.") # REMOVIDO
#__________________________________________________________________________________________________________
        #__________________________________________________________________________________________________________
        # Merge com Micro_Regiao_por_data_embarque
        micro = supabase.table("Micro_Regiao_por_data_embarque").select("*").execute().data
        if micro:
            df_micro = pd.DataFrame(micro)
            df_micro.columns = df_micro.columns.str.strip()

            # Detectar nome da coluna de data e região (assumindo 'REGIÃO' é o nome da coluna no Supabase)
            col_data_micro = [col for col in df_micro.columns if 'relação' in col.lower()]
            cidade_destino_col = 'CIDADE DESTINO'
            regiao_col = 'REGIÃO'

            # Garante que as colunas essenciais para o merge e para a região existam
            if col_data_micro and cidade_destino_col in df_micro.columns and regiao_col in df_micro.columns:
                data_col = col_data_micro[0]
                df_micro[data_col] = pd.to_numeric(df_micro[data_col], errors='coerce')

                # Preparar colunas para o merge (case-insensitive e trim para garantir match)
                df['Cidade de Entrega_upper'] = df['Cidade de Entrega'].astype(str).str.strip().str.upper()
                df_micro[cidade_destino_col + '_upper'] = df_micro[cidade_destino_col].astype(str).str.strip().str.upper()

                # Faz merge com base em Cidade de Entrega = CIDADE DESTINO e inclui a REGIÃO
                df = df.merge(
                    df_micro[[data_col, cidade_destino_col + '_upper', regiao_col]],
                    how='left',
                    left_on='Cidade de Entrega_upper',
                    right_on=cidade_destino_col + '_upper'
                )

                # Renomeia a coluna de região para o nome final desejado 'Regiao'
                df.rename(columns={regiao_col: 'Regiao'}, inplace=True)

                # Calcula Data de Embarque
                df['Data de Embarque'] = df['Previsao de Entrega'] - pd.to_timedelta(df[data_col], unit='D')

                # Remove colunas auxiliares criadas para o merge
                df.drop(columns=[data_col, cidade_destino_col + '_upper', 'Cidade de Entrega_upper'], inplace=True, errors='ignore')
            else:
                st.warning("Colunas de data de relação, cidade destino ou região não encontradas em Micro_Regiao_por_data_embarque. A coluna 'Regiao' será preenchida como nula.")
                df['Data de Embarque'] = pd.NaT
                df['Regiao'] = None # Garante que a coluna Regiao existe mesmo sem merge
        else:
            df['Data de Embarque'] = pd.NaT
            df['Regiao'] = None # Garante que a coluna Regiao existe mesmo sem dados
        # st.text("[DEBUG] Mescla com Micro_Regiao_por_data_embarque concluída.") # REMOVIDO
#______________________________________________________________________________________________________________________

        # Merge com Particularidades
        part = supabase.table("Particularidades").select("*").execute().data
        if part:
            df_part = pd.DataFrame(part)
            df_part.columns = df_part.columns.str.strip()
            df = df.merge(df_part[['CNPJ', 'Particularidade']], how='left',
                          left_on='CNPJ Destinatario', right_on='CNPJ')
            df.drop(columns=['CNPJ'], inplace=True)
        else:
            df['Particularidade'] = None
        # st.text("[DEBUG] Mescla com Particularidades concluída.") # REMOVIDO
#________________________________________________________________________________________________________________________
        # Merge com Clientes_Entrega_Agendada
        agendados = supabase.table("Clientes_Entrega_Agendada").select("*").execute().data
        if agendados:
            df_ag = pd.DataFrame(agendados)
            df_ag.columns = df_ag.columns.str.strip()

            # Corrigir o nome da coluna
            if 'CNPJ' in df_ag.columns and 'Status de Agenda' in df_ag.columns:
                # Filtra os CNPJs com 'Status de Agenda' == 'AGENDAR'
                cnpjs_agendar = df_ag[df_ag['Status de Agenda'].str.upper() == 'AGENDAR']['CNPJ'].str.strip().unique()

                # Marca como 'AGENDAR' na coluna Status se o CNPJ estiver na lista
                df['Status'] = df['CNPJ Destinatario'].str.strip().isin(cnpjs_agendar).map({True: 'AGENDAR', False: None})
            else:
                df['Status'] = None
                st.warning("Colunas 'CNPJ' e/ou 'Status de Agenda' não encontradas em Clientes_Entrega_Agendada.")
        else:
            df['Status'] = None
        # st.text("[DEBUG] Mescla com Clientes_Entrega_Agendada concluída.") # REMOVIDO


#________________________________________________________________________________________________________________________
        # Definição da Rota
        rotas = supabase.table("Rotas").select("*").execute().data
        # Definição da Rota
        df['Rota'] = None

        # Tabela geral de rotas
        rotas = supabase.table("Rotas").select("*").execute().data
        df_rotas = pd.DataFrame(rotas) if rotas else pd.DataFrame()
        df_rotas.columns = df_rotas.columns.str.strip()

        # Tabela específica de Porto Alegre
        rotas_poas = supabase.table("RotasPortoAlegre").select("*").execute().data
        df_poas = pd.DataFrame(rotas_poas) if rotas_poas else pd.DataFrame()
        df_poas.columns = df_poas.columns.str.strip()

        for idx, row in df.iterrows():
            cidade = row.get('Cidade de Entrega', '').strip().upper()
            bairro = row.get('Bairro do Destinatario', '').strip().upper()

            if cidade == 'PORTO ALEGRE' and not df_poas.empty:
                match = df_poas[df_poas['Bairro do Destinatario'].str.strip().str.upper() == bairro]
                if not match.empty:
                    df.at[idx, 'Rota'] = match.iloc[0]['Rota']
            elif not df_rotas.empty:
                match = df_rotas[df_rotas['Cidade de Entrega'].str.strip().str.upper() == cidade]
                if not match.empty:
                    df.at[idx, 'Rota'] = match.iloc[0]['Rota']
        # st.text("[DEBUG] Definição de rotas concluída.") # REMOVIDO

#__________________________________________________________________________________________________________________________
        # Pré-roterização
        hoje = pd.to_datetime('today').normalize()
        obrigatorias = df[
            (df['Data de Embarque'] < hoje + pd.Timedelta(days=1)) |
            ((df['Status'] == 'AGENDADA') & (df['Entrega Programada'].isna()))
        ].copy()

        confirmadas = df[~df['Serie_Numero_CTRC'].isin(obrigatorias['Serie_Numero_CTRC'])].copy()

        obrigatorias.drop_duplicates(subset='Serie_Numero_CTRC', inplace=True)
        confirmadas.drop_duplicates(subset='Serie_Numero_CTRC', inplace=True)

        colunas_finais = [
            'Serie_Numero_CTRC', 'Cliente Pagador', 'Chave CT-e', 'Cliente Destinatario',
            'Cidade de Entrega', 'Bairro do Destinatario', 'Previsao de Entrega',
            'Numero da Nota Fiscal', 'Status', 'Entrega Programada', 'Particularidade',
            'Codigo da Ultima Ocorrencia', 'Peso Real em Kg', 'Peso Calculado em Kg',
            'Cubagem em m³', 'Quantidade de Volumes', 'Valor do Frete', 'Rota','Regiao',
            'CEP de Entrega','CEP do Destinatario','CEP do Remetente'

        ]

        inserir_em_lote("pre_roterizacao", obrigatorias[colunas_finais])
        inserir_em_lote("confirmadas_producao", confirmadas[colunas_finais])

        st.success(f"Inseridos {len(obrigatorias)} em Pré Roterização e {len(confirmadas)} em Confirmar Produção.")

    except Exception as e:
        st.error(f"[ERRO] Regras de sincronização: {e}")

# ==============================================================================
# NOVAS CONSTANTES E FUNÇÃO AUXILIAR PARA FORMATO DE DATA BRASILEIRO
# ==============================================================================

# Formato de exibição de data e hora no padrão brasileiro
DATE_DISPLAY_FORMAT_STRING = '%d-%m-%Y %H:%M:%S'

# Lista de todas as colunas que são datas/horas no seu sistema e que devem ser formatadas para exibição
# Esta lista será usada consistentemente em todas as páginas para formatar as colunas do grid
GLOBAL_DATE_DISPLAY_COLUMNS = [
    "Data de Emissao", "Data de Autorizacao", "Data de inclusao da Ultima Ocorrencia",
    "Data da Ultima Ocorrencia", "Previsao de Entrega", "Entrega Programada",
    "Data da Entrega Realizada", "Data do Cancelamento", "Data do Escaneamento",
    "Data_Hora_Gerada" # Incluída aqui para que todas as datas sejam tratadas pela função
]

def apply_brazilian_date_format_for_display(df_to_format):
    """
    Aplica o formato de data brasileiro (DD-MM-YYYY HH:MM:SS) às colunas de data especificadas
    em um DataFrame, tratando valores nulos (NaT) para exibir como strings vazias.
    Garante que a coluna seja do tipo datetime antes de formatar.
    """
    for col in GLOBAL_DATE_DISPLAY_COLUMNS:
        if col in df_to_format.columns:
            # Primeiro, garante que a coluna é do tipo datetime.
            # Isso é crucial caso os dados venham do banco como strings e não sejam datetime64[ns] ainda.
            if not pd.api.types.is_datetime64_any_dtype(df_to_format[col]):
                df_to_format[col] = pd.to_datetime(df_to_format[col], errors='coerce')

            # Agora, aplica a formatação para exibição
            df_to_format[col] = df_to_format[col].apply(
                lambda x: x.strftime(DATE_DISPLAY_FORMAT_STRING)
                if pd.notna(x) and isinstance(x, (Timestamp, datetime)) # Verifica se é um objeto Timestamp ou datetime nativo
                else ''
            )
    return df_to_format

##########################################

# PÁGINA Confirmar Produção

##########################################
def pagina_confirmar_producao():
    st.markdown("## Confirmar Produção")

    # Carregando entregas diretamente da tabela 'confirmadas_producao'
    with st.spinner("🔄 Carregando entregas para confirmar produção..."):
        try:
            # Fonte de dados para esta página é 'confirmadas_producao'
            # Usando cache para evitar múltiplas chamadas ao Supabase a cada rerun desnecessário
            # A flag 'reload_confirmadas_producao' será usada para invalidar o cache e forçar um novo fetch
            recarregar = st.session_state.pop("reload_confirmadas_producao", False)
            if recarregar or "df_confirmadas_cache" not in st.session_state:
                
                df = pd.DataFrame(supabase.table("confirmadas_producao").select("*").execute().data)
                st.session_state["df_confirmadas_cache"] = df
            else:
                df = st.session_state["df_confirmadas_cache"]
            
            # Limpar e normalizar dados para evitar KeyErrors e problemas de tipo
            if not df.empty: # Garante que o DataFrame não está vazio antes de tentar normalizar
                if 'Rota' in df.columns:
                    df['Rota'] = df['Rota'].fillna('').astype(str)
                if 'Status' in df.columns:
                    df['Status'] = df['Status'].fillna('').astype(str)
                if 'Entrega Programada' in df.columns:
                    df['Entrega Programada'] = pd.to_datetime(df['Entrega Programada'], errors='coerce')
                    # O JsCode lida com NaT se convertermos para string no final, mas mantenha pd.NaT aqui para cálculos
                if 'Particularidade' in df.columns:
                    df['Particularidade'] = df['Particularidade'].fillna('').astype(str)
                if 'Serie_Numero_CTRC' in df.columns:
                    df['Serie_Numero_CTRC'] = df['Serie_Numero_CTRC'].astype(str)

        except Exception as e:
            st.error(f"Erro ao consultar o banco de dados: {e}")
            return

        if df.empty:
            st.info("Nenhuma entrega disponível para confirmar produção.")
            return

    # Exibir métricas gerais
    col1, col2, _ = st.columns([1, 1, 8])
    with col1:
        st.metric("Total de Rotas", df["Rota"].nunique() if "Rota" in df.columns else 0)
    with col2:
        st.metric("Total de Entregas", len(df))

    # Definir as colunas que devem ser exibidas no grid
    colunas_exibir = [
        "Serie_Numero_CTRC", "Rota", "Regiao", "Valor do Frete", "Cliente Pagador", "Chave CT-e",
        "Cliente Destinatario", "Cidade de Entrega", "Bairro do Destinatario", 
        "Previsao de Entrega", "Numero da Nota Fiscal", "Status", "Entrega Programada", 
        "Particularidade", "Codigo da Ultima Ocorrencia", "Peso Real em Kg", 
        "Peso Calculado em Kg", "Cubagem em m³", "Quantidade de Volumes"
    ]

    # Configuração de estilo condicional do grid (JsCode)
    linha_destacar = JsCode("""
        function(params) {
            const status = params.data['Status'];
            const entrega = params.data['Entrega Programada'];
            const particularidade = params.data['Particularidade'];
            // Verifica se a entrega está vazia ou contém apenas espaços (para compatibilidade com strings vazias)
            const isEntregaEmpty = !entrega || (typeof entrega === 'string' && entrega.trim() === '');
            if (status === 'AGENDAR' && isEntregaEmpty) {
                return { 'background-color': '#ffe0b2', 'color': '#333' }; // Amarelo claro para "AGENDAR" sem data
            }
            if (particularidade && typeof particularidade === 'string' && particularidade.trim() !== "") {
                return { 'background-color': '#fff59d', 'color': '#333' }; // Amarelo um pouco mais escuro para "Particularidade"
            }
            return null;
        }
    """)

    # Iterar sobre as rotas únicas para exibir os grids
    rotas_unicas = sorted(df["Rota"].dropna().unique()) if "Rota" in df.columns else []

    for rota in rotas_unicas:
        df_rota = df[df["Rota"] == rota].copy()
        if df_rota.empty:
            continue

        st.markdown(f"""
        <div style="margin-top:20px;padding:10px;background:#e8f0fe;border-left:4px solid #4285f4;border-radius:6px;display:inline-block;max-width:100%;">
            <strong>Rota:</strong> {rota}
        </div>
        """, unsafe_allow_html=True)

        # Informações agregadas sobre a rota (badges)
        col_badge, col_check_placeholder = st.columns([5, 1]) # O checkbox master agora vai dentro do expander
        with col_badge:
            # Garante que as colunas existem antes de tentar somar/formatar
            peso_calc_sum = df_rota['Peso Calculado em Kg'].sum() if 'Peso Calculado em Kg' in df_rota.columns else 0
            peso_real_sum = df_rota['Peso Real em Kg'].sum() if 'Peso Real em Kg' in df_rota.columns else 0
            valor_frete_sum = df_rota['Valor do Frete'].sum() if 'Valor do Frete' in df_rota.columns else 0
            cubagem_sum = df_rota['Cubagem em m³'].sum() if 'Cubagem em m³' in df_rota.columns else 0
            volumes_sum = df_rota['Quantidade de Volumes'].sum() if 'Quantidade de Volumes' in df_rota.columns else 0

            st.markdown(
                f"<span style='background:#eef2f7;border-radius:12px;padding:6px 12px;margin:4px;color:inherit;display:inline-block;'>{len(df_rota)} entregas</span>"
                f"<span style='background:#eef2f7;border-radius:12px;padding:6px 12px;margin:4px;color:inherit;display:inline-block;'>{formatar_brasileiro(peso_calc_sum)} kg calc</span>"
                f"<span style='background:#eef2f7;border-radius:12px;padding:6px 12px;margin:4px;color:inherit;display:inline-block;'>{formatar_brasileiro(peso_real_sum)} kg real</span>"
                f"<span style='background:#eef2f7;border-radius:12px;padding:6px 12px;margin:4px;color:inherit;display:inline-block;'>R$ {formatar_brasileiro(valor_frete_sum)}</span>"
                f"<span style='background:#eef2f7;border-radius:12px;padding:6px 12px;margin:4px;color:inherit;display:inline-block;'>{formatar_brasileiro(cubagem_sum)} m³</span>"
                f"<span style='background:#eef2f7;border-radius:12px;padding:6px 12px;margin:4px;color:inherit;display:inline-block;'>{int(volumes_sum)} volumes</span>",
                unsafe_allow_html=True
            )

        # Expander para o grid
        with st.expander("🔽 Selecionar entregas", expanded=False):
            # NOVO: Checkbox "Marcar todas" dentro do expander
            checkbox_key = f"marcar_todas_conf_prod_{rota}"
            # Garante que o estado do checkbox seja inicializado
            if checkbox_key not in st.session_state:
                st.session_state[checkbox_key] = False
            
            marcar_todas = st.checkbox("Marcar todas", key=checkbox_key)

            # Criação e estilização do grid (usando o AgGrid)
            df_formatado = df_rota[[col for col in colunas_exibir if col in df_rota.columns]].copy()
            df_formatado = apply_brazilian_date_format_for_display(df_formatado)

            # >>> AJUSTE ESTE BLOCO PARA FORMATAR DATAS COM VERIFICAÇÃO DE TIPO <<<
            
            if not df_formatado.empty:
                gb = GridOptionsBuilder.from_dataframe(df_formatado)
                gb.configure_default_column(minWidth=150)
                gb.configure_selection("multiple", use_checkbox=True)
                gb.configure_grid_options(paginationPageSize=12)
                gb.configure_grid_options(alwaysShowHorizontalScroll=True)
                gb.configure_grid_options(rowStyle={'font-size': '11px'})
                gb.configure_grid_options(onGridReady=GRID_RESIZE_JS_CODE) # <<< ADICIONADO AQUI
                grid_options = gb.build()
                grid_options["getRowStyle"] = linha_destacar # Atribui o JsCode aqui

                # Gerencia a chave única para o grid, essencial para o st.rerun() funcionar
                # A chave do grid só é alterada se os dados subjacentes tiverem sido modificados
                # Para evitar "winks" desnecessários
                grid_key_id = f"grid_conf_prod_{rota}"
                if grid_key_id not in st.session_state:
                    st.session_state[grid_key_id] = str(uuid.uuid4()) # Inicializa com um UUID

                grid_response = AgGrid(
                    df_formatado,
                    gridOptions=grid_options,
                    update_mode=GridUpdateMode.SELECTION_CHANGED, # Essencial para evitar o "wink" ao selecionar
                    fit_columns_on_grid_load=False,
                    width="100%",
                    height=400,
                    allow_unsafe_jscode=True,
                    key=st.session_state[grid_key_id], # Usa a chave única para o grid
                    data_return_mode="AS_INPUT",
                    theme=AgGridTheme.MATERIAL,
                    show_toolbar=False,
                    custom_css={
                        ".ag-theme-material .ag-cell": {
                            "font-size": "11px",
                            "line-height": "18px",
                            "border-right": "1px solid #ccc",
                        },
                        ".ag-theme-material .ag-row:last-child .ag-cell": {
                            "border-bottom": "1px solid #ccc",
                        },
                        ".ag-theme-material .ag-header-cell": {
                            "border-right": "1px solid #ccc",
                            "border-bottom": "1px solid #ccc",
                        },
                        ".ag-theme-material .ag-root-wrapper": {
                            "border": "1px solid black",
                            "border-radius": "6px",
                            "padding": "4px",
                        },
                        ".ag-theme-material .ag-header-cell-label": {
                            "font-size": "11px",
                        },
                        ".ag-center-cols-viewport": {
                            "overflow-x": "auto !important",
                            "overflow-y": "hidden",
                        },
                        ".ag-center-cols-container": {
                            "min-width": "100% !important",
                        },
                        "#gridToolBar": {
                            "padding-bottom": "0px !important",
                        }
                    }
                )

                # Captura os registros selecionados pelo usuário no grid
                # Lógica ajustada para considerar o checkbox "Marcar todas"
                if marcar_todas:
                    # Se "Marcar todas" estiver checado, seleciona todas as entregas do DataFrame atual
                    selecionadas = df_formatado[df_formatado["Serie_Numero_CTRC"].notna()].copy()
                else:
                    # Caso contrário, usa a seleção feita diretamente no grid
                    selecionadas = pd.DataFrame(grid_response.get("selected_rows", []))

                st.markdown(f"**📦 Entregas selecionadas:** {len(selecionadas)}")

                # Botão para confirmar produção
                if not selecionadas.empty:
                    if st.button(f"🚀 Enviar para Aprovação da Diretoria da Rota {rota}", key=f"btn_confirmar_{rota}"):
                        try:
                            # Prepara os dados para inserção na tabela de aprovacao_diretoria
                                                        # Prepara os dados para inserção na tabela de aprovacao_diretoria
                            df_confirmar = selecionadas.drop(columns=["_selectedRowNodeInfo"], errors="ignore").copy()
                            df_confirmar["Rota"] = rota # Garante que a rota esteja na coluna correta
                            
                            # --- NOVO/MODIFICADO: TRATAMENTO DE DATAS PARA INSERÇÃO NO SUPABASE ---
                            # As colunas de data no 'selecionadas' vêm como strings no formato brasileiro (DD-MM-AAAA HH:MM:SS).
                            # Primeiro, vamos converter essas strings de volta para objetos datetime.
                            # Usamos GLOBAL_DATE_DISPLAY_COLUMNS e DATE_DISPLAY_FORMAT_STRING (definidas no seu código).
                                                        # --- INÍCIO DO NOVO TRATAMENTO ROBUSTO DE DATAS PARA SUPABASE ---

                            # Step 1: Ensure date columns from AgGrid selection (strings in Brazilian format)
                            # are properly parsed into Pandas Timestamp objects.
                            for col_name in GLOBAL_DATE_DISPLAY_COLUMNS:
                                if col_name in df_confirmar.columns:
                                    df_confirmar[col_name] = pd.to_datetime(
                                        df_confirmar[col_name],
                                        format=DATE_DISPLAY_FORMAT_STRING, # Brazilian format (DD-MM-AAAA HH:MM:SS)
                                        errors='coerce' # Convert unparseable values to pd.NaT
                                    )

                            # Step 2: Iterate through all columns and convert any Pandas Timestamp or
                            # standard Python datetime.datetime objects to ISO 8601 strings.
                            # This catches cases where dtype might be 'object' but contains datetime objects.
                            for col_name in df_confirmar.columns:
                                # Only process columns that potentially contain datetime objects
                                # or are explicitly marked as date columns.
                                if col_name in GLOBAL_DATE_DISPLAY_COLUMNS or \
                                   pd.api.types.is_datetime64_any_dtype(df_confirmar[col_name]):
                                    df_confirmar[col_name] = df_confirmar[col_name].apply(
                                        lambda x: x.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(x) else None
                                    )
                                # For other 'object' columns that are NOT date columns, ensure they don't contain datetimes
                                elif df_confirmar[col_name].dtype == 'object':
                                    df_confirmar[col_name] = df_confirmar[col_name].apply(
                                        lambda x: x.strftime("%Y-%m-%d %H:%M:%S") if isinstance(x, (pd.Timestamp, datetime)) else x
                                    )

                            # Step 3: Replace any remaining numpy.nan, numpy.inf, or empty strings with None
                            # for general compatibility with Supabase. This should be done AFTER date formatting.
                            df_confirmar = df_confirmar.replace([np.nan, np.inf, -np.inf, ""], None)
                            st.session_state["reload_aprovacao_diretoria"] = True 

                            # --- FIM DO NOVO TRATAMENTO ROBUSTO DE DATAS PARA SUPABASE ---

                            # --- FIM DO NOVO/MODIFICADO BLOCO DE TRATAMENTO DE DATAS ---

                            registros = df_confirmar.to_dict(orient="records")
                            # Filtra registros inválidos (sem Serie_Numero_CTRC)
                            registros = [r for r in registros if r.get("Serie_Numero_CTRC")]

                            # Insere na tabela de aprovacao_diretoria
                            if registros: # Apenas insere se houver registros válidos
                                supabase.table("aprovacao_diretoria").insert(registros).execute()
                            
                            # === CORREÇÃO: Remove as entregas da tabela 'confirmadas_producao' ===
                            # As entregas são movidas da 'confirmadas_producao' para 'aprovacao_diretoria'.
                            chaves = [r["Serie_Numero_CTRC"] for r in registros]
                            if chaves: # Apenas deleta se houver chaves para deletar
                                supabase.table("confirmadas_producao").delete().in_("Serie_Numero_CTRC", chaves).execute()

                            # Limpa o estado da sessão para forçar a recarga dos grids e evitar problemas de cache.
                            # Isso é crucial para que o st.rerun() "veja" os dados atualizados do banco.
                            st.session_state["reload_confirmadas_producao"] = True # Sinaliza para recarregar os dados na próxima execução
                            st.session_state.pop(grid_key_id, None) # Remove a key do grid para forçar a reconstrução, se necessário

                            # Limpa o estado do checkbox "Marcar todas" para esta rota após a ação
                            st.session_state.pop(checkbox_key, None)
                                
                            st.success(f"✅ {len(chaves)} entregas da Rota {rota} foram enviadas para a próxima etapa (Aprovação da Diretoria).")
                            
                            # Força um rerun para atualizar a UI e refletir as mudanças
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao confirmar produção da rota {rota}: {e}")

                   


###########################################

# PÁGINA APROVAÇÃO DIRETORIA

##########################################

def pagina_aprovacao_diretoria():
    st.markdown("## Aprovação da Diretoria")

    # Obter a classe do usuário logado (assume 'colaborador' se não estiver definida por segurança)
    current_user_class = st.session_state.get("classe", "colaborador")
    is_user_aprovador = (current_user_class == "aprovador")

    # Mensagem de aviso se o usuário não for aprovador
    if not is_user_aprovador:
        st.warning("⛔ Apenas usuários com classe 'aprovador' podem realizar ações de aprovação de diretoria.")
        # Se a página só pode ser acessada por aprovadores e o usuário não é um, retorne.
        # Caso contrário, se a intenção for apenas desabilitar botões, pode-se remover este 'return'.
        # Mantendo o return por enquanto para seguir a lógica inicial de acesso restrito.
        return # Esta linha deve permanecer se você quer impedir que não-aprovadores vejam a página.

    try:
        with st.spinner("🔄 Carregando entregas pendentes para aprovação..."):
            # Lógica de cache para evitar múltiplas chamadas ao Supabase em reruns
            recarregar = st.session_state.pop("reload_aprovacao_diretoria", False) # Adiciona recarregamento de cache
            if recarregar or "df_aprovacao_diretoria_cache" not in st.session_state: # Verifica o cache
                df_aprovacao = pd.DataFrame(
                    supabase.table("aprovacao_diretoria").select("*").execute().data
                )
                st.session_state["df_aprovacao_diretoria_cache"] = df_aprovacao # Atualiza o cache
            else:
                df_aprovacao = st.session_state["df_aprovacao_diretoria_cache"] # Usa o cache existente

        if df_aprovacao.empty:
            st.info("Nenhuma entrega pendente para aprovação.")
            return

    except Exception as e:
        st.error(f"Erro ao carregar dados da aprovação: {e}")
        return


    df_aprovacao["Cliente Pagador"] = df_aprovacao["Cliente Pagador"].astype(str).str.strip().fillna("(Vazio)")


    df_exibir = df_aprovacao.copy()
    col1, col2, _ = st.columns([1, 1, 8])
    with col1:
        st.metric("Total de Clientes", df_exibir["Cliente Pagador"].nunique())
    with col2:
        st.metric("Total de Entregas", len(df_exibir))


    def badge(label):
        return f"<span style='background:#eef2f7;border-radius:12px;padding:6px 12px;margin:4px;color:inherit;display:inline-block;'>{label}</span>"

    colunas_exibir = [
        "Serie_Numero_CTRC", "Rota", "Regiao", "Valor do Frete", "Cliente Pagador", "Chave CT-e",
        "Cliente Destinatario", "Cidade de Entrega", "Bairro do Destinatario", "Previsao de Entrega",
        "Numero da Nota Fiscal", "Status", "Entrega Programada", "Particularidade", "Codigo da Ultima Ocorrencia",
        "Peso Real em Kg", "Peso Calculado em Kg", "Cubagem em m³", "Quantidade de Volumes"
    ]

    linha_destacar = JsCode("""
        function(params) {
            const status = params.data['Status'];
            const entrega = params.data['Entrega Programada'];
            const particularidade = params.data['Particularidade'];
            if (status === 'AGENDAR' && (!entrega || entrega.trim() === '')) {
                return { 'background-color': '#ffe0b2', 'color': '#333' };
            }
            if (particularidade && particularidade.trim() !== "") {
                return { 'background-color': '#fff59d', 'color': '#333' };
            }
            return null;
        }
    """)

    for cliente in sorted(df_aprovacao["Cliente Pagador"].unique()):
        df_cliente = df_aprovacao[df_aprovacao["Cliente Pagador"] == cliente].copy()
        if df_cliente.empty:
            continue

        st.markdown(f"""
        <div style="margin-top:20px;padding:10px;background:#e8f0fe;border-left:4px solid #4285f4;border-radius:6px;display:inline-block;max-width:100%;">
            <strong>Cliente:</strong> {cliente}
        </div>
        """, unsafe_allow_html=True)

        col_badge, col_check = st.columns([5, 1])
        with col_badge:
            st.markdown(
                badge(f"{len(df_cliente)} entregas") +
                badge(f"{formatar_brasileiro(df_cliente['Peso Calculado em Kg'].sum())} kg calc") +
                badge(f"{formatar_brasileiro(df_cliente['Peso Real em Kg'].sum())} kg real") +
                badge(f"R$ {formatar_brasileiro(df_cliente['Valor do Frete'].sum())}") +
                badge(f"{formatar_brasileiro(df_cliente['Cubagem em m³'].sum())} m³") +
                badge(f"{int(df_cliente['Quantidade de Volumes'].sum())} volumes"),
                unsafe_allow_html=True
            )


        with st.expander("🔽 Selecionar entregas", expanded=False):
            
            df_formatado = apply_brazilian_date_format_for_display(df_cliente[[col for col in colunas_exibir if col in df_cliente.columns]].copy())

             # NOVO: Checkbox "Marcar todas" dentro do expander
            checkbox_key = f"marcar_todas_aprov_{cliente}"
            if checkbox_key not in st.session_state:
                st.session_state[checkbox_key] = False
            marcar_todas = st.checkbox("Marcar todas", key=checkbox_key)

            if not df_formatado.empty:
                gb = GridOptionsBuilder.from_dataframe(df_formatado)
                gb.configure_default_column(minWidth=150)
                gb.configure_selection("multiple", use_checkbox=True)
                gb.configure_grid_options(paginationPageSize=12)
                gb.configure_grid_options(alwaysShowHorizontalScroll=True)
                gb.configure_grid_options(rowStyle={'font-size': '11px'})
                gb.configure_grid_options(onGridReady=GRID_RESIZE_JS_CODE) # <<< ADICIONADO AQUI
                grid_options = gb.build()
                grid_options["getRowStyle"] = linha_destacar

                grid_key_id = f"grid_aprovar_{cliente}"
                if grid_key_id not in st.session_state:
                    st.session_state[grid_key_id] = str(uuid.uuid4())

                grid_response = AgGrid(
                    df_formatado,
                    gridOptions=grid_options,
                    update_mode=GridUpdateMode.SELECTION_CHANGED,
                    fit_columns_on_grid_load=False,
                    width="100%",
                    height=400,
                    allow_unsafe_jscode=True,
                    key=st.session_state[grid_key_id],
                    data_return_mode="AS_INPUT",
                    theme=AgGridTheme.MATERIAL,
                    show_toolbar=False,
                    custom_css={
                        ".ag-theme-material .ag-cell": {
                            "font-size": "11px",
                            "line-height": "18px",
                            "border-right": "1px solid #ccc",
                        },
                        ".ag-theme-material .ag-row:last-child .ag-cell": {
                            "border-bottom": "1px solid #ccc",
                        },
                        ".ag-theme-material .ag-header-cell": {
                            "border-right": "1px solid #ccc",
                            "border-bottom": "1px solid #ccc",
                        },
                        ".ag-theme-material .ag-root-wrapper": {
                            "border": "1px solid black",
                            "border-radius": "6px",
                            "padding": "4px",
                        },
                        ".ag-theme-material .ag-header-cell-label": {
                            "font-size": "11px",
                        },
                        ".ag-center-cols-viewport": {
                            "overflow-x": "auto !important",
                            "overflow-y": "hidden",
                        },
                        ".ag-center-cols-container": {
                            "min-width": "100% !important",
                        },
                        "#gridToolBar": {
                            "padding-bottom": "0px !important",
                        }
                    }
                )

                if marcar_todas:
                    selecionadas = df_formatado[df_formatado["Serie_Numero_CTRC"].notna()].copy()
                else:
                    selecionadas = pd.DataFrame(grid_response.get("selected_rows", []))

                st.markdown(f"**📦 Entregas selecionadas:** {len(selecionadas)}")

                if not selecionadas.empty:
                    col_aprovar, col_rejeitar = st.columns(2) # Adiciona duas colunas para os botões

                    with col_aprovar:
                        if st.button(
                            f"✅ Aprovar entregas",
                            key=f"btn_aprovar_{cliente}",
                            disabled=not is_user_aprovador # Desabilita se o usuário não é aprovador
                        ):
                            try:
                                with st.spinner("✅ Aprovando entregas e movendo para Pré-Roteirização..."):
                                    df_aprovar = pd.DataFrame(selecionadas)
                                    # Remove AgGrid internal info
                                    df_aprovar = pd.DataFrame(selecionadas)
                                    # Remove AgGrid internal info
                                    df_aprovar = df_aprovar.drop(columns=["_selectedRowNodeInfo"], errors="ignore")

                                    # --- INÍCIO DO NOVO TRATAMENTO ROBUSTO DE DATAS PARA SUPABASE (APROVAR) ---

                                    # Step 1: Ensure date columns from AgGrid selection (strings in Brazilian format)
                                    # are properly parsed into Pandas Timestamp objects.
                                    for col_name in GLOBAL_DATE_DISPLAY_COLUMNS:
                                        if col_name in df_aprovar.columns:
                                            df_aprovar[col_name] = pd.to_datetime(
                                                df_aprovar[col_name],
                                                format=DATE_DISPLAY_FORMAT_STRING, # Brazilian format (DD-MM-AAAA HH:MM:SS)
                                                errors='coerce' # Convert unparseable values to pd.NaT
                                            )

                                    # Step 2: Iterate through all columns and convert any Pandas Timestamp or
                                    # standard Python datetime.datetime objects to ISO 8601 strings.
                                    # This catches cases where dtype might be 'object' but contains datetime objects.
                                    for col_name in df_aprovar.columns:
                                        # Only process columns that potentially contain datetime objects
                                        # or are explicitly marked as date columns.
                                        if col_name in GLOBAL_DATE_DISPLAY_COLUMNS or \
                                           pd.api.types.is_datetime64_any_dtype(df_aprovar[col_name]):
                                            df_aprovar[col_name] = df_aprovar[col_name].apply(
                                                lambda x: x.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(x) else None
                                            )
                                        # For other 'object' columns that are NOT date columns, ensure they don't contain datetimes
                                        # by attempting conversion if they are actually datetime objects.
                                        elif df_aprovar[col_name].dtype == 'object':
                                            df_aprovar[col_name] = df_aprovar[col_name].apply(
                                                lambda x: x.strftime("%Y-%m-%d %H:%M:%S") if isinstance(x, (pd.Timestamp, datetime)) else x
                                            )

                                    # Step 3: Replace any remaining numpy.nan, numpy.inf, or empty strings with None
                                    # for general compatibility with Supabase. This should be done AFTER date formatting.
                                    df_aprovar = df_aprovar.replace([np.nan, np.inf, -np.inf, ""], None)

                                    # --- FIM DO NOVO TRATAMENTO ROBUSTO DE DATAS PARA SUPABASE (APROVAR) ---

                                    registros_para_pre_roterizacao = df_aprovar.to_dict(orient="records")


                                    # Filter out records without valid primary key (Serie_Numero_CTRC)
                                    registros_para_pre_roterizacao = [r for r in registros_para_pre_roterizacao if r.get("Serie_Numero_CTRC")]

                                    # 1. Inserir os dados na tabela 'pre_roterizacao'
                                    if registros_para_pre_roterizacao:
                                        supabase.table("pre_roterizacao").insert(registros_para_pre_roterizacao).execute()

                                    # 2. Obter as chaves das entregas aprovadas e remover da tabela 'aprovacao_diretoria'
                                    chaves_aprovadas = [r.get("Serie_Numero_CTRC") for r in registros_para_pre_roterizacao if r.get("Serie_Numero_CTRC")]
                                    if chaves_aprovadas:
                                        supabase.table("aprovacao_diretoria").delete().in_("Serie_Numero_CTRC", chaves_aprovadas).execute()

                                    st.success(f"✅ {len(registros_para_pre_roterizacao)} entregas aprovadas e enviadas para Pré-Roteirização.")
                                    
                                    # Invalidate caches to force reload of data
                                    st.session_state["reload_aprovacao_diretoria"] = True # Cache da própria página
                                    st.session_state["reload_pre_roterizacao"] = True # Cache da Pré-Roteirização
                                    
                                    # Clear AgGrid key and checkbox for visual reconstruction
                                    st.session_state.pop(grid_key_id, None)
                                    st.session_state.pop(checkbox_key, None)

                                    st.rerun() # Force a new execution to update the UI

                            except Exception as e:
                                st.error(f"❌ Erro ao aprovar entregas: {e}")

                    with col_rejeitar:
                        if st.button(
                            f"❌ Rejeitar entregas",
                            key=f"btn_rejeitar_{cliente}",
                            disabled=not is_user_aprovador # Desabilita se o usuário não é aprovador
                        ):
                            try:
                                with st.spinner("🔄 Rejeitando entregas e retornando para Confirmar Produção..."):

                                    df_rejeitar = pd.DataFrame(selecionadas)
                                    # Remove AgGrid internal info
                                    df_rejeitar = df_rejeitar.drop(columns=["_selectedRowNodeInfo"], errors="ignore")

                                    # --- INÍCIO DO NOVO TRATAMENTO ROBUSTO DE DATAS PARA SUPABASE (REJEITAR) ---

                                    # Step 1: Ensure date columns from AgGrid selection (strings in Brazilian format)
                                    # are properly parsed into Pandas Timestamp objects.
                                    for col_name in GLOBAL_DATE_DISPLAY_COLUMNS:
                                        if col_name in df_rejeitar.columns:
                                            df_rejeitar[col_name] = pd.to_datetime(
                                                df_rejeitar[col_name],
                                                format=DATE_DISPLAY_FORMAT_STRING, # Brazilian format (DD-MM-AAAA HH:MM:SS)
                                                errors='coerce' # Convert unparseable values to pd.NaT
                                            )

                                    # Step 2: Iterate through all columns and convert any Pandas Timestamp or
                                    # standard Python datetime.datetime objects to ISO 8601 strings.
                                    # This catches cases where dtype might be 'object' but contains datetime objects.
                                    for col_name in df_rejeitar.columns:
                                        # Only process columns that potentially contain datetime objects
                                        # or are explicitly marked as date columns.
                                        if col_name in GLOBAL_DATE_DISPLAY_COLUMNS or \
                                           pd.api.types.is_datetime64_any_dtype(df_rejeitar[col_name]):
                                            df_rejeitar[col_name] = df_rejeitar[col_name].apply(
                                                lambda x: x.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(x) else None
                                            )
                                        # For other 'object' columns that are NOT date columns, ensure they don't contain datetimes
                                        # by attempting conversion if they are actually datetime objects.
                                        elif df_rejeitar[col_name].dtype == 'object':
                                            df_rejeitar[col_name] = df_rejeitar[col_name].apply(
                                                lambda x: x.strftime("%Y-%m-%d %H:%M:%S") if isinstance(x, (pd.Timestamp, datetime)) else x
                                            )

                                    # Step 3: Replace any remaining numpy.nan, numpy.inf, or empty strings with None
                                    # for general compatibility with Supabase. This should be done AFTER date formatting.
                                    df_rejeitar = df_rejeitar.replace([np.nan, np.inf, -np.inf, ""], None)

                                    # --- FIM DO NOVO TRATAMENTO ROBUSTO DE DATAS PARA SUPABASE (REJEITAR) ---

                                    registros_para_confirmar_producao = df_rejeitar.to_dict(orient="records")
                                    # Filter out records without valid primary key (Serie_Numero_CTRC)
                                    registros_para_confirmar_producao = [r for r in registros_para_confirmar_producao if r.get("Serie_Numero_CTRC")]

                                    # 1. Inserir os dados na tabela 'confirmadas_producao'
                                    if registros_para_confirmar_producao:
                                        supabase.table("confirmadas_producao").insert(registros_para_confirmar_producao).execute()

                                    # 2. Obter as chaves das entregas rejeitadas e remover da tabela 'aprovacao_diretoria'
                                    chaves_rejeitadas = [r.get("Serie_Numero_CTRC") for r in registros_para_confirmar_producao if r.get("Serie_Numero_CTRC")]
                                    if chaves_rejeitadas:
                                        supabase.table("aprovacao_diretoria").delete().in_("Serie_Numero_CTRC", chaves_rejeitadas).execute()

                                    st.warning(f"↩️ {len(registros_para_confirmar_producao)} entregas rejeitadas e retornadas para Confirmar Produção.")
                                    
                                    # Invalidate caches to force reload of data
                                    st.session_state["reload_aprovacao_diretoria"] = True # Cache da própria página
                                    st.session_state["reload_confirmadas_producao"] = True # Cache da Confirmar Produção
                                    
                                    # Clear AgGrid key and checkbox for visual reconstruction
                                    st.session_state.pop(grid_key_id, None)
                                    st.session_state.pop(checkbox_key, None)

                                    st.rerun() # Force a new execution to update the UI

                            except Exception as e:
                                st.error(f"❌ Erro ao rejeitar entregas: {e}")



##########################################

# Função PÁGINA PRÉ ROTERIZAÇÃO
##########################################
def pagina_pre_roterizacao():
    st.markdown("## Pré-Roteirização")

    with st.spinner("🔄 Carregando dados das entregas..."):
        try:
            # Reutiliza a lógica de cache ou recarrega do Supabase
            recarregar = st.session_state.pop("reload_pre_roterizacao", False)
            if recarregar or "df_pre_roterizacao_cache" not in st.session_state:
                df = carregar_base_supabase()
                dados_confirmados_raw = supabase.table("rotas_confirmadas").select("Serie_Numero_CTRC").execute().data
                dados_confirmados = pd.DataFrame(dados_confirmados_raw)
                st.session_state["df_pre_roterizacao_cache"] = df
                st.session_state["dados_confirmados_cache"] = dados_confirmados # Cachear também os confirmados
            else:
                df = st.session_state["df_pre_roterizacao_cache"]
                dados_confirmados = st.session_state["dados_confirmados_cache"]


        except Exception as e:
            st.error(f"Erro ao consultar as tabelas do Supabase: {e}")
            return

        if df is None or df.empty:
            st.info("Nenhuma entrega disponível.")
            return

        if not dados_confirmados.empty:
            df = df[~df["Serie_Numero_CTRC"].isin(dados_confirmados["Serie_Numero_CTRC"].astype(str))]
            
        if df.empty: # Verifica novamente se o DF ficou vazio após o filtro
            st.info("Nenhuma entrega disponível para pré-roterização após filtragem.")
            return


    col1, col2, _ = st.columns([1, 1, 8])
    with col1:
        st.metric("Total de Rotas", df["Rota"].nunique() if "Rota" in df.columns else 0)
    with col2:
        st.metric("Total de Entregas", len(df))

    def badge(label):
        return f"<span style='background:#eef2f7;border-radius:12px;padding:6px 12px;margin:4px;color:inherit;display:inline-block;'>{label}</span>"

    colunas_exibir = [
        "Serie_Numero_CTRC", "Rota", "Regiao", "Valor do Frete", "Cliente Pagador", "Chave CT-e", "Cliente Destinatario",
        "Cidade de Entrega", "Bairro do Destinatario", "Previsao de Entrega", "Numero da Nota Fiscal",
        "Status", "Entrega Programada", "Particularidade", "Codigo da Ultima Ocorrencia",
        "Peso Real em Kg", "Peso Calculado em Kg", "Cubagem em m³", "Quantidade de Volumes"
    ]

    linha_destacar = JsCode("""
        function(params) {
            const status = params.data['Status'];
            const entrega = params.data['Entrega Programada'];
            const particularidade = params.data['Particularidade'];
            if (status === 'AGENDAR' && (!entrega || entrega.trim() === '')) {
                return { 'background-color': '#ffe0b2', 'color': '#333' };
            }
            if (particularidade && particularidade.trim() !== "") {
                return { 'background-color': '#fff59d', 'color': '#333' };
            }
            return null;
        }
    """)

    for rota in sorted(df["Rota"].dropna().unique()):
        df_rota = df[df["Rota"] == rota].copy()
        if df_rota.empty:
            continue

        st.markdown(f"""
        <div style="margin-top:20px;padding:10px;background:#e8f0fe;border-left:4px solid #4285f4;border-radius:6px;display:inline-block;max-width:100%;">
            <strong>Rota:</strong> {rota}
        </div>
        """, unsafe_allow_html=True)

        st.markdown(
            badge(f"{len(df_rota)} entregas") +
            badge(f"{formatar_brasileiro(df_rota['Peso Calculado em Kg'].sum())} kg calc") +
            badge(f"{formatar_brasileiro(df_rota['Peso Real em Kg'].sum())} kg real") +
            badge(f"R$ {formatar_brasileiro(df_rota['Valor do Frete'].sum())}") +
            badge(f"{formatar_brasileiro(df_rota['Cubagem em m³'].sum())} m³") +
            badge(f"{int(df_rota['Quantidade de Volumes'].sum())} volumes"),
            unsafe_allow_html=True
        )

        with st.expander("🔽 Selecionar entregas", expanded=False):
            # NOVO: Checkbox "Marcar todas" dentro do expander
            checkbox_key = f"marcar_todas_pre_rota_{rota}"
            if checkbox_key not in st.session_state:
                st.session_state[checkbox_key] = False
            marcar_todas = st.checkbox("Marcar todas", key=checkbox_key)

            df_formatado = apply_brazilian_date_format_for_display(df_rota[[col for col in colunas_exibir if col in df_rota.columns]].copy())

            gb = GridOptionsBuilder.from_dataframe(df_formatado)
            gb.configure_default_column(minWidth=150)
            gb.configure_selection("multiple", use_checkbox=True)
            gb.configure_grid_options(paginationPageSize=12)
            gb.configure_grid_options(alwaysShowHorizontalScroll=True)
            gb.configure_grid_options(rowStyle={'font-size': '11px'})
            gb.configure_grid_options(onGridReady=GRID_RESIZE_JS_CODE) # <<< ADICIONADO AQUI
            grid_options = gb.build()
            grid_options["getRowStyle"] = linha_destacar

            grid_key = f"grid_pre_rota_{rota}"
            # Mantém a key constante a menos que os dados subjacentes mudem, não forcando novo UUID
            if grid_key not in st.session_state:
                st.session_state[grid_key] = str(uuid.uuid4())


            grid_response = AgGrid(
                df_formatado,
                gridOptions=grid_options,
                # AJUSTE AQUI: MUDANÇA DE MANUAL PARA SELECTION_CHANGED
                update_mode=GridUpdateMode.SELECTION_CHANGED, 
                fit_columns_on_grid_load=False,
                width="100%",
                height=400,
                allow_unsafe_jscode=True,
                key=st.session_state[grid_key],
                data_return_mode="AS_INPUT",
                theme=AgGridTheme.MATERIAL,
                show_toolbar=False,
                custom_css={
                    ".ag-theme-material .ag-cell": {
                        "font-size": "11px",
                        "line-height": "18px",
                        "border-right": "1px solid #ccc",
                    },
                    ".ag-theme-material .ag-row:last-child .ag-cell": {
                        "border-bottom": "1px solid #ccc",
                    },
                    ".ag-theme-material .ag-header-cell": {
                        "border-right": "1px solid #ccc",
                        "border-bottom": "1px solid #ccc",
                    },
                    ".ag-theme-material .ag-root-wrapper": {
                        "border": "1px solid black",
                        "border-radius": "6px",
                        "padding": "4px",
                    },
                    ".ag-theme-material .ag-header-cell-label": {
                        "font-size": "11px",
                    },
                    ".ag-center-cols-viewport": {
                        "overflow-x": "auto !important",
                        "overflow-y": "hidden",
                    },
                    ".ag-center-cols-container": {
                        "min-width": "100% !important",
                    },
                    "#gridToolBar": {
                        "padding-bottom": "0px !important",
                    }
                }
            )
            # Lógica ajustada para considerar o checkbox "Marcar todas"
            if marcar_todas:
                selecionadas = df_formatado[df_formatado["Serie_Numero_CTRC"].notna()].copy()
            else:
                selecionadas = pd.DataFrame(grid_response.get("selected_rows", []))

            st.markdown(f"**📦 Entregas selecionadas:** {len(selecionadas)}")

            if not selecionadas.empty: # BOTÃO AGORA SÓ APARECE SE TIVER SELEÇÃO
                if st.button(f"🚀 Confirmar entregas da Rota", key=f"btn_pre_rota_{rota}"):
                    try: # <-- Corrigido: 'try' deve estar na mesma indentação do 'if st.button'
                        df_confirmar = selecionadas.drop(columns=["_selectedRowNodeInfo"], errors="ignore").copy()
                        df_confirmar["Rota"] = rota

                        # --- INÍCIO DA LÓGICA MODIFICADA PARA TRATAMENTO DE DATAS ---
                        # Lista de todas as colunas que podem conter dados de data/hora
                        date_cols_to_process = [
                            "Previsao de Entrega",
                            "Entrega Programada",
                            "Data de Emissao",
                            "Data de Autorizacao",
                            "Data do Cancelamento",
                            "Data do Escaneamento",
                            "Data da Entrega Realizada",
                            "Data da Ultima Ocorrencia",
                            "Data de inclusao da Ultima Ocorrencia"
                            # Adicione aqui qualquer outra coluna de data/hora relevante
                        ]

                        for col_name in date_cols_to_process:
                            if col_name in df_confirmar.columns:
                                # Passo 1: Tenta converter a coluna para tipo datetime.
                                # Erros (como strings vazias, NaNs, etc.) serão convertidos para pd.NaT.
                                df_confirmar[col_name] = pd.to_datetime(df_confirmar[col_name], errors='coerce')

                                # Passo 2: Itera sobre a coluna para converter pd.NaT para None
                                # e formatar as datas válidas para a string esperada pelo banco.
                                df_confirmar[col_name] = df_confirmar[col_name].apply(
                                    lambda x: x.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(x) else None
                                )
                        # --- FIM DA LÓGICA MODIFICADA PARA TRATAMENTO DE DATAS ---

                        # Agora, trate outros NaN/Inf que não sejam de colunas de data/hora.
                        # Para colunas de data/hora, o pd.NaT já foi convertido para None acima.
                        df_confirmar = df_confirmar.replace([np.nan, np.inf, -np.inf], None)

                        registros = df_confirmar.to_dict(orient="records")
                        registros = [r for r in registros if r.get("Serie_Numero_CTRC")]

                        supabase.table("rotas_confirmadas").insert(registros).execute()
                        chaves = [r["Serie_Numero_CTRC"] for r in registros]
                        supabase.table("pre_roterizacao").delete().in_("Serie_Numero_CTRC", chaves).execute() # <-- Esta linha está correta aqui

                        # Limpa o estado da sessão para forçar a recarga dos grids e evitar problemas de cache.
                        st.session_state["reload_pre_roterizacao"] = True
                        # AJUSTE AQUI: ADICIONA FLAG PARA RECARREGAR ROTAS CONFIRMADAS
                        st.session_state["reload_rotas_confirmadas"] = True
                        st.session_state.pop(grid_key, None)
                        st.session_state.pop(checkbox_key, None)


                        st.success(f"✅ {len(chaves)} entregas da Rota {rota} foram confirmadas com sucesso.")
                        st.rerun()
                    except Exception as e: # <-- Corrigido: 'except' deve estar na mesma indentação do 'try'
                        st.error(f"❌ Erro ao confirmar entregas da rota {rota}: {e}")

##########################################

# PÁGINA ROTAS CONFIRMADAS

#########################################

def pagina_rotas_confirmadas():
    st.markdown("## Rotas Confirmadas")

    # --- INÍCIO: BLOCO DE CRIAÇÃO DE CARGA AVULSA (SEMPRE VISÍVEL E INTERATIVO) ---
    chaves_input = "" # Inicializa para ser usado no text_area

    if "nova_carga_em_criacao" not in st.session_state:
        st.session_state["nova_carga_em_criacao"] = False
        st.session_state["numero_nova_carga"] = ""

    # Se NÃO está em criação de carga, mostra o botão "Criar Nova Carga Avulsa"
    if not st.session_state["nova_carga_em_criacao"]:
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🆕 Criar Nova Carga Avulsa"):
                try:
                    numero_carga = gerar_proximo_numero_carga(supabase)
                    if numero_carga:
                        st.session_state["nova_carga_em_criacao"] = True
                        st.session_state["numero_nova_carga"] = numero_carga
                        st.rerun() # Força rerun para exibir a nova interface de adição
                except Exception as e:
                    st.error(f"Erro ao criar nova carga: {e}")
    # Se JÁ está em criação de carga, mostra a interface para adicionar chaves CT-e
    else:
        st.success(f"Nova Carga Criada: {st.session_state['numero_nova_carga']}")
        st.markdown("### Inserir Entregas na Carga")
        chaves_input = st.text_area("Insira as Chaves CT-e (uma por linha)")

        col1, col2 = st.columns([5, 1])
        with col1:
            adicionar = st.button("🚛 Adicionar Entregas à Carga", key="botao_manual")
        with col2:
            cancelar = st.button("❌", help="Cancelar Nova Carga")

        if cancelar:
            st.session_state["nova_carga_em_criacao"] = False
            st.session_state["numero_nova_carga"] = ""
            st.rerun()

        if adicionar:
            try:
                chaves = [re.sub(r"\s+", "", c) for c in chaves_input.splitlines() if c.strip()]
                if not chaves:
                    st.warning("Nenhuma Chave CT-e válida informada.")
                else: # APENAS PROSSIGA SE HOUVER CHAVES VÁLIDAS
                    entregas_encontradas = []

                def detectar_coluna_chave(tabela):
                    dados = supabase.table(tabela).select("*").limit(1).execute().data
                    if not dados:
                        return None
                    return next((k for k in dados[0].keys() if "chave" in k.lower() and "ct" in k.lower()), None)


                # Buscar todos os dados uma única vez para maior controle
                dados_rotas = supabase.table("rotas_confirmadas").select("*").execute().data
                dados_pre = supabase.table("pre_roterizacao").select("*").execute().data
                dados_aprovacao_diretoria = supabase.table("aprovacao_diretoria").select("*").execute().data # NOVO: Buscar dados da Aprovação Diretoria
                
                # 🔎 Buscar entregas já atribuídas a cargas
                dados_cargas = supabase.table("cargas_geradas").select("*").execute().data

                entregas_ja_em_carga = {}

                for d in dados_cargas:
                    d = {k.strip(): v for k, v in d.items()}  # limpa nomes de colunas

                    chave_cte = str(d.get("Chave CT-e", "")).strip()
                    serie_ctr = str(d.get("Serie_Numero_CTRC", "")).strip()
                    numero_carga = d.get("numero_carga")

                    if chave_cte:
                        entregas_ja_em_carga[chave_cte] = numero_carga
                    if serie_ctr:
                        entregas_ja_em_carga[serie_ctr] = numero_carga             

                chaves_inseridas_com_sucesso = [] # Para armazenar as chaves que foram realmente inseridas


                for chave in chaves:
                    try:
                        origem = None
                        entrega = None

                        # Verificar se a chave já está em alguma carga (manter como está)
                        if chave in entregas_ja_em_carga:
                            st.warning(f"⚠️ A entrega com chave '{chave}' já está na carga {entregas_ja_em_carga[chave]}.")
                            continue

                        # Padroniza o nome da coluna Chave CT-e para busca
                        chave_ct_e_col_name = "Chave CT-e" 

                        # 1. Buscar em rotas_confirmadas
                        dados = [d for d in dados_rotas if str(d.get(chave_ct_e_col_name, "")).strip() == chave]
                        if dados:
                            origem = "rotas_confirmadas"
                            entrega = dados[0]
                            entrega.pop("id", None) # Remove 'id' se existir

                        else:
                            # 2. Buscar em pre_roterizacao
                            dados = [d for d in dados_pre if str(d.get(chave_ct_e_col_name, "")).strip() == chave]
                            if dados:
                                origem = "pre_roterizacao"
                                entrega = dados[0]
                                entrega.pop("id", None) # Remove 'id' se existir
                            
                            else:
                                # 3. Buscar em aprovacao_diretoria (NOVO)
                                dados = [d for d in dados_aprovacao_diretoria if str(d.get(chave_ct_e_col_name, "")).strip() == chave]
                                if dados:
                                    origem = "aprovacao_diretoria"
                                    entrega = dados[0]
                                    entrega.pop("id", None) # Remove 'id' se existir


                        if not entrega:
                            st.warning(f"⚠️ Chave {chave} não encontrada em nenhuma das tabelas de origem ou já foi processada.")
                            continue
                        
                        # --- NOVO: Obtém o Serie_Numero_CTRC para exclusão/inserção ---
                        # Usar Serie_Numero_CTRC como o identificador principal para garantir consistência
                        serie_numero_ctrc_para_excluir = str(entrega.get('Serie_Numero_CTRC', '')).strip()
                        if not serie_numero_ctrc_para_excluir:
                            st.warning(f"⚠️ Entrega com Chave CT-e '{chave}' não possui Serie_Numero_CTRC válido. Ignorando.")
                            continue # Pula esta entrega se não tiver um Serie_Numero_CTRC

                        # Prepara a entrega para inserção em cargas_geradas
                        entrega["numero_carga"] = st.session_state["numero_nova_carga"]
                        entrega["Data_Hora_Gerada"] = data_hora_brasil_iso()
                        
                        # Limpa valores que podem causar problemas na inserção (NaN, NaT, objetos complexos)
                        # Este é o bloco de tratamento de valores para Supabase
                        entrega_limpa = {k: (
                            v.isoformat() if isinstance(v, (pd.Timestamp, datetime, date)) else # Converte datas para ISO
                            None if (isinstance(v, float) and (np.isnan(v) or np.isinf(v))) or pd.isna(v) else # Float NaN/Inf ou Pandas NaT para None
                            str(v) if isinstance(v, (dict, list)) else # Converte dict/list para string (se não forem JSON válidos)
                            v
                        ) for k, v in entrega.items()}

                        # 🔒 Colunas válidas para serem inseridas em cargas_geradas (manter como está no seu código)
                        colunas_validas = [
                            'Serie_Numero_CTRC', 'Rota', 'Regiao', 'Cliente Pagador', 'Chave CT-e', 'Cliente Destinatario',
                            'Cidade de Entrega', 'Bairro do Destinatario', 'Previsao de Entrega',
                            'Numero da Nota Fiscal', 'Status', 'Entrega Programada', 'Particularidade',
                            'Codigo da Ultima Ocorrencia', 'Peso Real em Kg', 'Peso Calculado em Kg',
                            'Cubagem em m³', 'Quantidade de Volumes', 'Valor do Frete',
                            'numero_carga', 'Data_Hora_Gerada'
                        ]

                        entrega_filtrada = {k: v for k, v in entrega_limpa.items() if k in colunas_validas}

                        # Tenta inserir no Supabase
                        insert_response = supabase.table("cargas_geradas").insert(entrega_filtrada).execute()
                        
                        if insert_response.error: # Verifica se a inserção falhou
                            st.error(f"Erro ao inserir {serie_numero_ctrc_para_excluir} na tabela 'cargas_geradas': {insert_response.error}")
                            continue # Se a inserção falhou, não tenta deletar e passa para a próxima chave
                        else:
                            # st.info(f"DEBUG: Inserido {serie_numero_ctrc_para_excluir} em cargas_geradas.") # Para depuração
                            entregas_encontradas.append(entrega) # Adiciona apenas se a inserção foi bem-sucedida
                            chaves_inseridas_com_sucesso.append(serie_numero_ctrc_para_excluir) # Usar o Serie_Numero_CTRC aqui

                        # --- MODIFICADO: Remove da tabela de origem usando Serie_Numero_CTRC ---
                        delete_response = None # Inicializa para capturar a resposta do delete
                        if origem == "rotas_confirmadas":
                            delete_response = supabase.table(origem).delete().eq("Serie_Numero_CTRC", serie_numero_ctrc_para_excluir).execute()
                            
                        elif origem == "pre_roterizacao":
                            delete_response = supabase.table(origem).delete().eq("Serie_Numero_CTRC", serie_numero_ctrc_para_excluir).execute()
                            
                        elif origem == "aprovacao_diretoria": # NOVO: Excluir da Aprovação da Diretoria
                            delete_response = supabase.table(origem).delete().eq("Serie_Numero_CTRC", serie_numero_ctrc_para_excluir).execute()

                        if delete_response and delete_response.error:
                             st.error(f"Erro ao deletar {serie_numero_ctrc_para_excluir} de {origem}: {delete_response.error}")
                            
                    except Exception as e_inner:
                        st.error(f"Erro geral ao processar chave '{chave}': {e_inner}")

                # ... (restante do código, incluindo as invalidações de cache e st.rerun() - como definido na correção anterior) ...
                if entregas_encontradas:
                    st.success(f"✅ {len(entregas_encontradas)} entrega(s) adicionada(s) à carga {st.session_state['numero_nova_carga']} com sucesso.")

                    # Limpa o estado da carga criada para voltar à visualização normal
                st.success(f"Operação de adição manual concluída!") # Exemplo de sucesso
                st.session_state["nova_carga_em_criacao"] = False # Volta para o estado inicial
                st.session_state["numero_nova_carga"] = ""
                st.session_state["reload_rotas_confirmadas"] = True # Recarrega as rotas confirmadas
                st.session_state["reload_cargas_geradas"] = True # Recarrega as cargas geradas
                st.session_state["reload_pre_roterizacao"] = True
                st.session_state["reload_aprovacao_diretoria"] = True

                st.rerun() # Força o rerun

            except Exception as e:
                st.error(f"Erro ao adicionar entregas manualmente: {e}")

            try:
                with st.spinner("�� Carregando dados das entregas..."):
                    recarregar = st.session_state.pop("reload_rotas_confirmadas", False)
                    if recarregar or "df_rotas_confirmadas_cache" not in st.session_state:          
                        data_from_supabase = supabase.table("rotas_confirmadas").select("*").execute().data
                        df = pd.DataFrame(data_from_supabase)
                        st.session_state["df_rotas_confirmadas_cache"] = df
                    else:
                        df = st.session_state["df_rotas_confirmadas_cache"]
            except Exception as e:
                st.error(f"❌ Erro ao carregar as Rotas Confirmadas: {e}")
                df = pd.DataFrame() 

            if df.empty:
                st.info("🛈 Nenhuma Rota Confirmada encontrada. Sincronize os dados e confirme as entregas na seção 'Pré-Roterização'.")
                #return # Retorna aqui para não renderizar o restante da página (métricas, grids, etc.) se não houver dados.
            # --- FIM: CARREGAMENTO DOS DADOS ---

            # ... (restante do código de pagina_rotas_confirmadas, que processa e exibe o df) ...
            col1, col2, _ = st.columns([1, 1, 8])
            with col1:
                st.metric("Total de Rotas", df["Rota"].nunique() if "Rota" in df.columns else 0)
            with col2:
                st.metric("Total de Entregas", len(df))


        def badge(label):
            return f"<span style='background:#eef2f7;border-radius:12px;padding:6px 12px;margin:4px;color:inherit;display:inline-block;'>{label}</span>"

        colunas_exibir = [
            "Serie_Numero_CTRC", "Rota", "Regiao","Valor do Frete", "Cliente Pagador", "Chave CT-e", "Cliente Destinatario",
            "Cidade de Entrega", "Bairro do Destinatario", "Previsao de Entrega",
            "Numero da Nota Fiscal", "Status", "Entrega Programada", "Particularidade",
            "Codigo da Ultima Ocorrencia", "Peso Real em Kg", "Peso Calculado em Kg",
            "Cubagem em m³", "Quantidade de Volumes"
        ]

        linha_destacar = JsCode("""
            function(params) {
                const status = params.data['Status'];
                const entrega = params.data['Entrega Programada'];
                const particularidade = params.data['Particularidade'];
                if (status === 'AGENDAR' && (!entrega || entrega.trim() === '')) {
                    return { 'background-color': '#ffe0b2', 'color': '#333' };
                }
                if (particularidade && particularidade.trim() !== "") {
                    return { 'background-color': '#fff59d', 'color': '#333' };
                }
                return null;
            }
        """)

        rotas_unicas = sorted(df["Rota"].dropna().unique())
        # st.write(f"DEBUG: Rotas únicas a serem exibidas: {rotas_unicas}") # DEBUG

        for rota in rotas_unicas:
            df_rota = df[df["Rota"] == rota].copy()
            if df_rota.empty:
                # st.info(f"DEBUG: df_rota para {rota} está vazia, pulando.") # DEBUG
                continue

            st.markdown(f"""
            <div style="margin-top:20px;padding:10px;background:#e8f0fe;border-left:4px solid #4285f4;border-radius:6px;display:inline-block;max-width:100%;">
                <strong>Rota:</strong> {rota}
            </div>
            """, unsafe_allow_html=True)

            st.markdown(
                badge(f"{len(df_rota)} entregas") +
                badge(f"{formatar_brasileiro(df_rota['Peso Calculado em Kg'].sum())} kg calc") +
                badge(f"{formatar_brasileiro(df_rota['Peso Real em Kg'].sum())} kg real") +
                badge(f"R$ {formatar_brasileiro(df_rota['Valor do Frete'].sum())}") +
                badge(f"{formatar_brasileiro(df_rota['Cubagem em m³'].sum())} m³") +
                badge(f"{int(df_rota['Quantidade de Volumes'].sum())} volumes"),
                unsafe_allow_html=True
            )

            with st.expander("🔽 Selecionar entregas", expanded=False):
                df_formatado = apply_brazilian_date_format_for_display(df_rota[[col for col in colunas_exibir if col in df_rota.columns]].copy())

                # NOVO: Checkbox "Marcar todas" dentro do expander
                checkbox_key = f"marcar_todas_rota_confirmada_{rota}"
                if checkbox_key not in st.session_state:
                    st.session_state[checkbox_key] = False
                marcar_todas = st.checkbox("Marcar todas", key=checkbox_key)


                gb = GridOptionsBuilder.from_dataframe(df_formatado)
                gb.configure_default_column(minWidth=150)
                gb.configure_selection("multiple", use_checkbox=True)
                gb.configure_grid_options(paginationPageSize=12)
                gb.configure_grid_options(alwaysShowHorizontalScroll=True)
                gb.configure_grid_options(rowStyle={"font-size": "11px"})
                gb.configure_grid_options(getRowStyle=linha_destacar)
                gb.configure_grid_options(headerCheckboxSelection=True)
                gb.configure_grid_options(rowSelection='multiple')
                gb.configure_grid_options(onGridReady=GRID_RESIZE_JS_CODE) # <<< ADICIONADO AQUI

                formatter = JsCode("""
                    function(params) {
                        if (!params.value) return '';
                        return Number(params.value).toLocaleString('pt-BR', {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2
                        });
                    }
                """)

                for col in ['Peso Real em Kg', 'Peso Calculado em Kg', 'Cubagem em m³', 'Quantidade de Volumes', 'Valor do Frete']:
                    if col in df_formatado.columns:
                        gb.configure_column(col, type=["numericColumn"], valueFormatter=formatter)

                grid_options = gb.build()
                grid_key = f"grid_rotas_confirmadas_{rota}"
                if grid_key not in st.session_state:
                    st.session_state[grid_key] = str(uuid.uuid4())

                with st.spinner("🔄 Carregando entregas da rota no grid..."):
                    grid_response = AgGrid(
                        df_formatado,
                        gridOptions=grid_options,
                        update_mode=GridUpdateMode.SELECTION_CHANGED,
                        fit_columns_on_grid_load=False,
                        width="100%",
                        height=400,
                        allow_unsafe_jscode=True,
                        key=st.session_state[grid_key],
                        data_return_mode="AS_INPUT",
                        theme=AgGridTheme.MATERIAL,
                        show_toolbar=False,
                        custom_css={
                            ".ag-theme-material .ag-cell": {
                                "font-size": "11px",
                                "line-height": "18px",
                                "border-right": "1px solid #ccc",
                            },
                            ".ag-theme-material .ag-row:last-child .ag-cell": {
                                "border-bottom": "1px solid #ccc",
                            },
                            ".ag-theme-material .ag-header-cell": {
                                "border-right": "1px solid #ccc",
                                "border-bottom": "1px solid #ccc",
                            },
                            ".ag-theme-material .ag-root-wrapper": {
                                "border": "1px solid black",
                                "border-radius": "6px",
                                "padding": "4px",
                            },
                            ".ag-theme-material .ag-header-cell-label": {
                                "font-size": "11px",
                            },
                            ".ag-center-cols-viewport": {
                                "overflow-x": "auto !important",
                                "overflow-y": "hidden",
                            },
                            ".ag-center-cols-container": {
                                "min-width": "100% !important",
                            },
                            "#gridToolBar": {
                                "padding-bottom": "0px !important",
                            }
                        }
                    )

                # Lógica ajustada para considerar o checkbox "Marcar todas"
                if marcar_todas:
                    selecionadas = df_formatado[df_formatado["Serie_Numero_CTRC"].notna()].copy().to_dict(orient="records")
                else:
                    selecionadas = grid_response.get("selected_rows", [])

                if selecionadas:
                    st.info(f"{len(selecionadas)} entrega(s) selecionada(s) para a rota {rota}.")

                # 🔸 Botão para criar nova carga automaticamente
                if st.button(f"➕ Criar Nova Carga com Entregas Selecionadas", key=f"botao_rota_{rota}"):
                    if not selecionadas:
                        st.warning("Selecione ao menos uma entrega.")
                    else:
                        try:
                            #st.info("DEBUG: Tentando criar nova carga com entregas selecionadas.") # DEBUG
                            df_selecionadas = pd.DataFrame(selecionadas)
                            chaves = df_selecionadas["Serie_Numero_CTRC"].dropna().astype(str).str.strip().tolist()

                            df_rota["Serie_Numero_CTRC"] = df_rota["Serie_Numero_CTRC"].astype(str).str.strip()
                            df_confirmar = df_rota[df_rota["Serie_Numero_CTRC"].isin(chaves)].copy()
                            df_confirmar = df_confirmar.replace([np.nan, np.inf, -np.inf], None)

                            for col in df_confirmar.select_dtypes(include=['datetime64[ns]']).columns:
                                df_confirmar[col] = df_confirmar[col].dt.strftime('%Y-%m-%d %H:%M:%S')

                            numero_carga = gerar_proximo_numero_carga(supabase)
                            df_confirmar["numero_carga"] = numero_carga
                            df_confirmar["Data_Hora_Gerada"] = data_hora_brasil_iso() # CORRIGIDO AQUI
                            

                            colunas_validas = [
                                'Serie_Numero_CTRC', 'Rota', 'Regiao', 'Cliente Pagador', 'Chave CT-e', 'Cliente Destinatario',
                                'Cidade de Entrega', 'Bairro do Destinatario', 'Previsao de Entrega',
                                'Numero da Nota Fiscal', 'Status', 'Entrega Programada', 'Particularidade',
                                'Codigo da Ultima Ocorrencia', 'Peso Real em Kg', 'Peso Calculado em Kg',
                                'Cubagem em m³', 'Quantidade de Volumes', 'Valor do Frete',
                                'numero_carga', 'Data_Hora_Gerada'
                            ]


                            dados_filtrados = df_confirmar[[col for col in colunas_validas if col in df_confirmar.columns]].to_dict(orient="records")
                            
                            if not dados_filtrados:
                                st.warning("DEBUG: Nenhum dado filtrado para inserir na carga.") # DEBUG
                                return


                            for tentativa in range(2):
                                try:
                                    resultado_insercao = supabase.table("cargas_geradas").insert(dados_filtrados).execute()
                                    #st.info(f"DEBUG: Tentativa {tentativa+1} - Inserção em 'cargas_geradas' bem-sucedida.") # DEBUG
                                    break
                                except Exception as e:
                                    if tentativa == 1:
                                        raise e
                                    st.warning("Erro temporário ao inserir. Tentando novamente em 2s...")
                                    time.sleep(2)

                            chaves_inseridas = [
                                str(item.get("Serie_Numero_CTRC")).strip()
                                for item in resultado_insercao.data
                                if item.get("Serie_Numero_CTRC")
                            ]

                            if set(chaves_inseridas) == set(chaves):
                                #st.info("DEBUG: Chaves inseridas correspondem às selecionadas. Deletando de 'rotas_confirmadas'.") # DEBUG
                                for tentativa in range(2):
                                    try:
                                        supabase.table("rotas_confirmadas").delete().in_("Serie_Numero_CTRC", chaves_inseridas).execute()
                                        #st.info(f"DEBUG: Tentativa {tentativa+1} - Deleção de 'rotas_confirmadas' bem-sucedida.") # DEBUG
                                        break
                                    except Exception as e:
                                        if tentativa == 1:
                                            raise e
                                        st.warning("Erro temporário ao remover entregas. Tentando novamente em 2s...")
                                        time.sleep(2)

                                st.success(f"✅ {len(chaves_inseridas)} entrega(s) adicionada(s) à carga {numero_carga}.")

                                # Força recarga dos caches para que as tabelas reflitam as mudanças
                                st.session_state["reload_rotas_confirmadas"] = True
                                st.session_state["reload_cargas_geradas"] = True
                                # Limpa keys dos grids para forçar reconstrução se necessário
                                st.session_state.pop(grid_key, None)
                                st.session_state.pop(checkbox_key, None) # Limpa o estado do checkbox

                                # NENHUM time.sleep() AQUI
                                st.rerun()

                            else:
                                st.warning("Algumas entregas não foram inseridas corretamente.")

                        except Exception as e:
                            st.error(f"Erro ao adicionar rota como carga: {e}")


                #  Botão para adicionar à carga existente
                cargas_existentes = supabase.table("cargas_geradas").select("numero_carga").execute().data
                cargas_disponiveis = sorted(set(item["numero_carga"] for item in cargas_existentes if item.get("numero_carga")))

                if cargas_disponiveis:
                    opcoes_selectbox = ["Selecionar Carga"] + cargas_disponiveis
                    carga_escolhida = st.selectbox(
                        "📦 Selecionar Carga Existente para adicionar as entregas",
                        options=opcoes_selectbox,
                        key=f"selectbox_carga_existente_{rota}"
                    )

                    if st.button(f"➕ Adicionar à Carga {carga_escolhida}", key=f"botao_add_existente_{rota}"):
                        if carga_escolhida == "Selecionar Carga":
                            st.warning("Selecione uma carga válida.")
                        elif not selecionadas:
                            st.warning("Selecione ao menos uma entrega.")
                        else:
                            try:
                                #st.info(f"DEBUG: Tentando adicionar à carga existente {carga_escolhida}.") # DEBUG
                                df_selecionadas = pd.DataFrame(selecionadas)
                                chaves = df_selecionadas["Serie_Numero_CTRC"].dropna().astype(str).str.strip().tolist()

                                df_rota["Serie_Numero_CTRC"] = df_rota["Serie_Numero_CTRC"].astype(str).str.strip()
                                df_confirmar = df_rota[df_rota["Serie_Numero_CTRC"].isin(chaves)].copy()
                                df_confirmar = df_confirmar.replace([np.nan, np.inf, -np.inf], None)

                                for col in df_confirmar.select_dtypes(include=['datetime64[ns]']).columns:
                                    df_confirmar[col] = df_confirmar[col].dt.strftime('%Y-%m-%d %H:%M:%S')

                                df_confirmar["numero_carga"] = carga_escolhida
                                df_confirmar["Data_Hora_Gerada"] = data_hora_brasil_iso() # CORRIGIDO AQUI
                                

                                colunas_validas = [
                                    'Serie_Numero_CTRC', 'Rota', 'Regiao', 'Cliente Pagador', 'Chave CT-e', 'Cliente Destinatario',
                                    'Cidade de Entrega', 'Bairro do Destinatario', 'Previsao de Entrega',
                                    'Numero da Nota Fiscal', 'Status', 'Entrega Programada', 'Particularidade',
                                    'Codigo da Ultima Ocorrencia', 'Peso Real em Kg', 'Peso Calculado em Kg',
                                    'Cubagem em m³', 'Quantidade de Volumes', 'Valor do Frete',
                                    'numero_carga', 'Data_Hora_Gerada'
                                ]


                                dados_filtrados = df_confirmar[[col for col in colunas_validas if col in df_confirmar.columns]].to_dict(orient="records")
                                
                                if not dados_filtrados:
                                    st.warning("DEBUG: Nenhum dado filtrado para adicionar à carga existente.") # DEBUG
                                    return


                                supabase.table("cargas_geradas").insert(dados_filtrados).execute()
                                #st.info(f"DEBUG: Inseridos {len(dados_filtrados)} registros em 'cargas_geradas' para carga existente.") # DEBUG
                                supabase.table("rotas_confirmadas").delete().in_("Serie_Numero_CTRC", chaves).execute()
                                #st.info(f"DEBUG: Removidos {len(chaves)} registros de 'rotas_confirmadas'.") # DEBUG

                                # Força recarga dos caches para que as tabelas reflitam as mudanças
                                st.session_state["reload_rotas_confirmadas"] = True
                                st.session_state["reload_cargas_geradas"] = True
                                st.session_state["reload_pre_roterizacao"] = True # Garante que pré-roterização também recarregue, caso a entrega estivesse lá
                                st.session_state["reload_aprovacao_diretoria"] = True # NOVO: Invalida o cache da Aprovação da Diretoria

                                # Limpa keys dos grids para forçar reconstrução se necessáriof
                                for key_prefix in ["grid_rotas_confirmadas_", "grid_carga_gerada_", "grid_aprovar_"]: # Inclui grids da aprovação
                                    for key in list(st.session_state.keys()):
                                        if key.startswith(key_prefix):
                                            st.session_state.pop(key, None)
                                # NENHUM time.sleep() AQUI
                                st.rerun()

                            except Exception as e:
                                st.error(f"Erro ao adicionar à carga existente: {e}")
                else:
                    st.info("Nenhuma carga existente encontrada para seleção.")




##########################################

# PÁGINA CARGAS GERADAS

##########################################

def pagina_cargas_geradas():
    st.markdown("## Cargas Geradas")

    try:
        with st.spinner(" Carregando dados das cargas..."):
            recarregar = st.session_state.pop("reload_cargas_geradas", False)
            if recarregar or "df_cargas_cache" not in st.session_state:
                dados = supabase.table("cargas_geradas").select("*").execute().data
                df = pd.DataFrame(dados)
                st.session_state["df_cargas_cache"] = df
            else:
                df = st.session_state["df_cargas_cache"]

        if df.empty:
            st.info("Nenhuma carga foi gerada ainda.")
            return

        with st.spinner(" Processando estatísticas e estrutura da página..."):
            df.columns = df.columns.str.strip()

            # --- INÍCIO DA OTIMIZAÇÃO: Pré-processamento do DataFrame completo ---
            # Faça uma cópia para formatar e garantir que não alteramos o cache original
            df_display = df.copy()

            df_display = apply_brazilian_date_format_for_display(df_display)

            # Tratar NaNs e pd.NaT em todo o DataFrame de uma vez
                        # Faça uma cópia para formatar e garantir que não alteramos o cache original
            df_display = df.copy()

            # Aplica o formato brasileiro a todas as colunas de data/hora
            df_display = apply_brazilian_date_format_for_display(df_display)

            # Tratar NaNs restantes em outras colunas (não datas) para exibição como string vazia
            # (pd.NaT já foi tratado para colunas de data pela função acima)
            df_display = df_display.replace([np.nan, None], "")

            # Colunas numéricas para garantir que são números antes do formatter JS
            numeric_cols_for_formatting = ['Peso Real em Kg', 'Peso Calculado em Kg', 'Cubagem em m³', 'Quantidade de Volumes', 'Valor do Frete']
            for col in numeric_cols_for_formatting:
                if col in df_display.columns:
                    # Converte para numérico, tratando erros. Isso é importante para o formatter JS.
                    df_display[col] = pd.to_numeric(df_display[col], errors='coerce').fillna(0) # .fillna(0) para evitar NaNs em cálculos/exibição
            # --- FIM DA OTIMIZAÇÃO ---

        col1, col2, _ = st.columns([1, 1, 8]) # Ajustado para 2 colunas como no padrão geral
        with col1:
            st.metric("Total de Cargas", df["numero_carga"].nunique() if "numero_carga" in df.columns else 0)
        with col2:
            st.metric("Total de Entregas", len(df))

            formatter = JsCode("""
                function(params) {
                    if (!params.value && params.value !== 0) return ''; // Inclui 0 como valor válido
                    return Number(params.value).toLocaleString('pt-BR', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                    });
                }
            """)

            def badge(label):
                return f"<span style='background:#eef2f7;border-radius:12px;padding:6px 12px;margin:4px;color:inherit;display:inline-block;'>{label}</span>"
             # Colunas a serem exibidas no grid para cada carga

            colunas_exibir = [
                "Serie_Numero_CTRC", "Rota", "Regiao", "Valor do Frete", "Cliente Pagador", "Chave CT-e", "Cliente Destinatario",
                "Cidade de Entrega", "Bairro do Destinatario", "Previsao de Entrega",
                "Numero da Nota Fiscal", "Status", "Entrega Programada", "Particularidade",
                "Codigo da Ultima Ocorrencia", "Peso Real em Kg", "Peso Calculado em Kg",
                "Cubagem em m³", "Quantidade de Volumes"
        ]


            cargas_unicas = sorted(df["numero_carga"].dropna().unique())

        for carga in cargas_unicas:
            # Agora, df_carga é uma subseleção de um DataFrame já pré-processado
            df_carga = df_display[df_display["numero_carga"] == carga].copy() # O .copy() ainda é útil aqui para evitar SettingWithCopyWarning

            if df_carga.empty:
                continue

            st.markdown(f"""
            <div style="margin-top:20px;padding:10px;background:#e8f0fe;border-left:4px solid #34a853;border-radius:6px;display:inline-block;max-width:100%;">
                <strong>Carga:</strong> {carga}
            </div>
            """, unsafe_allow_html=True)

            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(
                    badge(f"{len(df_carga)} entregas") +
                    badge(f"{formatar_brasileiro(df_carga['Peso Calculado em Kg'].sum())} kg calc") +
                    badge(f"{formatar_brasileiro(df_carga['Peso Real em Kg'].sum())} kg real") +
                    badge(f"R$ {formatar_brasileiro(df_carga['Valor do Frete'].sum())}") +
                    badge(f"{formatar_brasileiro(df_carga['Cubagem em m³'].sum())} m³") +
                    badge(f"{int(df_carga['Quantidade de Volumes'].sum())} volumes"),
                    unsafe_allow_html=True
                )

            with st.expander("🔽 Ver entregas da carga", expanded=False):
                checkbox_key = f"marcar_todas_carga_gerada_{carga}"
                if checkbox_key not in st.session_state:
                    st.session_state[checkbox_key] = False

                marcar_todas = st.checkbox("Marcar todas", key=checkbox_key)

                with st.spinner("Carregando entregas da carga no grid..."): # Este spinner pode ser removido ou seu tempo reduzido agora
                    # df_formatado agora é apenas uma seleção de colunas do df_carga (que já está limpo e formatado)
                    df_formatado = df_carga[[col for col in colunas_exibir if col in df_carga.columns]]

                    gb = GridOptionsBuilder.from_dataframe(df_formatado)
                    gb.configure_default_column(minWidth=150)
                    gb.configure_selection("multiple", use_checkbox=True)
                    gb.configure_grid_options(paginationPageSize=12)
                    gb.configure_grid_options(alwaysShowHorizontalScroll=True)
                    gb.configure_grid_options(rowStyle={"font-size": "11px"})
                    gb.configure_grid_options(getRowStyle=JsCode("""
                        function(params) {
                            const status = params.data.Status;
                            const entregaProg = params.data["Entrega Programada"];
                            const particularidade = params.data.Particularidade;
                            // A comparação com string vazia aqui é para o JS, o Python já trocou NaT/None para ""
                            if (status === "AGENDAR" && (!entregaProg || entregaProg.trim() === "")) {
                                return { 'background-color': '#ffe0b2', 'color': '#333' };
                            }
                            if (particularidade && particularidade.trim() !== "") {
                                return { 'background-color': '#fff59d', 'color': '#333' };
                            }
                            return null;
                        }
                    """))
                    gb.configure_grid_options(headerCheckboxSelection=True)
                    gb.configure_grid_options(rowSelection='multiple')
                    gb.configure_grid_options(onGridReady=GRID_RESIZE_JS_CODE)

                    # Aplicar formatter às colunas numéricas relevantes
                    for col in numeric_cols_for_formatting: # Usa a lista definida no pré-processamento
                        if col in df_formatado.columns:
                            gb.configure_column(col, type=["numericColumn"], valueFormatter=formatter)

                    grid_options = gb.build()

                    grid_key_id = f"grid_carga_gerada_{carga}"
                    if grid_key_id not in st.session_state:
                        st.session_state[grid_key_id] = str(uuid.uuid4())

                    grid_key = st.session_state[grid_key_id]

                # O AgGrid
                grid_response = AgGrid(
                    df_formatado,
                    gridOptions=grid_options,
                    update_mode=GridUpdateMode.SELECTION_CHANGED,
                    fit_columns_on_grid_load=False,
                    width="100%",
                    height=400,
                    allow_unsafe_jscode=True,
                    key=grid_key,
                    theme=AgGridTheme.MATERIAL,
                    show_toolbar=False,
                    custom_css={
                        ".ag-theme-material .ag-cell": {
                            "font-size": "11px",
                            "line-height": "18px",
                            "border-right": "1px solid #ccc",
                        },
                        ".ag-theme-material .ag-row:last-child .ag-cell": {
                            "border-bottom": "1px solid #ccc",
                        },
                        ".ag-theme-material .ag-header-cell": {
                            "border-right": "1px solid #ccc",
                            "border-bottom": "1px solid #ccc",
                        },
                        ".ag-theme-material .ag-root-wrapper": {
                            "border": "1px solid black",
                            "border-radius": "6px",
                            "padding": "4px",
                        },
                        ".ag-theme-material .ag-header-cell-label": {
                            "font-size": "11px",
                        },
                        ".ag-center-cols-viewport": {
                            "overflow-x": "auto !important",
                            "overflow-y": "hidden",
                        },
                        ".ag-center-cols-container": {
                            "min-width": "100% !important",
                        },
                        "#gridToolBar": {
                            "padding-bottom": "0px !important",
                        }
                    }
                )
                # Lógica ajustada para considerar o checkbox "Marcar todas"
                if marcar_todas:
                    selecionadas = df_formatado[df_formatado["Serie_Numero_CTRC"].notna()].copy().to_dict(orient="records")
                else:
                    selecionadas = grid_response.get("selected_rows", [])

                if selecionadas:
                    col_ret, col_aprov = st.columns([1, 1])

                    with col_ret:
                        if st.button(f"♻️ Retirar da Carga", key=f"btn_retirar_{carga}"):
                            try:
                                with st.spinner("🔄 Retirando entregas da carga..."):
                                    df_remover = pd.DataFrame(selecionadas)
                                    df_remover = df_remover.drop(columns=["_selectedRowNodeInfo"], errors="ignore")
                                    df_remover["Status"] = "AGENDAR"
                                    df_remover = df_remover.drop(columns=["numero_carga"], errors="ignore")

                                    # Se Data_Hora_Gerada é uma string formatada, precisamos convertê-la para ISO para Supabase
                                    if "Data_Hora_Gerada" in df_remover.columns:
                                        df_remover["Data_Hora_Gerada"] = df_remover["Data_Hora_Gerada"].apply(
                                            lambda x: datetime.strptime(x, "%d-%m-%Y %H:%M:%S").isoformat() if x else None
                                        )

                                    # Remover valores que causam erro no Supabase na inserção de volta (NaN, inf, etc.)
                                    df_remover = df_remover.replace([np.nan, pd.NaT, "", np.inf, -np.inf], None)
                                    registros = df_remover.to_dict(orient="records")

                                    # Insere de volta em rotas_confirmadas
                                    supabase.table("rotas_confirmadas").insert(registros).execute()

                                    # Remove de cargas_geradas
                                    chaves = df_remover["Serie_Numero_CTRC"].dropna().astype(str).tolist()
                                    supabase.table("cargas_geradas").delete().in_("Serie_Numero_CTRC", chaves).execute()

                                    # Verifica se a carga ficou vazia para deletar o registro da carga se necessário
                                    dados_restantes = supabase.table("cargas_geradas").select("numero_carga").eq("numero_carga", carga).execute().data
                                    if not dados_restantes:
                                        supabase.table("cargas_geradas").delete().eq("numero_carga", carga).execute()

                                    st.session_state.pop("df_cargas_cache", None)
                                    grid_key_id = f"grid_carga_gerada_{carga}"
                                    st.session_state.pop(grid_key_id, None)
                                    st.session_state.pop(checkbox_key, None)

                                    st.session_state["reload_cargas_geradas"] = True
                                    # >>> ADICIONE ESTA LINHA: Invalida o cache das Rotas Confirmadas <<<
                                    st.session_state["reload_rotas_confirmadas"] = True 

                                    # >>> ATUALIZE A MENSAGEM DE SUCESSO PARA SER MAIS ESPECÍFICA <<<
                                    st.success(f"✅ {len(chaves)} entrega(s) removida(s) da carga {carga} e retornada(s) para Rotas Confirmadas.")
                                    time.sleep(1)
                                    st.rerun()

                            except Exception as e:
                                st.error(f"Erro ao retirar entregas da carga: {e}")

                    with col_aprov:
                        valor_contratacao_key = f"valor_contratacao_{carga}"
                        valor_contratacao = st.number_input(
                            "Valor da Contratação da Carga (R$)",
                            min_value=0.0,
                            value=0.0,
                            step=0.01,
                            format="%.2f",
                            key=valor_contratacao_key,
                            disabled=not selecionadas
                        )

                        btn_aprovar_custos_key = f"btn_aprov_custos_{carga}"
                        if st.button(f"➤ Enviar para Aprovação de Custos", key=btn_aprovar_custos_key, disabled=not selecionadas or valor_contratacao <= 0):
                            if valor_contratacao <= 0:
                                st.warning("Por favor, insira um valor de contratação válido (maior que zero).")
                            else:
                                try:
                                    with st.spinner(" Enviando entregas para aprovação de custos..."):
                                        df_aprovar_custos = pd.DataFrame(selecionadas)
                                        df_aprovar_custos = df_aprovar_custos.drop(columns=["_selectedRowNodeInfo"], errors="ignore")

                                        # >>>>> ESTA É A LINHA DA CORREÇÃO DE 'numero_carga' <<<<<
                                        df_aprovar_custos["numero_carga"] = carga

                                        df_aprovar_custos["valor_contratacao"] = valor_contratacao

                                        # Se Data_Hora_Gerada é uma string formatada, precisamos convertê-la para ISO para Supabase
                                        if "Data_Hora_Gerada" in df_aprovar_custos.columns:
                                            df_aprovar_custos["Data_Hora_Gerada"] = df_aprovar_custos["Data_Hora_Gerada"].apply(
                                                lambda x: datetime.strptime(x, "%d-%m-%Y %H:%M:%S").isoformat() if x else None
                                            )

                                        df_aprovar_custos = df_aprovar_custos.replace([np.nan, pd.NaT, "", np.inf, -np.inf], None)
                                        registros_para_custos = df_aprovar_custos.to_dict(orient="records")

                                        if registros_para_custos:
                                            supabase.table("aprovacao_custos").insert(registros_para_custos).execute()

                                            chaves_para_remover = [r.get("Serie_Numero_CTRC") for r in registros_para_custos if r.get("Serie_Numero_CTRC")]

                                            if chaves_para_remover:
                                                supabase.table("cargas_geradas").delete().in_("Serie_Numero_CTRC", chaves_para_remover).execute()

                                            st.session_state["reload_cargas_geradas"] = True
                                            st.session_state["reload_aprovacao_custos"] = True

                                            st.session_state.pop(grid_key_id, None)

                                            st.success(f"✅ {len(registros_para_custos)} entregas da carga {carga} enviadas para Aprovação de Custos com valor R$ {valor_contratacao:.2f}.")
                                            time.sleep(1)
                                            st.rerun()
                                        else:
                                            st.warning("Nenhuma entrega válida selecionada para enviar para aprovação de custos.")

                                except Exception as e:
                                    st.error(f"❌ Erro ao enviar entregas para aprovação de custos: {e}")

    except Exception as e:
        st.error(f"❌ Erro ao enviar entregas para aprovação de custos: {e}")
##########################################

# PÁGINA APROVAÇÃO DE CUSTOS

##########################################

def pagina_aprovacao_custos():
    st.markdown("## Aprovação de Custos")

    # Obter a classe do usuário logado (assume 'colaborador' se não estiver definida por segurança)
    current_user_class = st.session_state.get("classe", "colaborador")
    is_user_aprovador = (current_user_class == "aprovador")

    # Mensagem de aviso se o usuário não for aprovador
    if not is_user_aprovador:
        st.warning("⛔ Apenas usuários com classe 'aprovador' podem realizar ações de aprovação de custos.")

    try:
        with st.spinner("🔄 Carregando dados para aprovação de custos..."):
            # Lógica de cache para evitar múltiplas chamadas ao Supabase em reruns
            recarregar = st.session_state.pop("reload_aprovacao_custos", False)
            if recarregar or "df_aprovacao_custos_cache" not in st.session_state:
                # Busca os dados da tabela 'aprovacao_custos' no Supabase
                dados = supabase.table("aprovacao_custos").select("*").execute().data
                df = pd.DataFrame(dados)
                st.session_state["df_aprovacao_custos_cache"] = df
            else:
                df = st.session_state["df_aprovacao_custos_cache"]

        if df.empty:
            st.info("Nenhuma carga pendente de aprovação de custos.")
            return

        df.columns = df.columns.str.strip() # Remove espaços em branco dos nomes das colunas

        # Garante que as colunas numéricas sejam tratadas como números para cálculos e exibição
        numeric_cols_to_convert = [
            'Peso Real em Kg', 'Peso Calculado em Kg', 'Cubagem em m³',
            'Quantidade de Volumes', 'Valor do Frete', 'valor_contratacao'
        ]
        for col in numeric_cols_to_convert:
            if col in df.columns:
                # Converte para numérico, tratando erros (coerce) e preenche NaN com 0
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Exibe métricas gerais no topo da página
        col1, col2, _ = st.columns([1, 1, 8]) # Ajustado para 2 colunas como no código mais recente
        with col1:
            st.metric("Total de Cargas Pendentes", df["numero_carga"].nunique() if "numero_carga" in df.columns else 0)
        with col2:
            st.metric("Total de Entregas Pendentes", len(df))

        # Define as colunas que serão exibidas no AgGrid
        colunas_exibir = [
            "Serie_Numero_CTRC", "Rota", "Regiao", "Valor do Frete", "Cliente Pagador", "Chave CT-e", "Cliente Destinatario",
            "Cidade de Entrega", "Bairro do Destinatario", "Previsao de Entrega",
            "Numero da Nota Fiscal", "Status", "Entrega Programada", "Particularidade",
            "Codigo da Ultima Ocorrencia", "Peso Real em Kg", "Peso Calculado em Kg",
            "Cubagem em m³", "Quantidade de Volumes", "valor_contratacao", "numero_carga" # Coluna valor_contratacao
        ]

        # Obtém as cargas únicas para iterar e exibir os grupos de entregas
        cargas_unicas = sorted(df["numero_carga"].dropna().unique())

        for carga in cargas_unicas:
            # Filtra o DataFrame para a carga atual
            df_carga = df[df["numero_carga"] == carga].copy()
            if df_carga.empty:
                continue

            # Obtém o valor de contratação para esta carga (assumindo que é o mesmo para todas as entregas da carga)
            valor_contratacao_carga = df_carga["valor_contratacao"].iloc[0] if "valor_contratacao" in df_carga.columns and not df_carga["valor_contratacao"].isnull().all() else 0.0

            # Título da carga
            st.markdown(f"""
            <div style="margin-top:20px;padding:10px;background:#e8f0fe;border-left:4px solid #f9ab00;border-radius:6px;display:inline-block;max-width:100%;">
                <strong>Carga:</strong> {carga}
            </div>
            """, unsafe_allow_html=True)

            # Seção de badges/resumo da carga
            col1_badges, col2_placeholder = st.columns([5, 1])
            with col1_badges:
                st.markdown(
                    f"""
                    <div style='display: flex; flex-wrap: wrap; gap: 8px;'>
                        {badge(f'{len(df_carga)} entregas')}
                        {badge(f'{formatar_brasileiro(df_carga["Peso Calculado em Kg"].sum())} kg calc')}
                        {badge(f'{formatar_brasileiro(df_carga["Peso Real em Kg"].sum())} kg real')}
                        {badge(f'R$ {formatar_brasileiro(df_carga["Valor do Frete"].sum())}')}
                        {badge(f'{formatar_brasileiro(df_carga["Cubagem em m³"].sum())} m³')}
                        {badge(f'{int(df_carga["Quantidade de Volumes"].sum())} volumes')}
                        {badge(f'Valor Contratação: R$ {formatar_brasileiro(valor_contratacao_carga)}')}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                # Fecha o container flexível
                st.markdown(f"</div>", unsafe_allow_html=True)

            # Expander para ver os detalhes da carga e interagir com o grid
            with st.expander("🔽 Ver entregas da carga para Aprovação de Custos", expanded=False):
                # Checkbox para selecionar/desselecionar todas as entregas desta carga
                checkbox_key = f"marcar_todas_aprov_custos_{carga}"
                if checkbox_key not in st.session_state:
                    st.session_state[checkbox_key] = False
                marcar_todas = st.checkbox("Marcar todas", key=checkbox_key)

                with st.spinner("🔄 Formatando entregas da carga para aprovação..."):
                    # Prepara o DataFrame para exibição no grid
                    df_formatado = df_carga[[col for col in colunas_exibir if col in df_carga.columns]].copy()
                    # NOVO: Aplica o formato brasileiro a todas as colunas de data
                    df_formatado = apply_brazilian_date_format_for_display(df_formatado)
                    # Tratar NaNs restantes em outras colunas (não datas) para exibição como string vazia
                    # (pd.NaT já foi tratado para colunas de data pela função acima)
                    df_formatado = df_formatado.replace([np.nan, None], "")

                    # Configuração do AgGrid
                    gb = GridOptionsBuilder.from_dataframe(df_formatado)
                    gb.configure_default_column(minWidth=150)
                    gb.configure_selection("multiple", use_checkbox=True)
                    gb.configure_grid_options(paginationPageSize=12)
                    gb.configure_grid_options(alwaysShowHorizontalScroll=True)
                    gb.configure_grid_options(rowStyle={"font-size": "11px"})
                    
                    # Estilo condicional das linhas (AGENDAR, Particularidade)
                    gb.configure_grid_options(getRowStyle=JsCode("""
                        function(params) {
                            const status = params.data.Status;
                            const entregaProg = params.data["Entrega Programada"];
                            const particularidade = params.data.Particularidade;
                            if (status === "AGENDAR" && (!entregaProg || entregaProg.trim() === "")) {
                                return { 'background-color': '#ffe0b2', 'color': '#333' }; // Amarelo claro
                            }
                            if (particularidade && particularidade.trim() !== "") {
                                return { 'background-color': '#fff59d', 'color': '#333' }; // Amarelo um pouco mais escuro
                            }
                            return null;
                        }
                    """))
                    gb.configure_grid_options(headerCheckboxSelection=True)
                    gb.configure_grid_options(rowSelection='multiple')
                    gb.configure_grid_options(onGridReady=GRID_RESIZE_JS_CODE) # Aplica o redimensionamento automático

                    # Aplica o JsCode 'formatter' às colunas numéricas relevantes no grid
                    for col in ['Peso Real em Kg', 'Peso Calculado em Kg', 'Cubagem em m³', 'Quantidade de Volumes', 'Valor do Frete', 'valor_contratacao']:
                        if col in df_formatado.columns:
                            gb.configure_column(col, type=["numericColumn"], valueFormatter=formatter)

                    grid_options = gb.build()
                    # Gerencia a chave do grid para forçar a atualização visual quando necessário
                    grid_key_id = f"grid_aprovacao_custos_{carga}"
                    if grid_key_id not in st.session_state:
                        st.session_state[grid_key_id] = str(uuid.uuid4())
                    grid_key = st.session_state[grid_key_id]

                # Renderiza o AgGrid na interface do Streamlit
                grid_response = AgGrid(
                    df_formatado,
                    gridOptions=grid_options,
                    update_mode=GridUpdateMode.SELECTION_CHANGED, # Essencial para capturar as seleções do usuário
                    fit_columns_on_grid_load=False,
                    width="100%",
                    height=400,
                    allow_unsafe_jscode=True,
                    key=grid_key,
                    theme=AgGridTheme.MATERIAL, # Tema visual do AgGrid
                    show_toolbar=False, # Oculta a barra de ferramentas padrão do AgGrid
                    custom_css={ # Estilos CSS personalizados para o AgGrid
                        ".ag-theme-material .ag-cell": { "font-size": "11px", "line-height": "18px", "border-right": "1px solid #ccc", },
                        ".ag-theme-material .ag-row:last-child .ag-cell": { "border-bottom": "1px solid #ccc", },
                        ".ag-theme-material .ag-header-cell": { "border-right": "1px solid #ccc", "border-bottom": "1px solid #ccc", },
                        ".ag-theme-material .ag-root-wrapper": { "border": "1px solid black", "border-radius": "6px", "padding": "4px", },
                        ".ag-theme-material .ag-header-cell-label": { "font-size": "11px", },
                        ".ag-center-cols-viewport": { "overflow-x": "auto !important", "overflow-y": "hidden", },
                        ".ag-center-cols-container": { "min-width": "100% !important", },
                        "#gridToolBar": { "padding-bottom": "0px !important", }
                    }
                )

                # Lógica para gerenciar as linhas selecionadas pelo usuário (ou pelo checkbox "Marcar todas")
                if marcar_todas:
                    selecionadas = df_formatado[df_formatado["Serie_Numero_CTRC"].notna()].copy().to_dict(orient="records")
                else:
                    selecionadas = grid_response.get("selected_rows", [])

                if selecionadas:
                    st.markdown(f"**📦 Entregas selecionadas:** {len(selecionadas)}")

                # MOVENDO E ADAPTANDO OS BOTÕES AQUI DENTRO DO EXPANDER
                col_aprovar, col_rejeitar = st.columns(2)
                with col_aprovar:
                    if st.button(
                        f"✅ Aprovar Carga {carga}",
                        key=f"aprovar_carga_{carga}",
                        disabled=not is_user_aprovador or not selecionadas # Desabilita se o usuário não é aprovador ou se nada está selecionado
                    ):
                        try:
                            with st.spinner("✅ Aprovando entregas e movendo para Cargas Aprovadas..."):
                                df_aprovar = pd.DataFrame(selecionadas)

                                # Remover a coluna "_selectedRowNodeInfo" que é interna do AgGrid
                                df_aprovar = df_aprovar.drop(columns=["_selectedRowNodeInfo"], errors="ignore")
                                
                                # Garante que as colunas de data/hora estejam em um formato amigável para o Supabase (ISO 8601)
                                date_cols_to_process = [
                                    "Previsao de Entrega", "Entrega Programada", "Data de Emissao",
                                    "Data de Autorizacao", "Data do Cancelamento", "Data do Escaneamento",
                                    "Data da Entrega Realizada", "Data da Ultima Ocorrencia",
                                    "Data de inclusao da Ultima Ocorrencia", "Data_Hora_Gerada"
                                ]
                                for col_name in date_cols_to_process:
                                    if col_name in df_aprovar.columns:
                                        df_aprovar[col_name] = pd.to_datetime(df_aprovar[col_name], errors='coerce')
                                        df_aprovar[col_name] = df_aprovar[col_name].apply(
                                            lambda x: x.isoformat() if pd.notna(x) else None
                                        )

                                # Substituir NaNs, NaTs e strings vazias por None para compatibilidade com Supabase
                                df_aprovar = df_aprovar.replace([np.nan, pd.NaT, "", np.inf, -np.inf], None)

                                # Converter para lista de dicionários para inserção no Supabase
                                registros_para_cargas_aprovadas = df_aprovar.to_dict(orient="records")
                                # Filtrar registros sem "Serie_Numero_CTRC" (chaves primárias)
                                registros_para_cargas_aprovadas = [r for r in registros_para_cargas_aprovadas if r.get("Serie_Numero_CTRC")]

                                # 1. Inserir os dados na tabela 'cargas_aprovadas'
                                if registros_para_cargas_aprovadas:
                                    supabase.table("cargas_aprovadas").insert(registros_para_cargas_aprovadas).execute()

                                # 2. Obter as chaves das entregas aprovadas e remover da tabela 'aprovacao_custos'
                                chaves_aprovadas = [r.get("Serie_Numero_CTRC") for r in registros_para_cargas_aprovadas if r.get("Serie_Numero_CTRC")]
                                if chaves_aprovadas:
                                    supabase.table("aprovacao_custos").delete().in_("Serie_Numero_CTRC", chaves_aprovadas).execute()

                                st.success(f"✅ {len(registros_para_cargas_aprovadas)} entregas da carga {carga} aprovadas e movidas para Cargas Aprovadas.")
                                
                                # Invalidar caches para forçar a recarga dos dados nas próximas visualizações
                                st.session_state["reload_aprovacao_custos"] = True
                                st.session_state["reload_cargas_aprovadas"] = True # <<< NOVO CACHE A INVALIDAR
                                # Limpar chaves do AgGrid e checkbox para forçar a reconstrução visual
                                st.session_state.pop(grid_key, None)
                                st.session_state.pop(checkbox_key, None)

                                st.rerun() # Força uma nova execução para atualizar a interface

                        except Exception as e:
                            st.error(f"❌ Erro ao aprovar carga: {e}")

                with col_rejeitar:
                    if st.button(
                        f"❌ Rejeitar Carga {carga}",
                        key=f"rejeitar_carga_{carga}",
                        disabled=not is_user_aprovador or not selecionadas # Desabilita se o usuário não é aprovador ou se nada está selecionado
                    ):
                        try:
                            with st.spinner("🔄 Rejeitando entregas e retornando para Cargas Geradas..."):
                                df_rejeitar = pd.DataFrame(selecionadas)

                                # 1. Preparar os dados para reinserção em 'cargas_geradas'
                                # Remover a coluna "_selectedRowNodeInfo" que é interna do AgGrid
                                df_rejeitar = df_rejeitar.drop(columns=["_selectedRowNodeInfo"], errors="ignore")
                                
                                # REMOVER A COLUNA 'valor_contratacao'
                                df_rejeitar = df_rejeitar.drop(columns=["valor_contratacao"], errors="ignore")

                                # Definir o novo Status para as entregas rejeitadas
                                # Escolhemos "AGENDAR" para indicar que precisam de reavaliação
                                df_rejeitar["Status"] = "AGENDAR" # OU "REJEITADA_CUSTOS" para um status mais específico
                                df_rejeitar["numero_carga"] = carga 
                                
                                # Garantir que as colunas de data/hora estejam em um formato amigável para o Supabase (ISO 8601)
                                # As datas podem vir como objetos datetime ou strings formatadas; converter para ISO.
                                date_cols_to_process = [
                                    "Previsao de Entrega", "Entrega Programada", "Data de Emissao",
                                    "Data de Autorizacao", "Data do Cancelamento", "Data do Escaneamento",
                                    "Data da Entrega Realizada", "Data da Ultima Ocorrencia",
                                    "Data de inclusao da Ultima Ocorrencia", "Data_Hora_Gerada"
                                ]
                                for col_name in date_cols_to_process:
                                    if col_name in df_rejeitar.columns:
                                        df_rejeitar[col_name] = pd.to_datetime(df_rejeitar[col_name], errors='coerce')
                                        df_rejeitar[col_name] = df_rejeitar[col_name].apply(
                                            lambda x: x.isoformat() if pd.notna(x) else None
                                        )

                                # Substituir NaNs, NaTs e strings vazias por None para compatibilidade com Supabase
                                df_rejeitar = df_rejeitar.replace([np.nan, pd.NaT, "", np.inf, -np.inf], None)

                                # Converter para lista de dicionários para inserção no Supabase
                                registros_para_cargas_geradas = df_rejeitar.to_dict(orient="records")
                                # Filtrar registros sem "Serie_Numero_CTRC" (chaves primárias)
                                registros_para_cargas_geradas = [r for r in registros_para_cargas_geradas if r.get("Serie_Numero_CTRC")]

                                # 2. Inserir os dados de volta na tabela 'cargas_geradas'
                                if registros_para_cargas_geradas:
                                    supabase.table("cargas_geradas").insert(registros_para_cargas_geradas).execute()

                                # 3. Obter as chaves das entregas rejeitadas e remover da tabela 'aprovacao_custos'
                                chaves_rejeitadas = [r.get("Serie_Numero_CTRC") for r in registros_para_cargas_geradas if r.get("Serie_Numero_CTRC")]
                                if chaves_rejeitadas:
                                    supabase.table("aprovacao_custos").delete().in_("Serie_Numero_CTRC", chaves_rejeitadas).execute()

                                st.warning(f"✅ {len(registros_para_cargas_geradas)} entregas da carga {carga} rejeitadas e retornadas para Cargas Geradas.")
                                
                                # Invalidar caches para forçar a recarga dos dados nas próximas visualizações
                                st.session_state["reload_aprovacao_custos"] = True
                                st.session_state["reload_cargas_geradas"] = True
                                # Limpar chaves do AgGrid e checkbox para forçar a reconstrução visual
                                st.session_state.pop(grid_key, None)
                                st.session_state.pop(checkbox_key, None)

                                st.rerun() # Força uma nova execução para atualizar a interface

                        except Exception as e:
                            st.error(f"❌ Erro ao rejeitar carga: {e}")

    except Exception as e:
        st.error("Erro ao carregar aprovação de custos:")
        st.exception(e)



# NO ARQUIVO: seu_arquivo.py
# ==============================================================================
# NOVA FUNÇÃO: pagina_cargas_aprovadas()
# ==============================================================================

def pagina_cargas_aprovadas():
    st.markdown("## Cargas Aprovadas")

    # Não precisa de verificação de classe aqui, pois é uma página de visualização

    try:
        with st.spinner("🔄 Carregando dados para cargas aprovadas..."):
            # Lógica de cache para evitar múltiplas chamadas ao Supabase em reruns
            recarregar = st.session_state.pop("reload_cargas_aprovadas", False)
            if recarregar or "df_cargas_aprovadas_cache" not in st.session_state:
                # Busca os dados da tabela 'cargas_aprovadas' no Supabase
                dados = supabase.table("cargas_aprovadas").select("*").execute().data
                df = pd.DataFrame(dados)
                st.session_state["df_cargas_aprovadas_cache"] = df
            else:
                df = st.session_state["df_cargas_aprovadas_cache"]

        if df.empty:
            st.info("Nenhuma carga foi aprovada ainda.")
            return

        df.columns = df.columns.str.strip() # Remove espaços em branco dos nomes das colunas

        # Garante que as colunas numéricas sejam tratadas como números para cálculos e exibição
        numeric_cols_to_convert = [
            'Peso Real em Kg', 'Peso Calculado em Kg', 'Cubagem em m³',
            'Quantidade de Volumes', 'Valor do Frete', 'valor_contratacao'
        ]
        for col in numeric_cols_to_convert:
            if col in df.columns:
                # Converte para numérico, tratando erros (coerce) e preenche NaN com 0
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Exibe métricas gerais no topo da página
        col1, col2 = st.columns([1, 1])
        with col1:
            st.metric("Total de Cargas Aprovadas", df["numero_carga"].nunique() if "numero_carga" in df.columns else 0)
        with col2:
            st.metric("Total de Entregas Aprovadas", len(df))

        # Define as colunas que serão exibidas no AgGrid
        # Mesmas colunas da aprovacao_custos, incluindo 'numero_carga' e 'valor_contratacao'
        colunas_exibir = [
            "Serie_Numero_CTRC", "Rota", "Regiao", "Valor do Frete", "Cliente Pagador", "Chave CT-e", "Cliente Destinatario",
            "Cidade de Entrega", "Bairro do Destinatario", "Previsao de Entrega",
            "Numero da Nota Fiscal", "Status", "Entrega Programada", "Particularidade",
            "Codigo da Ultima Ocorrencia", "Peso Real em Kg", "Peso Calculado em Kg",
            "Cubagem em m³", "Quantidade de Volumes", "valor_contratacao", "numero_carga" 
        ]

        # Obtém as cargas únicas para iterar e exibir os grupos de entregas
        cargas_unicas = sorted(df["numero_carga"].dropna().unique())

        for carga in cargas_unicas:
            # Filtra o DataFrame para a carga atual
            df_carga = df[df["numero_carga"] == carga].copy()
            if df_carga.empty:
                continue

            # Obtém o valor de contratação para esta carga (assumindo que é o mesmo para todas as entregas da carga)
            valor_contratacao_carga = df_carga["valor_contratacao"].iloc[0] if "valor_contratacao" in df_carga.columns and not df_carga["valor_contratacao"].isnull().all() else 0.0

            # Título da carga
            st.markdown(f"""
            <div style="margin-top:20px;padding:10px;background:#e8f0fe;border-left:4px solid #34a853;border-radius:6px;display:inline-block;max-width:100%;">
                <strong>Carga:</strong> {carga}
            </div>
            """, unsafe_allow_html=True)

            # Seção de badges/resumo da carga (com a correção do flexbox)
            col1_badges, col2_placeholder = st.columns([5, 1])
            with col1_badges:
                st.markdown(
                    f"""
                    <div style='display: flex; flex-wrap: wrap; gap: 8px;'>
                        {badge(f'{len(df_carga)} entregas')}
                        {badge(f'{formatar_brasileiro(df_carga["Peso Calculado em Kg"].sum())} kg calc')}
                        {badge(f'{formatar_brasileiro(df_carga["Peso Real em Kg"].sum())} kg real')}
                        {badge(f'R$ {formatar_brasileiro(df_carga["Valor do Frete"].sum())}')}
                        {badge(f'{formatar_brasileiro(df_carga["Cubagem em m³"].sum())} m³')}
                        {badge(f'{int(df_carga["Quantidade de Volumes"].sum())} volumes')}
                        {badge(f'Valor Contratação: R$ {formatar_brasileiro(valor_contratacao_carga)}')}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            # Expander para ver os detalhes da carga e interagir com o grid
            with st.expander("🔽 Ver entregas da carga aprovada", expanded=False):
                # Checkbox "Marcar todas" e seleção do grid podem ser mantidos para consistência visual
                checkbox_key = f"marcar_todas_cargas_aprovadas_{carga}"
                if checkbox_key not in st.session_state:
                    st.session_state[checkbox_key] = False
                marcar_todas = st.checkbox("Marcar todas", key=checkbox_key)

                with st.spinner("🔄 Formatando entregas da carga aprovada..."):
                    df_formatado = df_carga[[col for col in colunas_exibir if col in df_carga.columns]].copy()
                    # NOVO: Aplica o formato brasileiro a todas as colunas de data
                    df_formatado = apply_brazilian_date_format_for_display(df_formatado)
                    # Tratar NaNs restantes em outras colunas (não datas) para exibição como string vazia
                    # (pd.NaT já foi tratado para colunas de data pela função acima)
                    df_formatado = df_formatado.replace([np.nan, None], "")

                    gb = GridOptionsBuilder.from_dataframe(df_formatado)
                    gb.configure_default_column(minWidth=150)
                    gb.configure_selection("multiple", use_checkbox=True)
                    gb.configure_grid_options(paginationPageSize=12)
                    gb.configure_grid_options(alwaysShowHorizontalScroll=True)
                    gb.configure_grid_options(rowStyle={"font-size": "11px"})
                    
                    # Estilo condicional das linhas (AGENDAR, Particularidade)
                    gb.configure_grid_options(getRowStyle=JsCode("""
                        function(params) {
                            const status = params.data.Status;
                            const entregaProg = params.data["Entrega Programada"];
                            const particularidade = params.data.Particularidade;
                            if (status === "AGENDAR" && (!entregaProg || entregaProg.trim() === "")) {
                                return { 'background-color': '#ffe0b2', 'color': '#333' }; 
                            }
                            if (particularidade && particularidade.trim() !== "") {
                                return { 'background-color': '#fff59d', 'color': '#333' }; 
                            }
                            return null;
                        }
                    """))
                    gb.configure_grid_options(headerCheckboxSelection=True)
                    gb.configure_grid_options(rowSelection='multiple')
                    gb.configure_grid_options(onGridReady=GRID_RESIZE_JS_CODE) 

                    for col in ['Peso Real em Kg', 'Peso Calculado em Kg', 'Cubagem em m³', 'Quantidade de Volumes', 'Valor do Frete', 'valor_contratacao']:
                        if col in df_formatado.columns:
                            gb.configure_column(col, type=["numericColumn"], valueFormatter=formatter)

                    grid_options = gb.build()
                    grid_key_id = f"grid_cargas_aprovadas_{carga}"
                    if grid_key_id not in st.session_state:
                        st.session_state[grid_key_id] = str(uuid.uuid4())
                    grid_key = st.session_state[grid_key_id]

                grid_response = AgGrid(
                    df_formatado,
                    gridOptions=grid_options,
                    update_mode=GridUpdateMode.SELECTION_CHANGED,
                    fit_columns_on_grid_load=False,
                    width="100%",
                    height=400,
                    allow_unsafe_jscode=True,
                    key=grid_key,
                    theme=AgGridTheme.MATERIAL,
                    show_toolbar=False,
                    custom_css={ 
                        ".ag-theme-material .ag-cell": { "font-size": "11px", "line-height": "18px", "border-right": "1px solid #ccc", },
                        ".ag-theme-material .ag-row:last-child .ag-cell": { "border-bottom": "1px solid #ccc", },
                        ".ag-theme-material .ag-header-cell": { "border-right": "1px solid #ccc", "border-bottom": "1px solid #ccc", },
                        ".ag-theme-material .ag-root-wrapper": { "border": "1px solid black", "border-radius": "6px", "padding": "4px", },
                        ".ag-theme-material .ag-header-cell-label": { "font-size": "11px", },
                        ".ag-center-cols-viewport": { "overflow-x": "auto !important", "overflow-y": "hidden", },
                        ".ag-center-cols-container": { "min-width": "100% !important", },
                        "#gridToolBar": { "padding-bottom": "0px !important", }
                    }
                )

                if marcar_todas:
                    selecionadas = df_formatado[df_formatado["Serie_Numero_CTRC"].notna()].copy().to_dict(orient="records")
                else:
                    selecionadas = grid_response.get("selected_rows", [])

                if selecionadas:
                    st.markdown(f"**📦 Entregas selecionadas:** {len(selecionadas)}")
                # Sem botões de ação (Aprovar/Rejeitar), pois esta é uma página de visualização
    except Exception as e:
        st.error("Erro ao carregar cargas aprovadas:")
        st.exception(e)


# ========== EXECUÇÃO PRINCIPAL ========== #

login()  # Garante que o usuário esteja logado

# Mostra welcome + botão sair no topo da página principal
if st.session_state.get("login", False):
    col_welcome, col_logout = st.columns([10, 2]) # Ajuste as proporções das colunas conforme necessário
    with col_welcome:
        st.markdown(f"👋 **Bem-vindo, {st.session_state.get('username','Usuário')}!**")
    with col_logout:
        if st.button("🚪 Sair"):
            for key in ["login", "username", "is_admin", "expiry_time"]:
                cookies[key] = ""
            st.session_state.login = False
            st.rerun()
    st.markdown("---") # Linha separadora para separar o cabeçalho das abas

    # Definir as abas principais
    # Adicionei uma aba para "Administração e Configurações" para agrupar as opções de usuário.
    tab_sync, tab_operacoes, tab_admin_settings = st.tabs(["Sincronização", "Operações", "Administração e Configurações"])

    with tab_sync:
        pagina_sincronizacao()

    with tab_operacoes:
        # Sub-abas para as operações de roteirização
        sub_tab_confirmar_prod, sub_tab_aprov_dir, sub_tab_pre_rot, sub_tab_rotas_conf, sub_tab_cargas, sub_tab_aprov_custos, sub_tab_cargas_aprovadas = st.tabs([ # <<< ADICIONE sub_tab_cargas_aprovadas AQUI
            "Confirmar Produção", "Aprovação Diretoria", "Pré Roterização", "Rotas Confirmadas", "Cargas Geradas", "Aprovação de Custos", "Cargas Aprovadas" # <<< ADICIONE "Cargas Aprovadas" AQUI
        ])
        with sub_tab_confirmar_prod:
            pagina_confirmar_producao()
        with sub_tab_aprov_dir:
            pagina_aprovacao_diretoria()
        with sub_tab_pre_rot:
            pagina_pre_roterizacao()
        with sub_tab_rotas_conf:
            pagina_rotas_confirmadas()
        with sub_tab_cargas:
            pagina_cargas_geradas()
        with sub_tab_aprov_custos:
            pagina_aprovacao_custos()
        with sub_tab_cargas_aprovadas: # <<< NOVO BLOCO
            pagina_cargas_aprovadas()

    with tab_admin_settings:
        # Conteúdo da aba de Administração e Configurações
        if st.session_state.get("is_admin", False):
            st.subheader("Gerenciamento de Usuários")
            pagina_gerenciar_usuarios()
            st.markdown("---") # Separador visual

        st.subheader("Alterar Minha Senha")
        pagina_trocar_senha()

# Se o usuário não estiver logado, a função login() no início já teria parado o script.
# Este bloco 'else' não é estritamente necessário aqui se o login() faz um st.stop()
# Mas é uma boa prática para clareza.
else:
    # A página de login é exibida pela função login()
    pass # Nada a fazer aqui, pois o login() já cuida do acesso.


