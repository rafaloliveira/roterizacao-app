# 23-07 versão 1.0 ajustada os botões de salva e fechar carga




#sincronização, Pré Roterização e Rotas Confirmadas funcionando

import streamlit as st
st.set_page_config(
    page_title="Roteriza",  # Novo título para a aba do navegador
    page_icon="📡",       # Novo ícone para a aba. Pode ser um emoji,
                          # um caminho para um arquivo de imagem, ou uma URL.
    layout="wide",    # (Opcional) Pode ser "centered" ou "wide"
    initial_sidebar_state="auto" # (Opcional) Pode ser "auto", "expanded" ou "collapsed"
)

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
import traceback
from fpdf import FPDF
import io
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import Indenter

from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors

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
from decimal import Decimal, ROUND_HALF_UP, getcontext



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



def mover_entregas_para_outra_rota(ctrcs_selecionados, nova_rota_visual):
    if not ctrcs_selecionados:
        st.warning("Selecione ao menos uma entrega para mover.")
        return

    if not nova_rota_visual or nova_rota_visual == "Selecionar...":
        st.warning("Selecione uma rota válida.")
        return

    try:
        # ✅ CORREÇÃO: Atualização em lote usando .in_() para maior eficiência e robustez
        response = supabase.table("pre_roterizacao") \
            .update({"GrupoDeExibicao": nova_rota_visual}) \
            .in_("Serie_Numero_CTRC", ctrcs_selecionados) \
            .execute()
        
        if hasattr(response, 'data') and response.data:
            st.success(f"✅ {len(response.data)} entrega(s) movida(s visualmente) para o grupo '{nova_rota_visual}'.")
        else:
            st.warning(f"Movimentação solicitada para {len(ctrcs_selecionados)} entregas. Verifique o status no Supabase.")

        st.session_state["reload_pre_roterizacao"] = True
        st.rerun()

    except Exception as e:
        st.error(f"Erro ao mover entregas: {e}")


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

                # ✅ Define página inicial desejada após login
                #st.session_state.pagina = "Cargas Geradas"  # ⬅️ Altere aqui se quiser outra página como "Dashboard" ou "Pré-Roteirização"
                
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
                df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce') 
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
        minWidth=90
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
                'backgroundColor': '#FFA500', // LARANJA FORTE
                'color': '#000', // Texto preto para contraste
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
        # --- DEBUG 1: Após a primeira busca no Supabase ---
        base_raw_data = supabase.table("pre_roterizacao").select("*").execute().data
        base = pd.DataFrame(base_raw_data)
        #st.write(f"DEBUG: [carregar_base_supabase] Linhas após SELECT na pre_roterizacao: {len(base)}")

        if base.empty:
            #st.warning("DEBUG: [carregar_base_supabase] A busca inicial na pre_roterizacao retornou vazia. Verifique RLS ou dados.")
            return pd.DataFrame()

        # --- DEBUG 2: Após o merge com "Particularidades" ---
        part = supabase.table("Particularidades").select("*").execute().data
        if part:
            df_part = pd.DataFrame(part)
            df_part.columns = df_part.columns.str.strip()
            # Certifique-se que CNPJ Destinatario está como string antes do merge
            if 'CNPJ Destinatario' in base.columns:
                base['CNPJ Destinatario'] = base['CNPJ Destinatario'].astype(str).str.strip()
            if 'CNPJ' in df_part.columns:
                df_part['CNPJ'] = df_part['CNPJ'].astype(str).str.strip()

            base_merged_part = pd.merge(base, df_part[['CNPJ', 'Particularidade']], how='left',
            left_on='CNPJ Destinatario', right_on='CNPJ', suffixes=('', '_part_merge'))
            if 'Particularidade_part_merge' in base_merged_part.columns:
                # Prioriza a particularidade do merge, mas mantém a original se a do merge for nula
                base['Particularidade'] = base_merged_part['Particularidade_part_merge'].fillna(base.get('Particularidade', pd.NA))
            else:
                base['Particularidade'] = base.get('Particularidade', pd.NA) # Garante que a coluna exista
            base.drop(columns=['CNPJ_part_merge'], errors='ignore', inplace=True) # Renomeado para evitar conflito

        else:
            if 'Particularidade' not in base.columns:
                base['Particularidade'] = None # Garante que a coluna exista mesmo sem merge
        #: [carregar_base_supabase] Linhas após merge Particularidades: {len(base)}")


        # --- DEBUG 3: Após o merge com "Clientes_Entrega_Agendada" (AJUSTADO) ---
        # Garante que a coluna 'Status' exista no DataFrame 'base' ANTES de qualquer modificação
        # e que os valores já carregados da 'pre_roterizacao' sejam mantidos por padrão.
        if 'Status' not in base.columns:
            base['Status'] = pd.NA # Inicializa com valor ausente se a coluna não existe

        agendados = supabase.table("Clientes_Entrega_Agendada").select("*").execute().data
        if agendados:
            df_ag = pd.DataFrame(agendados)
            df_ag.columns = df_ag.columns.str.strip()
            if 'CNPJ' in df_ag.columns and 'Status de Agenda' in df_ag.columns:
                cnpjs_agendar = df_ag[df_ag['Status de Agenda'].str.upper() == 'AGENDAR']['CNPJ'].str.strip().unique()
                if 'CNPJ Destinatario' in base.columns:
                    # Identifica as linhas em 'base' cujo CNPJ do Destinatário está na lista de CNPJs a agendar
                    mask_para_agendar = base['CNPJ Destinatario'].astype(str).str.strip().isin(cnpjs_agendar)
                    # Aplica o status 'AGENDAR' APENAS para essas linhas que correspondem à máscara.
                    # O status das outras linhas (onde a máscara é False) será PRESERVADO.
                    base.loc[mask_para_agendar, 'Status'] = 'AGENDAR'
                # Não é mais necessário um 'else' aqui que defina o Status como None,
                # pois o valor original de 'Status' de 'base' já é preservado por padrão.
        # Se 'agendados' estiver vazio, ou as colunas CNPJ/Status de Agenda não existirem,
        # ou se 'CNPJ Destinatario' não estiver em 'base', o 'Status' original do DataFrame 'base' é mantido.
        #st.write(f"DEBUG: [carregar_base_supabase] Linhas após merge Clientes_Entrega_Agendada: {len(base)}")

        # --- DEBUG 4: Após a definição da Rota ---
        # Certifique-se que as colunas 'Cidade de Entrega' e 'Bairro do Destinatario' existam
        for col_name in ['Cidade de Entrega', 'Bairro do Destinatario']:
            if col_name not in base.columns:
                base[col_name] = None # Ou alguma string vazia se preferir
        base['Cidade de Entrega'] = base['Cidade de Entrega'].astype(str).str.strip().str.upper()
        base['Bairro do Destinatario'] = base['Bairro do Destinatario'].astype(str).str.strip().str.upper()

        rotas = supabase.table("Rotas").select("*").execute().data
        df_rotas = pd.DataFrame(rotas) if rotas else pd.DataFrame()
        df_rotas.columns = df_rotas.columns.str.strip()

        rotas_poas = supabase.table("RotasPortoAlegre").select("*").execute().data
        df_poas = pd.DataFrame(rotas_poas) if rotas_poas else pd.DataFrame()
        df_poas.columns = df_poas.columns.str.strip()

        base['Rota'] = None # Inicializa a coluna 'Rota'

        # Garante que as colunas de merge existem em df_rotas e df_poas
        if not df_rotas.empty and 'Cidade de Entrega' in df_rotas.columns and 'Rota' in df_rotas.columns:
            df_rotas['Cidade de Entrega_upper'] = df_rotas['Cidade de Entrega'].astype(str).str.strip().str.upper()
            rotas_dict = dict(zip(df_rotas['Cidade de Entrega_upper'], df_rotas['Rota']))
        else:
            rotas_dict = {}

        if not df_poas.empty and 'Bairro do Destinatario' in df_poas.columns and 'Rota' in df_poas.columns:
            df_poas['Bairro do Destinatario_upper'] = df_poas['Bairro do Destinatario'].astype(str).str.strip().str.upper()
            rotas_poa_dict = dict(zip(df_poas['Bairro do Destinatario_upper'], df_poas['Rota']))
        else:
            rotas_poa_dict = {}

        # Mapeia as rotas por apply
        def definir_rota_func(row):
            cidade = row.get('Cidade de Entrega', '').strip().upper()
            bairro = row.get('Bairro do Destinatario', '').strip().upper()

            if cidade == 'PORTO ALEGRE':
                return rotas_poa_dict.get(bairro, 'Indefinida')
            else:
                return rotas_dict.get(cidade, 'Indefinida')

        base['Rota'] = base.apply(definir_rota_func, axis=1)
        base['Rota'] = base['Rota'].fillna('Indefinida').replace('', 'Indefinida')

        #st.write(f"DEBUG: [carregar_base_supabase] Linhas após definir Rota: {len(base)}")


        # --- DEBUG 5: Após o processamento de "obrigatorias" e "confirmadas" ---
        # Este bloco *não altera* o 'base' que é retornado, mas é importante para entender o fluxo
        # Certifique-se de que df['Previsao de Entrega'] é datetime para esta comparação
        if 'Previsao de Entrega' in base.columns:
            base['Previsao de Entrega'] = pd.to_datetime(base['Previsao de Entrega'], errors='coerce')
        
        hoje = pd.Timestamp.today().normalize()
        d_mais_1 = hoje + pd.Timedelta(days=1)
        
        # Apenas para garantir que 'base' contém 'Serie_Numero_CTRC'
        if 'Serie_Numero_CTRC' not in base.columns:
            st.error("DEBUG: [carregar_base_supabase] Coluna 'Serie_Numero_CTRC' não encontrada no DataFrame 'base'. Isso pode causar problemas.")
            return pd.DataFrame() # Retorna vazio se a chave primária essencial estiver faltando

        # Formata datas para exibição (Isto é feito APENAS para exibição, não afeta o DataFrame subjacente para cálculos)
        for col in ["Previsao de Entrega", "Entrega Programada", "Data de Emissao"]: # <<-- ADICIONE "Data de Emissao" AQUI
            if col in base.columns:
                base[col] = pd.to_datetime(base[col], errors='coerce')
                base[col] = base[col].dt.strftime("%d-%m-%Y").fillna("")


        # --- DEBUG FINAL: Antes de retornar ---
        #st.write(f"DEBUG: [carregar_base_supabase] Linhas antes de retornar (base final): {len(base)}")
        return base

    except Exception as e:
        st.error(f"DEBUG: [carregar_base_supabase] Erro ao consultar ou processar as tabelas do Supabase: {e}")
        st.exception(e)
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
                    #st.warning(f"Candidato '{random_cargo_number}' já existe na tabela '{table_name}'. Tentando outro...")
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
def badge(label, background_color="#eef2f7", text_color="inherit"):
    """
    Retorna uma string HTML formatada como um 'badge' estilizado.
    Permite personalizar a cor de fundo e do texto.
    """
    return f"<span style='background:{background_color};color:{text_color};border-radius:12px;padding:6px 12px;margin:4px;display:inline-block;'>{label}</span>"

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


#--------------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------------
def salvar_hora_sincronizacao():
    agora = data_hora_brasil_iso()
    # Pega o nome de usuário do session_state
    usuario_logado = st.session_state.get("username", "Desconhecido") # "Desconhecido" caso não haja usuário logado

    # Cria um dicionário com as informações
    sync_info = {
        "timestamp": agora,
        "username": usuario_logado
    }
    
    try:
        # Converte o dicionário para uma string JSON antes de salvar
        supabase.table("metadados").upsert({"chave": "ultima_sincronizacao", "valor": json.dumps(sync_info)}).execute()
        # st.info(f"DEBUG: Salvo em metadados: {json.dumps(sync_info)}") # Debug opcional
    except Exception as e:
        st.warning(f"Erro ao salvar hora da sincronização: {e}")

def recuperar_hora_sincronizacao():
    try:
        dados = supabase.table("metadados").select("valor").eq("chave", "ultima_sincronizacao").execute()
        if dados.data:
            valor_salvo = dados.data[0]["valor"]
            try:
                # Tenta parsear como JSON
                sync_info = json.loads(valor_salvo)
                timestamp_str = sync_info.get("timestamp")
                username_str = sync_info.get("username", "Desconhecido") # Garante compatibilidade se o username não estiver no JSON antigo
            except json.JSONDecodeError:
                # Se não for JSON, assume que é apenas a data/hora (formato antigo)
                timestamp_str = valor_salvo
                username_str = "Desconhecido (Formato Antigo)"
            
            # Formata a data/hora
            data_hora_formatada = formatar_data_hora_br(timestamp_str)
            return data_hora_formatada, username_str
        else:
            return None, None # Retorna None para ambos se não houver dados
    except Exception as e:
        st.warning(f"Erro ao recuperar hora da sincronização: {e}")
        return None, None
    
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

    # Modificado para receber duas variáveis
    ultima_data, ultimo_usuario = recuperar_hora_sincronizacao()
    if ultima_data:
        st.markdown(f"🕒 Última sincronização registrada: **{ultima_data}** por **{ultimo_usuario}**")
    else:
        st.markdown("🕒 Última sincronização: **ainda não realizada**")

    st.markdown("### 1. Carregar Planilha Excel")
        
    arquivo_excel = st.file_uploader(
        "Selecione a planilha da fBaseroter:", 
        type=["xlsx"], 
        key=f"sync_file_uploader_{st.session_state.file_uploader_key}"
    )

    current_file_hash = None
    if arquivo_excel:
        current_file_hash = hashlib.md5(arquivo_excel.getvalue()).hexdigest()

    if current_file_hash != st.session_state.uploaded_sync_file_hash:
        st.session_state.uploaded_sync_file_hash = current_file_hash
        st.session_state.sync_triggered = False
        st.session_state.df_for_sync_cache = None

    if arquivo_excel:
        try:
            if st.session_state.df_for_sync_cache is None:
                df_raw = pd.read_excel(arquivo_excel)
                df_raw.columns = df_raw.columns.str.strip()
                st.session_state.df_for_sync_cache = df_raw

            st.success(f"Arquivo '{arquivo_excel.name}' carregado com sucesso!")
            st.write("Clique em 'Iniciar Sincronização' para começar o processo.")

            if st.button("🚀 Iniciar Sincronização", key="start_sync_button", disabled=st.session_state.sync_triggered):
                st.session_state.sync_triggered = True
                st.rerun()

        except Exception as e:
            st.error(f"Erro ao ler o arquivo Excel: {e}")
            st.session_state.uploaded_sync_file_hash = None
            st.session_state.sync_triggered = False
            st.session_state.df_for_sync_cache = None

    elif not arquivo_excel and st.session_state.uploaded_sync_file_hash:
        st.session_state.uploaded_sync_file_hash = None
        st.session_state.df_for_sync_cache = None
        st.session_state.sync_triggered = False
        st.info("Nenhum arquivo carregado. Faça o upload de um novo arquivo Excel para sincronizar.")
        return

    else:
        st.info("Aguardando o upload de um arquivo Excel para iniciar a sincronização.")
        return

    if st.session_state.sync_triggered:
        st.markdown("---")
        progress_bar = st.progress(0)
        
        try:
            progress_bar.progress(10)

            df_to_process = st.session_state.df_for_sync_cache.copy()

            colunas_para_remover = ['Capa de Canhoto de NF', 'Unnamed: 70']
            colunas_existentes_para_remover = [col for col in colunas_para_remover if col in df_to_process.columns]
            if colunas_existentes_para_remover:
                df_to_process.drop(columns=colunas_existentes_para_remover, inplace=True)

            renomear_colunas = {
                'Cubagem em m3': 'Cubagem em m³',
                'Serie/Numero CTRC': 'Serie_Numero_CTRC'
            }
            colunas_renomeadas = {k: v for k, v in renomear_colunas.items() if k in df_to_process.columns}
            if colunas_renomeadas:
                df_to_process.rename(columns=colunas_renomeadas, inplace=True)
            
            df_to_process = corrigir_tipos(df_to_process)

            supabase.table("fBaseroter").delete().neq("Serie_Numero_CTRC", "").execute()
            inserir_em_lote("fBaseroter", df_to_process)

            progress_bar.progress(30)

            progress_bar.progress(50)
            limpar_tabelas_relacionadas()

            progress_bar.progress(70)

            progress_bar.progress(90)
            aplicar_regras_e_preencher_tabelas()

            progress_bar.progress(95)

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
                carregar_base_supabase.clear()

            progress_bar.progress(100)

            # ✅ Mensagem final com contagem
            try:
                qtd_confirmadas = len(supabase.table("confirmadas_producao").select("Serie_Numero_CTRC").execute().data or [])
                qtd_pre_roterizacao = len(supabase.table("pre_roterizacao").select("Serie_Numero_CTRC").execute().data or [])

                st.success("✅ Sincronização finalizada com sucesso!")
                st.markdown(f"📦 Entregas em **Confirmar Produção**: **{qtd_confirmadas}**")
                st.markdown(f"🗂️ Entregas em **Pré-Roteirização**: **{qtd_pre_roterizacao}**")
                st.balloons()
            except Exception as e:
                st.error("⚠️ Sincronização concluída, mas houve erro ao consultar os totais.")
                st.exception(e)

            salvar_hora_sincronizacao()

            st.session_state.sync_triggered = False
            st.session_state.uploaded_sync_file_hash = None
            st.session_state.df_for_sync_cache = None
            st.session_state.file_uploader_key += 1

            

        except Exception as e:
            #st.error(f"❌ Ocorreu um erro durante a sincronização: {e}")
            st.session_state.sync_triggered = False
            st.session_state.uploaded_sync_file_hash = None
            st.session_state.df_for_sync_cache = None
            st.session_state.file_uploader_key += 1
            salvar_hora_sincronizacao()
            time.sleep(2)
            st.rerun()


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
         "Previsao de Entrega",
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
        "cargas_geradas", "aprovacao_custos", "cargas_aprovadas"
    ]

    for tabela in tabelas_para_limpar_por_ctrc:
        try:
            # A forma mais robusta de limpar uma tabela no Supabase é usar um filtro
            # que é garantido que sempre será verdadeiro para todos os registros que você deseja apagar.
            # Usaremos 'neq' (not equal to) em uma coluna que existe em todas essas tabelas
            # ('Serie_Numero_CTRC') com um valor que nunca existirá.
            # Adicionei um print para depuração.
            #st.write(f"DEBUG: Tentando limpar a tabela: {tabela}")
            response = supabase.table(tabela).delete().neq("Serie_Numero_CTRC", "DUMMY_VALUE_FOR_FULL_CLEAN_12345").execute()
            
            if response.data: # Se 'data' não for None, significa que algo foi retornado/deletado.
                st.success(f"✅ Tabela '{tabela}' limpa com sucesso. Registros afetados: {len(response.data) if response.data else 0}")
            elif response.error:
                st.error(f"❌ Erro ao limpar tabela '{tabela}': {response.error}")
            else:
                st.info(f"ℹ️ Tabela '{tabela}' já estava vazia ou não havia registros correspondentes para deletar.")


        except Exception as e:
            st.error(f"")
            #st.error(f"[ERRO GERAL] Ao tentar limpar a tabela '{tabela}': {e}. Por favor, verifique suas permissões (RLS) no Supabase ou se a coluna 'Serie_Numero_CTRC' existe em todas as tabelas listadas.")

def tratar_data_para_utc(valor):
    """
    Converte um valor de data/hora para uma string ISO 8601 em UTC.
    Prioriza o parsing de formatos ISO e lida com fusos horários.
    Lida com valores NaN, None e strings vazias.
    """
    if pd.isna(valor) or valor == "":
        return None

    dt_obj = None
    if isinstance(valor, str):
        try:
            # 1. Tenta parsear como ISO 8601 (formato preferencial do Supabase), assumindo UTC se nao especificado.
            # 'errors='raise'' para nos dar controle sobre o fallback.
            dt_obj = pd.to_datetime(valor, errors='raise', utc=True)
        except ValueError:
            # 2. Se a tentativa ISO falhar, tenta parsear com dayfirst=True (comum para formatos brasileiros DD-MM-YYYY).
            # 'errors='coerce'' converte falhas para NaT.
            dt_obj = pd.to_datetime(valor, errors='coerce', dayfirst=True)
            
    elif isinstance(valor, (pd.Timestamp, datetime)):
        dt_obj = valor
    else:
        # 3. Tenta coercer outros tipos (ex: numpy.datetime64) para datetime.
        dt_obj = pd.to_datetime(valor, errors='coerce')

    if pd.isna(dt_obj): # Se, após todas as tentativas, ainda for NaT (data inválida)
        return None # Retorna None para ser salvo como NULL no banco de dados

    # Se o objeto datetime estiver "naive" (sem fuso horário), assume que ele está no fuso horário do Brasil.
    if dt_obj.tzinfo is None:
        # 'ambiguous' e 'nonexistent' ajudam a lidar com mudanças de horário de verão.
        dt_obj = dt_obj.tz_localize(FUSO_BRASIL, ambiguous='NaT', nonexistent='NaT')
        if pd.isna(dt_obj): # Se a localização falhar, retorna None
            return None

    # Converte o objeto datetime para o fuso horário UTC e retorna no formato ISO 8601.
    # '.isoformat(timespec='seconds')' para incluir segundos, '.replace('+00:00', 'Z')' para padronizar 'Z' para UTC.
    return dt_obj.tz_convert("UTC").isoformat(timespec='seconds').replace('+00:00', 'Z')



# ------------------------#############-------------------------------------------
def adicionar_entregas_a_carga(ctrcs_selecionados, numero_carga_destino): 
    #st.write("DEBUG: Função 'adicionar_entregas_a_carga' iniciada.")
    #st.write(f"DEBUG: Número da Carga Destino: {numero_carga_destino}")
    #st.write(f"DEBUG: CTRCs selecionados para adição: {ctrcs_selecionados[:5]}...")

    if not ctrcs_selecionados:
        st.warning("⚠️ Nenhum CTRC selecionado.")
        return

    if not numero_carga_destino:
        st.error("Erro interno: Número da carga de destino não fornecido.")
        return

    numero_carga = numero_carga_destino
    entregas_coletadas = []
    found_ctrc_in_pre_roterizacao = set()

    # Carrega os dados brutos da tabela 'pre_roterizacao'
    dados_pre_all = supabase.table("pre_roterizacao").select("*").execute().data or []
    dados_pre_dict = {str(d.get("Serie_Numero_CTRC", "")).strip(): d for d in dados_pre_all}

    # Recupera as entregas com base somente nos CTRCs selecionados
    for ctrc in ctrcs_selecionados:
        entrega = dados_pre_dict.get(str(ctrc).strip())
        if entrega:
            entregas_coletadas.append(entrega)
            found_ctrc_in_pre_roterizacao.add(ctrc)

    if not entregas_coletadas:
        st.warning("⚠️ Nenhuma entrega encontrada na tabela 'pre_roterizacao' para os CTRCs informados.")
        return

    df_para_inserir = pd.DataFrame(entregas_coletadas)

    if "GrupoDeExibicao" not in df_para_inserir.columns:
        df_para_inserir["GrupoDeExibicao"] = df_para_inserir["Rota"]

    df_para_inserir["GrupoDeExibicao"] = df_para_inserir["GrupoDeExibicao"].fillna(df_para_inserir["Rota"])
    df_para_inserir["Data_Hora_Gerada"] = data_hora_brasil_iso()
    df_para_inserir["numero_carga"] = numero_carga

    # --- BLOCO DE TRATAMENTO ROBUSTO PARA DATAS ---
    strict_date_cols = ["Previsao de Entrega", "Entrega Programada"]

    # --- BLOCO DE TRATAMENTO ROBUSTO PARA DATAS ---
    strict_date_cols = ["Previsao de Entrega", "Entrega Programada"]

    strict_date_cols = ["Previsao de Entrega", "Entrega Programada"]

    for col_name in strict_date_cols:
        if col_name in df_para_inserir.columns:
            # Converte para datetime com formato brasileiro
            df_para_inserir[col_name] = pd.to_datetime(df_para_inserir[col_name], errors='coerce', dayfirst=True)
            # Substitui NaT por None
            df_para_inserir[col_name] = df_para_inserir[col_name].where(df_para_inserir[col_name].notna(), None)
            # Converte para UTC ISO 8601
            df_para_inserir[col_name] = df_para_inserir[col_name].apply(tratar_data_para_utc)

    # --- FIM DO BLOCO DE TRATAMENTO DE DATAS ---

    dados_para_insercao = df_para_inserir.to_dict(orient='records')

    insert_success = False
    inserted_ctrcs = []

    for tentativa in range(2): # Tenta inserir duas vezes em caso de falha temporária
        try:
            insert_response = supabase.table("cargas_geradas").insert(dados_para_insercao).execute()
            if insert_response and insert_response.data:
                inserted_ctrcs = [r.get("Serie_Numero_CTRC") for r in insert_response.data if r.get("Serie_Numero_CTRC")]
                insert_success = True
                st.success(f"✅ {len(inserted_ctrcs)} entrega(s) adicionada(s) à Carga {numero_carga}.")
                break # Sai do loop de tentativas se a inserção for bem-sucedida
        except Exception as e:
            st.warning(f"Erro na tentativa {tentativa + 1} de inserção: {e}")
            if tentativa == 0:
                time.sleep(1) # Pequena pausa antes de tentar novamente

    if not insert_success:
        st.error(f"❌ Falha ao adicionar entregas à carga {numero_carga}.")
        return

    # Deleta as entregas de 'pre_roterizacao' após a inserção bem-sucedida em 'cargas_geradas'
    if inserted_ctrcs:
        try:
            # Calcula a interseção para garantir que apenas CTRCs realmente inseridos sejam deletados
            ctrcs_to_delete_from_pre = list(set(inserted_ctrcs).intersection(found_ctrc_in_pre_roterizacao))
            if ctrcs_to_delete_from_pre:
                delete_response_pre = supabase.table("pre_roterizacao").delete().in_("Serie_Numero_CTRC", ctrcs_to_delete_from_pre).execute()
                st.info(f"Removidas {len(delete_response_pre.data)} entregas de 'pre_roterizacao'.")
        except Exception as e:
            st.warning(f"Erro ao deletar de 'pre_roterizacao': {e}")
    else:
        st.warning("Nenhuma entrega foi realmente inserida para deletar da tabela de origem.")

    # Força o recarregamento dos caches de estado da sessão para atualizar os grids
    st.session_state["reload_rotas_confirmadas"] = True
    st.session_state["reload_pre_roterizacao"] = True
    st.session_state["reload_cargas_geradas"] = True
    st.session_state.pop("df_pre_roterizacao_cache", None)
    st.session_state.pop("df_rotas_confirmadas_cache", None)
    st.session_state.pop("df_cargas_cache", None)

    st.rerun() # Força uma nova execução do script para refletir as mudanças


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
            (df['Data de Embarque'] < hoje + pd.Timedelta(days=1)) | # Entregas com data de embarque até o dia atual (passadas ou hoje)
            ((df['Status'] == 'AGENDAR') & (df['Entrega Programada'].isna())) | # Entregas com status 'AGENDAR' e sem 'Entrega Programada'
            (df['Entrega Programada'].notna()) | # Entregas que JÁ possuem uma 'Entrega Programada'
            # --- NOVA CONDIÇÃO ADICIONADA AQUI ---
            (df['Codigo da Ultima Ocorrencia'].isin(['17', '39', '78', '79'])) # Entregas com códigos de ocorrência específicos
        ].copy()

        confirmadas = df[~df['Serie_Numero_CTRC'].isin(obrigatorias['Serie_Numero_CTRC'])].copy()

        obrigatorias.drop_duplicates(subset='Serie_Numero_CTRC', inplace=True)
        confirmadas.drop_duplicates(subset='Serie_Numero_CTRC', inplace=True)

        colunas_finais = [
            'Serie_Numero_CTRC', 'Data de Emissao','Cliente Pagador', 'Chave CT-e', 'Cliente Destinatario',
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
DATE_DISPLAY_FORMAT_STRING = '%d-%m-%Y'

# Formato de exibição de data no padrão brasileiro (apenas data)
DATE_ONLY_DISPLAY_FORMAT_STRING = '%d-%m-%Y'


# Lista de todas as colunas que são datas/horas no seu sistema e que devem ser formatadas para exibição
# ATENÇÃO: As colunas nesta lista serão formatadas com HORA.
GLOBAL_DATE_DISPLAY_COLUMNS = [
    "Data de Emissao", "Data de Autorizacao", "Data de inclusao da Ultima Ocorrencia",
    "Data da Ultima Ocorrencia", "Previsao de Entrega", "Entrega Programada",
    "Data da Entrega Realizada", "Data do Cancelamento", "Data do Escaneamento",
    "Data_Hora_Gerada", "data_fechamento", "data_aprovacao_custos"
]


# Nova função para aplicar formato de data APENAS (sem hora)
def apply_brazilian_date_only_format_for_display(df_to_format, date_cols):
    for col in date_cols:
        if col in df_to_format.columns:
            if not pd.api.types.is_datetime64_any_dtype(df_to_format[col]):
                df_to_format[col] = pd.to_datetime(df_to_format[col], errors='coerce', dayfirst=True)
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
                # Detecta automaticamente se a string está no formato brasileiro ou ISO
                amostras_validas = df_to_format[col].dropna().astype(str).head(5)
                if amostras_validas.str.match(r"\d{2}-\d{2}-\d{4}").any():
                    df_to_format[col] = pd.to_datetime(df_to_format[col], errors='coerce', dayfirst=True)
                elif amostras_validas.str.match(r"\d{4}-\d{2}-\d{2}").any():
                    df_to_format[col] = pd.to_datetime(df_to_format[col], errors='coerce', dayfirst=False)
                else:
                    df_to_format[col] = pd.to_datetime(df_to_format[col], errors='coerce', dayfirst=True)

            # Formata para exibição no padrão brasileiro
            df_to_format[col] = df_to_format[col].apply(
                lambda x: x.strftime(DATE_DISPLAY_FORMAT_STRING)
                if pd.notna(x) and isinstance(x, (Timestamp, datetime))
                else ''
            )
    return df_to_format

# Constantes para colunas que devem ser tratadas como APENAS DATA (sem hora)
# em algumas conversões (e.g., re-parsing do AgGrid para Supabase)
DATE_ONLY_REPARSE_COLUMNS = ['Previsao de Entrega', 'Entrega Programada']

#FUNÇÃO GERAR PDF 
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO
import pandas as pd
from datetime import datetime, date
import numpy as np
from pandas import Timestamp # Importação mantida para compatibilidade de tipos

# Supondo que FUSO_BRASIL e formatar_brasileiro já estão definidos no seu código
# Exemplo (se não estiverem definidos, mantenha os seus):
from zoneinfo import ZoneInfo

def formatar_brasileiro(valor):
    if valor is None or (isinstance(valor, (float, np.float64)) and np.isnan(valor)):
        return "0,00"
    if not isinstance(valor, (int, float, np.float64)):
        valor = pd.to_numeric(valor, errors='coerce')
        if pd.isna(valor):
            return "0,00"
    formatted_us = "{:,.2f}".format(valor)
    formatted_br = formatted_us.replace('.', 'TEMP').replace(',', '.').replace('TEMP', ',')
    return formatted_br



############################## Gerar PDF ########################################################

def gerar_pdf_carga(df_entregas, carga, rota, motorista, placa, veiculo, valor_frete, valor_contratacao):
    buffer = BytesIO()

    # Confirme que este é o caminho EXATO para o seu logo.png
    image_path = r"C:\Users\Rafael\Roteriza\Scripts\logo.png" 
    img_width = 1.0 * inch # Largura desejada para o logo
    img_height = 0.75 * inch # Altura desejada para o logo

    def draw_image_on_page(canvas_obj, doc):
        page_width, page_height = landscape(letter)
        
        # --- ALTERAÇÃO PRINCIPAL AQUI: Usar as margens do documento ---
        # x_pos: Alinha com a margem esquerda do documento
        x_pos = doc.leftMargin 
        
        # y_pos: Calcula a posição Y para que o topo da imagem esteja alinhado
        # com a margem superior do documento.
        # page_height - doc.topMargin é a posição da margem superior.
        # Subtraímos img_height para obter a posição inferior da imagem.
        y_pos = page_height - img_height - doc.topMargin
        try:
            canvas_obj.drawImage(image_path, x_pos, y_pos, width=img_width, height=img_height, preserveAspectRatio=True)
        except Exception as e:
            print(f"Erro ao desenhar imagem no PDF: {e}")

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=inch / 2, # 0.5 polegadas
        leftMargin=inch / 2, # Aumentei um pouco para 0.5 para dar espaço à imagem
        topMargin=inch / 2,  # 0.5 polegadas
        bottomMargin=inch / 2,
        onPage=draw_image_on_page # Continua chamando a função para desenhar em cada página
    )
    styles = getSampleStyleSheet()
    h1 = styles['h1']
    styles.add(ParagraphStyle(name='CustomNormal', parent=styles['Normal'], spaceBefore=6, spaceAfter=6, leading=14))

    header_paragraph_style = ParagraphStyle(
        name='TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        alignment=1,
        leading=9,
        spaceAfter=3
    )

    cell_paragraph_style = ParagraphStyle(
        name='TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        alignment=0,
        leading=9
    )

    elements = []

       # --- ADICIONE ESTA LINHA AQUI! (Espaço para o logo) ---
    elements.append(Spacer(1, 0.75 * inch)) # Ajuste 0.75 conforme necessário para o tamanho do seu logo

    # --- Cabeçalho da Carga ---
    elements.append(Paragraph(f"Detalhes da Carga: <font color='#1A73E8'><b>{carga}</b></font>", h1))
    elements.append(Spacer(1, 0.2 * inch))

    info_data = [
        [
            Paragraph(f"<b>Rota:</b> {rota}", styles['CustomNormal']),
            Paragraph(f"<b>Motorista:</b> {motorista if motorista and motorista.strip() else '<i>Não Informado</i>'}", styles['CustomNormal']),
            Paragraph(f"<b>Placa:</b> {placa if placa and placa.strip() else '<i>Não Informada</i>'}", styles['CustomNormal']),
        ],
        [
            Paragraph(f"<b>Tipo de Veículo:</b> {veiculo if veiculo and veiculo.strip() else '<i>Não Informado</i>'}", styles['CustomNormal']),
            Paragraph(f"<b>Valor de Contratação:</b> R$ {formatar_brasileiro(valor_contratacao)}", styles['CustomNormal']),
            ""
        ]
    ]

    info_table = Table(info_data)
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(info_table)

    # --- Cálculo Totais ---
    df_entregas["Peso Real em Kg"] = pd.to_numeric(df_entregas.get("Peso Real em Kg", 0), errors="coerce").fillna(0)
    df_entregas["Cubagem em m³"] = pd.to_numeric(df_entregas.get("Cubagem em m³", 0), errors="coerce").fillna(0)

    qtd_entregas = len(df_entregas)
    peso_real_total = df_entregas["Peso Real em Kg"].sum()
    cubagem_total = df_entregas["Cubagem em m³"].sum()

    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph("<b>Resumo das Entregas:</b>", styles['h2']))
    elements.append(Spacer(1, 0.1 * inch))

    resumo_dados = [
        [
            Paragraph(f"<b>Qtde Total de Entregas:</b> {qtd_entregas}", styles['CustomNormal']),
            Paragraph(f"<b>Peso Real Total:</b> {formatar_brasileiro(peso_real_total)} Kg", styles['CustomNormal']),
            Paragraph(f"<b>Cubagem Total:</b> {formatar_brasileiro(cubagem_total)} m³", styles['CustomNormal']),
        ]
    ]

    resumo_table = Table(resumo_dados)
    resumo_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(resumo_table)

    # --- Tabela de Entregas ---
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph("<b>Entregas Associadas:</b>", styles['h2']))
    elements.append(Spacer(1, 0.1 * inch))

    cols_header_map = {
        "Numero da Nota Fiscal": "Nº da<br/>NF",
        "Cliente Pagador": "Cliente<br/>Pagador",
        "Cidade de Entrega": "Cidade<br/>de Entrega",
        "Quantidade de Volumes": "Qtd<br/>Volumes",
        "Cliente Destinatario": "Cliente<br/>Destinatário",
        "Bairro do Destinatario": "Bairro do<br/>Destinatário",
        "Previsao de Entrega": "Previsão<br/>de Entrega",
        "Entrega Programada": "Entrega<br/>Programada",
        "Peso Calculado em Kg": "Peso<br/>Calculado<br/>(Kg)",
        "Peso Real em Kg": "Peso Real<br/>(Kg)",
        "Cubagem em m³": "Cubagem<br/>(m³)",
        "Serie_Numero_CTRC": "Série/Nº<br/>CTRC"
    }

    requested_order_keys = [
        "Numero da Nota Fiscal", "Cliente Pagador", "Cidade de Entrega", "Quantidade de Volumes",
        "Cliente Destinatario", "Bairro do Destinatario", "Previsao de Entrega",
        "Entrega Programada", "Peso Calculado em Kg", "Peso Real em Kg", "Cubagem em m³","Serie_Numero_CTRC"
    ]

    df_filtrado = df_entregas[[col for col in requested_order_keys if col in df_entregas.columns]].copy()

    header_row = []
    for col_name in df_filtrado.columns:
        display_name = cols_header_map.get(col_name, col_name)
        header_row.append(Paragraph(display_name, header_paragraph_style))

    for col in ["Valor do Frete", "Peso Real em Kg", "Peso Calculado em Kg", "Cubagem em m³"]:
        if col in df_filtrado.columns:
            df_filtrado[col] = pd.to_numeric(df_filtrado[col], errors='coerce').fillna(0)
            df_filtrado[col] = df_filtrado[col].apply(lambda x: formatar_brasileiro(x))

    for col in ["Previsao de Entrega", "Entrega Programada"]:
        if col in df_filtrado.columns:
            df_filtrado[col] = pd.to_datetime(df_filtrado[col], errors='coerce').dt.strftime('%d-%m-%Y').fillna('')

    table_body_data = []
    for _, row in df_filtrado.iterrows():
        row_data = []
        for col_name in df_filtrado.columns:
            cell_value = row[col_name]
            alignment = 2 if col_name in ["Peso Calculado em Kg", "Peso Real em Kg", "Cubagem em m³", "Valor do Frete"] else 0
            temp_cell_style = ParagraphStyle(name='TempCell', parent=cell_paragraph_style, alignment=alignment)
            row_data.append(Paragraph(str(cell_value), temp_cell_style))
        table_body_data.append(row_data)

    dados_tabela = [header_row] + table_body_data

    if not table_body_data:
        elements.append(Paragraph("<i>Nenhuma entrega detalhada disponível para esta carga.</i>", styles['CustomNormal']))
    else:
        col_widths = [
            0.8 * inch, 1.0 * inch, 1.1 * inch, 0.7 * inch, 0.9 * inch,
            0.7 * inch, 0.9 * inch, 0.7 * inch, 0.8 * inch, 0.8 * inch, 0.7 * inch,
            0.9 * inch 
        ]
        table = Table(dados_tabela, colWidths=col_widths, hAlign='LEFT')
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EFEFEF')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ]))
        elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()



# ===========================================
# # FIM DAS NOVAS FUNÇÕES PARA GERAÇÃO DE PDF
# ===========================================
##########################################

# PÁGINA Confirmar Produção

##########################################
def pagina_confirmar_producao():
    st.markdown("## Confirmar Produção")

    # Carregando entregas diretamente da tabela 'confirmadas_producao'
    with st.spinner("🔄 Carregando entregas para confirmar produção..."):
        try:
            recarregar = st.session_state.pop("reload_confirmadas_producao", False)
            if recarregar or "df_confirmadas_cache" not in st.session_state:
                df = pd.DataFrame(supabase.table("confirmadas_producao").select("*").execute().data)
                st.session_state["df_confirmadas_cache"] = df
            else:
                df = st.session_state["df_confirmadas_cache"]

            if not df.empty:
                if 'Rota' in df.columns:
                    df['Rota'] = df['Rota'].fillna('').astype(str)
                if 'Status' in df.columns:
                    df['Status'] = df['Status'].fillna('').astype(str)
                if 'Entrega Programada' in df.columns:
                    df['Entrega Programada'] = pd.to_datetime(df['Entrega Programada'], errors='coerce') 
                if 'Particularidade' in df.columns:
                    df['Particularidade'] = df['Particularidade'].fillna('').astype(str)
                if 'Serie_Numero_CTRC' in df.columns:
                    df['Serie_Numero_CTRC'] = df['Serie_Numero_CTRC'].astype(str)
                if 'Cliente Pagador' in df.columns:
                    df['Cliente Pagador'] = df['Cliente Pagador'].fillna('').astype(str)

        except Exception as e:
            st.error(f"Erro ao consultar o banco de dados: {e}")
            return

        if df.empty:
            st.info("Nenhuma entrega disponível para confirmar produção.")
            return

    # ========= MÉTRICAS COMPARATIVAS =========
    col_total_2, col_total_1, col_total_3, col_total_4, spacer, col_conf_1, col_conf_2, col_conf_3 = st.columns([1, 1, 1, 1, 0.5, 1, 1, 1])

    with col_total_2:
        st.metric("📦 Total de Entregas", len(df))

    with col_total_1:
        st.metric("📦 Total de Clientes", df["Cliente Pagador"].nunique() if "Cliente Pagador" in df.columns else 0)

    with col_total_3:
        st.metric("⚖️ Peso Real (kg)", formatar_brasileiro(df['Peso Real em Kg'].sum()))

    with col_total_4:
        st.metric("📏 Peso Calculado (kg)", formatar_brasileiro(df['Peso Calculado em Kg'].sum()))

    # 🔹 DADOS CONFIRMADOS NA SESSÃO (à direita)
    try:
        df_confirmadas = pd.DataFrame(supabase.table("aprovacao_diretoria").select("*").execute().data)
    except Exception as e:
        st.error(f"Erro ao carregar dados da aprovação da diretoria: {e}")
        df_confirmadas = pd.DataFrame()


    total_confirmadas = len(df_confirmadas)
    peso_real_conf = df_confirmadas["Peso Real em Kg"].sum() if "Peso Real em Kg" in df_confirmadas else 0
    peso_calc_conf = df_confirmadas["Peso Calculado em Kg"].sum() if "Peso Calculado em Kg" in df_confirmadas else 0

    with col_conf_1:
        st.metric("✅ Entregas Confirmadas", total_confirmadas)

    with col_conf_2:
        st.metric("✅ Peso Real Confirmado", formatar_brasileiro(peso_real_conf))

    with col_conf_3:
        st.metric("✅ Peso Calculado Confirmado", formatar_brasileiro(peso_calc_conf))


    # Definir as colunas que devem ser exibidas no grid
    colunas_exibir = [
    "Serie_Numero_CTRC",  "Cliente Pagador", "Cliente Destinatario", "Cidade de Entrega",
    "Bairro do Destinatario", "Previsao de Entrega", "Numero da Nota Fiscal",  "Status",
    "Entrega Programada", "Peso Real em Kg", "Peso Calculado em Kg", "Valor do Frete",
    "Rota", "Regiao", "Data de Emissao", "Chave CT-e",
    "Particularidade", "Codigo da Ultima Ocorrencia", "Cubagem em m³", "Quantidade de Volumes"
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
            return { 'background-color': '#FFA500', 'color': '#000' }; // LARANJA FORTE
        }

        if (particularidade && typeof particularidade === 'string' && particularidade.trim() !== "") {
            return { 'background-color': '#FFFF00', 'color': '#000' }; // AMARELO FORTE
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
        with st.expander("🔽 Selecionar entregas", expanded=True):
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
                gb.configure_default_column(minWidth=90)
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
                    update_mode=GridUpdateMode.SELECTION_CHANGED,  #  acompanhar teste 
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

                qtd_sel = len(selecionadas)
                peso_real_sel = selecionadas["Peso Real em Kg"].sum() if "Peso Real em Kg" in selecionadas else 0
                peso_calc_sel = selecionadas["Peso Calculado em Kg"].sum() if "Peso Calculado em Kg" in selecionadas else 0

                st.markdown(
                    f"<span style='font-weight:bold;'>📦 Entregas selecionadas:</span> {qtd_sel} &nbsp;&nbsp; | &nbsp;&nbsp; "
                    f"<span style='font-weight:bold;'>⚖️ Peso Real:</span> {formatar_brasileiro(peso_real_sel)} kg &nbsp;&nbsp; | &nbsp;&nbsp; "
                    f"<span style='font-weight:bold;'>📏 Peso Calculado:</span> {formatar_brasileiro(peso_calc_sel)} kg",
                    unsafe_allow_html=True
                )

                # Botão para confirmar produção
                if not selecionadas.empty:
                    if st.button(" Enviar para Aprovação", key=f"enviar_aprovacao_{cliente_pagador}"):
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
                            if registros:  # Apenas insere se houver registros válidos
                                supabase.table("aprovacao_diretoria").insert(registros).execute()

                                # ✅ Alimenta o contador da sessão com o que foi confirmado
                                st.session_state["df_entregas_confirmadas"] = pd.DataFrame(registros)
                            
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
    st.markdown("## Aprovação Produção")

    # --- INÍCIO DO BLOCO DE CARREGAMENTO DE DADOS (MOVIDO PARA O TOPO) ---
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
            return # Se estiver vazio, sai da função antes de tentar processar
    except Exception as e:
        st.error(f"Erro ao carregar dados da aprovação: {e}")
        return # Sai da função se houver um erro no carregamento
    # --- FIM DO BLOCO DE CARREGAMENTO DE DADOS ---

    # Agora, df_aprovacao está garantida de estar definida se a execução chegou até aqui.

    if st.button("✅ Aprovar Todas as Entregas da Página", key="btn_aprovar_todas_topo"):
        try:
            with st.spinner("🔄 Aprovando todas as entregas."):
                # df_aprovacao agora estará disponível aqui
                df_aprovar = df_aprovacao.drop(columns=["_selectedRowNodeInfo"], errors="ignore").copy()
                df_aprovar["aprovador_diretoria_login"] = st.session_state.get("username", "Desconhecido")
                df_aprovar["data_aprovacao_diretoria"] = data_hora_brasil_iso()

                # Normaliza datas antes de salvar
                for col in GLOBAL_DATE_DISPLAY_COLUMNS:
                    if col in df_aprovar.columns:
                        df_aprovar[col] = pd.to_datetime(df_aprovar[col], errors='coerce')
                        df_aprovar[col] = df_aprovar[col].apply(lambda x: x.isoformat() if pd.notna(x) else None)

                df_aprovar = df_aprovar.replace([np.nan, np.inf, -np.inf, ""], None)
                registros = df_aprovar.to_dict(orient="records")
                registros = [r for r in registros if r.get("Serie_Numero_CTRC")]

                if registros:
                    supabase.table("pre_roterizacao").insert(registros).execute()
                    chaves = [r["Serie_Numero_CTRC"] for r in registros]
                    supabase.table("aprovacao_diretoria").delete().in_("Serie_Numero_CTRC", chaves).execute()

                    st.session_state["reload_aprovacao_diretoria"] = True
                    st.session_state["reload_pre_roterizacao"] = True
                    st.success(f"✅ {len(chaves)} entregas aprovadas em lote.")
                    st.rerun()
                else:
                    st.info("Nenhuma entrega válida encontrada para aprovar.")
        except Exception as e:
            st.error(f"❌ Erro ao aprovar todas as entregas: {e}")

    # Obter a classe do usuário logado (assume 'colaborador' se não estiver definida por segurança)
    current_user_class = st.session_state.get("classe", "colaborador")
    is_user_aprovador = (current_user_class == "aprovador")

    # Mensagem de aviso se o usuário não for aprovador
    if not is_user_aprovador:
        st.warning("⛔ Apenas usuários com classe 'aprovador' podem realizar ações de aprovação de diretoria.")

    # ======= BLOCO DE MÉTRICAS: TOTAL + APROVADAS (lado a lado) =======
    col2, col1, col3, col4, spacer, col5, col6, col7 = st.columns([1, 1, 1, 1, 0.3, 1, 1, 1])

    with col1:
        st.metric("👥 Total de Clientes", df_aprovacao["Cliente Pagador"].nunique()) # df_aprovacao já definido aqui

    with col2:
        st.metric("📦 Total de Entregas", len(df_aprovacao)) # df_aprovacao já definido aqui

    with col3:
        st.metric("⚖️ Peso Real (kg)", formatar_brasileiro(df_aprovacao["Peso Real em Kg"].sum())) # df_aprovacao já definido aqui

    with col4:
        st.metric("📏 Peso Calculado (kg)", formatar_brasileiro(df_aprovacao["Peso Calculado em Kg"].sum())) # df_aprovacao já definido aqui

    # === MÉTRICAS DINÂMICAS (Entregas selecionadas para aprovação) ===
    df_selecionadas_globais = st.session_state.get("df_aprovadas_diretoria", pd.DataFrame())
    qtd_aprovadas = len(df_selecionadas_globais)
    peso_real_aprovado = df_selecionadas_globais["Peso Real em Kg"].sum() if "Peso Real em Kg" in df_selecionadas_globais else 0
    peso_calc_aprovado = df_selecionadas_globais["Peso Calculado em Kg"].sum() if "Peso Calculado em Kg" in df_selecionadas_globais else 0

    with col5:
        st.metric("✅ Entregas Aprovadas", qtd_aprovadas)
    with col6:
        st.metric("✅ Peso Real Aprovado", formatar_brasileiro(peso_real_aprovado))
    with col7:
        st.metric("✅ Peso Calc. Aprovado", formatar_brasileiro(peso_calc_aprovado))
        
    def badge(label):
        return f"<span style='background:#eef2f7;border-radius:12px;padding:6px 12px;margin:4px;color:inherit;display:inline-block;'>{label}</span>"

    colunas_exibir = [
    "Serie_Numero_CTRC",  "Cliente Pagador", "Cliente Destinatario", "Cidade de Entrega",
    "Bairro do Destinatario", "Previsao de Entrega", "Numero da Nota Fiscal",  "Status",
    "Entrega Programada", "Peso Real em Kg", "Peso Calculado em Kg", "Valor do Frete",
    "Rota", "Regiao", "Data de Emissao", "Chave CT-e",
    "Particularidade", "Codigo da Ultima Ocorrencia", "Cubagem em m³", "Quantidade de Volumes"
]

    linha_destacar = JsCode("""
    function(params) {
        const status = params.data['Status'];
        const entrega = params.data['Entrega Programada'];
        const particularidade = params.data['Particularidade'];

        // Verifica se a entrega está vazia ou contém apenas espaços (para compatibilidade com strings vazias)
        const isEntregaEmpty = !entrega || (typeof entrega === 'string' && entrega.trim() === '');

        if (status === 'AGENDAR' && isEntregaEmpty) {
            return { 'background-color': '#ffff00', 'color': '#333' }; // Amarelo puro para "AGENDAR" sem data
        }

        if (particularidade && typeof particularidade === 'string' && particularidade.trim() !== "") {
            return { 'background-color': '#bc8f8f', 'color': '#fff' }; // Rosado escuro para "Particularidade"
        }

        return null;
    }
""")


    for cliente in sorted(df_aprovacao["Cliente Pagador"].unique()): # df_aprovacao já definido aqui
        df_cliente = df_aprovacao[df_aprovacao["Cliente Pagador"] == cliente].copy() # df_aprovacao já definido aqui
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

        with st.expander("🔽 Selecionar entregas", expanded=True):
            df_formatado = apply_brazilian_date_format_for_display(df_cliente[[col for col in colunas_exibir if col in df_cliente.columns]].copy())

            # NOVO: Checkbox "Marcar todas" dentro do expander
            checkbox_key = f"marcar_todas_aprov_{cliente}"
            if checkbox_key not in st.session_state:
                st.session_state[checkbox_key] = False
            marcar_todas = st.checkbox("Marcar todas", key=checkbox_key)

            if not df_formatado.empty:
                gb = GridOptionsBuilder.from_dataframe(df_formatado)
                gb.configure_default_column(minWidth=90)
                gb.configure_selection("multiple", use_checkbox=True)
                gb.configure_grid_options(paginationPageSize=12)
                gb.configure_grid_options(alwaysShowHorizontalScroll=True)
                gb.configure_grid_options(rowStyle={'font-size': '11px'})
                gb.configure_grid_options(onGridReady=GRID_RESIZE_JS_CODE)
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

                qtd_sel = len(selecionadas)
                peso_real_sel = selecionadas["Peso Real em Kg"].sum() if "Peso Real em Kg" in selecionadas else 0
                peso_calc_sel = selecionadas["Peso Calculado em Kg"].sum() if "Peso Calculado em Kg" in selecionadas else 0

                st.markdown(
                    f"<span style='font-weight:bold;'>📦 Entregas selecionadas:</span> {qtd_sel} &nbsp;&nbsp; | &nbsp;&nbsp; "
                    f"<span style='font-weight:bold;'>⚖️ Peso Real:</span> {formatar_brasileiro(peso_real_sel)} kg &nbsp;&nbsp; | &nbsp;&nbsp; "
                    f"<span style='font-weight:bold;'>📏 Peso Calculado:</span> {formatar_brasileiro(peso_calc_sel)} kg",
                    unsafe_allow_html=True
                )

                if not selecionadas.empty:
                    col_aprovar, col_rejeitar = st.columns(2)

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
                                        # 🔄 Acumula aprovadas na sessão
                                        df_aprovadas_sessao = pd.DataFrame(registros_para_pre_roterizacao)
                                        if "df_aprovadas_diretoria" in st.session_state:
                                            st.session_state["df_aprovadas_diretoria"] = pd.concat([st.session_state["df_aprovadas_diretoria"], df_aprovadas_sessao], ignore_index=True)
                                        else:
                                            st.session_state["df_aprovadas_diretoria"] = df_aprovadas_sessao
                                    chaves_aprovadas = [r.get("Serie_Numero_CTRC") for r in registros_para_pre_roterizacao if r.get("Serie_Numero_CTRC")]
                                    if chaves_aprovadas:
                                        supabase.table("aprovacao_diretoria").delete().in_("Serie_Numero_CTRC", chaves_aprovadas).execute()

                                    st.success(f"✅ {len(registros_para_pre_roterizacao)} entregas aprovadas e enviadas para Pré-Roteirização.")
                                    
                                    # --- INVALIDAÇÃO DE CACHES E KEYS DE GRIDS (Origem e Destino) ---
                                    st.session_state["reload_aprovacao_diretoria"] = True
                                    st.session_state.pop(grid_key_id, None)
                                    st.session_state.pop(checkbox_key, None)

                                    rotas_afetadas = df_aprovar["Rota"].dropna().unique()
                                    for rota_afetadas_val in rotas_afetadas:
                                        key_do_session_state_para_o_uuid = f"grid_pre_rota_{rota_afetadas_val}"
                                        if key_do_session_state_para_o_uuid in st.session_state:
                                            st.session_state.pop(key_do_session_state_para_o_uuid, None)
                                    st.session_state["reload_pre_roterizacao"] = True
                                    st.write(f"DEBUG - Rotas sendo processadas para invalidação do grid de Pré-Roterização: {rotas_afetadas.tolist()}")
                                    # --- FIM DA INVALIDAÇÃO ---

                                    st.rerun()

                            except Exception as e:
                                st.error(f"❌ Erro ao aprovar entregas: {e}")

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
                                    st.session_state["reload_aprovacao_diretoria"] = True
                                    st.session_state.pop(grid_key_id, None)
                                    st.session_state.pop(checkbox_key, None)

                                    clientes_afetados = df_rejeitar["Cliente Pagador"].dropna().unique()
                                    for cliente_afetado in clientes_afetados:
                                        grid_key_confirmar_prod = f"grid_conf_prod_{cliente_afetado}"
                                        if grid_key_confirmar_prod in st.session_state:
                                            st.session_state.pop(grid_key_confirmar_prod, None)
                                    
                                    st.session_state["reload_confirmadas_producao"] = True
                                    # --- FIM DA ATUALIZAÇÃO DO GRID ---

                                    st.rerun()

                            except Exception as e:
                                st.error(f"❌ Erro ao rejeitar entregas: {e}")



##########################################

# Função PÁGINA PRÉ ROTERIZAÇÃO
##########################################
# Função completa consolidada com carregamento, métricas, grids e ações de carga
def pagina_pre_roterizacao():
    st.markdown("## Pré-Roteirização")

    # --- Bloco de criação de carga avulsa ---
    if "nova_carga_em_criacao" not in st.session_state:
        st.session_state["nova_carga_em_criacao"] = False
        st.session_state["numero_nova_carga"] = ""

    if not st.session_state["nova_carga_em_criacao"]:
        if st.button("🆕 Criar Nova Carga Avulsa", key="btn_nova_carga_avulsa"):
            try:
                numero_carga = gerar_proximo_numero_carga(supabase)
                if numero_carga:
                    st.session_state["nova_carga_em_criacao"] = True
                    st.session_state["numero_nova_carga"] = numero_carga
                    st.rerun()
            except Exception as e:
                st.error(f"Erro ao criar nova carga: {e}")
    else:
        st.success(f"Nova Carga Criada: {st.session_state['numero_nova_carga']}")
        chaves_input = st.text_area("Insira as Chaves CT-e (uma por linha)")

        col1, col2 = st.columns([4, 1.2])
        with col1:
            adicionar = st.button("➕ Adicionar Entregas à Carga", key="botao_manual")
        with col2:
            cancelar = st.button("❌ Cancelar", help="Cancelar Nova Carga")

        if cancelar:
            st.session_state["nova_carga_em_criacao"] = False
            st.session_state["numero_nova_carga"] = ""
            st.rerun()

        if adicionar:
            try:
                chaves = [re.sub(r"\s+", "", c) for c in chaves_input.splitlines() if c.strip()]
                if not chaves:
                    st.warning("Nenhuma Chave CT-e válida informada.")
                    return

                dados_pre = supabase.table("pre_roterizacao").select("*").execute().data or []
            
                dados_cargas = supabase.table("cargas_geradas").select("*").execute().data or []

                entregas_ja_em_carga = {
                    str(d.get("Chave CT-e", "")).strip(): d.get("numero_carga")
                    for d in dados_cargas if d.get("Chave CT-e")
                }

                entregas_encontradas = []

                for chave in chaves:
                    if chave in entregas_ja_em_carga:
                        st.warning(f"⚠️ A entrega com chave '{chave}' já está na carga {entregas_ja_em_carga[chave]}.")
                        continue

                    entrega = next((d for d in dados_pre if str(d.get("Chave CT-e", "")).strip() == chave), None)
                    origem = "pre_roterizacao"

                    

                    if not entrega:
                        st.warning(f"⚠️ Chave {chave} não encontrada ou já foi processada.")
                        continue

                    entrega.pop("id", None)
                    entrega["numero_carga"] = st.session_state["numero_nova_carga"]
                    entrega["Data_Hora_Gerada"] = data_hora_brasil_iso()

                    # ✅ Tratamento de datas
                    colunas_data = [
                        "Previsao de Entrega", "Entrega Programada", "Data de Emissao", "Data de Autorizacao",
                        "Data da Entrega Realizada", "Data do Cancelamento", "Data do Escaneamento",
                        "Data da Ultima Ocorrencia", "Data de inclusao da Ultima Ocorrencia"
                    ]

                    for col in colunas_data:
                        if col in entrega:
                            try:
                                valor_original = entrega.get(col)

                                # Preservar vazio se for AGENDAR sem data
                                if col == "Entrega Programada" and entrega.get("Status") == "AGENDAR" and not valor_original:
                                    entrega[col] = None
                                else:
                                    try:
                                        entrega[col] = pd.to_datetime(valor_original, errors='coerce')
                                        entrega[col] = entrega[col].isoformat() if pd.notnull(entrega[col]) else None
                                    except Exception:
                                        entrega[col] = None

                            except Exception:
                                entrega[col] = None

                    for k, v in entrega.items():
                        if k in colunas_data:
                            continue
                        if isinstance(v, (dict, list)):
                            entrega[k] = str(v)
                        elif isinstance(v, (float, int)) and (pd.isna(v) or np.isinf(v)):
                            entrega[k] = None
                        elif isinstance(v, pd._libs.tslibs.nattype.NaTType) or pd.isna(v):
                            entrega[k] = None
                        else:
                            entrega[k] = v

                    entregas_encontradas.append(entrega)

                    if origem:
                        supabase.table(origem).delete().eq("Serie_Numero_CTRC", entrega["Serie_Numero_CTRC"]).execute()

                if entregas_encontradas:
                    try:
                        supabase.table("cargas_geradas").insert(entregas_encontradas).execute()
                        st.success(f"✅ {len(entregas_encontradas)} entrega(s) adicionada(s) à carga {st.session_state['numero_nova_carga']}.")
                    except Exception as e:
                        st.error(f"Erro ao salvar entregas na carga: {e}")

                st.session_state["nova_carga_em_criacao"] = False
                st.session_state["numero_nova_carga"] = ""
                st.session_state["reload_pre_roterizacao"] = True
                st.session_state["reload_cargas_geradas"] = True
               
                st.rerun()

            except Exception as e:
                st.error(f"Erro ao adicionar entregas: {e}")


    # --- Bloco de carregamento de dados ---
    with st.spinner("🔄 Carregando dados das entregas..."):
        try:
            df_aprovadas_diretoria = st.session_state.get("df_aprovadas_diretoria", pd.DataFrame())
            dados_confirmados = pd.DataFrame()

            recarregar = st.session_state.pop("reload_pre_roterizacao", False)
            
            if recarregar or "df_pre_roterizacao_cache" not in st.session_state or \
               (st.session_state.get("df_pre_roterizacao_cache") is not None and st.session_state["df_pre_roterizacao_cache"].empty):
                #st.write("DEBUG: [pagina_pre_roterizacao] Cache desativado, recarregar=True, ou cache vazio. Chamando carregar_base_supabase()...")
                df_total = carregar_base_supabase() # Esta chamada retorna 192 linhas
                
                #st.write(f"DEBUG: [pagina_pre_roterizacao] carregar_base_supabase() retornou {len(df_total)} linhas. df_total.empty: {df_total.empty}") # <--- AQUI
                st.session_state["df_pre_roterizacao_cache"] = df_total # Atualiza o cache com o resultado

                # Invalida as chaves dos grids APENAS se um recarregamento explícito ocorreu E se df_total não está vazio
                if recarregar and not df_total.empty:
                    for key in list(st.session_state.keys()):
                        if key.startswith("grid_pre_rota_"):
                            st.session_state.pop(key, None) # Remove a key para forçar reconstrução do grid
            else:
                #st.write("DEBUG: [pagina_pre_roterizacao] Usando dados do cache 'df_pre_roterizacao_cache'.")
                df_total = st.session_state["df_pre_roterizacao_cache"] # Pega do cache

            df_visivel = df_total.copy() # Cria uma cópia para trabalhar na página

            # 📤 Exportação em Excel de todas as entregas visíveis na pré-roteirização
            if not df_visivel.empty:
                excel_buffer = BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                    df_visivel.to_excel(writer, index=False, sheet_name="Pre-Roterizacao")
                    writer.close()
                excel_buffer.seek(0)

                st.download_button(
                    label="📥 Baixar Excel Geral da Pré-Roteirização",
                    data=excel_buffer,
                    file_name="pre_roterizacao_entregas.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_excel_pre_rota"
                )


            st.session_state['_pre_roterizacao_df_check'] = df_visivel
            df_to_check = st.session_state['_pre_roterizacao_df_check']
                
            #st.write(f"DEBUG: [pagina_pre_roterizacao] df_visivel tem {len(df_visivel)} linhas antes das verificações empty. df_visivel.empty: {df_visivel.empty}") # <--- E AQUI

        except Exception as e:
            st.error(f"Erro ao consultar as tabelas do Supabase: {e}")
            return

        if df_visivel.empty:
            st.info("Nenhuma entrega disponível.")
            #st.write("DEBUG: [pagina_pre_roterizacao] df_visivel está vazio. Exibindo mensagem e retornando.")
            return

        

        if df_visivel.empty:
            st.info("Nenhuma entrega disponível para pré-roterização após filtragem.")
            return

    # ======= NOVAS MÉTRICAS SEPARADAS: EXISTENTES vs DIRETORIA =======
    col_esq_1, col_esq_2, col_esq_3, col_esq_4, spacer, col_dir_1, col_dir_2, col_dir_3 = st.columns([1, 1, 1, 1, 0.3, 1, 1, 1])

# 🔹 Esquerda: métricas apenas das entregas ainda visíveis para pré-roterização
    with col_esq_1:
        st.metric("📦 Entregas Pendentes", len(df_visivel))
    with col_esq_2:
        st.metric("🛣️ Rotas Pendentes", df_visivel["Rota"].nunique() if "Rota" in df_visivel.columns else 0)
    with col_esq_3:
        st.metric("⚖️ Peso Real Total", formatar_brasileiro(df_visivel["Peso Real em Kg"].sum()))
    with col_esq_4:
        st.metric("📏 Peso Calculado Total", formatar_brasileiro(df_visivel["Peso Calculado em Kg"].sum()))

    # 🔹 Direita: métricas do que veio da diretoria
    qtde_aprovadas = len(df_aprovadas_diretoria)
    peso_real_aprovado = df_aprovadas_diretoria["Peso Real em Kg"].sum() if "Peso Real em Kg" in df_aprovadas_diretoria else 0
    peso_calc_aprovado = df_aprovadas_diretoria["Peso Calculado em Kg"].sum() if "Peso Calculado em Kg" in df_aprovadas_diretoria else 0

    with col_dir_1:
        st.metric("✅ Entregas da Diretoria", qtde_aprovadas)
    with col_dir_2:
        st.metric("✅ Peso Real", formatar_brasileiro(peso_real_aprovado))
    with col_dir_3:
        st.metric("✅ Peso Calculado", formatar_brasileiro(peso_calc_aprovado))



    def badge(label):
        return f"<span style='background:#eef2f7;border-radius:12px;padding:6px 12px;margin:4px;color:inherit;display:inline-block;'>{label}</span>"

    colunas_exibir = [
    "Serie_Numero_CTRC",  "Cliente Pagador", "Cliente Destinatario", "Cidade de Entrega",
    "Previsao de Entrega","Entrega Programada","Peso Real em Kg", "Status","Bairro do Destinatario", 
    "Numero da Nota Fiscal", "Peso Calculado em Kg", "Valor do Frete",
    "Rota", "Regiao", "Data de Emissao", "Chave CT-e",
    "Particularidade", "Codigo da Ultima Ocorrencia", "Cubagem em m³", "Quantidade de Volumes"
]

    linha_destacar = JsCode("""
    function(params) {
        const status = params.data['Status'];
        const entrega = params.data['Entrega Programada'];
        const particularidade = params.data['Particularidade'];

        // Verifica se a entrega está vazia ou contém apenas espaços (para compatibilidade com strings vazias)
        const isEntregaEmpty = !entrega || (typeof entrega === 'string' && entrega.trim() === '');

        if (status === 'AGENDAR' && isEntregaEmpty) {
            return { 'background-color': '#ffff00', 'color': '#333' }; // Amarelo puro para "AGENDAR" sem data
        }

        if (particularidade && typeof particularidade === 'string' && particularidade.trim() !== "") {
            return { 'background-color': '#bc8f8f', 'color': '#fff' }; // Rosado escuro para "Particularidade"
        }

        return null;
    }
""")


    if "GrupoDeExibicao" not in df_visivel.columns:
        df_visivel["GrupoDeExibicao"] = None

    df_visivel["Rota_Grupo"] = df_visivel["GrupoDeExibicao"].fillna(df_visivel["Rota"])

    for rota_visual in sorted(df_visivel["Rota_Grupo"].dropna().unique()):
        df_rota = df_visivel[df_visivel["Rota_Grupo"] == rota_visual].copy()
        
        if df_rota.empty:
            continue

        # --- CORREÇÃO AQUI: Calcular a rota predominante ---
        # A rota predominante é a 'Rota' original que mais aparece no grupo atual (df_rota)
        rota_predominante = "NÃO DEFINIDA" # Valor padrão
        if 'Rota' in df_rota.columns and not df_rota['Rota'].empty:
            rotas_validas = df_rota['Rota'].dropna()
            if not rotas_validas.empty:
                rota_predominante = rotas_validas.value_counts().idxmax()
            else:
                # Se não há rotas válidas, mas há um GrupoDeExibicao, pode ser usado
                if rota_visual and rota_visual != rota_predominante: # Evita duplicar "NÃO DEFINIDA"
                    rota_predominante = rota_visual
        # --- FIM DA CORREÇÃO ---

        # Selecione as Regiões associadas à Rota
        regioes = df_rota["Regiao"].dropna().unique()
        regiao_display = " / ".join(regioes) if len(regioes) > 1 else regioes[0] if regioes else "–"

        # Exibe Rota e Região(s) - Use a 'rota_predominante'
        st.markdown(f"""
        <div style="margin-top:20px;padding:10px;background:#e8f0fe;border-left:4px solid #4285f4;border-radius:6px;display:inline-block;max-width:100%;">
            <strong>Rota Predominante:</strong> {rota_predominante} &nbsp; | &nbsp; <strong>Região:</strong> {regiao_display}
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

            # === Cálculo do valor ideal de contratação com base no Valor do Frete ===
        percentuais_ideais = {
            "INTERIOR 1": 0.35,
            "INTERIOR 2": 0.45,
            "POA CAPITAL": 0.30
        }

        regiao_chave = regioes[0] if len(regioes) > 0 else None
        percentual_usado = percentuais_ideais.get(regiao_chave, None)

        if percentual_usado is not None and "Valor do Frete" in df_rota.columns:
            # Garantir tipo numérico do frete
            df_rota["Valor do Frete"] = pd.to_numeric(df_rota["Valor do Frete"], errors="coerce")
            valor_frete_total = df_rota["Valor do Frete"].sum()
            valor_ideal = valor_frete_total * percentual_usado

            st.markdown(
                f"""
                <div style='padding: 8px 12px; margin-top: 6px; background-color:#eaf4ea;
                            border-left: 4px solid #4caf50; border-radius: 4px;'>
                    💡 <strong> Custo parcial estimado</strong> para região <b>{regiao_chave}</b>
                    ({int(percentual_usado * 100)}% do frete): <b>R$ {formatar_brasileiro(valor_ideal)}</b>
                </div>
                """,
                unsafe_allow_html=True
            )
        elif percentual_usado is not None:
            st.warning(f"A coluna 'Valor do Frete' não está disponível para a Rota {rota_predominante}.")
        else:
            st.warning(f"A região '{regiao_chave}' não possui percentual definido.")


        with st.expander("🔽 Selecionar entregas", expanded=True):
        # NOVO: Checkbox "Marcar todas" dentro do expander
            checkbox_key = f"marcar_todas_pre_rota_{rota_visual}"
            if checkbox_key not in st.session_state:
                st.session_state[checkbox_key] = False
            marcar_todas = st.checkbox("Marcar todas", key=checkbox_key)

            df_formatado = apply_brazilian_date_format_for_display(
                df_rota[[col for col in colunas_exibir if col in df_rota.columns]].copy()
            )

            


            gb = GridOptionsBuilder.from_dataframe(df_formatado)
            gb.configure_default_column(minWidth=145)
            gb.configure_selection("multiple", use_checkbox=True)
            gb.configure_grid_options(paginationPageSize=12)
            gb.configure_grid_options(alwaysShowHorizontalScroll=True)
            gb.configure_grid_options(rowStyle={'font-size': '11px'})
            gb.configure_grid_options(onGridReady=GRID_RESIZE_JS_CODE) # <<< ADICIONADO AQUI
            grid_options = gb.build()
            grid_options["getRowStyle"] = linha_destacar

            grid_key = f"grid_pre_rota_{rota_visual}" 
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

            # ✅ Cálculos e exibição de métricas
            qtd_entregas = len(selecionadas)
            peso_real_total = selecionadas.get("Peso Real em Kg", pd.Series(dtype=float)).sum()
            peso_calculado_total = selecionadas.get("Peso Calculado em Kg", pd.Series(dtype=float)).sum()
            valor_frete_total = selecionadas.get("Valor do Frete", pd.Series(dtype=float)).sum()

            st.markdown(
                f"""
                <div style='display: flex; gap: 24px; padding: 8px 0; font-size: 0.95rem; font-weight: 600;'>
                    <span>📦 Entregas selecionadas: {qtd_entregas}</span>
                    <span>⚖️ Peso Real: {formatar_brasileiro(peso_real_total)} kg</span>
                    <span>📏 Peso Calculado: {formatar_brasileiro(peso_calculado_total)} kg</span>
                    <span>💰 Valor do Frete: R$ {formatar_brasileiro(valor_frete_total)}</span>
                </div>
                """,
                unsafe_allow_html=True
            )

            if not selecionadas.empty:  # BOTÃO AGORA SÓ APARECE SE TIVER SELEÇÃO

                chaves_cte = selecionadas["Chave CT-e"].dropna().astype(str).str.strip().tolist()
                ctrcs_selecionados = selecionadas["Serie_Numero_CTRC"].dropna().astype(str).str.strip().tolist()



                # ➕ Botão: Criar nova carga com entregas selecionadas
                if st.button(f"🟢 Gerar Carga com entregas da Rota {rota_predominante}", key=f"btn_nova_carga_rota_{rota_visual}"):
                    try:
                        #st.write("DEBUG: Botão 'Gerar Carga' clicado.")
                        #st.write(f"DEBUG: CTRCs selecionados recebidos: {ctrcs_selecionados[:5]}...") # Mostra os primeiros 5 CTRCs
                        numero_carga = gerar_proximo_numero_carga(supabase)
                        if numero_carga:
                            adicionar_entregas_a_carga(ctrcs_selecionados, numero_carga)

                        else:
                            st.error("Erro ao gerar número de carga.")
                    except Exception as e:
                        st.error(f"Erro ao criar nova carga: {e}")

                # # 🔄 Substituto do botão: Mover entregas para outra rota existente na pré-roteirização
                rotas_disponiveis = sorted([
                    r for r in df_visivel["Rota_Grupo"].dropna().unique().tolist()
                    if r != rota_visual
                ])
                if rotas_disponiveis:
                    nova_rota = st.selectbox(
                        "🚚 Mover entregas selecionadas para outra rota:",
                        options=["Selecionar..."] + rotas_disponiveis,
                        key=f"selectbox_mover_rota_{rota_visual}"
                    )

                    if st.button(f"🔄 Mover entregas para rota '{nova_rota}'", key=f"btn_mover_rota_{rota_visual}"):
                        if nova_rota == "Selecionar...":
                            st.warning("Por favor, selecione uma rota válida.")
                        else:
                            try:
                                mover_entregas_para_outra_rota(ctrcs_selecionados, nova_rota)
                                
                                # ✅ Força recarregamento de dados
                                st.session_state["reload_pre_roterizacao"] = True

                                # ✅ Limpa as chaves dos grids para forçar redesenho
                                for key in list(st.session_state.keys()):
                                    if key.startswith("grid_pre_rota_"):
                                        st.session_state.pop(key, None)

                                # ✅ Atualiza a tela com dados novos
                                st.rerun()

                            except Exception as e:
                                st.error(f"Erro ao mover entregas: {e}")

                            st.session_state["reload_pre_roterizacao"] = True

                            # ✅ Limpa os estados de seleção dos grids (chaves começam com 'grid_pre_rota_')
                            for key in list(st.session_state.keys()):
                                if key.startswith("grid_pre_rota_"):
                                    st.session_state.pop(key, None)

                            # ✅ Força recarregamento da página com novos dados
                            st.rerun()

                else:
                    st.info("Nenhuma outra rota disponível para movimentação.")



# ==============================================================================
# FUNÇÃO: pagina_cargas_geradas()
# ==============================================================================
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
                df = pd.DataFrame(dados)  # ou carregado do Supabase

                # Aplicar o formato correto às datas
                for col_name in GLOBAL_DATE_DISPLAY_COLUMNS:
                    if col_name in df.columns:
                        df[col_name] = pd.to_datetime(df[col_name], errors='coerce', utc=True)
                        df[col_name] = df[col_name].dt.tz_localize(None)

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

            # ✅ FORMATAÇÃO DAS DATAS COMO NA PÁGINA DA DIRETORIA
            for col_name in ["Previsao de Entrega", "Entrega Programada"]:
                if col_name in df_display.columns:
                    df_display[col_name] = df_display[col_name].apply(
                        lambda x: x.strftime("%d-%m-%Y") if pd.notna(x) else ""
                    )
            df_display = df_display.replace([np.nan, None], "")

            if "valor_contratacao" in df_display.columns:
                df_display["valor_contratacao"] = pd.to_numeric(df_display["valor_contratacao"], errors="coerce").fillna(0.0)

            # --- CORREÇÃO AQUI: LISTA FIXA DE VEÍCULOS ---
            # Preparar a lista de opções de veículos para o selectbox
            # Lista definida pelo usuário, mantendo a consistência de letras maiúsculas
            static_vehicle_types = ["CARRETA","HR", "3/4", "TOCO", "TRUCK","VAN"]
            vehicle_options_list = [""] + static_vehicle_types # Adiciona a opção vazia no início
            # --- FIM DA CORREÇÃO ---


            numeric_cols_for_formatting = [
                'Peso Real em Kg', 'Peso Calculado em Kg', 'Cubagem em m³',
                'Quantidade de Volumes', 'Valor do Frete', 'valor_contratacao'
            ]
            for col in numeric_cols_for_formatting:
                if col in df_display.columns:
                    df_display[col] = pd.to_numeric(df_display[col], errors='coerce').fillna(0)


        col1, col2, col3, col4, _ = st.columns([1, 1, 1, 1, 6])
        with col1:
            st.metric("Total de Cargas", df["numero_carga"].nunique() if "numero_carga" in df.columns else 0)
        with col2:
            st.metric("Total de Entregas", len(df))
        with col3:
            st.metric("Peso Real (kg)", formatar_brasileiro(df['Peso Real em Kg'].sum()))
        with col4:
            st.metric("Peso Calculado (kg)", formatar_brasileiro(df['Peso Calculado em Kg'].sum()))


        formatter = JsCode("""
            function(params) {
                if (!params.value && params.value !== 0) return ''; // Inclui 0 como valor válido
                return Number(params.value).toLocaleString('pt-BR', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                });
            }
        """)

        def badge(label, background_color="#eef2f7", text_color="inherit"): # Adicionado cores default para badge
            return f"<span style='background:{background_color};color:{text_color};border-radius:12px;padding:6px 12px;margin:4px;display:inline-block;'>{label}</span>"

        colunas_exibir = [
        "Serie_Numero_CTRC",  "Cliente Pagador", "Cliente Destinatario", "Cidade de Entrega",
        "Bairro do Destinatario", "Previsao de Entrega", "Numero da Nota Fiscal",  "Status",
        "Entrega Programada", "Peso Real em Kg", "Peso Calculado em Kg", "Valor do Frete",
        "Rota", "Regiao", "Data de Emissao", "Chave CT-e",
        "Particularidade", "Codigo da Ultima Ocorrencia", "Cubagem em m³", "Quantidade de Volumes"
]

        cargas_unicas = sorted(df["numero_carga"].dropna().unique())

        for carga in cargas_unicas:
            # df_carga_raw para cálculos numéricos e 'Regiao'
            df_carga_raw = df[df["numero_carga"] == carga].copy()

            if df_carga_raw.empty:
                continue
            # --- INÍCIO DO BLOCO MOVIDO / CORRIGIDO (definições de info_ antes do markdown) ---
            motorista_info = df_carga_raw["motorista"].dropna().unique()
            placa_info = df_carga_raw["placa"].dropna().unique()
            veiculo_info = df_carga_raw["veiculo"].dropna().unique()
            valor_contratacao_info = df_carga_raw["valor_contratacao"].dropna().unique()

            info_motorista = motorista_info[0] if len(motorista_info) > 0 else ""
            info_placa = placa_info[0] if len(placa_info) > 0 else ""
            info_veiculo = veiculo_info[0] if len(veiculo_info) > 0 else "-"
            info_valor_contratacao = formatar_brasileiro(valor_contratacao_info[0]) if len(valor_contratacao_info) > 0 else "0,00"

            # Determinar a Rota dominante (a mais frequente)
            rota_dominante = "NÃO INFORMADA"
            if "Rota" in df_carga_raw.columns and not df_carga_raw["Rota"].empty:
                rotas_validas = df_carga_raw["Rota"].dropna()
                if not rotas_validas.empty:
                    rota_dominante = rotas_validas.value_counts().idxmax()
            # --- FIM DO BLOCO MOVIDO / CORRIGIDO ---

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
                <strong>Carga:</strong> {carga} &nbsp; | &nbsp;
                <strong>Rota:</strong> {rota_dominante} &nbsp; | &nbsp;
                <strong>Placa:</strong> {info_placa} &nbsp; | &nbsp;
                <strong>Veículo:</strong> {info_veiculo}
            </div>
            """, unsafe_allow_html=True)


            col1, col2 = st.columns([5, 1])
            with col1:
                # Pré-calcula o HTML de cada badge individualmente para evitar problemas na f-string multi-linha
                badge_entregas = badge(f'{len(df_carga_raw)} entregas')
                badge_peso_calc = badge(f'{formatar_brasileiro(df_carga_raw["Peso Calculado em Kg"].sum())} kg calc')
                badge_peso_real = badge(f'{formatar_brasileiro(df_carga_raw["Peso Real em Kg"].sum())} kg real')
                badge_valor_frete = badge(f'Valor frete: R$ {formatar_brasileiro(total_frete_carga)}') # Use R\$ aqui se for a intenção
                badge_cubagem = badge(f'{formatar_brasileiro(df_carga_raw["Cubagem em m³"].sum())} m³')
                badge_volumes = badge(f'{int(df_carga_raw["Quantidade de Volumes"].sum())} volumes')
                badge_motorista = badge(f'Motorista: {info_motorista}')
                badge_placa = badge(f'Placa: {info_placa}')
                badge_valor_contratacao = badge(f'Valor da Contratação: R$ {info_valor_contratacao}') # Use R\$ aqui se for a intenção

                # Lógica para determinar a data de download do PDF para o badge
                pdf_downloaded_display_date = None
                if f"pdf_downloaded_{carga}" in st.session_state:
                    pdf_downloaded_display_date = st.session_state[f"pdf_downloaded_{carga}"]
                elif "pdf_downloaded_at" in df_carga_raw.columns and pd.notna(df_carga_raw["pdf_downloaded_at"].iloc[0]):
                    pdf_downloaded_display_date = formatar_data_hora_br(df_carga_raw["pdf_downloaded_at"].iloc[0])

                # Pré-renderiza o HTML do badge do PDF se houver uma data, senão uma string vazia
                pdf_badge_html_fragment = ""
                if pdf_downloaded_display_date:
                    pdf_badge_html_fragment = badge(f'PDF baixado em: {pdf_downloaded_display_date}', background_color="#6c757d", text_color="white")

                # Inclui todas as variáveis de badge na f-string principal
                st.markdown(
                    f"""
                    <div style='display: flex; flex-wrap: wrap; gap: 8px;'>
                        {badge_entregas}
                        {badge_peso_calc}
                        {badge_peso_real}
                        {badge_valor_frete}
                        {badge_cubagem}
                        {badge_volumes}
                        {badge_motorista}
                        {badge_placa}
                        {badge_valor_contratacao}
                        {pdf_badge_html_fragment}
                    </div>
                    """,
                    unsafe_allow_html=True
                )


            with col2:
                if st.button("🖨️ PDF", key=f"pdf_{carga}"):
                    try:
                        with st.spinner(f"Gerando PDF para a carga {carga}... Por favor, aguarde..."):
                            pdf_motorista = info_motorista if info_motorista != "-" else ""
                            pdf_placa = info_placa if info_placa != "-" else ""
                            pdf_veiculo = info_veiculo if info_veiculo != "-" else ""
                            pdf_valor_contratacao = valor_contratacao_info[0] if len(valor_contratacao_info) > 0 else 0.0

                            buffer_pdf = gerar_pdf_carga(
                                df_entregas=df_carga_raw,
                                carga=carga,
                                rota=rota_dominante, # Alterado para usar rota_dominante
                                motorista=pdf_motorista,
                                placa=pdf_placa,
                                veiculo=pdf_veiculo, 
                                valor_frete=total_frete_carga,
                                valor_contratacao=pdf_valor_contratacao
                            )


                            # --- INÍCIO DA ADIÇÃO: Salvar data/hora do download do PDF ---
                        data_pdf_download = datetime.utcnow().isoformat()
                        try:
                            supabase.table("cargas_geradas").update({
                                "pdf_downloaded_at": data_pdf_download
                            }).eq("numero_carga", carga).execute()
                            # Atualiza o session_state para feedback imediato no badge
                            st.session_state[f"pdf_downloaded_{carga}"] = formatar_data_hora_br(pd.to_datetime(data_pdf_download))
                            # Força recarregamento dos dados para atualizar o dataframe em memória
                            st.session_state.pop("df_cargas_cache", None)
                            st.session_state["reload_cargas_geradas"] = True # Sinaliza para recarregar a página
                        except Exception as e_db:
                            st.warning(f"⚠️ Não foi possível registrar o download do PDF no banco de dados: {e_db}")
                        # --- FIM DA ADIÇÃO ---

                        st.success(f"✅ PDF da carga {carga} gerado com sucesso!")
                        # Este botão de download aparecerá SOMENTE após o PDF ser gerado
                        st.download_button(
                            label="📥 Baixar PDF da Carga", # Rótulo mais descritivo
                            data=buffer_pdf, # Os bytes do PDF gerado
                            file_name=f"carga_{carga}.pdf", # Nome do arquivo para download
                            mime="application/pdf", # Tipo MIME do arquivo (indica que é um PDF)
                            key=f"download_pdf_final_{carga}" # Chave única para este botão
                        )

                        
                    except Exception as e:
                        # Em caso de erro na geração, exibe uma mensagem clara
                        st.error(f"❌ Erro ao gerar o PDF da carga {carga}: {e}. "
                                "Por favor, verifique a implementação da função 'gerar_pdf_carga' e os dados da carga.")

            # ==============================================================================
            # FIM DO BLOCO DO BOTÃO DE PDF MODIFICADO
            # ==============================================================================


            with st.expander("🔽 Ver entregas da carga", expanded=True):
                checkbox_key = f"marcar_todas_carga_gerada_{carga}"
                if checkbox_key not in st.session_state:
                    st.session_state[checkbox_key] = False

                marcar_todas = st.checkbox("Marcar todas", key=checkbox_key)

                with st.spinner("Carregando entregas da carga no grid..."):
                    df_formatado = df_display[df_display["numero_carga"] == carga][[col for col in colunas_exibir if col in df_display.columns]]
                    df_formatado = apply_brazilian_date_format_for_display(df_formatado) # Linha que causa o problema de datas, remover se ainda não o fez.

                    gb = GridOptionsBuilder.from_dataframe(df_formatado)
                    gb.configure_default_column(minWidth=145)
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
                                return { 'background-color': '#FFA500', 'color': '#000' }; // LARANJA FORTE
                            }
                            if (particularidade && particularidade.trim() !== "") {
                                return { 'background-color': '#FFFF00', 'color': '#000' }; // AMARELO FORTE
                            }
                            return null;
                        }
                    """))
                    gb.configure_grid_options(headerCheckboxSelection=True)
                    gb.configure_grid_options(rowSelection='multiple')
                    #gb.configure_grid_options(onGridReady=GRID_RESIZE_JS_CODE)

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
                                with st.spinner(" Retirando entregas da carga..."):
                                    # Lista de CTRCs selecionados no AgGrid (formato de exibição)
                                    ctrcs_a_remover_do_grid = [s.get("Serie_Numero_CTRC") for s in selecionadas if s.get("Serie_Numero_CTRC")]

                                    if not ctrcs_a_remover_do_grid:
                                        st.warning("Nenhuma entrega válida selecionada para remover.")
                                        return

                                    # BUSCA OS DADOS ORIGINAIS DO SUPABASE para garantir fidelidade
                                    response_original = supabase.table("cargas_geradas").select("*").in_("Serie_Numero_CTRC", ctrcs_a_remover_do_grid).execute()
                                    dados_originais = response_original.data

                                    if not dados_originais:
                                        st.warning("Não foi possível recuperar os dados originais das entregas no Supabase para os CTRCs selecionados. Nenhuma ação será realizada.")
                                        return

                                    df_para_retornar = pd.DataFrame(dados_originais)

                                    # Remove colunas específicas de "carga" que não pertencem a "pre_roterizacao"
                                    df_para_retornar = df_para_retornar.drop(columns=[
                                        "numero_carga", "Data_Hora_Gerada", "motorista", "placa", "veiculo",
                                        "valor_contratacao", "aprovador_custos_login", "data_aprovacao_custos"
                                    ], errors="ignore")

                                    # Converte datas para o formato ISO UTC para inserção no Supabase
                                    for col_name in GLOBAL_DATE_DISPLAY_COLUMNS:
                                        if col_name in df_para_retornar.columns:
                                            df_para_retornar[col_name] = df_para_retornar[col_name].apply(tratar_data_para_utc)

                                    # Substitui NaNs e outros por None para o Supabase
                                    df_para_retornar = df_para_retornar.replace([np.nan, pd.NaT, np.inf, -np.inf, ""], None)

                                    registros_para_inserir = df_para_retornar.to_dict(orient="records")

                                    # Tenta inserir em "pre_roterizacao" com tratamento de duplicidade
                                    if registros_para_inserir:
                                        try:
                                            supabase.table("pre_roterizacao").insert(registros_para_inserir).execute()
                                            st.session_state["reload_pre_roterizacao"] = True
                                        except Exception as e_insert:
                                            if "23505" in str(e_insert) and "duplicate key value violates unique constraint" in str(e_insert):
                                                key_info = registros_para_inserir[0].get('Serie_Numero_CTRC', 'Desconhecida') if registros_para_inserir else 'Desconhecida'
                                                st.error(f"❌ Erro de duplicidade ao retornar entrega {key_info} para Pré-Roterização: Já existe um registro com essa chave. Isso pode indicar uma falha de deleção anterior ou um dado inconsistente. Por favor, verifique o Supabase manualmente.")
                                            else:
                                                st.error(f"❌ Erro ao inserir entregas em Pré-Roterização: {e_insert}")
                                            return # Interrompe a execução se a inserção falhar

                                    # >> DELEÇÃO DA CARGA GERADA COM RETRY <<
                                    delete_success = False
                                    deleted_count = 0
                                    attempted_delete = bool(ctrcs_a_remover_do_grid) # Baseia-se na lista de CTRCs selecionados

                                    for tentativa in range(2): # 2 tentativas
                                        if not attempted_delete:
                                            delete_success = True
                                            break

                                        try:
                                            delete_response = supabase.table("cargas_geradas").delete().in_("Serie_Numero_CTRC", ctrcs_a_remover_do_grid).execute()

                                            if delete_response.data:
                                                deleted_count = len(delete_response.data)
                                                st.success(f"DEBUG: Deleção em 'cargas_geradas' na Tentativa {tentativa+1} bem-sucedida! {deleted_count} registros realmente deletados.")
                                                delete_success = True
                                                break
                                            elif delete_response.error:
                                                raise Exception(delete_response.error.message)
                                            else:
                                                st.warning(f"DEBUG: Deleção em 'cargas_geradas' na Tentativa {tentativa+1} retornou sem erro, mas 0 registros deletados. Possível problema de RLS ou itens não encontrados. Resposta: {delete_response}")
                                                if tentativa < 1: time.sleep(1) # Pequena pausa antes de tentar novamente
                                                continue

                                        except Exception as e_delete:
                                            st.error(f"DEBUG: Exceção inesperada durante deleção de 'cargas_geradas': {e_delete} (Tipo: {type(e_delete)})")
                                            st.warning(f"Tentativa {tentativa+1}/2: Exceção geral durante remoção de 'cargas_geradas': {e_delete}")
                                            if tentativa < 1: time.sleep(1)
                                            continue

                                    if not delete_success and attempted_delete:
                                        raise Exception(f"Falha CRÍTICA na remoção de {len(ctrcs_a_remover_do_grid)} entrega(s) de 'Cargas Geradas'. "
                                                        f"Verifique as políticas RLS ou inconsistência de dados no Supabase.")
                                    elif deleted_count > 0:
                                        st.success(f"✅ {deleted_count} entregas removidas de 'Cargas Geradas'.")
                                    elif attempted_delete and deleted_count == 0:
                                        st.warning(f"ℹ️ Deleção de 'Cargas Geradas' concluída, mas 0 entregas foram removidas. Isso pode indicar RLS ou que já haviam sido movidas.")

                                    if delete_success:
                                        # Verifica se a carga ainda possui entregas após a deleção
                                        dados_restantes_na_carga_pos_delete = supabase.table("cargas_geradas").select("Serie_Numero_CTRC").eq("numero_carga", carga).limit(1).execute().data
                                        if not dados_restantes_na_carga_pos_delete:
                                            # Aqui você poderia, por exemplo, remover um registro "cabeçalho" da carga se ele existisse em outra tabela.
                                            # No seu modelo atual, as informações da carga (motorista, placa, etc.) estão por entrega,
                                            # então não há um registro de "carga" separado para deletar aqui.
                                            pass
                                    
                                    # Limpa os caches e estados da sessão para forçar a atualização dos grids
                                    st.session_state.pop("df_cargas_cache", None)
                                    grid_key_id = f"grid_carga_gerada_{carga}"
                                    st.session_state.pop(grid_key_id, None)
                                    st.session_state.pop(checkbox_key, None) # Limpa o checkbox "Marcar todas"

                                    st.session_state["reload_cargas_geradas"] = True # Força o recarregamento da página "Cargas Geradas"
                                    
                                    # Mensagem final de sucesso (corrigida para Pré-Roterização)
                                    st.success(f"✅ {len(ctrcs_a_remover_do_grid)} entrega(s) removida(s) da carga {carga} e retornada(s) para Pré-Roterização.")
                                    st.rerun() # Força a re-renderização da aplicação

                            except Exception as e:
                                st.error(f"❌ Ocorreu um erro inesperado ao retirar entregas da carga: {e}")
                                st.warning("A operação pode ter sido interrompida. Por favor, verifique a situação das entregas nas tabelas 'Pré-Roterização' e 'Cargas Geradas'.")

                    with col_aprov:
                        valor_contratacao_key = f"valor_contratacao_{carga}"

                        st.markdown("<br>", unsafe_allow_html=True) # Separador visual

                        # --- INPUTS DE MOTORISTA, PLACA E VEÍCULO (NOVO) --- #
                        col_mot, col_placa, col_veiculo = st.columns([1.5, 1, 1.5])
                        with col_mot:
                            motorista = st.text_input("Nome do Motorista", value=info_motorista, key=f"motorista_input_{carga}")
                        with col_placa:
                            placa = st.text_input("Placa do Veículo", value=info_placa, key=f"placa_input_{carga}")
                        with col_veiculo:
                            # Encontra o índice da opção atual para pré-selecionar o selectbox
                            try:
                                # Garante que info_veiculo está em maiúsculas e sem espaços para a comparação
                                default_vehicle_index = vehicle_options_list.index(info_veiculo.upper().strip())
                            except ValueError:
                                default_vehicle_index = 0 # Default para a primeira (vazia) se não encontrado

                            veiculo_selected = st.selectbox(
                                "Tipo de Veículo",
                                options=vehicle_options_list,
                                index=default_vehicle_index,
                                key=f"veiculo_input_{carga}"
                            )

                        st.subheader(f"Valor da Contratação da Carga {carga}")

                        if valor_sugerido_contratacao > 0:
                            st.info(f"**Sugestão de Valor:** Para atingir a meta da região '{dominant_region}' ({MAX_COST_PER_REGION.get(dominant_region, 0)*100:.0f}%), o valor ideal seria de **R$ {formatar_brasileiro(valor_sugerido_contratacao)}**")
                        elif total_frete_carga > 0:
                            st.warning(f"Não foi possível calcular uma sugestão de valor de contratação para a Rota {rota_dominante} / Região {dominant_region}.")
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

                        salvar_key = f"btn_salvar_info_{carga}"
                        if st.button(f"💾 Salvar Informações", key=f"btn_salvar_{carga}", disabled=not (motorista or placa or veiculo_selected or valor_contratacao)):
                            
                            try:
                                with st.spinner("Salvando dados da carga..."):

                                    supabase.table("cargas_geradas").update({
                                        "motorista": motorista.upper().strip(),
                                        "placa": placa.upper().strip(),
                                        "veiculo": veiculo_selected.upper().strip() if veiculo_selected else None, # Salvando o veículo selecionado
                                        "valor_contratacao": valor_contratacao
                                    }).eq("numero_carga", carga).execute()

                                    # ✅ Limpa os inputs da session_state
                                    st.session_state.pop(f"motorista_input_{carga}", None)
                                    st.session_state.pop(f"placa_input_{carga}", None)
                                    st.session_state.pop(f"veiculo_input_{carga}", None) # Limpando o estado do selectbox do veículo
                                    st.session_state.pop(valor_contratacao_key, None)

                                    # ✅ Limpa cache e força recarregamento dos dados e do grid
                                    st.session_state.pop("df_cargas_cache", None)
                                    st.session_state["reload_cargas_geradas"] = True

                                    st.success("✅ Informações da carga salvas com sucesso.")
                                    st.rerun()

                            except Exception as e:
                                st.error(f"❌ Erro ao salvar dados: {e}")


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

                                        motorista_to_save = motorista.strip().upper() if isinstance(motorista, str) else ""
                                        placa_to_save = placa.strip().upper() if isinstance(placa, str) else ""
                                        veiculo_to_save = veiculo_selected.upper().strip() if veiculo_selected else None # Usando o veículo selecionado

                                        df_aprovar_custos["motorista"] = motorista_to_save
                                        df_aprovar_custos["placa"] = placa_to_save
                                        df_aprovar_custos["veiculo"] = veiculo_to_save # Incluindo o tipo de veículo
                                        df_aprovar_custos["valor_contratacao"] = valor_contratacao # Garante que o valor do input é salvo

                                        # Aplicando o bloco robusto de tratamento de datas para envio ao Supabase
                                        for col_name in GLOBAL_DATE_DISPLAY_COLUMNS:
                                            if col_name in df_aprovar_custos.columns:
                                                temp_str_series = df_aprovar_custos[col_name].astype(str).str.strip()
                                                is_empty_or_invalid_str = temp_str_series.isin(['', 'nat', 'nan'])
                                                df_aprovar_custos.loc[is_empty_or_invalid_str, col_name] = None
                                                to_parse_indices = df_aprovar_custos.loc[~is_empty_or_invalid_str, col_name].index

                                                if not to_parse_indices.empty:
                                                    current_col_values_to_parse = df_aprovar_custos.loc[to_parse_indices, col_name]
                                                    input_format_str = DATE_ONLY_DISPLAY_FORMAT_STRING if col_name in DATE_ONLY_REPARSE_COLUMNS else DATE_DISPLAY_FORMAT_STRING
                                                    parsed_dates = pd.to_datetime(
                                                        current_col_values_to_parse,
                                                        format=input_format_str,
                                                        errors='coerce'
                                                    )
                                                    localized_utc_dates = parsed_dates.apply(
                                                        lambda x: x.tz_localize(FUSO_BRASIL, ambiguous='NaT', nonexistent='NaT').tz_convert('UTC')
                                                        if pd.notna(x) else pd.NaT
                                                    )
                                                    df_aprovar_custos.loc[to_parse_indices, col_name] = localized_utc_dates.apply(
                                                        lambda x: x.isoformat(timespec='seconds').replace('+00:00', 'Z')
                                                        if pd.notna(x) else None
                                                    )

                                        df_aprovar_custos = df_aprovar_custos.replace([np.nan, pd.NaT, np.inf, -np.inf, ""], None)

                                        registros_para_custos = df_aprovar_custos.to_dict(orient="records")

                                        if registros_para_custos:
                                            supabase.table("aprovacao_custos").insert(registros_para_custos).execute()
                                            chaves_para_remover = [r.get("Serie_Numero_CTRC") for r in registros_para_custos if r.get("Serie_Numero_CTRC")]
                                            if chaves_para_remover:
                                                supabase.table("cargas_geradas").delete().in_("Serie_Numero_CTRC", chaves_para_remover).execute()
                                                # Atualiza a carga remanescente com motorista/placa/veiculo/valor_contratacao
                                                # Isso é crucial se a carga não for totalmente movida
                                                supabase.table("cargas_geradas").update({
                                                    "motorista": motorista_to_save,
                                                    "placa": placa_to_save,
                                                    "veiculo": veiculo_to_save,
                                                    "valor_contratacao": valor_contratacao
                                                }).eq("numero_carga", carga).execute()


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
        st.error(f"❌ Erro geral inesperado ao retirar entregas da carga: {e}")
        st.warning("A operação pode ter sido interrompida. Por favor, verifique a situação das entregas nas tabelas 'Rotas Confirmadas' e 'Cargas Geradas'.")

# ==============================================================================
# FUNÇÃO: pagina_aprovacao_custos() - ATUALIZADA
# ==============================================================================
def pagina_aprovacao_custos():
    st.markdown("## Aprovação de Custos")

    MAX_COST_PER_REGION = {
        'INTERIOR 1': 0.35,
        'INTERIOR 2': 0.45,
        'POA CAPITAL': 0.30
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

                if not df.empty:
                    # ✅ Formatar datas para exibição no grid como dd-mm-aaaa
                    for col in ["Previsao de Entrega", "Entrega Programada"]:
                        if col in df.columns:
                            df[col] = pd.to_datetime(df[col], errors='coerce')
                            df[col] = df[col].apply(lambda x: x.strftime('%d-%m-%Y') if pd.notnull(x) else "")

                    # ✅ Garante que 'numero_carga' seja string no cache
                    if 'numero_carga' in df.columns:
                        df['numero_carga'] = df['numero_carga'].astype(str)

                st.session_state["df_aprovacao_custos_cache"] = df
            else:
                df = st.session_state["df_aprovacao_custos_cache"]

        if df.empty:
            st.info("Nenhuma carga pendente de aprovação de custos.")
            return

        df.columns = df.columns.str.strip()

        if is_user_aprovador and not df.empty:
            if st.button("✅ Aprovar Todas as Entregas da Página"):
                try:
                    with st.spinner("🔄 Aprovando todas as entregas..."):

                        df_aprovar = df.drop(columns=["_selectedRowNodeInfo"], errors="ignore").copy()
                        df_aprovar["aprovador_custos_login"] = st.session_state.get("username", "Desconhecido")
                        df_aprovar["data_aprovacao_custos"] = data_hora_brasil_iso()

                        # Normaliza datas
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
                            chaves = [r["Serie_Numero_CTRC"] for r in registros_para_cargas_aprovadas]
                            supabase.table("aprovacao_custos").delete().in_("Serie_Numero_CTRC", chaves).execute()

                        st.success(f"✅ {len(registros_para_cargas_aprovadas)} entregas aprovadas com sucesso.")
                        st.session_state["reload_aprovacao_custos"] = True
                        st.session_state["reload_cargas_aprovadas"] = True
                        st.rerun()

                except Exception as e:
                    st.error(f"❌ Erro ao aprovar entregas: {e}")




        if 'numero_carga' in df.columns:
            df['numero_carga'] = df['numero_carga'].astype(str)

        numeric_cols_to_convert = [
            'Peso Real em Kg', 'Peso Calculado em Kg', 'Cubagem em m³',
            'Quantidade de Volumes', 'Valor do Frete', 'valor_contratacao'
        ]
        for col in numeric_cols_to_convert:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        if 'Regiao' in df.columns:
            df['Regiao'] = df['Regiao'].astype(str).str.strip().str.upper().replace('NAN', 'NÃO DEFINIDA')

        col1, col2, col3, col4, _ = st.columns([1, 1, 1, 1, 6])
        with col1:
            st.metric("Total de Cargas Pendentes", df["numero_carga"].nunique() if "numero_carga" in df.columns else 0)
        with col2:
            st.metric("Total de Entregas Pendentes", len(df))
        with col3:
            st.metric("Peso Real (kg)", formatar_brasileiro(df['Peso Real em Kg'].sum()))
        with col4:
            st.metric("Peso Calculado (kg)", formatar_brasileiro(df['Peso Calculado em Kg'].sum()))


        colunas_exibir = [
        "Serie_Numero_CTRC",  "Cliente Pagador", "Cliente Destinatario", "Cidade de Entrega",
        "Bairro do Destinatario", "Previsao de Entrega", "Numero da Nota Fiscal",  "Status",
        "Entrega Programada", "Peso Real em Kg", "Peso Calculado em Kg", "Valor do Frete",
        "Rota", "Regiao", "Data de Emissao", "Chave CT-e",
        "Particularidade", "Codigo da Ultima Ocorrencia", "Cubagem em m³", "Quantidade de Volumes"
]

        cargas_unicas = sorted(df["numero_carga"].dropna().unique())

        for carga in cargas_unicas:
            df_carga = df[df["numero_carga"] == carga].copy()
            if df_carga.empty:
                continue

            valor_contratacao_carga_existente = df_carga["valor_contratacao"].iloc[0] if "valor_contratacao" in df_carga.columns and not df_carga["valor_contratacao"].isnull().all() else 0.0
            
            # --- Cálculos de Rentabilidade e Custo por Região ---
            total_frete_carga = df_carga["Valor do Frete"].sum()

            motorista_ = df_carga["motorista"].iloc[0] if "motorista" in df_carga.columns and not df_carga["motorista"].isnull().all() else "–"
            placa_veiculo = df_carga["placa"].iloc[0] if "placa" in df_carga.columns and not df_carga["placa"].isnull().all() else "–"
            veiculo = df_carga["veiculo"].iloc[0] if "veiculo" in df_carga.columns and not df_carga["veiculo"].isnull().all() else "–"

            
            
            
            rentabilidade_percentual = 0.0
            situacao_custo_regional = "N/A"
            cor_situacao = "gray"

            if total_frete_carga > 0:
                rentabilidade_percentual = ((total_frete_carga - valor_contratacao_carga_existente) / total_frete_carga) * 100
                percentual_custo = 100 - rentabilidade_percentual
                cor_custo = "#ffc107" if percentual_custo <= 100 else "#dc3545"
                cor_texto_custo = "black" if percentual_custo <= 100 else "white"
                # Determinar a região dominante da carga
                dominant_region = 'NÃO DEFINIDA'
                if 'Regiao' in df_carga.columns and not df_carga['Regiao'].empty:
                    # Filtra 'NÃO DEFINIDA' para o cálculo da região dominante se outras regiões existirem
                    regions_to_consider = df_carga['Regiao'][df_carga['Regiao'] != 'NÃO DEFINIDA']
                    if not regions_to_consider.empty:
                        dominant_region = regions_to_consider.value_counts().idxmax()
                    elif not df_carga['Regiao'].empty: # Se todas forem 'NÃO DEFINIDA', pega a primeira
                        dominant_region = df_carga['Regiao'].iloc[0]

                # DEBUG: Verificar região
                #st.write(f"- Região Dominante: {dominant_region}")
                
                max_cost_allowed = MAX_COST_PER_REGION.get(dominant_region, None)
                
                # DEBUG: Verificar limite
                #st.write(f"- Limite da Região: {max_cost_allowed}")

                if max_cost_allowed is not None:
                    custo_receita_ratio = (valor_contratacao_carga_existente / total_frete_carga)
                    
                    # 🚀 INÍCIO DO AJUSTE 🚀
                    # Arredonda o ratio calculado para 4 casas decimais para precisão na comparação
                    custo_receita_ratio = round(custo_receita_ratio, 4)
                    # Arredonda o limite permitido para 4 casas decimais para consistência na comparação
                    max_cost_allowed = round(max_cost_allowed, 4)
                    # 🚀 FIM DO AJUSTE 🚀
                    
                    # DEBUG: Verificar cálculo
                    #st.write(f"- Ratio Calculado: {custo_receita_ratio:.4f} ({custo_receita_ratio*100:.2f}%)")
                    #st.write(f"- Limite Permitido: {max_cost_allowed:.4f} ({max_cost_allowed*100:.2f}%)")
                    #st.write(f"- Comparação: {custo_receita_ratio:.4f} <= {max_cost_allowed:.4f} = {custo_receita_ratio <= max_cost_allowed}")
                    
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
                if valor_contratacao_carga_existente > 0:
                    situacao_custo_regional = "Frete total zero, Contratação > 0"
                    cor_situacao = "#dc3545"
                else:
                    situacao_custo_regional = "Frete total zero, Contratação zero"
                    cor_situacao = "gray"


            # Obter rota predominante
            rota_dominante = "–"
            if "Rota" in df_carga.columns and not df_carga["Rota"].isnull().all():
                rota_dominante = df_carga["Rota"].value_counts().idxmax()

            # Exibir Carga + Rota
            st.markdown(f"""
            <div style="margin-top:20px;padding:10px;background:#e8f0fe;border-left:4px solid #f9ab00;border-radius:6px;display:inline-block;max-width:100%;">
                <strong>Carga:</strong> {carga} &nbsp;&nbsp;|&nbsp;&nbsp; <strong>Rota Predominante:</strong> {rota_dominante}
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
                        {badge(f'Rentabilidade: {rentabilidade_percentual:.2f}%', background_color=("#28a745" if rentabilidade_percentual >= 0 else "#dc3545"), text_color="white")}
                        {badge(f'Custo: {percentual_custo:.2f}%', background_color=cor_custo, text_color=cor_texto_custo)}
                        {badge(f'Situação Custo: {situacao_custo_regional}', background_color=cor_situacao, text_color='white')}
                        {badge(f'Motorista: {motorista_}')}
                        {badge(f'Placa: {placa_veiculo}')}
                        {badge(f'Veículo: {veiculo}')}
                        {badge(f'Valor contratação: R$ {formatar_brasileiro(valor_contratacao_carga_existente)}')}

                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
            with st.expander("🔽 Ver entregas da carga para Aprovação de Custos", expanded=True):
                

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
                    gb.configure_default_column(minWidth=145)
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
                    fit_columns_on_grid_load=True,
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

                # Remove a necessidade de checkbox "marcar todas" e considera todas automaticamente selecionadas
                selecionadas = df_formatado[df_formatado["Serie_Numero_CTRC"].notna()].copy().to_dict(orient="records")

                if selecionadas:
                    st.markdown(f"**📦 Entregas selecionadas:** {len(selecionadas)}")
                    # --- REMOVIDO: CAMPO DE ENTRADA E SUGESTÃO ---
                    # Não há campo para preencher valor de contratação nem mostrar sugestão nesta página.

            col_aprovar, col_rejeitar = st.columns(2)
            with col_aprovar:
                if st.button(
                    f"✅ Aprovar Carga {carga}",
                    key=f"aprovar_carga_{carga}",
                    disabled=not is_user_aprovador
                ):
                    try:
                        with st.spinner("✅ Aprovando entregas e movendo para Cargas Aprovadas..."):
                            df_aprovar = pd.DataFrame(selecionadas)

                            df_aprovar = df_aprovar.drop(columns=["_selectedRowNodeInfo"], errors="ignore")
                            
                            df_aprovar["numero_carga"] = carga
                            df_aprovar["valor_contratacao"] = valor_contratacao_carga_existente # Usa o valor existente da carga

                            df_aprovar["motorista"] = motorista_ # CORREÇÃO AQUI
                            df_aprovar["placa"] = placa_veiculo  # CORREÇÃO AQUI
                            df_aprovar["veiculo"] = veiculo
                            
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
                            #st.session_state.pop(checkbox_key, None)

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
                            
                            #df_rejeitar["Status"] = "AGENDAR" 
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
                            #st.session_state.pop(checkbox_key, None)

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
        return
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

                for col in ['Entrega Programada', 'Previsao de Entrega']:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col], errors='coerce')  # Deixe o pandas detectar o formato
                        df[col] = df[col].apply(lambda x: x.strftime('%d-%m-%Y') if pd.notna(x) else '')


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


        col1, col2, col3, col4, _ = st.columns([1, 1, 1, 1, 6])
        with col1:
            st.metric("Total de Cargas Aprovadas", df["numero_carga"].nunique() if "numero_carga" in df.columns else 0)
        with col2:
            st.metric("Total de Entregas Aprovadas", len(df))
        with col3: # NOVO: Peso Real
            st.metric("Peso Real (kg)", formatar_brasileiro(df['Peso Real em Kg'].sum()))
        with col4: # NOVO: Peso Calculado
            st.metric("Peso Calculado (kg)", formatar_brasileiro(df['Peso Calculado em Kg'].sum()))

        # --- Definição dos Custos Máximos por Região ---
        MAX_COST_PER_REGION = {
            'INTERIOR 1': 0.35,  # 35%
            'INTERIOR 2': 0.45,  # 45%
            'POA CAPITAL': 0.30   # 30%
        }

        colunas_exibir = [
        "Serie_Numero_CTRC",  "Cliente Pagador", "Cliente Destinatario", "Cidade de Entrega",
        "Bairro do Destinatario", "Previsao de Entrega", "Numero da Nota Fiscal",  "Status",
        "Entrega Programada", "Peso Real em Kg", "Peso Calculado em Kg", "Valor do Frete",
        "Rota", "Regiao", "Data de Emissao", "Chave CT-e",
        "Particularidade", "Codigo da Ultima Ocorrencia", "Cubagem em m³", "Quantidade de Volumes",
        "valor_contratacao", "numero_carga", "motorista", "placa",
        "veiculo", "aprovador_custos_login", "data_aprovacao_custos"
]

        cargas_unicas = sorted(df["numero_carga"].dropna().unique())

        for carga in cargas_unicas:
            df_carga = df[df["numero_carga"] == carga].copy()
            if df_carga.empty:
                continue

            valor_contratacao_carga = df_carga["valor_contratacao"].iloc[0] if "valor_contratacao" in df_carga.columns and not df_carga["valor_contratacao"].isnull().all() else 0.0
            motorista_carga = df_carga["motorista"].iloc[0] if "motorista" in df_carga.columns and not df_carga["motorista"].isnull().all() else 'Não Informado'
            placa_carga = df_carga["placa"].iloc[0] if "placa" in df_carga.columns and not df_carga["placa"].isnull().all() else 'Não Informada'
            # NOVO: Adicione esta linha para ler o tipo de veículo
            veiculo_carga = df_carga["veiculo"].iloc[0] if "veiculo" in df_carga.columns and not df_carga["veiculo"].isnull().all() else 'Não Informado'
            aprovador_custos_login = df_carga["aprovador_custos_login"].iloc[0] if "aprovador_custos_login" in df_carga.columns and not df_carga["aprovador_custos_login"].isnull().all() else 'Desconhecido'
            data_aprovacao_custos = df_carga["data_aprovacao_custos"].iloc[0] if "data_aprovacao_custos" in df_carga.columns and not df_carga["data_aprovacao_custos"].isnull().all() else None


            
            getcontext().prec = 6  # Define precisão suficiente

            # --- Cálculos de Rentabilidade e Custo por Região ---
            total_frete_carga = df_carga["Valor do Frete"].sum()

            rentabilidade_percentual = 0.0
            situacao_custo_regional = "N/A"
            cor_situacao = "gray"

            if total_frete_carga > 0:
                try:
                    custo = Decimal(str(valor_contratacao_carga))
                    frete = Decimal(str(total_frete_carga))
                    custo_receita_ratio = (custo / frete).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)

                    # Determinar a região dominante da carga
                    dominant_region = 'NÃO DEFINIDA'
                    if 'Regiao' in df_carga.columns and not df_carga['Regiao'].empty:
                        regions_to_consider = df_carga['Regiao'][df_carga['Regiao'] != 'NÃO DEFINIDA']
                        if not regions_to_consider.empty:
                            dominant_region = regions_to_consider.value_counts().idxmax()
                        elif not df_carga['Regiao'].empty:
                            dominant_region = df_carga['Regiao'].iloc[0]

                    max_cost_allowed = Decimal(str(MAX_COST_PER_REGION.get(dominant_region, 0)))

                    if custo_receita_ratio <= max_cost_allowed:
                        situacao_custo_regional = f"Dentro do Limite ({(max_cost_allowed * 100):.0f}%)"
                        cor_situacao = "#28a745"  # Verde
                    else:
                        situacao_custo_regional = f"Acima do Limite ({(max_cost_allowed * 100):.0f}%)"
                        cor_situacao = "#dc3545"  # Vermelho

                    rentabilidade_percentual = ((frete - custo) / frete * 100).quantize(Decimal('0.01'))
                
                except Exception as e:
                    situacao_custo_regional = f"Erro no cálculo: {e}"
                    cor_situacao = "gray"
                    rentabilidade_percentual = 0.0

            else:
                situacao_custo_regional = "Total do Frete zero, cálculo impossível."
                cor_situacao = "gray"
                rentabilidade_percentual = 0.0

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
                        {badge(f'Veículo: {veiculo_carga}')}
                        {badge(f'Rentabilidade: {rentabilidade_percentual:.2f}%')}
                        {badge(f'Situação Custo: {situacao_custo_regional}', background_color=cor_situacao, text_color='white')}
                        {badge(f'Aprovado por: {aprovador_custos_login}')}
                        {badge(f'Em: {formatar_data_hora_br(data_aprovacao_custos)}')}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                # 
            with col2_placeholder:
                if st.button("🖨️ PDF", key=f"pdf_{carga}"):
                    try:
                        with st.spinner(f"Gerando PDF para a carga {carga}... Por favor, aguarde..."):
                            pdf_motorista = motorista_carga if motorista_carga != "-" else ""
                            pdf_placa = placa_carga if placa_carga != "-" else ""
                            pdf_veiculo = veiculo_carga if veiculo_carga != "-" else ""
                            pdf_valor_contratacao = valor_contratacao_carga

                            # Define rota dominante da carga (igual ao usado no cálculo de custo regional)
                            rota_dominante = df_carga['Rota'].mode()[0] if 'Rota' in df_carga.columns and not df_carga['Rota'].isnull().all() else 'NÃO DEFINIDA'

                            buffer_pdf = gerar_pdf_carga(
                                df_entregas=df_carga.copy(),
                                carga=carga,
                                rota=rota_dominante,
                                motorista=pdf_motorista,
                                placa=pdf_placa,
                                veiculo=pdf_veiculo,
                                valor_frete=total_frete_carga,
                                valor_contratacao=pdf_valor_contratacao
                            )

                        st.success(f"✅ PDF da carga {carga} gerado com sucesso!")
                        st.download_button(
                            label="📥 Baixar PDF da Carga",
                            data=buffer_pdf,
                            file_name=f"carga_{carga}.pdf",
                            mime="application/pdf",
                            key=f"download_pdf_final_{carga}"
                        )
                    except Exception as e:
                        st.error(f"❌ Erro ao gerar o PDF da carga {carga}: {e}")





                # --- CAMPOS PARA MOTORISTA E PLACA PARA EDIÇÃO E BOTÃO ÚNICO DE SALVAR E FECHAR ---
                
            with st.expander("🔽 Ver entregas da carga aprovada", expanded=True):
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
                    selecionadas = df_formatado[df_formatado["Serie_Numero_CTRC"].notna()].copy().to_dict(orient="records")

                    gb = GridOptionsBuilder.from_dataframe(df_formatado)
                    gb.configure_default_column(minWidth=145)
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
                        selected_rows=df_formatado.to_dict("records"),
                        fit_columns_on_grid_load=True,
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

                            # Botão para Retornar à Aprovação de Custos
                # --- NOVO BLOCO ---
                col_fechar, col_retornar = st.columns([1,1])

                with col_fechar:
                    if st.button(
                        f"✅ Salvar e Fechar Carga {carga}",
                        key=f"salvar_fechar_carga_{carga}"
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
                            df_to_move["motorista"] = motorista_carga  # Usa valor já carregado da carga
                            df_to_move["placa"] = placa_carga # Já está em UPPER()
                            df_to_move["veiculo"] = veiculo_carga # <--- ADICIONADO PARA VEICULO
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

                with col_retornar: # <<< ESTE É O NOVO BOTÃO E LÓGICA
                    if st.button(
                        f"↩️ Retornar à Aprovação de Custos",
                        key=f"retornar_aprov_custos_{carga}"
                    ):
                        try:
                            with st.spinner(f"Retornando carga {carga} para aprovação de custos..."):
                                # 1. Obter todas as entregas desta carga de 'cargas_aprovadas'
                                response_fetch = supabase.table("cargas_aprovadas").select("*").eq("numero_carga", carga).execute()
                                data_to_move = response_fetch.data

                                if not data_to_move:
                                    st.warning(f"Nenhuma entrega encontrada para a carga {carga} em Cargas Aprovadas para retornar.")
                                    st.rerun()
                                    return

                                df_to_move = pd.DataFrame(data_to_move)

                                # 2. Resetar campos de auditoria de aprovação de custos
                                # As informações de motorista, placa, veículo e valor_contratacao são MANTIDAS
                                df_to_move["aprovador_custos_login"] = None
                                df_to_move["data_aprovacao_custos"] = None
                                # Garante que 'situacao' e 'fechador_carga_login' (se por algum erro existirem) não sejam levados
                                df_to_move = df_to_move.drop(columns=["situacao", "fechador_carga_login", "data_fechamento"], errors="ignore")

                                # 3. Preparar dados para inserção em 'aprovacao_custos'
                                # Reutiliza a lógica de tratamento de datas para Supabase (ISO UTC)
                                date_cols_for_supabase = [
                                    "Previsao de Entrega", "Entrega Programada", "Data de Emissao",
                                    "Data de Autorizacao", "Data do Cancelamento", "Data do Escaneamento",
                                    "Data da Entrega Realizada", "Data da Ultima Ocorrencia",
                                    "Data de inclusao da Ultima Ocorrencia", "Data_Hora_Gerada"
                                ]
                                for col_name in date_cols_for_supabase:
                                    if col_name in df_to_move.columns:
                                        df_to_move[col_name] = pd.to_datetime(df_to_move[col_name], errors='coerce')
                                        df_to_move[col_name] = df_to_move[col_name].apply(tratar_data_para_utc)
                                
                                df_to_move = df_to_move.replace([np.nan, pd.NaT, "", np.inf, -np.inf], None)

                                records_to_insert = df_to_move.to_dict(orient="records")

                                # 4. Inserir em 'aprovacao_custos'
                                if records_to_insert:
                                    supabase.table("aprovacao_custos").insert(records_to_insert).execute()
                                    st.success(f"Carga {carga} retornada para Aprovação de Custos com sucesso!")
                                else:
                                    st.warning(f"Não há registros válidos para mover para Aprovação de Custos para a carga {carga}.")
                                    st.rerun()
                                    return

                                # 5. Deletar da 'cargas_aprovadas'
                                supabase.table("cargas_aprovadas").delete().eq("numero_carga", carga).execute()
                                
                                # Forçar recarregamento das páginas afetadas
                                st.session_state["reload_cargas_aprovadas"] = True
                                st.session_state["reload_aprovacao_custos"] = True
                                
                                st.rerun()

                        except Exception as e:
                            st.error(f"Erro ao retornar carga {carga} para aprovação de custos: {e}")
                # --- FIM DO NOVO BLOCO ---

    except Exception as e: # <--- ADICIONE ESTE BLOCO (se ele ainda não estiver lá)
            st.error("Erro ao carregar cargas aprovadas:")
            st.exception(e)
# ==============================================================================
# Função pagina_cargas_fechadas() - com os ajustes aplicados
# ==============================================================================

def pagina_cargas_fechadas():
    st.markdown("## Cargas Encerradas")

    try:
        with st.spinner("🔄 Carregando dados para cargas fechadas..."):
            recarregar = st.session_state.pop("reload_cargas_fechadas", False)
            if recarregar or "df_cargas_fechadas_cache" not in st.session_state:
                dados = supabase.table("cargas_fechadas").select("*").execute().data
                df = pd.DataFrame(dados)

                # --- Converte colunas relevantes para datetime UTC (sem format forçado) ---
                for col_name in GLOBAL_DATE_DISPLAY_COLUMNS:
                    if col_name in df.columns:
                        df[col_name] = pd.to_datetime(df[col_name], errors='coerce', utc=True)

                # --- Formata Entrega Programada e Previsao de Entrega para dd-mm-aaaa ---
                for col in ['Entrega Programada', 'Previsao de Entrega']:
                    if col in df.columns:
                        df[col] = df[col].dt.tz_localize(None).dt.strftime('%d-%m-%Y')


                # --- End ---
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
        col1, col2, col_download = st.columns([1, 1, 8])
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
        "Serie_Numero_CTRC",  "Cliente Pagador", "Cliente Destinatario", "Cidade de Entrega",
        "Bairro do Destinatario", "Previsao de Entrega", "Numero da Nota Fiscal",  "Status",
        "Entrega Programada", "Peso Real em Kg", "Peso Calculado em Kg", "Valor do Frete",
        "Rota", "Regiao", "Data de Emissao", "Chave CT-e",
        "Particularidade", "Codigo da Ultima Ocorrencia", "Cubagem em m³", "Quantidade de Volumes",
        "valor_contratacao", "numero_carga", "motorista", "placa",
        "data_fechamento", "situacao", "aprovador_custos_login", "data_aprovacao_custos",
        "fechador_carga_login"
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
                csv_downloaded_display_date = None
                if f"csv_downloaded_{carga}" in st.session_state:
                    csv_downloaded_display_date = st.session_state[f"csv_downloaded_{carga}"]
                elif "csv_downloaded_at" in df_carga.columns and pd.notna(df_carga["csv_downloaded_at"].iloc[0]):
                    csv_downloaded_display_date = formatar_data_hora_br(df_carga["csv_downloaded_at"].iloc[0])

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
                        {badge(f'Situação Custo: {situacao_custo_regional}', background_color=cor_situacao, text_color='white')}
                        {badge(f'Aprovado por: {aprovador_custos_login}')}
                        {badge(f'Em: {formatar_data_hora_br(data_aprovacao_custos)}')}
                        {badge(f'Fechado por: {fechador_carga_login}')}
                        {badge(f'Fechada em: {formatar_data_hora_br(data_fechamento_carga)}') if data_fechamento_carga else ''}
                        {badge(f'Situação: {situacao_carga}')}
                        {badge(f'CSV baixado em: {csv_downloaded_display_date}', background_color="#6c757d", text_color="white") if csv_downloaded_display_date else ""}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
            with col2_placeholder:
                col_pdf, col_excel = st.columns([1, 1])
                with col_pdf:
                    pdf_motorista = motorista_carga if motorista_carga and motorista_carga != "-" else ""
                    pdf_placa = placa_carga if placa_carga and placa_carga != "-" else ""
                    pdf_veiculo = df_carga["veiculo"].iloc[0] if "veiculo" in df_carga.columns and not df_carga["veiculo"].isnull().all() else ""
                    pdf_valor_contratacao = valor_contratacao_carga

                    rota_dominante = (
                        df_carga['Rota'].mode()[0]
                        if 'Rota' in df_carga.columns and not df_carga['Rota'].isnull().all()
                        else 'NÃO DEFINIDA'
                    )

                    try:
                        buffer_pdf = gerar_pdf_carga(
                            df_entregas=df_carga.copy(),
                            carga=carga,
                            rota=rota_dominante,
                            motorista=pdf_motorista,
                            placa=pdf_placa,
                            veiculo=pdf_veiculo,
                            valor_frete=total_frete_carga,
                            valor_contratacao=pdf_valor_contratacao
                        )

                        st.download_button(
                            label="🖨️ PDF",
                            data=buffer_pdf,
                            file_name=f"carga_encerrada_{carga}.pdf",
                            mime="application/pdf",
                            key=f"pdf_fechada_{carga}"
                        )
                    except Exception as e:
                        st.error(f"❌ Erro ao gerar o PDF da carga encerrada {carga}: {e}")


                with col_excel:
                    try:
                        import io
                        output = io.StringIO()

                        # Remove timezone das datas
                        for col in df_carga.select_dtypes(include=['datetimetz']).columns:
                            df_carga[col] = df_carga[col].dt.tz_localize(None)

                        colunas_chaves = ["Chave CT-e", "Serie_Numero_CTRC"]
                        colunas_existentes = [col for col in colunas_chaves if col in df_carga.columns]

                        if not colunas_existentes:
                            st.warning(f"❌ A carga {carga} não possui colunas necessárias para exportar.")
                            return

                        df_chaves = df_carga[colunas_existentes].dropna(how="all").copy().reset_index(drop=True)

                        if df_chaves.empty:
                            st.warning(f"❌ A carga {carga} não possui dados válidos de chaves para exportar.")
                            return

                        # Limpa os dados (string com trim)
                        for col in df_chaves.columns:
                            df_chaves[col] = df_chaves[col].astype(str).str.strip()

                        # Formata colunas com números longos para manter integridade no Excel
                        if "Chave CT-e" in df_chaves.columns:
                            df_chaves["Chave CT-e"] = df_chaves["Chave CT-e"].apply(lambda x: f'="{x}"')

                        # Escreve CSV com BOM e separador ";"
                        df_chaves.to_csv(output, index=False, encoding='utf-8-sig', sep=';')
                        csv_data = output.getvalue()

                        # Botão de ação para salvar o estado
                        if st.button(f"📥 Gerar CSV da Carga {carga}", key=f"btn_csv_{carga}"):
                            data_csv_download = datetime.utcnow().isoformat()

                            try:
                                # Salva no banco Supabase
                                supabase.table("cargas_fechadas").update({
                                    "csv_downloaded_at": data_csv_download
                                }).eq("numero_carga", carga).execute()

                                # Atualiza o badge local com a nova data
                                st.session_state[f"csv_downloaded_{carga}"] = formatar_data_hora_br(pd.to_datetime(data_csv_download))

                                # Limpa cache local para forçar recarregamento (opcional)
                                st.session_state.pop("df_cargas_fechadas_cache", None)

                                st.success(f"CSV baixado e registrado com sucesso para a carga {carga}.")
                            except Exception as e:
                                st.error(f"❌ Erro ao salvar csv_downloaded_at no banco: {e}")



                        # Se o estado estiver salvo, mostra o botão de download
                        if f"csv_downloaded_{carga}" in st.session_state:
                            st.download_button(
                                label="⬇️ Clique para baixar o CSV",
                                data=csv_data,
                                file_name=f"carga_encerrada_{carga}_chaves.csv",
                                mime="text/csv",
                                key=f"download_csv_chaves_carga_{carga}"
                            )

                            badge_data = badge(f"CSV baixado em: {st.session_state[f'csv_downloaded_{carga}']}")

                    except Exception as e:
                        st.error(f"❌ Erro ao gerar CSV da carga {carga}: {e}")



            with st.expander("🔽 Ver entregas da carga fechada", expanded=True):


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
                    gb.configure_default_column(minWidth=145)
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
                    fit_columns_on_grid_load=True,
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
                        df_csv[col_date] = df_csv[col_date].apply(
                            # Usamos format='%d-%m-%Y' para strings conhecidas neste formato.
                            # Se x não for string, pd.to_datetime o trata como um objeto datetime.
                            lambda x: pd.to_datetime(x, format="%d-%m-%Y", errors='coerce').strftime("%d-%m-%Y %H:%M:%S") if isinstance(x, str) else (x.strftime("%d-%m-%Y %H:%M:%S") if pd.notna(x) else "")
                        )


                csv_content = df_csv.to_csv(index=False, sep=';', encoding='utf-8-sig')
                
                # Apenas as colunas solicitadas para o CSV
                colunas_para_csv = ["Chave CT-e", "Serie_Numero_CTRC"]
                df_csv = df_carga[[col for col in colunas_para_csv if col in df_carga.columns]].copy()

                # Remove espaços extras
                for col in df_csv.columns:
                    df_csv[col] = df_csv[col].astype(str).str.strip()

                # Garante que a Chave CT-e tenha os 44 dígitos completos no Excel
                if "Chave CT-e" in df_csv.columns:
                    df_csv["Chave CT-e"] = df_csv["Chave CT-e"].apply(lambda x: f"'{x}")

                # Gera CSV em UTF-8 sem BOM
                csv_content = df_csv.to_csv(index=False, sep=';', encoding='utf-8')

                # --- Botão Geral de Download CSV para todas as cargas filtradas ---
        st.markdown("### 📥 Download Geral de Chaves das Cargas Fechadas no Período")

        try:
            colunas_para_csv = ["Chave CT-e", "Serie_Numero_CTRC"]
            df_csv_geral = df_filtrado[[col for col in colunas_para_csv if col in df_filtrado.columns]].copy()

            # Remove espaços extras
            for col in df_csv_geral.columns:
                df_csv_geral[col] = df_csv_geral[col].astype(str).str.strip()

            # Garante que a Chave CT-e tenha os 44 dígitos completos no Excel
            if "Chave CT-e" in df_csv_geral.columns:
                df_csv_geral["Chave CT-e"] = df_csv_geral["Chave CT-e"].apply(lambda x: f'="{x}"')

            # Gera CSV em UTF-8
            csv_content_geral = df_csv_geral.to_csv(index=False, sep=';', encoding='utf-8')

            st.download_button(
                label="⬇️ Baixar CSV Geral de Cargas Fechadas",
                data=csv_content_geral,
                file_name="cargas_fechadas_chaves.csv",
                mime="text/csv",
                key="download_csv_geral"
            )
        except Exception as e:
            st.warning("⚠️ Não foi possível gerar o CSV geral.")
            st.exception(e)

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
    abas = ["Sincronização", "Operações", "Administração e Configurações"]
    aba_selecionada = st.radio("Selecione uma aba:", abas, horizontal=True)

    if aba_selecionada == "Sincronização":
        pagina_sincronizacao()

    elif aba_selecionada == "Operações":
        sub_abas = [
            "Confirmar Produção", "Aprovação Diretoria", "Pré Roterização", 
            "Cargas Geradas", "Aprovação de Custos", "Cargas Aprovadas", "Cargas Encerradas"
        ]
        sub_aba = st.radio("Selecione a sub-aba:", sub_abas, horizontal=True)

        if sub_aba == "Confirmar Produção":
            pagina_confirmar_producao()
        elif sub_aba == "Aprovação Diretoria":
            pagina_aprovacao_diretoria()
        elif sub_aba == "Pré Roterização":
            pagina_pre_roterizacao()
        elif sub_aba == "Cargas Geradas":
            pagina_cargas_geradas()
        elif sub_aba == "Aprovação de Custos":
            pagina_aprovacao_custos()
        elif sub_aba == "Cargas Aprovadas":
            pagina_cargas_aprovadas()
        elif sub_aba == "Cargas Encerradas":
            pagina_cargas_fechadas()

    elif aba_selecionada == "Administração e Configurações":
        if st.session_state.get("is_admin", False):
            st.subheader("Gerenciamento de Usuários")
            pagina_gerenciar_usuarios()
            st.markdown("---")  # Separador visual

        st.subheader("Alterar Minha Senha")
        pagina_trocar_senha()


