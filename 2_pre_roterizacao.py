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
import random

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
    Lida com valores nulos ou inválidos.
    """
    if data_iso is None:
        return '' # Retorna string vazia se o valor for None ou nulo
    
    # Tratamento para pandas.NaT (Not a Time) ou outros valores nulos de data
    if pd.isna(data_iso):
        return ''

    dt = None # Inicializa dt como None

    if isinstance(data_iso, str):
        try:
            # Tenta converter de string ISO, ou de formato DD-MM-YYYY (se a origem for um campo de texto não ISO)
            # Prioriza fromisoformat para strings que já vêm do Supabase
            dt = datetime.fromisoformat(data_iso)
        except ValueError:
            # Se não for ISO, tenta como formato brasileiro para strings
            try:
                dt = datetime.strptime(data_iso, "%d-%m-%Y %H:%M:%S")
            except ValueError:
                # Se ainda der erro, tenta apenas a data (sem tempo)
                try:
                    dt = datetime.strptime(data_iso, "%d-%m-%Y")
                except ValueError:
                    return str(data_iso) # Em último caso, retorna a string original se não puder converter
        except Exception: # Captura outras exceções inesperadas na conversão de string
            return str(data_iso) # Retorna a string original

    elif isinstance(data_iso, (datetime, date, pd.Timestamp)): # Já é um objeto de data/hora válido
        dt = data_iso
    else: # Tenta coercer para datetime se for outro tipo (e.g., numpy.datetime64)
        try:
            dt = pd.to_datetime(data_iso, errors='coerce')
            if pd.isna(dt): # Se a conversão resultar em NaT, trata como nulo
                return ''
        except Exception:
            return str(data_iso) # Retorna string se não puder converter

    # Após todas as tentativas de conversão, verifica se dt é um objeto válido
    if dt is None:
        return ''

    # Se dt vier sem timezone, assume que é UTC (Supabase armazena como UTC por padrão)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc).astimezone(FUSO_BRASIL)
    else:
        # Se já tem timezone, apenas converte para o fuso horário desejado
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
    


# A função gerar_proximo_numero_carga()
def gerar_proximo_numero_carga(supabase):
    """
    Gera um número de carga aleatório de 6 dígitos, garantindo sua unicidade
    em todas as tabelas de cargas do Supabase.
    Retorna o número de carga único ou None em caso de falha ou esgotamento de tentativas.
    """
    cargo_tables = ["cargas_geradas", "aprovacao_custos", "cargas_aprovadas", "cargas_fechadas"]
    max_retries = 1000 # Limite de tentativas para encontrar um número único
    
    st.info("Iniciando geração de número de carga aleatório e único...")

    for attempt in range(max_retries):
        # Gera um número aleatório de 6 dígitos, formatado com zeros à esquerda
        random_cargo_number = f"{random.randint(0, 999999):06d}"
        
        is_unique_candidate = True
        
        # Verifica a unicidade em todas as tabelas relevantes
        for table_name in cargo_tables:
            try:
                # Consulta a tabela para ver se este número de carga já existe
                # Assume que 'numero_carga' é o nome da coluna em todas essas tabelas
                response = supabase.table(table_name).select("numero_carga").eq("numero_carga", random_cargo_number).limit(1).execute()
                
                if response.data and len(response.data) > 0:
                    # Número de carga já existe nesta tabela, não é único
                    is_unique_candidate = False
                    st.warning(f"Candidato '{random_cargo_number}' já existe na tabela '{table_name}'. Tentando outro...")
                    break # Sai do loop de tabelas e tenta um novo random_cargo_number
            except Exception as e:
                # ERRO CRÍTICO: Se a consulta ao Supabase falhar, não podemos garantir a unicidade.
                # É mais seguro falhar no processo de geração e informar o usuário.
                st.error(f"Erro CRÍTICO de comunicação com o Supabase ao verificar unicidade em '{table_name}'.")
                st.error(f"Detalhes do erro: {e}")
                st.warning("Não foi possível garantir a unicidade do número da carga devido a problemas com o banco de dados. Por favor, tente novamente e verifique os logs do Supabase.")
                return None # Indica falha
        
        if is_unique_candidate:
            # Encontrou um número aleatório único!
            st.success(f"Número de carga único gerado com sucesso: {random_cargo_number} (Tentativa {attempt + 1})")
            return random_cargo_number
            
    # Se o loop terminar sem encontrar um número único após max_retries
    st.error(f"Não foi possível gerar um número de carga único após {max_retries} tentativas. O espaço de números pode estar saturado ou há um problema persistente na comunicação.")
    return None # Indica falha
################################################################
GRID_RESIZE_JS_CODE = JsCode("""
function(params) {
    const gridApi = params.api;
    const gridDiv = params.eGridDiv; // O elemento DOM raiz do grid

    const resizeColumns = () => {
        // --- ADIÇÃO AQUI: Verifica se gridApi é válido antes de usar ---
        if (!gridApi) {
            console.warn("AgGrid API não disponível no momento do redimensionamento de colunas.");
            return; // Aborta a execução se gridApi for undefined
        }
        // --- FIM DA ADIÇÃO ---

        gridDiv.offsetWidth; // Força reflow para layout mais atualizado
        gridApi.sizeColumnsToFit();
    };

    // Pequeno atraso para dar tempo à estrutura DOM do Streamlit
    setTimeout(resizeColumns, 200);

    const resizeObserver = new ResizeObserver(entries => {
        for (let entry of entries) {
            entry.target.offsetWidth;
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

            if 'carregar_base_supabase' in locals() or 'carregar_base_supabase' in globals():
                carregar_base_supabase.clear() # Limpa o cache da função
            
            
            progress_bar.progress(100) # 100%

            # --- TRECHO PARA MENSAGEM DE SUCESSO E BALÕES ---
            #st.success("✅ Sincronização concluída com sucesso!")
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
                time.sleep(2)
        else:
            st.error(f"[ERRO] Falha final ao inserir lote {i}–{i + len(sublote) - 1} na tabela '{nome_tabela}'.")
        time.sleep(pausa)


#------------------------------------------------------------------------------
def limpar_tabelas_relacionadas():
    # Lista de tabelas que precisam ser limpas completamente
    # 'fBaseroter' já é limpa separadamente no início da pagina_sincronizacao
    tabelas_para_limpar_por_ctrc = [
        "confirmadas_producao", "aprovacao_diretoria", "pre_roterizacao",
        "rotas_confirmadas", "cargas_geradas", "aprovacao_custos", "cargas_aprovadas"
    ]

    for tabela in tabelas_para_limpar_por_ctrc:
        try:
            # A forma mais robusta de limpar uma tabela no Supabase é usar um filtro
            # que é garantido que sempre será verdadeiro para todos os registros que você deseja apagar.
            # Usaremos 'neq' (not equal to) em uma coluna que existe em todas essas tabelas
            # ('Serie_Numero_CTRC') com um valor que nunca existirá.
            # Adicionei um print para depuração.
            st.write(f"DEBUG: Tentando limpar a tabela: {tabela}")
            response = supabase.table(tabela).delete().neq("Serie_Numero_CTRC", "DUMMY_VALUE_FOR_FULL_CLEAN_12345").execute()
            
            if response.data: # Se 'data' não for None, significa que algo foi retornado/deletado.
                st.success(f"✅ Tabela '{tabela}' limpa com sucesso. Registros afetados: {len(response.data) if response.data else 0}")
            elif response.error:
                st.error(f"❌ Erro ao limpar tabela '{tabela}': {response.error}")
            else:
                st.info(f"ℹ️ Tabela '{tabela}' já estava vazia ou não havia registros correspondentes para deletar.")


        except Exception as e:
            st.error(f"[ERRO GERAL] Ao tentar limpar a tabela '{tabela}': {e}. Por favor, verifique suas permissões (RLS) no Supabase ou se a coluna 'Serie_Numero_CTRC' existe em todas as tabelas listadas.")


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

# Formato de exibição de data e hora no padrão brasileiro (completo com horas, minutos, segundos)
DATE_DISPLAY_FORMAT_STRING = '%d-%m-%Y %H:%M:%S'

# Formato de exibição de data no padrão brasileiro (apenas data)
DATE_ONLY_DISPLAY_FORMAT_STRING = '%d-%m-%Y'


# Lista de todas as colunas que são datas/horas no seu sistema e que devem ser formatadas para exibição
# ATENÇÃO: As colunas nesta lista serão formatadas com HORA.
GLOBAL_DATE_DISPLAY_COLUMNS = [
    "Data de Emissao", "Data de Autorizacao", "Data de inclusao da Ultima Ocorrencia",
    "Data da Ultima Ocorrencia", "Previsao de Entrega", "Entrega Programada",
    "Data da Entrega Realizada", "Data do Cancelamento", "Data do Escaneamento",
    "Data_Hora_Gerada", "data_fechamento", "data_aprovacao_custos","Data_Hora_Gerada", 
    "data_fechamento", "data_aprovacao_custos"
]

# Nova função para aplicar formato de data APENAS (sem hora)
def apply_brazilian_date_only_format_for_display(df_to_format, date_cols):
    for col in date_cols:
        if col in df_to_format.columns:
            if not pd.api.types.is_datetime64_any_dtype(df_to_format[col]):
                df_to_format[col] = pd.to_datetime(df_to_format[col], errors='coerce')
            df_to_format[col] = df_to_format[col].apply(
                lambda x: x.strftime(DATE_ONLY_DISPLAY_FORMAT_STRING)
                if pd.notna(x) and isinstance(x, (Timestamp, datetime))
                else ''
            )
    return df_to_format


#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Ajuste a função apply_brazilian_date_format_for_display para usar o novo GLOBAL_DATE_DISPLAY_COLUMNS
def apply_brazilian_date_format_for_display(df_to_format):
    for col in GLOBAL_DATE_DISPLAY_COLUMNS:
        if col in df_to_format.columns:
            if not pd.api.types.is_datetime64_any_dtype(df_to_format[col]):
                # Adicione 'dayfirst=True' aqui
                df_to_format[col] = pd.to_datetime(df_to_format[col], errors='coerce')
            df_to_format[col] = df_to_format[col].apply(
                lambda x: x.strftime(DATE_DISPLAY_FORMAT_STRING)
                if pd.notna(x) and isinstance(x, (Timestamp, datetime))
                else ''
            )
    return df_to_format



# Constantes para colunas que devem ser tratadas como APENAS DATA (sem hora)
# em algumas conversões (e.g., re-parsing do AgGrid para Supabase)
DATE_ONLY_REPARSE_COLUMNS = ['Previsao de Entrega', 'Entrega Programada']

##########################################

# PÁGINA Confirmar Produção

##########################################
def pagina_confirmar_producao():
    st.markdown("## Confirmar Produção")

    # Carregando entregas diretamente da tabela 'confirmadas_producao'
    with st.spinner("🔄 Carregando entregas para confirmar produção..."):
        try:
            # Fonte de dados para esta página é 'confirmadas_producao'
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
                    # Garante que seja datetime para que o JsCode possa lidar com NaT corretamente
                    df['Entrega Programada'] = pd.to_datetime(df['Entrega Programada'], errors='coerce') 
                if 'Particularidade' in df.columns:
                    df['Particularidade'] = df['Particularidade'].fillna('').astype(str)
                if 'Serie_Numero_CTRC' in df.columns:
                    df['Serie_Numero_CTRC'] = df['Serie_Numero_CTRC'].astype(str)
                if 'Cliente Pagador' in df.columns: # Novo: Garantir Cliente Pagador como string
                    df['Cliente Pagador'] = df['Cliente Pagador'].fillna('').astype(str)

        except Exception as e:
            st.error(f"Erro ao consultar o banco de dados: {e}")
            return

        if df.empty:
            st.info("Nenhuma entrega disponível para confirmar produção.")
            return

    # Exibir métricas gerais
    col1, col2, _ = st.columns([1, 1, 8])
    with col1:
        # Agora conta clientes únicos
        st.metric("Total de Clientes", df["Cliente Pagador"].nunique() if "Cliente Pagador" in df.columns else 0)
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

    # Configuração de estilo condicional do grid (JsCode) - Permanece a mesma, pois é por linha
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

    # Iterar sobre os clientes pagadores únicos para exibir os grids
    # Usamos 'Cliente Pagador' agora
    clientes_pagadores_unicos = sorted(df["Cliente Pagador"].dropna().unique()) if "Cliente Pagador" in df.columns else []

    for cliente_pagador in clientes_pagadores_unicos:
        # Filtra o DataFrame pelo cliente pagador atual
        df_cliente = df[df["Cliente Pagador"] == cliente_pagador].copy()
        if df_cliente.empty:
            continue

        st.markdown(f"""
        <div style="margin-top:20px;padding:10px;background:#e8f0fe;border-left:4px solid #4285f4;border-radius:6px;display:inline-block;max-width:100%;">
            <strong>Cliente Pagador:</strong> {cliente_pagador}
        </div>
        """, unsafe_allow_html=True)

        # Informações agregadas sobre o cliente (badges)
        col_badge, col_check_placeholder = st.columns([5, 1])
        with col_badge:
            # Garante que as colunas existem antes de tentar somar/formatar
            peso_calc_sum = df_cliente['Peso Calculado em Kg'].sum() if 'Peso Calculado em Kg' in df_cliente.columns else 0
            peso_real_sum = df_cliente['Peso Real em Kg'].sum() if 'Peso Real em Kg' in df_cliente.columns else 0
            valor_frete_sum = df_cliente['Valor do Frete'].sum() if 'Valor do Frete' in df_cliente.columns else 0
            cubagem_sum = df_cliente['Cubagem em m³'].sum() if 'Cubagem em m³' in df_cliente.columns else 0
            volumes_sum = df_cliente['Quantidade de Volumes'].sum() if 'Quantidade de Volumes' in df_cliente.columns else 0

            st.markdown(
                f"<span style='background:#eef2f7;border-radius:12px;padding:6px 12px;margin:4px;color:inherit;display:inline-block;'>{len(df_cliente)} entregas</span>"
                f"<span style='background:#eef2f7;border-radius:12px;padding:6px 12px;margin:4px;color:inherit;display:inline-block;'>{formatar_brasileiro(peso_calc_sum)} kg calc</span>"
                f"<span style='background:#eef2f7;border-radius:12px;padding:6px 12px;margin:4px;color:inherit;display:inline-block;'>{formatar_brasileiro(peso_real_sum)} kg real</span>"
                f"<span style='background:#eef2f7;border-radius:12px;padding:6px 12px;margin:4px;color:inherit;display:inline-block;'>Valor frete: R$ {formatar_brasileiro(valor_frete_sum)}</span>"
                f"<span style='background:#eef2f7;border-radius:12px;padding:6px 12px;margin:4px;color:inherit;display:inline-block;'>{formatar_brasileiro(cubagem_sum)} m³</span>"
                f"<span style='background:#eef2f7;border-radius:12px;padding:6px 12px;margin:4px;color:inherit;display:inline-block;'>{int(volumes_sum)} volumes</span>",
                unsafe_allow_html=True
            )

        # Expander para o grid
        with st.expander("🔽 Selecionar entregas", expanded=False):
            # NOVO: Checkbox "Marcar todas" dentro do expander
            checkbox_key = f"marcar_todas_conf_prod_{cliente_pagador}"
            # Garante que o estado do checkbox seja inicializado
            if checkbox_key not in st.session_state:
                st.session_state[checkbox_key] = False
            
            marcar_todas = st.checkbox("Marcar todas", key=checkbox_key)

            # Criação e estilização do grid (usando o AgGrid)
            df_formatado = df_cliente[[col for col in colunas_exibir if col in df_cliente.columns]].copy()
            df_formatado = apply_brazilian_date_format_for_display(df_formatado)
            
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
                grid_key_id = f"grid_conf_prod_{cliente_pagador}"
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
                    if st.button(f" Enviar para Aprovação"):
                        try:
                            # Prepara os dados para inserção na tabela de aprovacao_diretoria
                            df_confirmar = selecionadas.drop(columns=["_selectedRowNodeInfo"], errors="ignore").copy()
                            # A coluna "Rota" é um atributo da entrega e deve ser mantida, não confundir com o agrupamento
                            
                            # --- NOVO/MODIFICADO: TRATAMENTO DE DATAS PARA INSERÇÃO NO SUPABASE ---
                            # As colunas de data no 'selecionadas' vêm como strings no formato brasileiro (DD-MM-AAAA HH:MM:SS).
                            # Primeiro, vamos converter essas strings de volta para objetos datetime.
                            # Usamos GLOBAL_DATE_DISPLAY_COLUMNS e DATE_DISPLAY_FORMAT_STRING (definidas no seu código).
                            for col_name in GLOBAL_DATE_DISPLAY_COLUMNS:
                                if col_name in df_confirmar.columns:
                                    df_confirmar[col_name] = pd.to_datetime(
                                        df_confirmar[col_name],
                                        format=DATE_DISPLAY_FORMAT_STRING, # Brazilian format (DD-MM-AAAA HH:MM:SS)
                                        errors='coerce' # Convert unparseable values to pd.NaT
                                    )

                            # Step 2: Iterate through all columns and convert any Pandas Timestamp or
                            # standard Python datetime.datetime objects to ISO 8601 strings.
                            for col_name in df_confirmar.columns:
                                if col_name in GLOBAL_DATE_DISPLAY_COLUMNS or \
                                   pd.api.types.is_datetime64_any_dtype(df_confirmar[col_name]):
                                    df_confirmar[col_name] = df_confirmar[col_name].apply(
                                        lambda x: x.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(x) else None
                                    )
                                elif df_confirmar[col_name].dtype == 'object':
                                    df_confirmar[col_name] = df_confirmar[col_name].apply(
                                        lambda x: x.strftime("%Y-%m-%d %H:%M:%S") if isinstance(x, (pd.Timestamp, datetime)) else x
                                    )

                            df_confirmar = df_confirmar.replace([np.nan, np.inf, -np.inf, ""], None)

                            registros = df_confirmar.to_dict(orient="records")
                            # Filtra registros inválidos (sem Serie_Numero_CTRC)
                            registros = [r for r in registros if r.get("Serie_Numero_CTRC")]

                            # Insere na tabela de aprovacao_diretoria
                            if registros: # Apenas insere se houver registros válidos
                                supabase.table("aprovacao_diretoria").insert(registros).execute()
                            
                            # === CORREÇÃO: Remove as entregas da tabela 'confirmadas_producao' ===
                            chaves = [r["Serie_Numero_CTRC"] for r in registros]
                            if chaves: # Apenas deleta se houver chaves para deletar
                                supabase.table("confirmadas_producao").delete().in_("Serie_Numero_CTRC", chaves).execute()

                            # Limpa o estado da sessão para forçar a recarga dos grids e evitar problemas de cache.
                            st.session_state["reload_confirmadas_producao"] = True # Sinaliza para recarregar os dados na próxima execução
                            st.session_state.pop(grid_key_id, None) # Remove a key do grid para forçar a reconstrução, se necessário
                            st.session_state.pop(checkbox_key, None) # Limpa o estado do checkbox "Marcar todas" para esta rota após a ação

                            st.session_state["reload_aprovacao_diretoria"] = True

                            st.success(f"✅ {len(chaves)} entregas do Cliente {cliente_pagador} foram enviadas para a próxima etapa (Aprovação da Diretoria).")
                            
                            # Força um rerun para atualizar a UI e refletir as mudanças
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao confirmar produção do cliente {cliente_pagador}: {e}")

                   


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
                badge(f"Valor frete: R$ {formatar_brasileiro(df_cliente['Valor do Frete'].sum())}") +
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

                    # ... (código existente) ...
                    with col_aprovar:
                        if st.button(
                            f"✅ Aprovar entregas",
                            key=f"btn_aprovar_{cliente}",
                            disabled=not is_user_aprovador
                        ):
                            try:
                                with st.spinner("✅ Aprovando entregas e movendo para Pré-Roteirização..."):
                                    df_aprovar = pd.DataFrame(selecionadas)
                                    df_aprovar = df_aprovar.drop(columns=["_selectedRowNodeInfo"], errors="ignore")

                                    # --- TRATAMENTO DE DATAS PARA SUPABASE ---
                                    for col_name in GLOBAL_DATE_DISPLAY_COLUMNS:
                                        if col_name in df_aprovar.columns:
                                            df_aprovar[col_name] = pd.to_datetime(
                                                df_aprovar[col_name],
                                                format=DATE_DISPLAY_FORMAT_STRING,
                                                errors='coerce'
                                            )

                                    for col_name in df_aprovar.columns:
                                        if col_name in GLOBAL_DATE_DISPLAY_COLUMNS or \
                                           pd.api.types.is_datetime64_any_dtype(df_aprovar[col_name]):
                                            df_aprovar[col_name] = df_aprovar[col_name].apply(
                                                lambda x: x.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(x) else None
                                            )
                                        elif df_aprovar[col_name].dtype == 'object':
                                            df_aprovar[col_name] = df_aprovar[col_name].apply(
                                                lambda x: x.strftime("%Y-%m-%d %H:%M:%S") if isinstance(x, (pd.Timestamp, datetime)) else x
                                            )

                                    df_aprovar = df_aprovar.replace([np.nan, np.inf, -np.inf, ""], None)
                                    # --- FIM DO TRATAMENTO ---

                                    registros_para_pre_roterizacao = df_aprovar.to_dict(orient="records")
                                    registros_para_pre_roterizacao = [r for r in registros_para_pre_roterizacao if r.get("Serie_Numero_CTRC")]

                                    if registros_para_pre_roterizacao:
                                        supabase.table("pre_roterizacao").insert(registros_para_pre_roterizacao).execute()

                                    chaves_aprovadas = [r.get("Serie_Numero_CTRC") for r in registros_para_pre_roterizacao if r.get("Serie_Numero_CTRC")]
                                    if chaves_aprovadas:
                                        supabase.table("aprovacao_diretoria").delete().in_("Serie_Numero_CTRC", chaves_aprovadas).execute()

                                    st.success(f"✅ {len(registros_para_pre_roterizacao)} entregas aprovadas e enviadas para Pré-Roteirização.")
                                    
                                    # --- INVALIDAÇÃO DE CACHES E KEYS DE GRIDS (Origem e Destino) ---
                                    st.session_state["reload_aprovacao_diretoria"] = True # Recarrega a página atual
                                    st.session_state.pop(grid_key_id, None) # Invalida o grid da página de origem
                                    st.session_state.pop(checkbox_key, None) # Limpa o estado do checkbox

                                    # Invalidação da key do grid de destino (Pré Roterização)
                                    rotas_afetadas = df_aprovar["Rota"].dropna().unique()
                                    # AQUI ESTÁ O AJUSTE PRINCIPAL: Remove a chave do UUID do AgGrid
                                    for rota_afetadas_val in rotas_afetadas:
                                        # Primeiro, remove a chave que guarda o UUID do AgGrid
                                        # Esta é a chave 'pai' que dita o UUID real do grid
                                        key_do_session_state_para_o_uuid = f"grid_pre_rota_{rota_afetadas_val}"
                                        if key_do_session_state_para_o_uuid in st.session_state:
                                            st.session_state.pop(key_do_session_state_para_o_uuid, None)

                                    st.session_state["reload_pre_roterizacao"] = True # Recarrega a página de destino (dados)
                                    st.write(f"DEBUG - Rotas sendo processadas para invalidação do grid de Pré-Roterização: {rotas_afetadas.tolist()}")
                                    # --- FIM DA INVALIDAÇÃO ---

                                    st.rerun()

                            except Exception as e:
                                st.error(f"❌ Erro ao aprovar entregas: {e}")

                    # ... (código existente) ...
                    with col_rejeitar:
                        if st.button(
                            f"❌ Rejeitar entregas",
                            key=f"btn_rejeitar_{cliente}",
                            disabled=not is_user_aprovador
                        ):
                            try:
                                with st.spinner("🔄 Rejeitando entregas e retornando para Confirmar Produção..."):
                                    df_rejeitar = pd.DataFrame(selecionadas)
                                    df_rejeitar = df_rejeitar.drop(columns=["_selectedRowNodeInfo"], errors="ignore")

                                    # *** INTEGRIDADE DE DADOS: GARANTIR QUE DATAS VAZIAS PERMANEÇAM VAZIAS ***
                                    # Este bloco garante que os tipos de dados estejam corretos para o Supabase
                                    # e que valores vazios no grid (vindos como string) sejam None no banco.
                                    for col_name in GLOBAL_DATE_DISPLAY_COLUMNS:
                                        if col_name in df_rejeitar.columns:
                                            df_rejeitar[col_name] = pd.to_datetime(
                                                df_rejeitar[col_name],
                                                format=DATE_DISPLAY_FORMAT_STRING,
                                                errors='coerce'
                                            )

                                    for col_name in df_rejeitar.columns:
                                        if col_name in GLOBAL_DATE_DISPLAY_COLUMNS or \
                                           pd.api.types.is_datetime64_any_dtype(df_rejeitar[col_name]):
                                            df_rejeitar[col_name] = df_rejeitar[col_name].apply(
                                                lambda x: x.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(x) else None
                                            )
                                        elif df_rejeitar[col_name].dtype == 'object':
                                            df_rejeitar[col_name] = df_rejeitar[col_name].apply(
                                                lambda x: x.strftime("%Y-%m-%d %H:%M:%S") if isinstance(x, (pd.Timestamp, datetime)) else x
                                            )

                                    df_rejeitar = df_rejeitar.replace([np.nan, np.inf, -np.inf, ""], None)
                                    # *** FIM DA INTEGRIDADE DE DADOS ***

                                    registros_para_confirmar_producao = df_rejeitar.to_dict(orient="records")
                                    registros_para_confirmar_producao = [r for r in registros_para_confirmar_producao if r.get("Serie_Numero_CTRC")]

                                    if registros_para_confirmar_producao:
                                        supabase.table("confirmadas_producao").insert(registros_para_confirmar_producao).execute()

                                    chaves_rejeitadas = [r.get("Serie_Numero_CTRC") for r in registros_para_confirmar_producao if r.get("Serie_Numero_CTRC")]
                                    if chaves_rejeitadas:
                                        supabase.table("aprovacao_diretoria").delete().in_("Serie_Numero_CTRC", chaves_rejeitadas).execute()
                                    
                                    st.warning(f"↩️ {len(registros_para_confirmar_producao)} entregas rejeitadas e retornadas para Confirmar Produção.")
                                    
                                    # --- ATUALIZAÇÃO DO GRID DE ORIGEM E DESTINO ---
                                    st.session_state["reload_aprovacao_diretoria"] = True # Recarrega os dados da página atual
                                    st.session_state.pop(grid_key_id, None) # Invalida o grid da página de origem
                                    st.session_state.pop(checkbox_key, None) # Limpa o estado do checkbox

                                    # Invalidação da key do grid de destino (Confirmar Produção)
                                    # Isso força o grid de Confirmar Produção a redesenhar com os itens que retornaram.
                                    clientes_afetados = df_rejeitar["Cliente Pagador"].dropna().unique()
                                    for cliente_afetado in clientes_afetados:
                                        grid_key_confirmar_prod = f"grid_conf_prod_{cliente_afetado}"
                                        if grid_key_confirmar_prod in st.session_state:
                                            st.session_state.pop(grid_key_confirmar_prod, None)
                                    
                                    st.session_state["reload_confirmadas_producao"] = True # Recarrega os dados da página de destino
                                    # --- FIM DA ATUALIZAÇÃO DO GRID ---

                                    st.rerun()

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
            badge(f"Valor frete: R$ {formatar_brasileiro(df_rota['Valor do Frete'].sum())}") +
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
                                # FIX PRINCIPAL AQUI: Especifique o formato de entrada para pd.to_datetime
                                df_confirmar[col_name] = pd.to_datetime(
                                    df_confirmar[col_name],
                                    format=DATE_DISPLAY_FORMAT_STRING, # <-- Adicione esta linha!
                                    errors='coerce'
                                )
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

    # --- INÍCIO: BLOCO DE CRIAÇÃO DE CARGA AVULSA ---
    if "nova_carga_em_criacao" not in st.session_state:
        st.session_state["nova_carga_em_criacao"] = False
        st.session_state["numero_nova_carga"] = ""

    if not st.session_state["nova_carga_em_criacao"]:
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🆕 Criar Nova Carga Avulsa"):
                try:
                    numero_carga = gerar_proximo_numero_carga(supabase)
                    if numero_carga:
                        st.session_state["nova_carga_em_criacao"] = True
                        st.session_state["numero_nova_carga"] = numero_carga
                        st.rerun()
                    else:
                        st.error("Falha ao gerar um número de carga único. Por favor, tente novamente.")
                except Exception as e:
                    st.error(f"Erro ao criar nova carga: {e}")
    else:
        st.success(f"Nova Carga Criada: {st.session_state['numero_nova_carga']}")
        st.markdown("### Inserir Entregas na Carga")
        chaves_input = st.text_area("Insira as Chaves CT-e (uma por linha)")

        col1, col2 = st.columns([5, 1])
        with col1:
            adicionar = st.button("➕ Adicionar Entregas à Carga", key="botao_manual")
        with col2:
            cancelar = st.button("❌", help="Cancelar Nova Carga")

        if cancelar:
            st.session_state["nova_carga_em_criacao"] = False
            st.session_state["numero_nova_carga"] = ""
            st.rerun()

        if adicionar:
            chaves_ct_e_para_adicionar = [re.sub(r"\s+", "", c) for c in chaves_input.splitlines() if c.strip()]
            if not chaves_ct_e_para_adicionar:
                st.warning("Nenhuma Chave CT-e válida informada.")
            else:
                try:
                    # Chamar a sua função existente para adicionar entregas à carga
                    adicionar_entregas_a_carga(chaves_ct_e_para_adicionar)
                except Exception as e:
                    st.error(f"Erro ao adicionar entregas manualmente: {e}")
    # --- FIM: BLOCO DE CRIAÇÃO DE CARGA AVULSA ---

    # --- INÍCIO: CARREGAMENTO DOS DADOS DE ROTAS CONFIRMADAS E EXIBIÇÃO ---
    try:
        with st.spinner("🔄 Carregando dados das entregas..."):
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
        st.info(" Nenhuma Rota Confirmada encontrada.")
        return

    # --- MÉTRICAS GERAIS ---
    col1, col2, _ = st.columns([1, 1, 8])
    with col1:
        st.metric("Total de Rotas", df["Rota"].nunique() if "Rota" in df.columns else 0)
    with col2:
        st.metric("Total de Entregas", len(df))

    # --- DEFINIÇÕES DE BADGES E COLUNAS ---
    def badge(label):
        return f"<span style='background:#eef2f7;border-radius:12px;padding:6px 12px;margin:4px;color:inherit;display:inline-block;'>{label}</span>"

    colunas_exibir = [
        "Serie_Numero_CTRC", "Rota", "Regiao", "Valor do Frete", "Cliente Pagador", "Chave CT-e", "Cliente Destinatario",
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
            if (status === 'AGENDAR' && (!entrega || (typeof entrega === 'string' && entrega.trim() === ''))) {
                return { 'background-color': '#ffe0b2', 'color': '#333' };
            }
            if (particularidade && typeof particularidade === 'string' && particularidade.trim() !== "") {
                return { 'background-color': '#fff59d', 'color': '#333' };
            }
            return null;
        }
    """)
    
    # === MODIFICAÇÃO AQUI: Sanitização e extração de rotas_unicas ===
    rotas_unicas = []
    if 'Rota' in df.columns and not df.empty:
        # 1. Converte para string e remove espaços em branco (início/fim)
        df['Rota'] = df['Rota'].astype(str).str.strip()
        # 2. Substitui strings vazias (ou apenas espaços) por NaN para que dropna funcione
        df['Rota'] = df['Rota'].replace('', np.nan) 
        # 3. Pega os valores únicos e ordena
        rotas_unicas = sorted(df["Rota"].dropna().unique())
    # === FIM DA MODIFICAÇÃO ===

    for rota in rotas_unicas:
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
            badge(f"Valor frete: R$ {formatar_brasileiro(df_rota['Valor do Frete'].sum())}") +
            badge(f"{formatar_brasileiro(df_rota['Cubagem em m³'].sum())} m³") +
            badge(f"{int(df_rota['Quantidade de Volumes'].sum())} volumes"),
            unsafe_allow_html=True
        )

        with st.expander("🔽 Selecionar entregas", expanded=False):
            df_formatado = df_rota[[col for col in colunas_exibir if col in df_rota.columns]].copy()
            df_formatado = apply_brazilian_date_format_for_display(df_formatado)

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
            gb.configure_grid_options(onGridReady=GRID_RESIZE_JS_CODE)

            formatter = JsCode("""
                function(params) {
                    if (!params.value && params.value !== 0) return '';
                    return Number(params.value).toLocaleString('pt-BR', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                    });
                }
            """)

            date_only_formatter = JsCode("""
                function(params) {
                    if (params.value === null || typeof params.value === 'undefined' || params.value === '') return '';
                    const parts = params.value.split(' ')[0];
                    return parts;
                }
            """)
           
            for col in ['Peso Real em Kg', 'Peso Calculado em Kg', 'Cubagem em m³', 'Quantidade de Volumes', 'Valor do Frete']:
                if col in df_formatado.columns:
                    gb.configure_column(col, type=["numericColumn"], valueFormatter=formatter)

            for col in ['Previsao de Entrega', 'Entrega Programada']:
                if col in df_formatado.columns:
                    gb.configure_column(col, valueFormatter=date_only_formatter)

            grid_options = gb.build()

            grid_key = f"grid_rotas_confirmadas_{rota}"
            if grid_key not in st.session_state:
                st.session_state[grid_key] = str(uuid.uuid4())

            with st.spinner(" Carregando entregas da rota no grid..."):
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
                st.info(f"{len(selecionadas)} entrega(s) selecionada(s) para a rota {rota}.")

            # === MODIFICAÇÃO AQUI: Chave do botão ===
            # 🔸 Botão para criar nova carga automaticamente
            if st.button(f"➕ Criar Nova Carga com Entregas Selecionadas", key=f"btn_criar_carga_{rota}"):
                if not selecionadas:
                    st.warning("Selecione ao menos uma entrega.")
                else:
                    try:
                        # 1. Prepara os dados para inserção (a partir das linhas selecionadas do AgGrid)
                        df_para_inserir = pd.DataFrame(selecionadas).drop(columns=["_selectedRowNodeInfo"], errors="ignore").copy()
                        chaves_ctrc_selecionadas = df_para_inserir["Serie_Numero_CTRC"].dropna().astype(str).str.strip().tolist()

                        # NOVO PASSO: Verifique se as entregas já existem em 'cargas_geradas'
                        existing_ctrcs_in_target = set()
                        if chaves_ctrc_selecionadas: # Apenas consulta se há chaves para verificar
                            try:
                                response = supabase.table("cargas_geradas").select("Serie_Numero_CTRC").in_("Serie_Numero_CTRC", chaves_ctrc_selecionadas).execute()
                                if response.data:
                                    existing_ctrcs_in_target = {item["Serie_Numero_CTRC"] for item in response.data}
                            except Exception as e:
                                # Captura erros de comunicação do Supabase durante a verificação de existência
                                st.warning(f"Aviso: Não foi possível verificar entregas existentes na tabela 'cargas_geradas' devido a erro de comunicação: {e}")
                                # Não retornamos aqui, mas a inserção pode falhar se o item já existir e a verificação falhou

                        if existing_ctrcs_in_target:
                            st.warning(f"As seguintes entregas já existem em 'cargas_geradas' e não serão inseridas novamente: {', '.join(existing_ctrcs_in_target)}")
                            df_para_inserir = df_para_inserir[~df_para_inserir["Serie_Numero_CTRC"].isin(existing_ctrcs_in_target)]
                            chaves_ctrc_selecionadas = df_para_inserir["Serie_Numero_CTRC"].dropna().astype(str).str.strip().tolist()
                            
                            if not chaves_ctrc_selecionadas:
                                st.info("Todas as entregas selecionadas já existem na carga. Nenhuma nova entrega para processar.")
                                st.session_state["reload_rotas_confirmadas"] = True # Recarrega a página atual para limpar a seleção
                                st.session_state["reload_cargas_geradas"] = True   # Recarrega a página de destino (para o caso de já estarem lá e não serem exibidas)
                                st.rerun()
                                return # Sai da função se não há entregas para inserir

                        # Se após a filtragem não houver mais entregas para inserir, pare.
                        if not chaves_ctrc_selecionadas:
                            st.info("Nenhuma entrega elegível para ser adicionada à carga.")
                            st.session_state["reload_rotas_confirmadas"] = True
                            st.rerun()
                            return

                        # ... (Seu código existente para tratamento de datas para Supabase) ...
                                                # O dataframe 'df_para_inserir' (que veio de 'selecionadas') contém colunas de data como STRINGS formatadas.
                        # Precisamos convertê-las de volta para datetime antes de enviar para o Supabase.
                        # As colunas Previsao de Entrega e Entrega Programada virão como 'DD-MM-AAAA'.
                        # As outras colunas de data (se selecionadas) virão como 'DD-MM-AAAA HH:MM:SS'.

                        for col_name in GLOBAL_DATE_DISPLAY_COLUMNS: # GLOBAL_DATE_DISPLAY_COLUMNS é a lista abrangente
                            if col_name in df_para_inserir.columns:
                                # Determina o formato de input correto para pd.to_datetime com base na coluna
                                if col_name in DATE_ONLY_REPARSE_COLUMNS:
                                    # Espera formato 'DD-MM-AAAA' (sem hora)
                                    input_format_str = DATE_ONLY_DISPLAY_FORMAT_STRING # (e.g., '%d-%m-%Y')
                                else:
                                    # Espera formato 'DD-MM-AAAA HH:MM:SS' (com hora)
                                    input_format_str = DATE_DISPLAY_FORMAT_STRING # (e.g., '%d-%m-%Y %H:%M:%S')

                                # Tenta converter a string para um objeto datetime
                                dt_obj_series = pd.to_datetime(df_para_inserir[col_name], format=input_format_str, errors='coerce')
                                
                                # Se o objeto de data/hora é naive (sem fuso horário), assumimos que é fuso do Brasil
                                # e o convertemos para UTC, que é o que o Supabase prefere.
                                # Adiciona timezone-aware local e converte para UTC
                                dt_obj_series = dt_obj_series.dt.tz_localize(FUSO_BRASIL, ambiguous='NaT', nonexistent='NaT')
                                dt_obj_series = dt_obj_series.dt.tz_convert('UTC')

                                # Converte o objeto datetime (agora UTC) para a string ISO 8601 que o Supabase espera
                                df_para_inserir[col_name] = dt_obj_series.apply(
                                    lambda x: x.isoformat(timespec='seconds').replace('+00:00', 'Z') if pd.notna(x) else None
                                )
                        
                        df_para_inserir = df_para_inserir.replace([np.nan, pd.NaT, np.inf, -np.inf, ""], None)
                        


                        # 3. GERAÇÃO DO NÚMERO DA CARGA (COM VALIDAÇÃO DE UNICIDADE)
                        numero_carga = gerar_proximo_numero_carga(supabase)
                        if not numero_carga: # Se a função retornou None, significa que falhou a geração de um número único.
                            st.error("Não foi possível gerar um número de carga único. Operação cancelada.")
                            st.session_state["reload_rotas_confirmadas"] = True # Força reload para limpar o estado
                            st.rerun()
                            return

                        df_para_inserir["numero_carga"] = numero_carga
                        df_para_inserir["Data_Hora_Gerada"] = data_hora_brasil_iso()

                        # 4. Filtra apenas as colunas válidas para a tabela de destino
                        colunas_validas_carga = [
                            'Serie_Numero_CTRC', 'Rota', 'Regiao', 'Cliente Pagador', 'Chave CT-e', 'Cliente Destinatario',
                            'Cidade de Entrega', 'Bairro do Destinatario', 'Previsao de Entrega',
                            'Numero da Nota Fiscal', 'Status', 'Entrega Programada', 'Particularidade',
                            'Codigo da Ultima Ocorrencia', 'Peso Real em Kg', 'Peso Calculado em Kg',
                            'Cubagem em m³', 'Quantidade de Volumes', 'Valor do Frete',
                            'numero_carga', 'Data_Hora_Gerada'
                        ]
                        dados_para_insercao = df_para_inserir[[col for col in colunas_validas_carga if col in df_para_inserir.columns]].to_dict(orient="records")

                        if not dados_para_insercao:
                            st.warning("Nenhum dado válido para inserir na carga após o processamento.")
                            st.session_state["reload_rotas_confirmadas"] = True
                            st.rerun()
                            return

                        # 5. Tenta inserir os dados na tabela 'cargas_geradas' com re-tentativas
                        insert_success = False
                        for tentativa in range(2):
                            try:
                                st.info(f"DEBUG: Tentando inserir {len(dados_para_insercao)} registros na tabela 'cargas_geradas' (tentativa {tentativa+1}).")
                                insert_response = supabase.table("cargas_geradas").insert(dados_para_insercao).execute()

                                # Se a execução chegou aqui sem exceção, a chamada API foi bem-sucedida.
                                # Agora verificamos se o .data contém os registros inseridos.
                                if insert_response.data:
                                    st.success(f"DEBUG: Inserção em 'cargas_geradas' na Tentativa {tentativa+1} bem-sucedida! {len(insert_response.data)} registros inseridos.")
                                    insert_success = True
                                    break # Sucesso, sai do loop de retries
                                else:
                                    # Caso raro: API retorna sucesso, mas .data é vazio. Pode ser RLS impedindo retorno dos dados.
                                    st.warning(f"DEBUG: Inserção em 'cargas_geradas' na Tentativa {tentativa+1} retornou sem erro, mas sem dados afetados. Resposta: {insert_response}")
                                    if tentativa == 0: time.sleep(1) # Tenta novamente
                                    continue # Próxima tentativa

                            except Exception as e_insert:
                                error_message = str(e_insert)
                                # Verifica se é o erro de chave duplicada (PostgreSQL 23505)
                                if "23505" in error_message and "duplicate key value violates unique constraint" in error_message:
                                    st.warning(f"DEBUG: Erro de chave duplicada ({error_message}) detectado. A entrega já existe em 'cargas_geradas'. Considerado sucesso para esta fase (já está lá).")
                                    insert_success = True # A entrega já está no destino, então a "operação" foi bem-sucedida
                                    break # Sai do loop de retries
                                else:
                                    # Loga qualquer outra exceção inesperada
                                    st.error(f"DEBUG: Exceção inesperada durante inserção em 'cargas_geradas': {e_insert} (Tipo: {type(e_insert)})")
                                    st.warning(f"Tentativa {tentativa+1}/2: Exceção geral durante inserção em 'cargas_geradas': {e_insert}")
                                    if tentativa == 0: time.sleep(1) # Tenta novamente
                                    continue # Próxima tentativa
                        
                        # --- MODIFICAÇÃO CHAVE AQUI ---
                        if not insert_success:
                            st.error(f"❌ Falha completa ao inserir entregas na carga após múltiplas tentativas. As entregas NÃO foram movidas de 'Rotas Confirmadas'. Por favor, verifique a tabela 'cargas_geradas' manualmente.")
                            st.session_state["reload_cargas_geradas"] = True # Garante que a página de cargas geradas seja atualizada
                            st.session_state["reload_rotas_confirmadas"] = True # Garante que a página atual seja atualizada
                            st.rerun() # Força uma nova renderização
                            return # Sai para evitar processamento adicional se a inserção falhou

                        st.success(f"✅ {len(dados_para_insercao)} entregas inseridas na Carga {numero_carga}.")

                        # 6. SOMENTE SE A INSERÇÃO FOI BEM-SUCEDIDA, TENTA DELETAR DA ORIGEM ('rotas_confirmadas')
                        delete_success = False
                        deleted_count = 0 # Para rastrear quantas foram realmente deletadas
                        for tentativa in range(2):
                            try:
                                st.info(f"DEBUG: Tentando deletar {len(chaves_ctrc_selecionadas)} CTRCs da tabela 'rotas_confirmadas' (tentativa {tentativa+1}).")
                                # Executa a deleção
                                delete_response = supabase.table("rotas_confirmadas").delete().in_("Serie_Numero_CTRC", chaves_ctrc_selecionadas).execute()

                                # Se a execução chegou aqui sem exceção, a chamada API foi bem-sucedida.
                                # Agora verificamos se o .data contém os registros deletados.
                                if delete_response.data: # Para DELETE, .data contém a lista de objetos deletados
                                    deleted_count = len(delete_response.data)
                                    st.success(f"DEBUG: Deleção em 'rotas_confirmadas' na Tentativa {tentativa+1} bem-sucedida! {deleted_count} registros realmente deletados.")
                                    delete_success = True
                                    break # Sucesso, sai do loop de retries
                                else:
                                    # Este caminho é tomado se execute() não levantou um erro, mas .data está vazio.
                                    # Isso é um forte indicador de RLS impedindo a deleção, ou que não havia linhas correspondentes.
                                    if chaves_ctrc_selecionadas: # Se realmente tentamos deletar algo
                                        st.warning(f"DEBUG: Deleção em 'rotas_confirmadas' na Tentativa {tentativa+1} retornou sem erro, mas 0 registros deletados. Possível problema de RLS ou itens não encontrados. Resposta: {delete_response}")
                                        # Como o Supabase não lançou um erro, mas disse 0 linhas, consideramos como "sucesso" (a API funcionou),
                                        # mas alertamos o usuário se ele esperava deleções.
                                        delete_success = True # Considera "sucesso" porque a chamada API funcionou
                                        break # Sai do loop de retries
                                    else:
                                        # Não havia itens para deletar, então é uma operação bem-sucedida de não-operação.
                                        st.info(f"DEBUG: Nenhuma chave para deletar de 'rotas_confirmadas'. Operação de deleção não necessária.")
                                        delete_success = True
                                        break # Sai do loop de retries

                            except Exception as e_delete:
                                # Captura qualquer exceção lançada por execute() (ex: problemas de rede, erros gerais da API)
                                error_message = str(e_delete)
                                st.error(f"DEBUG: Exceção inesperada durante deleção de 'rotas_confirmadas': {e_delete} (Tipo: {type(e_delete)})")
                                st.warning(f"Tentativa {tentativa+1}/2: Exceção geral durante remoção de 'rotas_confirmadas': {e_delete}")
                                if tentativa == 0: time.sleep(1) # Tenta novamente
                                # Se for um erro geral, delete_success permanece False, então ele tentará novamente ou falhará completamente.

                        # --- MODIFICAÇÃO CHAVE AQUI ---
                        if not delete_success: # Isso agora realmente significa que a operação de deleção falhou após as retries.
                            st.error(f"⚠️ As entregas foram inseridas em 'cargas_geradas', mas **FALHARAM AO SEREM REMOVIDAS** de 'rotas_confirmadas' após múltiplas tentativas. "
                                     f"**POR FAVOR, VERIFIQUE AS POLÍTICAS RLS NO SUPABASE PARA A TABELA `rotas_confirmadas` E A CONSISTÊNCIA DOS DADOS MANUALMENTE.**")
                        else:
                            if deleted_count > 0:
                                st.success(f"✅ {deleted_count} entregas removidas de 'Rotas Confirmadas'.")
                            else:
                                st.warning(f"ℹ️ Deleção de 'Rotas Confirmadas' concluída, mas 0 entregas foram removidas. Verifique RLS ou se os itens já haviam sido movidos.")
                        # --- FIM DA MODIFICAÇÃO CHAVE ---

                        # 7. Atualiza o estado da sessão para forçar a recarga dos caches e grids
                        st.session_state["reload_rotas_confirmadas"] = True
                        st.session_state["reload_cargas_geradas"] = True
                        st.session_state["reload_pre_roterizacao"] = True
                        st.session_state["reload_aprovacao_diretoria"] = True
                        st.session_state["reload_aprovacao_custos"] = True
                        st.session_state["reload_cargas_aprovadas"] = True

                        # Remove todas as chaves de grid das páginas afetadas para forçar uma recriação completa
                        # Isso inclui a página atual e a página de destino
                        keys_to_pop_rotas_confirmadas = [key for key in st.session_state.keys() if key.startswith("grid_rotas_confirmadas_")]
                        for key in keys_to_pop_rotas_confirmadas:
                            st.session_state.pop(key, None)

                        keys_to_pop_cargas_geradas = [key for key in st.session_state.keys() if key.startswith("grid_carga_gerada_")]
                        for key in keys_to_pop_cargas_geradas:
                            st.session_state.pop(key, None)

                        # Adiciona um pequeno atraso para permitir que o banco de dados propague a gravação
                        time.sleep(1.5) # Aumentado para 1.5 segundos para maior robustez na sincronização

                        st.rerun()

                    except Exception as e_main:
                        st.error(f"❌ Ocorreu um erro inesperado durante a operação de mover entregas para cargas: {e_main}")
                        st.warning("A operação pode ter sido interrompida. Por favor, verifique a situação das entregas nas tabelas 'Rotas Confirmadas' e 'Cargas Geradas'.")
                        st.session_state["reload_rotas_confirmadas"] = True
                        st.rerun()

# ... (restante da sua função pagina_rotas_confirmadas) ...


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

                # ... Seu código anterior da pagina_rotas_confirmadas ...

            # 🔸 Botão para criar nova carga automaticamente
                if st.button(f"➕ Criar Nova Carga com Entregas Selecionadas", key=f"botao_rota_{rota}"):
                    if not selecionadas:
                        st.warning("Selecione ao menos uma entrega.")
                    else:
                        try:
                            # 1. Prepara os dados para inserção (a partir das linhas selecionadas do AgGrid)
                            df_para_inserir = pd.DataFrame(selecionadas).drop(columns=["_selectedRowNodeInfo"], errors="ignore").copy()
                            chaves_ctrc_selecionadas = df_para_inserir["Serie_Numero_CTRC"].dropna().astype(str).str.strip().tolist()

                            # NOVO PASSO: Verifique se as entregas já existem em 'cargas_geradas'
                            existing_ctrcs_in_target = set()
                            if chaves_ctrc_selecionadas: # Apenas consulta se há chaves para verificar
                                try:
                                    response = supabase.table("cargas_geradas").select("Serie_Numero_CTRC").in_("Serie_Numero_CTRC", chaves_ctrc_selecionadas).execute()
                                    if response.data:
                                        existing_ctrcs_in_target = {item["Serie_Numero_CTRC"] for item in response.data}
                                except Exception as e:
                                    # Captura erros de comunicação do Supabase durante a verificação de existência
                                    st.warning(f"Aviso: Não foi possível verificar entregas existentes na tabela 'cargas_geradas' devido a erro de comunicação: {e}")
                                    # Não retornamos aqui, mas a inserção pode falhar se o item já existir e a verificação falhou

                            if existing_ctrcs_in_target:
                                st.warning(f"As seguintes entregas já existem em 'cargas_geradas' e não serão inseridas novamente: {', '.join(existing_ctrcs_in_target)}")
                                df_para_inserir = df_para_inserir[~df_para_inserir["Serie_Numero_CTRC"].isin(existing_ctrcs_in_target)]
                                chaves_ctrc_selecionadas = df_para_inserir["Serie_Numero_CTRC"].dropna().astype(str).str.strip().tolist()
                                
                                if not chaves_ctrc_selecionadas:
                                    st.info("Todas as entregas selecionadas já existem na carga. Nenhuma nova entrega para processar.")
                                    st.session_state["reload_rotas_confirmadas"] = True # Recarrega a página atual para limpar a seleção
                                    st.session_state["reload_cargas_geradas"] = True   # Recarrega a página de destino (para o caso de já estarem lá e não serem exibidas)
                                    st.rerun()
                                    return # Sai da função se não há entregas para inserir

                            # Se após a filtragem não houver mais entregas para inserir, pare.
                            if not chaves_ctrc_selecionadas:
                                st.info("Nenhuma entrega elegível para ser adicionada à carga.")
                                st.session_state["reload_rotas_confirmadas"] = True
                                st.rerun()
                                return

                            # ... (Seu código existente para tratamento de datas para Supabase) ...
                            for col_name in GLOBAL_DATE_DISPLAY_COLUMNS:
                                if col_name in df_para_inserir.columns:
                                    dt_obj = pd.to_datetime(df_para_inserir[col_name], format=DATE_DISPLAY_FORMAT_STRING, errors='coerce')
                                    dt_obj = dt_obj.dt.tz_localize(FUSO_BRASIL)
                                    dt_obj = dt_obj.dt.tz_convert('UTC')
                                    df_para_inserir[col_name] = dt_obj.apply(
                                        lambda x: x.isoformat(timespec='seconds').replace('+00:00', 'Z') if pd.notna(x) else None
                                    )
                            df_para_inserir = df_para_inserir.replace([np.nan, pd.NaT, np.inf, -np.inf, ""], None)


                            # 3. GERAÇÃO DO NÚMERO DA CARGA (COM VALIDAÇÃO DE UNICIDADE)
                            numero_carga = gerar_proximo_numero_carga(supabase)
                            if not numero_carga: # Se a função retornou None, significa que falhou a geração de um número único.
                                st.error("Não foi possível gerar um número de carga único. Operação cancelada.")
                                st.session_state["reload_rotas_confirmadas"] = True # Força reload para limpar o estado
                                st.rerun()
                                return

                            df_para_inserir["numero_carga"] = numero_carga
                            df_para_inserir["Data_Hora_Gerada"] = data_hora_brasil_iso()

                            # 4. Filtra apenas as colunas válidas para a tabela de destino
                            colunas_validas_carga = [
                                'Serie_Numero_CTRC', 'Rota', 'Regiao', 'Cliente Pagador', 'Chave CT-e', 'Cliente Destinatario',
                                'Cidade de Entrega', 'Bairro do Destinatario', 'Previsao de Entrega',
                                'Numero da Nota Fiscal', 'Status', 'Entrega Programada', 'Particularidade',
                                'Codigo da Ultima Ocorrencia', 'Peso Real em Kg', 'Peso Calculado em Kg',
                                'Cubagem em m³', 'Quantidade de Volumes', 'Valor do Frete',
                                'numero_carga', 'Data_Hora_Gerada'
                            ]
                            dados_para_insercao = df_para_inserir[[col for col in colunas_validas_carga if col in df_para_inserir.columns]].to_dict(orient="records")

                            if not dados_para_insercao:
                                st.warning("Nenhum dado válido para inserir na carga após o processamento.")
                                st.session_state["reload_rotas_confirmadas"] = True
                                st.rerun()
                                return

                            # 5. Tenta inserir os dados na tabela 'cargas_geradas' com re-tentativas
                            insert_success = False
                            for tentativa in range(2):
                                try:
                                    insert_response = supabase.table("cargas_geradas").insert(dados_para_insercao).execute()
                                    if insert_response.error:
                                        st.warning(f"Tentativa {tentativa+1}/2: Erro ao inserir na tabela 'cargas_geradas': {insert_response.error.message}")
                                        if tentativa == 0: time.sleep(1)
                                    else:
                                        insert_success = True
                                        break
                                except Exception as e_insert:
                                    st.warning(f"Tentativa {tentativa+1}/2: Exceção durante inserção em 'cargas_geradas': {e_insert}")
                                    if tentativa == 0: time.sleep(1)
                            
                            # --- MODIFICAÇÃO CHAVE AQUI ---
                            if not insert_success:
                                st.error(f"❌ Falha completa ao inserir entregas na carga após múltiplas tentativas. As entregas NÃO foram movidas de 'Rotas Confirmadas' ou já existiam. Por favor, verifique a tabela 'cargas_geradas' manualmente.")
                                st.session_state["reload_cargas_geradas"] = True # Garante que a página de cargas geradas seja atualizada
                                st.session_state["reload_rotas_confirmadas"] = True # Garante que a página atual seja atualizada
                                st.rerun() # Força uma nova renderização
                                return # Sai para evitar processamento adicional se a inserção falhou

                            st.success(f"✅ {len(dados_para_insercao)} entregas inseridas na Carga {numero_carga}.")

                            # 6. SOMENTE SE A INSERÇÃO FOI BEM-SUCEDIDA, TENTA DELETAR DA ORIGEM ('rotas_confirmadas')
                            delete_success = False
                            for tentativa in range(2):
                                try:
                                    delete_response = supabase.table("rotas_confirmadas").delete().in_("Serie_Numero_CTRC", chaves_ctrc_selecionadas).execute()
                                    if delete_response.error:
                                        st.warning(f"Tentativa {tentativa+1}/2: Erro ao remover de 'rotas_confirmadas': {delete_response.error.message}")
                                        if tentativa == 0: time.sleep(1)
                                    else:
                                        delete_success = True
                                        break
                                except Exception as e_delete:
                                    st.warning(f"Tentativa {tentativa+1}/2: Exceção durante remoção de 'rotas_confirmadas': {e_delete}")
                                    if tentativa == 0: time.sleep(1)

                            if not delete_success:
                                st.warning(f"⚠️ As entregas foram inseridas em 'cargas_geradas', mas NÃO foram removidas de 'rotas_confirmadas' após múltiplas tentativas. Por favor, verifique manualmente as duas tabelas para evitar duplicação.")
                            else:
                                st.success(f"✅ {len(chaves_ctrc_selecionadas)} entregas removidas de 'Rotas Confirmadas'.")

                            # 7. Atualiza o estado da sessão para forçar a recarga dos caches e grids
                            st.session_state["reload_rotas_confirmadas"] = True
                            st.session_state["reload_cargas_geradas"] = True
                            st.session_state["reload_pre_roterizacao"] = True
                            st.session_state["reload_aprovacao_diretoria"] = True
                            st.session_state["reload_aprovacao_custos"] = True
                            st.session_state["reload_cargas_aprovadas"] = True

                            # Remove todas as chaves de grid da página "Cargas Geradas" para forçar uma recriação completa
                            keys_to_pop_cargas_geradas = [key for key in st.session_state.keys() if key.startswith("grid_carga_gerada_")]
                            for key in keys_to_pop_cargas_geradas:
                                st.session_state.pop(key, None)

                            # Adiciona um pequeno atraso para permitir que o banco de dados propague a gravação
                            time.sleep(1.5) # Aumentado para 1.5 segundos para maior robustez na sincronização

                            grid_key_of_current_rota = f"grid_rotas_confirmadas_{rota}"
                            st.session_state.pop(grid_key_of_current_rota, None)
                            st.session_state.pop(f"marcar_todas_rota_confirmada_{rota}", None)

                            st.rerun()

                        except Exception as e_main:
                            st.error(f"❌ Ocorreu um erro inesperado durante a operação: {e_main}")
                            st.warning("A operação pode ter sido interrompida. Por favor, verifique a situação das entregas nas tabelas 'Rotas Confirmadas' e 'Cargas Geradas'.")
                            st.session_state["reload_rotas_confirmadas"] = True
                            st.rerun()
    

                            return

                            st.success(f"✅ {len(dados_para_insercao)} entregas adicionadas à Carga {carga_escolhida}.")

                            # 5. SOMENTE SE A INSERÇÃO FOI BEM-SUCEDIDA, TENTA DELETAR DA ORIGEM ('rotas_confirmadas')
                            delete_success = False
                            for tentativa in range(2):
                                try:
                                    delete_response = supabase.table("rotas_confirmadas").delete().in_("Serie_Numero_CTRC", chaves_ctrc_selecionadas).execute()
                                    if delete_response.error:
                                        st.warning(f"Tentativa {tentativa+1}/2: Erro ao remover de 'rotas_confirmadas': {delete_response.error.message}")
                                        if tentativa == 0: time.sleep(1)
                                    else:
                                        delete_success = True
                                        break
                                except Exception as e_delete:
                                    st.warning(f"Tentativa {tentativa+1}/2: Exceção durante remoção de 'rotas_confirmadas': {e_delete}")
                                    if tentativa == 0: time.sleep(1)

                            if not delete_success:
                                st.warning(f"⚠️ As entregas foram adicionadas à carga {carga_escolhida}, mas NÃO foram removidas de 'rotas_confirmadas' após múltiplas tentativas. Por favor, verifique manualmente as duas tabelas para evitar duplicação.")
                            else:
                                st.success(f"✅ {len(chaves_ctrc_selecionadas)} entregas removidas de 'Rotas Confirmadas'.")

                            # 6. Atualiza o estado da sessão para forçar a recarga dos caches e grids
                            st.session_state["reload_rotas_confirmadas"] = True
                            st.session_state["reload_cargas_geradas"] = True
                            st.session_state["reload_pre_roterizacao"] = True
                            st.session_state["reload_aprovacao_diretoria"] = True
                            st.session_state["reload_aprovacao_custos"] = True
                            st.session_state["reload_cargas_aprovadas"] = True

                            grid_key_of_current_rota = f"grid_rotas_confirmadas_{rota}"
                            st.session_state.pop(grid_key_of_current_rota, None)
                            st.session_state.pop(f"marcar_todas_rota_confirmada_{rota}", None)

                            st.rerun()

                        except Exception as e_main:
                            st.error(f"❌ Ocorreu um erro inesperado durante a operação: {e_main}")
                            st.warning("A operação pode ter sido interrompida. Por favor, verifique a situação das entregas nas tabelas 'Rotas Confirmadas' e 'Cargas Geradas'.")
                            st.session_state["reload_rotas_confirmadas"] = True
                            st.rerun()
            else:
                st.info("Nenhuma carga existente encontrada para seleção.")



##########################################

# PÁGINA CARGAS GERADAS

##########################################
def pagina_cargas_geradas():
    st.markdown("## Cargas Geradas")

    # Define os limites de custo por região aqui, pois o cálculo será feito nesta página.
    MAX_COST_PER_REGION = {
        'INTERIOR 1': 0.35,  # 35%
        'INTERIOR 2': 0.45,  # 45%
        'POA CAPITAL': 0.30   # 30%
    }

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

            # Garante que 'Regiao' seja string e trata nulos para o cálculo
            if 'Regiao' in df.columns:
                df['Regiao'] = df['Regiao'].astype(str).str.strip().str.upper().replace('NAN', 'NÃO DEFINIDA')

            df_display = df.copy()

            df_display = apply_brazilian_date_format_for_display(df_display)

            df_display = df_display.replace([np.nan, None], "")

            numeric_cols_for_formatting = ['Peso Real em Kg', 'Peso Calculado em Kg', 'Cubagem em m³', 'Quantidade de Volumes', 'Valor do Frete']
            for col in numeric_cols_for_formatting:
                if col in df_display.columns:
                    df_display[col] = pd.to_numeric(df_display[col], errors='coerce').fillna(0)

        col1, col2, _ = st.columns([1, 1, 8])
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
        
        colunas_exibir = [
            "Serie_Numero_CTRC", "Rota", "Regiao", "Valor do Frete", "Cliente Pagador", "Chave CT-e", "Cliente Destinatario",
            "Cidade de Entrega", "Bairro do Destinatario", "Previsao de Entrega",
            "Numero da Nota Fiscal", "Status", "Entrega Programada", "Particularidade",
            "Codigo da Ultima Ocorrencia", "Peso Real em Kg", "Peso Calculado em Kg",
            "Cubagem em m³", "Quantidade de Volumes"
        ]

        cargas_unicas = sorted(df["numero_carga"].dropna().unique())

        for carga in cargas_unicas:
            # df_carga_raw para cálculos numéricos e 'Regiao'
            df_carga_raw = df[df["numero_carga"] == carga].copy()
            
            if df_carga_raw.empty:
                continue

            # --- CÁLCULOS PARA A SUGESTÃO DE VALOR DE CONTRATAÇÃO ---
            total_frete_carga = df_carga_raw["Valor do Frete"].sum()

            dominant_region = 'NÃO DEFINIDA'
            if 'Regiao' in df_carga_raw.columns and not df_carga_raw['Regiao'].empty:
                regions_to_consider = df_carga_raw['Regiao'][df_carga_raw['Regiao'] != 'NÃO DEFINIDA']
                if not regions_to_consider.empty:
                    dominant_region = regions_to_consider.value_counts().idxmax()
                elif not df_carga_raw['Regiao'].empty:
                    dominant_region = df_carga_raw['Regiao'].iloc[0]

            max_cost_allowed = MAX_COST_PER_REGION.get(dominant_region, None)
            
            valor_sugerido_contratacao = 0.0
            if total_frete_carga > 0 and max_cost_allowed is not None:
                valor_sugerido_contratacao = total_frete_carga * max_cost_allowed
                valor_sugerido_contratacao = round(valor_sugerido_contratacao, 2)
                valor_sugerido_contratacao = max(0.0, valor_sugerido_contratacao)

            st.markdown(f"""
            <div style="margin-top:20px;padding:10px;background:#e8f0fe;border-left:4px solid #34a853;border-radius:6px;display:inline-block;max-width:100%;">
                <strong>Carga:</strong> {carga}
            </div>
            """, unsafe_allow_html=True)

            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(
                    badge(f"{len(df_carga_raw)} entregas") +
                    badge(f"{formatar_brasileiro(df_carga_raw['Peso Calculado em Kg'].sum())} kg calc") +
                    badge(f"{formatar_brasileiro(df_carga_raw['Peso Real em Kg'].sum())} kg real") +
                    badge(f"Valor frete: R$ {formatar_brasileiro(total_frete_carga)}") +
                    badge(f"{formatar_brasileiro(df_carga_raw['Cubagem em m³'].sum())} m³") +
                    badge(f"{int(df_carga_raw['Quantidade de Volumes'].sum())} volumes"),
                    unsafe_allow_html=True
                )

            with st.expander("🔽 Ver entregas da carga", expanded=False):
                checkbox_key = f"marcar_todas_carga_gerada_{carga}"
                if checkbox_key not in st.session_state:
                    st.session_state[checkbox_key] = False

                marcar_todas = st.checkbox("Marcar todas", key=checkbox_key)

                with st.spinner("Carregando entregas da carga no grid..."):
                    df_formatado = df_display[df_display["numero_carga"] == carga][[col for col in colunas_exibir if col in df_display.columns]]

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

                    for col in numeric_cols_for_formatting:
                        if col in df_formatado.columns:
                            gb.configure_column(col, type=["numericColumn"], valueFormatter=formatter)

                    grid_options = gb.build()

                    grid_key_id = f"grid_carga_gerada_{carga}"
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
                    col_ret, col_aprov = st.columns([1, 1])

                    with col_ret:
                        if st.button(f"♻️ Retirar da Carga", key=f"btn_retirar_{carga}"):
                            try:
                                with st.spinner("🔄 Retirando entregas da carga..."):
                                    df_remover = pd.DataFrame(selecionadas)
                                    df_remover = df_remover.drop(columns=["_selectedRowNodeInfo"], errors="ignore")
                                    df_remover["Status"] = "AGENDAR"
                                    df_remover = df_remover.drop(columns=["numero_carga"], errors="ignore")

                                    if "Data_Hora_Gerada" in df_remover.columns:
                                        df_remover["Data_Hora_Gerada"] = df_remover["Data_Hora_Gerada"].apply(
                                            lambda x: datetime.strptime(x, "%d-%m-%Y %H:%M:%S").isoformat() if x else None
                                        )

                                    df_remover = df_remover.replace([np.nan, pd.NaT, "", np.inf, -np.inf], None)
                                    registros = df_remover.to_dict(orient="records")

                                    supabase.table("rotas_confirmadas").insert(registros).execute()

                                    chaves = df_remover["Serie_Numero_CTRC"].dropna().astype(str).tolist()
                                    supabase.table("cargas_geradas").delete().in_("Serie_Numero_CTRC", chaves).execute()

                                    dados_restantes = supabase.table("cargas_geradas").select("numero_carga").eq("numero_carga", carga).execute().data
                                    if not dados_restantes:
                                        supabase.table("cargas_geradas").delete().eq("numero_carga", carga).execute()

                                    st.session_state.pop("df_cargas_cache", None)
                                    grid_key_id = f"grid_carga_gerada_{carga}"
                                    st.session_state.pop(grid_key_id, None)
                                    st.session_state.pop(checkbox_key, None)

                                    st.session_state["reload_cargas_geradas"] = True
                                    st.session_state["reload_rotas_confirmadas"] = True 

                                    # --- ADIÇÃO CRÍTICA PARA INVALIDAR A KEY DO AGGRID DAS ROTAS AFETADAS ---
                                    # Obter as rotas únicas das entregas que foram removidas
                                    rotas_afetadas = df_remover["Rota"].dropna().unique()
                                    for rota_afetada in rotas_afetadas:
                                        # Construir a chave do grid da rota afetada
                                        grid_key_rotas_confirmadas = f"grid_rotas_confirmadas_{rota_afetada}"
                                        # Remover a chave do estado da sessão para forçar a recriação do grid
                                        if grid_key_rotas_confirmadas in st.session_state:
                                            st.session_state.pop(grid_key_rotas_confirmadas, None)

                                    st.success(f"✅ {len(chaves)} entrega(s) removida(s) da carga {carga} e retornada(s) para Rotas Confirmadas.")
                                    
                                    st.rerun()

                            except Exception as e:
                                st.error(f"Erro ao retirar entregas da carga: {e}")

                    with col_aprov:
                        valor_contratacao_key = f"valor_contratacao_{carga}"
                        
                        # --- EXIBIÇÃO DA SUGESTÃO DE VALOR DE CONTRATAÇÃO ---
                        st.markdown("---<br>", unsafe_allow_html=True) # Separador visual
                        st.subheader(f"Valor da Contratação da Carga {carga}")
                        
                        if valor_sugerido_contratacao > 0:
                            st.info(f"**Sugestão de Valor:** Para atingir a meta da região '{dominant_region}' ({MAX_COST_PER_REGION.get(dominant_region, 0)*100:.0f}%), o valor ideal seria de **R$ {formatar_brasileiro(valor_sugerido_contratacao)}**")
                        elif total_frete_carga > 0:
                            st.warning(f"Não foi possível calcular uma sugestão de valor de contratação para a região '{dominant_region}'.")
                        else:
                            st.info("Não foi possível calcular uma sugestão de valor de contratação (frete total zero).")

                        valor_contratacao = st.number_input(
                            "Valor da Contratação da Carga (R$)",
                            min_value=0.0,
                            value=valor_sugerido_contratacao, # Pré-preenche com a sugestão
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

                                        df_aprovar_custos["numero_carga"] = carga
                                        df_aprovar_custos["valor_contratacao"] = valor_contratacao # Garante que o valor do input é salvo

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
                                            
                                            st.rerun()
                                        else:
                                            st.warning("Nenhuma entrega válida selecionada para enviar para aprovação de custos.")
                                except Exception as e:
                                    st.error(f"❌ Erro ao enviar entregas para aprovação de custos: {e}")

    except Exception as e:
        st.error(f"❌ Erro ao enviar entregas para aprovação de custos: {e}")

# ==============================================================================
# FUNÇÃO: pagina_aprovacao_custos() - ATUALIZADA
# ==============================================================================
def pagina_aprovacao_custos():
    st.markdown("## Aprovação de Custos")

    # Define os limites de custo por região aqui, pois o cálculo será feito nesta página.
    MAX_COST_PER_REGION = {
        'INTERIOR 1': 0.35,  # 35%
        'INTERIOR 2': 0.45,  # 45%
        'POA CAPITAL': 0.30   # 30%
    }

    current_user_class = st.session_state.get("classe", "colaborador")
    is_user_aprovador = (current_user_class == "aprovador")

    if not is_user_aprovador:
        st.warning("⛔ Apenas usuários com classe 'aprovador' podem realizar ações de aprovação de custos.")

    try:
        with st.spinner("🔄 Carregando dados para aprovação de custos..."):
            recarregar = st.session_state.pop("reload_aprovacao_custos", False)
            if recarregar or "df_aprovacao_custos_cache" not in st.session_state:
                dados = supabase.table("aprovacao_custos").select("*").execute().data
                df = pd.DataFrame(dados)
                # Garante que 'numero_carga' seja tratado como string no cache
                if not df.empty and 'numero_carga' in df.columns:
                    df['numero_carga'] = df['numero_carga'].astype(str)
                st.session_state["df_aprovacao_custos_cache"] = df
            else:
                df = st.session_state["df_aprovacao_custos_cache"]

        if df.empty:
            st.info("Nenhuma carga pendente de aprovação de custos.")
            return

        df.columns = df.columns.str.strip()


        if 'numero_carga' in df.columns:
            df['numero_carga'] = df['numero_carga'].astype(str)

        numeric_cols_to_convert = [
            'Peso Real em Kg', 'Peso Calculado em Kg', 'Cubagem em m³',
            'Quantidade de Volumes', 'Valor do Frete', 'valor_contratacao'
        ]
        for col in numeric_cols_to_convert:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Garante que 'Regiao' seja string e trata nulos para o cálculo
        if 'Regiao' in df.columns:
            df['Regiao'] = df['Regiao'].astype(str).str.strip().str.upper().replace('NAN', 'NÃO DEFINIDA')


        col1, col2, _ = st.columns([1, 1, 8])
        with col1:
            st.metric("Total de Cargas Pendentes", df["numero_carga"].nunique() if "numero_carga" in df.columns else 0)
        with col2:
            st.metric("Total de Entregas Pendentes", len(df))

        colunas_exibir = [
            "Serie_Numero_CTRC", "Rota", "Regiao", "Valor do Frete", "Cliente Pagador", "Chave CT-e", "Cliente Destinatario",
            "Cidade de Entrega", "Bairro do Destinatario", "Previsao de Entrega",
            "Numero da Nota Fiscal", "Status", "Entrega Programada", "Particularidade",
            "Codigo da Ultima Ocorrencia", "Peso Real em Kg", "Peso Calculado em Kg",
            "Cubagem em m³", "Quantidade de Volumes", "valor_contratacao", "numero_carga"
        ]

        cargas_unicas = sorted(df["numero_carga"].dropna().unique())

        for carga in cargas_unicas:
        
            st.write(f"DEBUG: Tentando renderizar a carga: {carga}")
            df_carga = df[df["numero_carga"] == carga].copy()
            if df_carga.empty:
                st.write(f"DEBUG: df_carga vazia para {carga}. Pulando.")
                continue

            valor_contratacao_carga_existente = df_carga["valor_contratacao"].iloc[0] if "valor_contratacao" in df_carga.columns and not df_carga["valor_contratacao"].isnull().all() else 0.0
            
            # --- Cálculos de Rentabilidade e Custo por Região (necessários para a sugestão) ---
            total_frete_carga = df_carga["Valor do Frete"].sum()
            
            rentabilidade_percentual = 0.0
            situacao_custo_regional = "N/A"
            cor_situacao = "gray"

            if total_frete_carga > 0:
                rentabilidade_percentual = ((total_frete_carga - valor_contratacao_carga_existente) / total_frete_carga) * 100
                
                # Determinar a região dominante da carga
                dominant_region = 'NÃO DEFINIDA'
                if 'Regiao' in df_carga.columns and not df_carga['Regiao'].empty:
                    # Filtra 'NÃO DEFINIDA' para o cálculo da região dominante se outras regiões existirem
                    regions_to_consider = df_carga['Regiao'][df_carga['Regiao'] != 'NÃO DEFINIDA']
                    if not regions_to_consider.empty:
                        dominant_region = regions_to_consider.value_counts().idxmax()
                    elif not df_carga['Regiao'].empty: # Se todas forem 'NÃO DEFINIDA', pega a primeira
                        dominant_region = df_carga['Regiao'].iloc[0]

                max_cost_allowed = MAX_COST_PER_REGION.get(dominant_region, None) # Pega o limite para a região dominante

                if max_cost_allowed is not None:
                    custo_receita_ratio = (valor_contratacao_carga_existente / total_frete_carga)
                    if custo_receita_ratio <= max_cost_allowed:
                        situacao_custo_regional = f"Dentro do Limite ({max_cost_allowed*100:.0f}%)"
                        cor_situacao = "#28a745" # Verde
                    else:
                        situacao_custo_regional = f"Acima do Limite ({max_cost_allowed*100:.0f}%)"
                        cor_situacao = "#dc3545" # Vermelho
                else:
                    situacao_custo_regional = f"Região '{dominant_region}' sem limite definido"
                    cor_situacao = "orange"
            else: # total_frete_carga is 0 or less
                rentabilidade_percentual = 0.0
                if valor_contratacao_carga_existente > 0:
                    situacao_custo_regional = "Frete total zero, Contratação > 0"
                    cor_situacao = "#dc3545" # Vermelho
                else:
                    situacao_custo_regional = "Frete total zero, Contratação zero"
                    cor_situacao = "gray"


            st.markdown(f"""
            <div style="margin-top:20px;padding:10px;background:#e8f0fe;border-left:4px solid #f9ab00;border-radius:6px;display:inline-block;max-width:100%;">
                <strong>Carga:</strong> {carga}
            </div>
            """, unsafe_allow_html=True)

            col1_badges, col2_placeholder = st.columns([5, 1])
            with col1_badges:
                st.markdown(
                    f"""
                    <div style='display: flex; flex-wrap: wrap; gap: 8px;'>
                        {badge(f'{len(df_carga)} entregas')}
                        {badge(f'{formatar_brasileiro(df_carga["Peso Calculado em Kg"].sum())} kg calc')}
                        {badge(f'{formatar_brasileiro(df_carga["Peso Real em Kg"].sum())} kg real')}
                        {badge(f'Valor frete: R$ {formatar_brasileiro(total_frete_carga)}')}
                        {badge(f'{formatar_brasileiro(df_carga["Cubagem em m³"].sum())} m³')}
                        {badge(f'{int(df_carga["Quantidade de Volumes"].sum())} volumes')}
                        {badge(f'Valor Contratação: R$ {formatar_brasileiro(valor_contratacao_carga_existente)}')}
                        {badge(f'Rentabilidade: {rentabilidade_percentual:.2f}%')}
                        <span style='background:{cor_situacao};color:white;border-radius:12px;padding:6px 12px;margin:4px;display:inline-block;'>Situação Custo: {situacao_custo_regional}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
            with st.expander("🔽 Ver entregas da carga para Aprovação de Custos", expanded=False):
                checkbox_key = f"marcar_todas_aprov_custos_{carga}"
                if checkbox_key not in st.session_state:
                    st.session_state[checkbox_key] = False
                marcar_todas = st.checkbox("Marcar todas", key=checkbox_key)

                with st.spinner("Formatando entregas da carga para aprovação..."):
                    # Define formatter for numeric values
                    formatter = JsCode("""
                        function(params) {
                            if (!params.value && params.value !== 0) return '';
                            return Number(params.value).toLocaleString('pt-BR', {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2
                            });
                        }
                    """)

                    # NOVO: Formatter para exibir APENAS a parte da data (dd-mm-aaaa)
                    date_only_formatter = JsCode("""
                        function(params) {
                            if (params.value === null || typeof params.value === 'undefined' || params.value === '') return '';
                            const parts = params.value.split(' ')[0];
                            return parts;
                        }
                    """)
                    
                    df_formatado = df_carga[[col for col in colunas_exibir if col in df_carga.columns]].copy()
                    df_formatado = apply_brazilian_date_format_for_display(df_formatado)
                    df_formatado = df_formatado.replace([np.nan, None], "")

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

                    # --- NOVO: Configuração para colunas de data que devem ser APENAS dd-mm-aaaa ---
                    for col in ['Previsao de Entrega', 'Entrega Programada']: # Adicione outras colunas de data se quiser que sejam APENAS data
                        if col in df_formatado.columns:
                            gb.configure_column(col, valueFormatter=date_only_formatter)
                    # --- Fim da Configuração de colunas de data ---




                    grid_options = gb.build()
                    grid_key_id = f"grid_aprovacao_custos_{carga}"
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
                    # --- REMOVIDO: CAMPO DE ENTRADA E SUGESTÃO ---
                    # Não há campo para preencher valor de contratação nem mostrar sugestão nesta página.

            col_aprovar, col_rejeitar = st.columns(2)
            with col_aprovar:
                if st.button(
                    f"✅ Aprovar Carga {carga}",
                    key=f"aprovar_carga_{carga}",
                    disabled=not is_user_aprovador or not selecionadas # Removido 'or valor_contratacao <= 0'
                ):
                    try:
                        with st.spinner("✅ Aprovando entregas e movendo para Cargas Aprovadas..."):
                            df_aprovar = pd.DataFrame(selecionadas)

                            df_aprovar = df_aprovar.drop(columns=["_selectedRowNodeInfo"], errors="ignore")
                            
                            df_aprovar["numero_carga"] = carga
                            df_aprovar["valor_contratacao"] = valor_contratacao_carga_existente # Usa o valor existente da carga
                            
                            df_aprovar["aprovador_custos_login"] = st.session_state.get("username", "Desconhecido")
                            df_aprovar["data_aprovacao_custos"] = data_hora_brasil_iso()

                            date_cols_to_process = [
                                "Previsao de Entrega", "Entrega Programada", "Data de Emissao",
                                "Data de Autorizacao", "Data do Cancelamento", "Data do Escaneamento",
                                "Data da Entrega Realizada", "Data da Ultima Ocorrencia",
                                "Data de inclusao da Ultima Ocorrencia", "Data_Hora_Gerada",
                                "data_aprovacao_custos"
                            ]
                            for col_name in date_cols_to_process:
                                if col_name in df_aprovar.columns:
                                    df_aprovar[col_name] = pd.to_datetime(df_aprovar[col_name], errors='coerce')
                                    df_aprovar[col_name] = df_aprovar[col_name].apply(
                                        lambda x: x.isoformat() if pd.notna(x) else None
                                    )

                            df_aprovar = df_aprovar.replace([np.nan, pd.NaT, "", np.inf, -np.inf], None)

                            registros_para_cargas_aprovadas = df_aprovar.to_dict(orient="records")
                            registros_para_cargas_aprovadas = [r for r in registros_para_cargas_aprovadas if r.get("Serie_Numero_CTRC")]

                            if registros_para_cargas_aprovadas:
                                supabase.table("cargas_aprovadas").insert(registros_para_cargas_aprovadas).execute()

                            chaves_aprovadas = [r.get("Serie_Numero_CTRC") for r in registros_para_cargas_aprovadas if r.get("Serie_Numero_CTRC")]
                            if chaves_aprovadas:
                                supabase.table("aprovacao_custos").delete().in_("Serie_Numero_CTRC", chaves_aprovadas).execute()

                            st.success(f"✅ {len(registros_para_cargas_aprovadas)} entregas da carga {carga} aprovadas e movidas para Cargas Aprovadas.")
                            st.session_state["reload_aprovacao_custos"] = True
                            st.session_state["reload_cargas_aprovadas"] = True
                            st.session_state.pop(grid_key, None)
                            st.session_state.pop(checkbox_key, None)

                            st.rerun()

                    except Exception as e:
                        st.error(f"❌ Erro ao aprovar carga: {e}")

            with col_rejeitar:
                if st.button(
                    f"❌ Rejeitar Carga {carga}",
                    key=f"rejeitar_carga_{carga}",
                    disabled=not is_user_aprovador or not selecionadas
                ):
                    try:
                        with st.spinner("🔄 Rejeitando entregas e retornando para Cargas Geradas..."):
                            df_rejeitar = pd.DataFrame(selecionadas)

                            df_rejeitar = df_rejeitar.drop(columns=["_selectedRowNodeInfo"], errors="ignore")
                            df_rejeitar = df_rejeitar.drop(columns=["valor_contratacao"], errors="ignore") # valor_contratacao é removido ao rejeitar
                            
                            df_rejeitar["Status"] = "AGENDAR" 
                            df_rejeitar["numero_carga"] = carga
                            
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

                            df_rejeitar = df_rejeitar.replace([np.nan, pd.NaT, "", np.inf, -np.inf], None)

                            registros_para_cargas_geradas = df_rejeitar.to_dict(orient="records")
                            registros_para_cargas_geradas = [r for r in registros_para_cargas_geradas if r.get("Serie_Numero_CTRC")]

                            if registros_para_cargas_geradas:
                                supabase.table("cargas_geradas").insert(registros_para_cargas_geradas).execute()

                            chaves_rejeitadas = [r.get("Serie_Numero_CTRC") for r in registros_para_cargas_geradas if r.get("Serie_Numero_CTRC")]
                            if chaves_rejeitadas:
                                supabase.table("aprovacao_custos").delete().in_("Serie_Numero_CTRC", chaves_rejeitadas).execute()

                            st.warning(f"✅ {len(registros_para_cargas_geradas)} entregas da carga {carga} rejeitadas e retornadas para Cargas Geradas.")
                            
                            st.session_state["reload_aprovacao_custos"] = True
                            st.session_state.pop(grid_key, None)
                            st.session_state.pop(checkbox_key, None)

                            grid_key_carga_gerada = f"grid_carga_gerada_{carga}"
                            if grid_key_carga_gerada in st.session_state:
                                st.session_state.pop(grid_key_carga_gerada, None)
                            st.session_state["reload_cargas_geradas"] = True

                            st.rerun()

                    except Exception as e:
                        st.error(f"❌ Erro ao rejeitar carga: {e}")

    except Exception as e:
        st.error("Erro ao carregar aprovação de custos:")
        st.exception(e)
# ==============================================================================
# FUNÇÃO: pagina_cargas_aprovadas() -
# ==============================================================================
def pagina_cargas_aprovadas():
    st.markdown("## Cargas Aprovadas")

    try:
        with st.spinner("🔄 Carregando dados para cargas aprovadas..."):
            recarregar = st.session_state.pop("reload_cargas_aprovadas", False)
            if recarregar or "df_cargas_aprovadas_cache" not in st.session_state:
                dados = supabase.table("cargas_aprovadas").select("*").execute().data
                df = pd.DataFrame(dados)
                st.session_state["df_cargas_aprovadas_cache"] = df
            else:
                df = st.session_state["df_cargas_aprovadas_cache"]

        if df.empty:
            st.info("Nenhuma carga aprovada pendente de fechamento.")
            return

        df.columns = df.columns.str.strip()

        numeric_cols_to_convert = [
            'Peso Real em Kg', 'Peso Calculado em Kg', 'Cubagem em m³',
            'Quantidade de Volumes', 'Valor do Frete', 'valor_contratacao'
        ]
        for col in numeric_cols_to_convert:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # --- Certifica que 'Regiao', 'motorista', 'placa' são strings e tratam nulos ---
        if 'Regiao' in df.columns:
            df['Regiao'] = df['Regiao'].astype(str).str.strip().str.upper().replace('NAN', 'NÃO DEFINIDA')
        if 'motorista' in df.columns:
            df['motorista'] = df['motorista'].astype(str).str.strip().replace('nan', 'Não Informado')
        if 'placa' in df.columns:
            df['placa'] = df['placa'].astype(str).str.strip().replace('nan', 'Não Informada')
        # Novas colunas de auditoria
        if 'aprovador_custos_login' in df.columns:
            df['aprovador_custos_login'] = df['aprovador_custos_login'].astype(str).str.strip().replace('nan', 'Desconhecido')


        col1, col2 = st.columns([1, 1])
        with col1:
            st.metric("Total de Cargas Aprovadas", df["numero_carga"].nunique() if "numero_carga" in df.columns else 0)
        with col2:
            st.metric("Total de Entregas Aprovadas", len(df))

        # --- Definição dos Custos Máximos por Região ---
        MAX_COST_PER_REGION = {
            'INTERIOR 1': 0.35,  # 35%
            'INTERIOR 2': 0.45,  # 45%
            'POA CAPITAL': 0.30   # 30%
        }

        colunas_exibir = [
            "Serie_Numero_CTRC", "Rota", "Regiao", "Valor do Frete", "Cliente Pagador", "Chave CT-e", "Cliente Destinatario",
            "Cidade de Entrega", "Bairro do Destinatario", "Previsao de Entrega",
            "Numero da Nota Fiscal", "Status", "Entrega Programada", "Particularidade",
            "Codigo da Ultima Ocorrencia", "Peso Real em Kg", "Peso Calculado em Kg",
            "Cubagem em m³", "Quantidade de Volumes", "valor_contratacao", "numero_carga",
            "motorista", "placa",
            "aprovador_custos_login", "data_aprovacao_custos" # Adicionadas para exibição
        ]

        cargas_unicas = sorted(df["numero_carga"].dropna().unique())

        for carga in cargas_unicas:
            df_carga = df[df["numero_carga"] == carga].copy()
            if df_carga.empty:
                continue

            valor_contratacao_carga = df_carga["valor_contratacao"].iloc[0] if "valor_contratacao" in df_carga.columns and not df_carga["valor_contratacao"].isnull().all() else 0.0
            motorista_carga = df_carga["motorista"].iloc[0] if "motorista" in df_carga.columns and not df_carga["motorista"].isnull().all() else 'Não Informado'
            placa_carga = df_carga["placa"].iloc[0] if "placa" in df_carga.columns and not df_carga["placa"].isnull().all() else 'Não Informada'
            aprovador_custos_login = df_carga["aprovador_custos_login"].iloc[0] if "aprovador_custos_login" in df_carga.columns and not df_carga["aprovador_custos_login"].isnull().all() else 'Desconhecido'
            data_aprovacao_custos = df_carga["data_aprovacao_custos"].iloc[0] if "data_aprovacao_custos" in df_carga.columns and not df_carga["data_aprovacao_custos"].isnull().all() else None


            # --- Cálculos de Rentabilidade e Custo por Região ---
            total_frete_carga = df_carga["Valor do Frete"].sum()
            
            rentabilidade_percentual = 0.0
            situacao_custo_regional = "N/A"
            cor_situacao = "gray"

            if total_frete_carga > 0:
                rentabilidade_percentual = ((total_frete_carga - valor_contratacao_carga) / total_frete_carga) * 100
                
                # Determinar a região dominante da carga
                dominant_region = 'NÃO DEFINIDA'
                if 'Regiao' in df_carga.columns and not df_carga['Regiao'].empty:
                    regions_to_consider = df_carga['Regiao'][df_carga['Regiao'] != 'NÃO DEFINIDA']
                    if not regions_to_consider.empty:
                        dominant_region = regions_to_consider.value_counts().idxmax()
                    elif not df_carga['Regiao'].empty:
                        dominant_region = df_carga['Regiao'].iloc[0]

                max_cost_allowed = MAX_COST_PER_REGION.get(dominant_region, None)

                if max_cost_allowed is not None:
                    custo_receita_ratio = (valor_contratacao_carga / total_frete_carga)
                    if custo_receita_ratio <= max_cost_allowed:
                        situacao_custo_regional = f"Dentro do Limite ({max_cost_allowed*100:.0f}%)"
                        cor_situacao = "#28a745" # Verde
                    else:
                        situacao_custo_regional = f"Acima do Limite ({max_cost_allowed*100:.0f}%)"
                        cor_situacao = "#dc3545" # Vermelho
                else:
                    situacao_custo_regional = f"Região '{dominant_region}' sem limite definido"
                    cor_situacao = "orange"
            else:
                rentabilidade_percentual = 0.0
                situacao_custo_regional = "Total do Frete zero, cálculo impossível."
                cor_situacao = "gray"


            st.markdown(f"""
            <div style="margin-top:20px;padding:10px;background:#e8f0fe;border-left:4px solid #34a853;border-radius:6px;display:inline-block;max-width:100%;">
                <strong>Carga:</strong> {carga}
            </div>
            """, unsafe_allow_html=True)

            col1_badges, col2_placeholder = st.columns([5, 1])
            with col1_badges:
                st.markdown(
                    f"""
                    <div style='display: flex; flex-wrap: wrap; gap: 8px;'>
                        {badge(f'{len(df_carga)} entregas')}
                        {badge(f'{formatar_brasileiro(df_carga["Peso Calculado em Kg"].sum())} kg calc')}
                        {badge(f'{formatar_brasileiro(df_carga["Peso Real em Kg"].sum())} kg real')}
                        {badge(f'Valor frete: R$ {formatar_brasileiro(total_frete_carga)}')}
                        {badge(f'{formatar_brasileiro(df_carga["Cubagem em m³"].sum())} m³')}
                        {badge(f'{int(df_carga["Quantidade de Volumes"].sum())} volumes')}
                        {badge(f'Valor Contratação: R$ {formatar_brasileiro(valor_contratacao_carga)}')}
                        {badge(f'Motorista: {motorista_carga}')}
                        {badge(f'Placa: {placa_carga}')}
                        {badge(f'Rentabilidade: {rentabilidade_percentual:.2f}%')}
                        <span style='background:{cor_situacao};color:white;border-radius:12px;padding:6px 12px;margin:4px;display:inline-block;'>Situação Custo: {situacao_custo_regional}</span>
                        {badge(f'Aprovado por: {aprovador_custos_login}')}
                        {badge(f'Em: {formatar_data_hora_br(data_aprovacao_custos)}')}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                # --- CAMPOS PARA MOTORISTA E PLACA PARA EDIÇÃO E BOTÃO ÚNICO DE SALVAR E FECHAR ---
                st.markdown("---")
                st.subheader(f"Informações do Motorista e Veículo da Carga {carga}")
                
                # --- APLICA CAPS LOCK AUTOMÁTICO E GARANTE VALOR INICIAL ---
                motorista_edit = st.text_input("Nome do Motorista:", value=motorista_carga if motorista_carga != 'Não Informado' else '', key=f"motorista_edit_{carga}").upper()
                placa_edit = st.text_input("Placa do Veículo (ex: ABC-1234):", value=placa_carga if placa_carga != 'Não Informada' else '', key=f"placa_edit_{carga}").upper()
                
                if st.button(
                    f"✅ Salvar e Fechar Carga {carga}",
                    key=f"salvar_fechar_carga_{carga}",
                    disabled=not motorista_edit.strip() or not placa_edit.strip() 
                ):
                    try:
                        # 1. Obter todas as entregas desta carga de 'cargas_aprovadas'
                        response_fetch = supabase.table("cargas_aprovadas").select("*").eq("numero_carga", carga).execute()
                        data_to_move = response_fetch.data

                        if not data_to_move:
                            st.warning(f"Nenhuma entrega encontrada para a carga {carga} em Cargas Aprovadas para fechar.")
                            st.rerun() # Recarrega para limpar estado
                            return

                        df_to_move = pd.DataFrame(data_to_move)

                        # 2. Adicionar/Atualizar 'motorista', 'placa', 'data_fechamento', 'situacao' e 'fechador_carga_login'
                        df_to_move["motorista"] = motorista_edit # Já está em UPPER()
                        df_to_move["placa"] = placa_edit # Já está em UPPER()
                        df_to_move["data_fechamento"] = data_hora_brasil_iso() # Data e hora atual do Brasil
                        df_to_move["situacao"] = "Fechada" # Definir a situação
                        df_to_move["fechador_carga_login"] = st.session_state.get("username", "Desconhecido") # Quem fechou

                        # 3. Preparar dados para inserção em 'cargas_fechadas'
                        date_cols_to_process_for_insert = [
                            "Previsao de Entrega", "Entrega Programada", "Data de Emissao",
                            "Data de Autorizacao", "Data do Cancelamento", "Data do Escaneamento",
                            "Data da Entrega Realizada", "Data da Ultima Ocorrencia",
                            "Data de inclusao da Ultima Ocorrencia", "Data_Hora_Gerada",
                            "data_fechamento", "data_aprovacao_custos" # Inclui as novas e existentes
                        ]
                        for col_name in date_cols_to_process_for_insert:
                            if col_name in df_to_move.columns:
                                df_to_move[col_name] = pd.to_datetime(df_to_move[col_name], errors='coerce')
                                df_to_move[col_name] = df_to_move[col_name].apply(
                                    lambda x: x.isoformat() if pd.notna(x) else None
                                )
                        df_to_move = df_to_move.replace([np.nan, pd.NaT, "", np.inf, -np.inf], None)

                        records_to_insert = df_to_move.to_dict(orient="records")

                        # 4. Inserir em 'cargas_fechadas'
                        if records_to_insert:
                            supabase.table("cargas_fechadas").insert(records_to_insert).execute()
                            st.success(f"Carga {carga} movida para Cargas Fechadas com sucesso!")
                        else:
                            st.warning(f"Não há registros válidos para mover para Cargas Fechadas para a carga {carga}.")
                            st.rerun() # Não deleta se não inseriu
                            return 

                        # 5. Deletar da 'cargas_aprovadas' (original)
                        supabase.table("cargas_aprovadas").delete().eq("numero_carga", carga).execute()
                        
                        st.session_state["reload_cargas_aprovadas"] = True # Força recarregamento da página atual
                        st.session_state["reload_cargas_fechadas"] = True # Força recarregamento da nova página
                        st.rerun() # Renderiza novamente para mostrar as mudanças

                    except Exception as e:
                        st.error(f"Erro ao salvar e fechar carga {carga}: {e}")
                


            with st.expander("🔽 Ver entregas da carga aprovada", expanded=False):
                checkbox_key = f"marcar_todas_cargas_aprovadas_{carga}"
                if checkbox_key not in st.session_state:
                    st.session_state[checkbox_key] = False
                marcar_todas = st.checkbox("Marcar todas", key=checkbox_key)


                with st.spinner("🔄 Formatando entregas da carga aprovada..."):
                    # Define formatter for numeric values
                    formatter = JsCode("""
                        function(params) {
                            if (!params.value && params.value !== 0) return '';
                            return Number(params.value).toLocaleString('pt-BR', {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2
                            });
                        }
                    """)

                    # NOVO: Formatter para exibir APENAS a parte da data (dd-mm-aaaa)
                    date_only_formatter = JsCode("""
                        function(params) {
                            if (params.value === null || typeof params.value === 'undefined' || params.value === '') return '';
                            const parts = params.value.split(' ')[0];
                            return parts;
                        }
                    """)
               
                    df_formatado = df_carga[[col for col in colunas_exibir if col in df_carga.columns]].copy()
                    df_formatado = apply_brazilian_date_format_for_display(df_formatado) # Aplica o formato completo (dd-mm-aaaa HH:MM:SS)
                    df_formatado = df_formatado.replace([np.nan, None], "")

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

                    # --- NOVO: Configuração para colunas de data que devem ser APENAS dd-mm-aaaa ---
                    for col in ['Previsao de Entrega', 'Entrega Programada']: # Adicione outras colunas de data se quiser que sejam APENAS data
                        if col in df_formatado.columns:
                            gb.configure_column(col, valueFormatter=date_only_formatter)
                    # --- Fim da Configuração de colunas de data ---

                    # Formatação específica para as novas colunas de auditoria que podem ser datas completas
                    for col in ['data_aprovacao_custos']:
                        if col in df_formatado.columns:
                            gb.configure_column(col, valueFormatter=JsCode("""
                                function(params) {
                                    if (params.value) {
                                        return params.value; // Já está em dd-mm-yyyy HH:MM:SS
                                    }
                                    return '';
                                }
                            """))
                    grid_options = gb.build()
                    grid_key_id = f"grid_cargas_aprovadas_{carga}"
                    if grid_key_id not in st.session_state:
                        st.session_state[grid_key_id] = str(uuid.uuid4())
                    grid_key = st.session_state[grid_key_id]

                    # AQUI ESTÁ A CORREÇÃO: A chamada para AgGrid agora está dentro do bloco 'with'
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
                    st.markdown(f"**Entregas selecionadas:** {len(selecionadas)}")
    except Exception as e:
        st.error("Erro ao carregar cargas aprovadas:")
        st.exception(e)







# ==============================================================================
# Função pagina_cargas_fechadas() - com os ajustes aplicados
# ==============================================================================

def pagina_cargas_fechadas():
    st.markdown("## Cargas Fechadas")

    try:
        with st.spinner("🔄 Carregando dados para cargas fechadas..."):
            recarregar = st.session_state.pop("reload_cargas_fechadas", False)
            if recarregar or "df_cargas_fechadas_cache" not in st.session_state:
                dados = supabase.table("cargas_fechadas").select("*").execute().data
                df = pd.DataFrame(dados)

                # --- Convert all relevant date columns to UTC datetime objects immediately ---
                # Isso garante que as colunas de data sejam do tipo datetime antes de qualquer outra operação
                for col_name in GLOBAL_DATE_DISPLAY_COLUMNS:
                    if col_name in df.columns:
                        df[col_name] = pd.to_datetime(df[col_name], errors='coerce', utc=True)
                # --- End of date conversion ---

                st.session_state["df_cargas_fechadas_cache"] = df
            else:
                df = st.session_state["df_cargas_fechadas_cache"]

        if df.empty:
            st.info("Nenhuma carga foi fechada ainda.")
            return

        df.columns = df.columns.str.strip()

        # --- Tratamento de colunas numéricas ---
        numeric_cols_to_convert = [
            'Peso Real em Kg', 'Peso Calculado em Kg', 'Cubagem em m³',
            'Quantidade de Volumes', 'Valor do Frete', 'valor_contratacao'
        ]
        for col in numeric_cols_to_convert:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # --- Certifica que colunas de texto são string e tratam nulos ---
        if 'Regiao' in df.columns:
            df['Regiao'] = df['Regiao'].astype(str).str.strip().str.upper().replace('NAN', 'NÃO DEFINIDA')
        if 'motorista' in df.columns:
            df['motorista'] = df['motorista'].astype(str).str.strip().replace('nan', 'Não Informado')
        if 'placa' in df.columns:
            df['placa'] = df['placa'].astype(str).str.strip().replace('nan', 'Não Informada')
        if 'situacao' in df.columns:
            df['situacao'] = df['situacao'].astype(str).str.strip().replace('nan', 'Não Definida')
        if 'aprovador_custos_login' in df.columns:
            df['aprovador_custos_login'] = df['aprovador_custos_login'].astype(str).str.strip().replace('nan', 'Desconhecido')
        if 'fechador_carga_login' in df.columns:
            df['fechador_carga_login'] = df['fechador_carga_login'].astype(str).str.strip().replace('nan', 'Desconhecido')

        # Exibição de métricas gerais antes da filtragem por data
        col1, col2 = st.columns([1, 1])
        with col1:
            st.metric("Total de Cargas Fechadas", df["numero_carga"].nunique() if "numero_carga" in df.columns else 0)
        with col2:
            st.metric("Total de Entregas Fechadas", len(df))

        st.markdown("---") # Separador visual para os filtros

        # --- Filtro por Data de Fechamento ---
        st.subheader("🔍Filtrar por Data de Fechamento")
        col_data_inicio, col_data_fim = st.columns(2)
        with col_data_inicio:
            # Pega a data mínima do DataFrame, garante que seja um objeto date para o date_input
            min_date_val = df['data_fechamento'].min().date() if not df['data_fechamento'].empty and pd.notna(df['data_fechamento'].min()) else None
            data_inicio = st.date_input("Data Inicial", value=min_date_val, key="filtro_data_inicio")
        with col_data_fim:
            # Pega a data máxima do DataFrame, garante que seja um objeto date para o date_input
            max_date_val = df['data_fechamento'].max().date() if not df['data_fechamento'].empty and pd.notna(df['data_fechamento'].max()) else None
            data_fim = st.date_input("Data Final", value=max_date_val, key="filtro_data_fim")

        # Aplica a filtragem por data
        df_filtrado = df.copy()
        if data_inicio:
            # Converte data_inicio (datetime.date) para um Timestamp timezone-aware (UTC)
            start_of_day_utc = pd.Timestamp(data_inicio, tz='UTC')
            df_filtrado = df_filtrado[df_filtrado['data_fechamento'] >= start_of_day_utc]

        if data_fim:
            # Converte data_fim (datetime.date) para um Timestamp timezone-aware (UTC)
            # e define-o para o final do dia (23:59:59.999...) em UTC
            end_of_day_utc = pd.Timestamp(data_fim, tz='UTC') + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
            df_filtrado = df_filtrado[df_filtrado['data_fechamento'] <= end_of_day_utc]
        
        # Verifica se o DataFrame filtrado está vazio
        if df_filtrado.empty:
            st.info("Nenhuma carga encontrada para o período selecionado.")
            return # Sai da função se não houver dados para exibir

        # --- Definição dos Custos Máximos por Região (para exibição) ---
        MAX_COST_PER_REGION = {
            'INTERIOR 1': 0.35,  # 35%
            'INTERIOR 2': 0.45,  # 45%
            'POA CAPITAL': 0.30   # 30%
        }

        colunas_exibir = [
            "Serie_Numero_CTRC", "Rota", "Regiao", "Valor do Frete", "Cliente Pagador", "Chave CT-e", "Cliente Destinatario",
            "Cidade de Entrega", "Bairro do Destinatario", "Previsao de Entrega",
            "Numero da Nota Fiscal", "Status", "Entrega Programada", "Particularidade",
            "Codigo da Ultima Ocorrencia", "Peso Real em Kg", "Peso Calculado em Kg",
            "Cubagem em m³", "Quantidade de Volumes", "valor_contratacao", "numero_carga",
            "motorista", "placa", "data_fechamento", "situacao", # Colunas existentes
            "aprovador_custos_login", "data_aprovacao_custos", "fechador_carga_login" # Novas colunas de auditoria
        ]

        # Usa o DataFrame filtrado para obter as cargas únicas
        cargas_unicas = sorted(df_filtrado["numero_carga"].dropna().unique())

        for carga in cargas_unicas:
            # df_carga agora é baseado no df_filtrado
            df_carga = df_filtrado[df_filtrado["numero_carga"] == carga].copy()
            if df_carga.empty:
                continue 

            valor_contratacao_carga = df_carga["valor_contratacao"].iloc[0] if "valor_contratacao" in df_carga.columns and not df_carga["valor_contratacao"].isnull().all() else 0.0
            motorista_carga = df_carga["motorista"].iloc[0] if "motorista" in df_carga.columns and not df_carga["motorista"].isnull().all() else 'Não Informado'
            placa_carga = df_carga["placa"].iloc[0] if "placa" in df_carga.columns and not df_carga["placa"].isnull().all() else 'Não Informada'
            data_fechamento_carga = df_carga["data_fechamento"].iloc[0] if "data_fechamento" in df_carga.columns and not df_carga["data_fechamento"].isnull().all() else None
            situacao_carga = df_carga["situacao"].iloc[0] if "situacao" in df_carga.columns and not df_carga["situacao"].isnull().all() else 'Não Definida'
            aprovador_custos_login = df_carga["aprovador_custos_login"].iloc[0] if "aprovador_custos_login" in df_carga.columns and not df_carga["aprovador_custos_login"].isnull().all() else 'Desconhecido'
            data_aprovacao_custos = df_carga["data_aprovacao_custos"].iloc[0] if "data_aprovacao_custos" in df_carga.columns and not df_carga["data_aprovacao_custos"].isnull().all() else None
            fechador_carga_login = df_carga["fechador_carga_login"].iloc[0] if "fechador_carga_login" in df_carga.columns and not df_carga["fechador_carga_login"].isnull().all() else 'Desconhecido'

            # --- Cálculos de Rentabilidade e Custo por Região (para exibição) ---
            total_frete_carga = df_carga["Valor do Frete"].sum()
            
            rentabilidade_percentual = 0.0
            situacao_custo_regional = "N/A"
            cor_situacao = "gray"

            if total_frete_carga > 0:
                rentabilidade_percentual = ((total_frete_carga - valor_contratacao_carga) / total_frete_carga) * 100
                
                # Determinar a região dominante da carga
                dominant_region = 'NÃO DEFINIDA'
                if 'Regiao' in df_carga.columns and not df_carga['Regiao'].empty:
                    regions_to_consider = df_carga['Regiao'][df_carga['Regiao'] != 'NÃO DEFINIDA']
                    if not regions_to_consider.empty:
                        dominant_region = regions_to_consider.value_counts().idxmax()
                    elif not df_carga['Regiao'].empty:
                        dominant_region = df_carga['Regiao'].iloc[0]

                max_cost_allowed = MAX_COST_PER_REGION.get(dominant_region, None)

                if max_cost_allowed is not None:
                    custo_receita_ratio = (valor_contratacao_carga / total_frete_carga)
                    if custo_receita_ratio <= max_cost_allowed:
                        situacao_custo_regional = f"Dentro do Limite ({max_cost_allowed*100:.0f}%)"
                        cor_situacao = "#28a745" # Verde
                    else:
                        situacao_custo_regional = f"Acima do Limite ({max_cost_allowed*100:.0f}%)"
                        cor_situacao = "#dc3545" # Vermelho
                else:
                    situacao_custo_regional = f"Região '{dominant_region}' sem limite definido"
                    cor_situacao = "orange"
            else:
                rentabilidade_percentual = 0.0
                situacao_custo_regional = "Total do Frete zero, cálculo impossível."
                cor_situacao = "gray"


            st.markdown(f"""
            <div style="margin-top:20px;padding:10px;background:#e8f0fe;border-left:4px solid #34a853;border-radius:6px;display:inline-block;max-width:100%;">
                <strong>Carga:</strong> {carga}
            </div>
            """, unsafe_allow_html=True)

            col1_badges, col2_placeholder = st.columns([5, 1])
            with col1_badges:
                st.markdown(
                    f"""
                    <div style='display: flex; flex-wrap: wrap; gap: 8px;'>
                        {badge(f'{len(df_carga)} entregas')}
                        {badge(f'{formatar_brasileiro(df_carga["Peso Calculado em Kg"].sum())} kg calc')}
                        {badge(f'{formatar_brasileiro(df_carga["Peso Real em Kg"].sum())} kg real')}
                        {badge(f'Valor frete: R$ {formatar_brasileiro(total_frete_carga)}')}
                        {badge(f'{formatar_brasileiro(df_carga["Cubagem em m³"].sum())} m³')}
                        {badge(f'{int(df_carga["Quantidade de Volumes"].sum())} volumes')}
                        {badge(f'Valor Contratação: R$ {formatar_brasileiro(valor_contratacao_carga)}')}
                        {badge(f'Motorista: {motorista_carga}')}
                        {badge(f'Placa: {placa_carga}')}
                        {badge(f'Rentabilidade: {rentabilidade_percentual:.2f}%')}
                        <span style='background:{cor_situacao};color:white;border-radius:12px;padding:6px 12px;margin:4px;display:inline-block;'>Situação Custo: {situacao_custo_regional}</span>
                        {badge(f'Aprovado por: {aprovador_custos_login}')}
                        {badge(f'Em: {formatar_data_hora_br(data_aprovacao_custos)}')}
                        {badge(f'Fechado por: {fechador_carga_login}')}
                        {badge(f'Fechada em: {formatar_data_hora_br(data_fechamento_carga)}') if data_fechamento_carga else ''}
                        {badge(f'Situação: {situacao_carga}')}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
            with st.expander("🔽 Ver entregas da carga fechada", expanded=False):
                checkbox_key = f"marcar_todas_cargas_fechadas_{carga}"
                if checkbox_key not in st.session_state:
                    st.session_state[checkbox_key] = False
                marcar_todas = st.checkbox("Marcar todas", key=checkbox_key)

                with st.spinner("🔄 Formatando entregas da carga fechada..."):
                    # Define formatter for numeric values
                    formatter = JsCode("""
                        function(params) {
                            if (!params.value && params.value !== 0) return '';
                            return Number(params.value).toLocaleString('pt-BR', {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2
                            });
                        }
                    """)

                    # NOVO: Formatter para exibir APENAS a parte da data (dd-mm-aaaa)
                    date_only_formatter = JsCode("""
                        function(params) {
                            if (params.value === null || typeof params.value === 'undefined' || params.value === '') return '';
                            const parts = params.value.split(' ')[0];
                            return parts;
                        }
                    """)
                    
                    df_formatado = df_carga[[col for col in colunas_exibir if col in df_carga.columns]].copy()
                    df_formatado = apply_brazilian_date_format_for_display(df_formatado)
                    df_formatado = df_formatado.replace([np.nan, None], "")

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

                    # --- NOVO: Configuração para colunas de data que devem ser APENAS dd-mm-aaaa ---
                    for col in ['Previsao de Entrega', 'Entrega Programada']: # Adicione outras colunas de data se quiser que sejam APENAS data
                        if col in df_formatado.columns:
                            gb.configure_column(col, valueFormatter=date_only_formatter)
                    # --- Fim da Configuração de colunas de data ---
                    
                    if 'data_fechamento' in df_formatado.columns:
                        gb.configure_column('data_fechamento', valueFormatter=JsCode("""
                            function(params) {
                                if (params.value) {
                                    return params.value; // Já está em dd-mm-yyyy HH:MM:SS
                                }
                                return '';
                            }
                        """))
                    
                    if 'situacao' in df_formatado.columns:
                        gb.configure_column('situacao', type=["textColumn"])
                    if 'data_aprovacao_custos' in df_formatado.columns:
                        gb.configure_column('data_aprovacao_custos', valueFormatter=JsCode("""
                            function(params) {
                                if (params.value) {
                                    return params.value; // Já está em dd-mm-yyyy HH:MM:SS
                                }
                                return '';
                            }
                        """))

                    grid_options = gb.build()
                    grid_key_id = f"grid_cargas_fechadas_{carga}"
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

                # --- Botão de Download CSV e Botão de Impressão ---
                st.markdown("---") # Separador
                
                # Prepara os dados para o CSV. Aqui df_carga ainda contém os objetos datetime
                # porque df_formatado é uma cópia separada para o AgGrid.
                colunas_para_csv = [
                    "Serie_Numero_CTRC", "Chave CT-e", "numero_carga", 
                    "Cliente Pagador", "Cliente Destinatario", "Cidade de Entrega",
                    "Bairro do Destinatario", "Previsao de Entrega", "Valor do Frete",
                    "motorista", "placa", "data_fechamento", "situacao",
                    "aprovador_custos_login", "data_aprovacao_custos", "fechador_carga_login"
                ]
                df_csv = df_carga[[col for col in colunas_para_csv if col in df_carga.columns]].copy()
                
                # Converte colunas de data para um formato legível em CSV
                for col_date in ["Previsao de Entrega", "data_fechamento", "data_aprovacao_custos"]:
                    if col_date in df_csv.columns:
                        # As colunas já são datetime objetos (UTC) devido à conversão inicial.
                        # Basta aplicar o strftime, cuidando de NaT.
                        df_csv[col_date] = df_csv[col_date].apply(
                            lambda x: x.strftime("%d-%m-%Y %H:%M:%S") if pd.notna(x) else ""
                        )

                csv_content = df_csv.to_csv(index=False, sep=';', encoding='utf-8-sig')
                
                col_csv_button, col_print_button = st.columns(2)

                with col_csv_button:
                    st.download_button(
                        label=f"⬇️ Baixar CSV da Carga {carga}",
                        data=csv_content,
                        file_name=f"relatorio_carga_{carga}.csv",
                        mime="text/csv",
                        key=f"download_csv_{carga}"
                    )
                with col_print_button:
                    # Este botão não inicia uma impressão direta, mas informa o usuário.
                    st.button(
                        label=f"🖨️ Imprimir Visualização da Carga {carga}",
                        help="Utilize a função de impressão do seu navegador (Ctrl+P ou Cmd+P) para a visualização atual da carga.",
                        key=f"print_button_{carga}"
                    )
                    

                st.markdown("---") # Separador final para a seção de botões de cada carga

    except Exception as e:
        st.error("Erro ao carregar cargas fechadas:")
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
            sub_tab_confirmar_prod, sub_tab_aprov_dir, sub_tab_pre_rot, \
            sub_tab_rotas_conf, sub_tab_cargas, sub_tab_aprov_custos, \
            sub_tab_cargas_aprovadas, sub_tab_cargas_fechadas = st.tabs([
                "Confirmar Produção", "Aprovação Diretoria", "Pré Roterização", 
                "Rotas Confirmadas", "Cargas Geradas", "Aprovação de Custos", 
                "Cargas Aprovadas", "Cargas Fechadas"
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
        with sub_tab_cargas_aprovadas:
            pagina_cargas_aprovadas()
        with sub_tab_cargas_fechadas: 
            pagina_cargas_fechadas()

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


