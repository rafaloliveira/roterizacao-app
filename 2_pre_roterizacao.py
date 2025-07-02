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
        hoje = datetime.now().strftime("%Y%m%d")  # ex: '20250626'
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
    
##############################
# Página de sincronização
##############################
# Adicione estas inicializações no INÍCIO DO SEU SCRIPT, logo após as importações globais e antes de qualquer função,
# ou dentro da sua função principal se você tiver uma, mas fora de qualquer função que chame st.rerun() frequentemente.
# Isso garante que o estado persista entre os reruns.
if "sync_triggered" not in st.session_state:
    st.session_state.sync_triggered = False
if "uploaded_sync_file_hash" not in st.session_state: # Usar hash para detectar novo upload de mesmo nome
    st.session_state.uploaded_sync_file_hash = None
if "df_for_sync_cache" not in st.session_state: # Cache do DF lido para evitar re-leitura constante
    st.session_state.df_for_sync_cache = None


def pagina_sincronizacao():
    st.title("🔄 Sincronização de Dados com Supabase")
    
    # Inicializa o estado se não existir
    if 'sync_triggered' not in st.session_state:
        st.session_state.sync_triggered = False

    if 'uploaded_sync_file_hash' not in st.session_state:  # Usar hash para identificar mudança de arquivo
        st.session_state.uploaded_sync_file_hash = None

    if 'df_for_sync_cache' not in st.session_state:  # Cache do arquivo lido
        st.session_state.df_for_sync_cache = None

    # Carregar arquivo Excel
    st.markdown("### Passo 1: Carregar Planilha Excel")
    arquivo_excel = st.file_uploader("Selecione a planilha da fBaseroter:", type=["xlsx"], key="sync_file_uploader")

    current_file_hash = None
    if arquivo_excel:
        # Gera hash do arquivo carregado para detectar alterações/mudanças
        current_file_hash = hashlib.md5(arquivo_excel.getvalue()).hexdigest()

    if current_file_hash != st.session_state.uploaded_sync_file_hash:
        # Arquivo novo ou alterado
        st.session_state.uploaded_sync_file_hash = current_file_hash
        st.session_state.sync_triggered = False
        st.session_state.df_for_sync_cache = None  # Limpa cache de arquivo lido

    if arquivo_excel:
        try:
            # Notifica o usuário sobre o carregamento
            if st.session_state.df_for_sync_cache is None:
                # Cacheia o arquivo somente uma vez
                df_raw = pd.read_excel(arquivo_excel)
                df_raw.columns = df_raw.columns.str.strip()  # Remove espaços desnecessários
                st.session_state.df_for_sync_cache = df_raw

            st.success(f"Arquivo '{arquivo_excel.name}' carregado com sucesso!")
            st.write("Clique no botão abaixo para iniciar a sincronização.")

            # Botão para iniciar sincronização
            if st.button("🚀 Iniciar Sincronização", disabled=st.session_state.sync_triggered):
                st.session_state.sync_triggered = True
                st.warning("Sincronização em andamento. Por favor, aguarde!")
                st.rerun()  # Força o rerun para iniciar o processo

        except Exception as e:
            st.error(f"Erro ao ler o arquivo Excel: {e}")
            st.session_state.uploaded_sync_file_hash = None
            st.session_state.df_for_sync_cache = None
            st.session_state.sync_triggered = False

    elif not arquivo_excel and st.session_state.uploaded_sync_file_hash:
        # Arquivo antigo removido
        st.session_state.uploaded_sync_file_hash = None
        st.session_state.df_for_sync_cache = None
        st.session_state.sync_triggered = False
        st.info("Nenhum arquivo carregado. Faça o upload de um arquivo Excel para sincronizar.")
        return  # Sai da função se não há arquivo para processar

    else:
        # Nenhum arquivo carregado pela primeira vez
        st.info("Aguardando o upload de um arquivo Excel para iniciar a sincronização.")
        return  # Sai da função se não há arquivo carregado ainda

    # --- Sincronização (Apenas se o botão foi clicado) ---
    if st.session_state.sync_triggered:
        st.write("---")
        st.header("Sincronização em andamento...")

        # Barra de progresso
        progresso = st.progress(0)  # Inicializa a barra de 0%

        try:
            # Passo 1: Importando dados para fBaseroter
            st.info("Passo 1/4: Limpando e inserindo dados em 'fBaseroter'...")
            progresso.progress(25)  # 25% concluído
            df_to_process = st.session_state.df_for_sync_cache.copy()
            df_to_process = corrigir_tipos(df_to_process)  # Verifique se essa função está definida

            supabase.table("fBaseroter").delete().neq("Serie_Numero_CTRC", "").execute()
            inserir_em_lote("fBaseroter", df_to_process)  # Certifique-se de que inserir_em_lote está definida
            st.success("👉 Dados importados para 'fBaseroter' com sucesso!")

            # Passo 2: Limpando tabelas dependentes
            st.info("Passo 2/4: Limpando tabelas relacionadas...")
            progresso.progress(50)  # 50% concluído
            limpar_tabelas_relacionadas()  # Certifique-se de que essa função está definida
            st.success("👉 Tabelas relacionadas limpas com sucesso!")

            # Passo 3: Aplicando regras de negócio
            st.info("Passo 3/4: Aplicando regras de negócio e populando tabelas...")
            progresso.progress(75)  # 75% concluído
            aplicar_regras_e_preencher_tabelas()  # Certifique-se de que essa função está definida
            st.success("👉 Regras de negócio aplicadas com sucesso!")

            # Passo 4: Invalidando caches
            st.info("Passo 4/4: Invalidando caches para atualizar as páginas...")
            progresso.progress(100)  # 100% concluído
            st.session_state["reload_pre_roterizacao"] = True
            st.session_state.pop("df_pre_roterizacao_cache", None)
            st.session_state["reload_rotas_confirmadas"] = True
            st.session_state.pop("df_rotas_confirmadas_cache", None)
            st.success("👉 Caches invalidados para garantir a atualização das páginas!")

            # Finaliza o processo de sincronização
            st.success("✅ Sincronização concluída com sucesso!")
            st.balloons()
            st.session_state.sync_triggered = False  # Reseta o gatilho
            st.session_state.df_for_sync_cache = None

        except Exception as e:
            st.error(f"❌ Ocorreu um erro durante a sincronização: {e}")
            st.session_state.sync_triggered = False  # Para o processo em caso de erro
            st.session_state.df_for_sync_cache = None
            raise

        # Botão para nova sincronização
        st.write("---")
        if st.button("🔄 Realizar Nova Sincronização"):
            st.session_state.sync_triggered = False
            st.session_state.uploaded_sync_file_hash = None
            st.session_state.df_for_sync_cache = None
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
        "Data do Escaneamento", "Data da Entrega Realizada", "CEP de Entrega",
        "CEP do Destinatario","CEP do Remetente" 
    ]

    for col in df.columns:
        # Formatar para string só se for coluna de data e coluna existir no df
        if col in colunas_data:
            try:
                df[col] = pd.to_datetime(df[col], errors='coerce')
                df[col] = df[col].dt.strftime('%Y-%m-%d')
            except Exception:
                pass

    st.write("[DEBUG] Quantidade de NaNs por coluna (antes do applymap):", df.isna().sum())

    def limpar_valores(obj):
        if pd.isna(obj):
            return None
        return obj

    dados = df.applymap(limpar_valores).to_dict(orient="records")

    if dados:
        st.write("[DEBUG] Primeira linha do lote limpo:", dados[0])

    for i in range(0, len(dados), lote):
        sublote = dados[i:i + lote]
        for tentativa in range(tentativas):
            try:
                supabase.table(nome_tabela).insert(sublote).execute()
                st.info(f"[DEBUG] Inseridos {len(sublote)} registros na tabela '{nome_tabela}' (lote {i}–{i + len(sublote) - 1}).")
                break
            except Exception as e:
                st.warning(f"[TENTATIVA {tentativa + 1}] Erro ao inserir lote {i}–{i + len(sublote) - 1}: {e}")
                time.sleep(1)
        else:
            st.error(f"[ERRO] Falha final ao inserir lote {i}–{i + len(sublote) - 1} na tabela '{nome_tabela}'.")
        time.sleep(pausa)
def inserir_em_lote(nome_tabela, df, lote=100, tentativas=3, pausa=0.2):
    # Defina as colunas de data do jeito que você já conhece
    colunas_data = [
        "Data da Ultima Ocorrencia", "Data de inclusao da Ultima Ocorrencia",
        "Entrega Programada", "Previsao de Entrega",
        "Data de Emissao", "Data de Autorizacao", "Data do Cancelamento",
        "Data do Escaneamento", "Data da Entrega Realizada","CEP de Entrega","CEP do Destinatario",
        "'CEP do Remetente"
    ]

    for col in df.columns:
        # Formatar para string só se for coluna de data e coluna existir no df
        if col in colunas_data:
            try:
                df[col] = pd.to_datetime(df[col], errors='coerce')
                df[col] = df[col].dt.strftime('%Y-%m-%d')
            except Exception:
                pass

    st.write("[DEBUG] Quantidade de NaNs por coluna (antes do applymap):", df.isna().sum())

    def limpar_valores(obj):
        if pd.isna(obj):
            return None
        return obj

    dados = df.applymap(limpar_valores).to_dict(orient="records")

    if dados:
        st.write("[DEBUG] Primeira linha do lote limpo:", dados[0])

    for i in range(0, len(dados), lote):
        sublote = dados[i:i + lote]
        for tentativa in range(tentativas):
            try:
                supabase.table(nome_tabela).insert(sublote).execute()
                st.info(f"[DEBUG] Inseridos {len(sublote)} registros na tabela '{nome_tabela}' (lote {i}–{i + len(sublote) - 1}).")
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
        "rotas_confirmadas", "cargas_geradas", "aprovacao_custos"
    ]

    for tabela in tabelas:
        try:
            res = supabase.table(tabela).select("*").limit(1).execute()
            if res.data:
                chave = list(res.data[0].keys())[0]
                valor_exclusao = "00000000-0000-0000-0000-000000000000" if "uuid" in str(type(res.data[0][chave])).lower() else "0"

                # Executa o delete com filtro válido
                supabase.table(tabela).delete().neq(chave, valor_exclusao).execute()

                st.warning(f"[DEBUG] Dados da tabela '{tabela}' foram apagados.")
            else:
                st.info(f"[DEBUG] Tabela '{tabela}' já estava vazia.")
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
    st.subheader("🔍 Aplicando Regras de Negócio")

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

        st.text(f"[DEBUG] {len(df)} registros carregados de fBaseroter.")
#__________________________________________________________________________________________________________
        # Merge com Micro_Regiao_por_data_embarque
        micro = supabase.table("Micro_Regiao_por_data_embarque").select("*").execute().data
        if micro:
            df_micro = pd.DataFrame(micro)
            df_micro.columns = df_micro.columns.str.strip()

            # Detectar nome da coluna de data automaticamente
            col_data_micro = [col for col in df_micro.columns if 'relação' in col.lower()]
            if col_data_micro:
                data_col = col_data_micro[0]
                df_micro[data_col] = pd.to_numeric(df_micro[data_col], errors='coerce')

                # Corrigir nome da coluna de cidade
                cidade_col = 'CIDADE DESTINO'

                # Faz merge com base em Cidade de Entrega = CIDADE DESTINO
                df = df.merge(
                    df_micro[[data_col, cidade_col]],
                    how='left',
                    left_on='Cidade de Entrega',
                    right_on=cidade_col
                )

                # Calcula Data de Embarque
                df['Data de Embarque'] = df['Previsao de Entrega'] - pd.to_timedelta(df[data_col], unit='D')

                df.drop(columns=[data_col, cidade_col], inplace=True)
            else:
                st.warning("Coluna de data de relação não encontrada.")
                df['Data de Embarque'] = pd.NaT
        else:
            df['Data de Embarque'] = pd.NaT
        st.text("[DEBUG] Mescla com Micro_Regiao_por_data_embarque concluída.")
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
        st.text("[DEBUG] Mescla com Particularidades concluída.")
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
        st.text("[DEBUG] Mescla com Clientes_Entrega_Agendada concluída.")


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
        st.text("[DEBUG] Definição de rotas concluída.")

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
            'Cubagem em m³', 'Quantidade de Volumes', 'Valor do Frete', 'Rota',
            'CEP de Entrega','CEP do Destinatario','CEP do Remetente'

        ]

        inserir_em_lote("pre_roterizacao", obrigatorias[colunas_finais])
        inserir_em_lote("confirmadas_producao", confirmadas[colunas_finais])

        st.success(f"[SUCESSO] Inseridos {len(obrigatorias)} em pre_roterizacao e {len(confirmadas)} em confirmadas_producao.")

    except Exception as e:
        st.error(f"[ERRO] Regras de sincronização: {e}")



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
        "Serie_Numero_CTRC", "Rota", "Valor do Frete", "Cliente Pagador", "Chave CT-e",
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

            if not df_formatado.empty:
                gb = GridOptionsBuilder.from_dataframe(df_formatado)
                gb.configure_default_column(minWidth=150)
                gb.configure_selection("multiple", use_checkbox=True)
                gb.configure_grid_options(paginationPageSize=12)
                gb.configure_grid_options(alwaysShowHorizontalScroll=True)
                gb.configure_grid_options(rowStyle={'font-size': '11px'})
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
                            df_confirmar = selecionadas.drop(columns=["_selectedRowNodeInfo"], errors="ignore").copy()
                            df_confirmar["Rota"] = rota # Garante que a rota esteja na coluna correta
                            
                            # Converte NaT/NaN para None para compatibilidade com Supabase
                            df_confirmar = df_confirmar.replace([np.nan, np.inf, -np.inf, pd.NaT], None)
                            # Formata colunas de data/hora para string ISO se existirem
                            for col in df_confirmar.select_dtypes(include=["datetime64[ns]"]).columns:
                                if df_confirmar[col].notna().any(): # Apenas formata se houver valores não-NaT
                                    df_confirmar[col] = df_confirmar[col].dt.strftime("%Y-%m-%d %H:%M:%S")

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

    usuario = st.session_state.get("username")
    dados_usuario = supabase.table("usuarios").select("classe").eq("nome_usuario", usuario).execute().data
    if not dados_usuario or dados_usuario[0].get("classe") != "aprovador":
        st.warning("🔒 Apenas usuários com classe 'aprovador' podem acessar esta página.")
        return

    try:
        with st.spinner("🔄 Carregando entregas pendentes para aprovação..."):
            df_aprovacao = pd.DataFrame(
                supabase.table("aprovacao_diretoria").select("*").execute().data
            )

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
        "Serie_Numero_CTRC", "Rota", "Valor do Frete", "Cliente Pagador", "Chave CT-e",
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
            df_formatado = df_cliente[[col for col in colunas_exibir if col in df_cliente.columns]].copy()

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
                    if st.button(f"🚀 Aprovar entregas", key=f"btn_aprovar_{cliente}"):
                        try:
                            chaves = selecionadas["Serie_Numero_CTRC"].dropna().astype(str).str.strip().tolist()
                            df_aprovar = df_cliente[df_cliente["Serie_Numero_CTRC"].isin(chaves)].copy()

                            df_aprovar = df_aprovar.replace([np.nan, np.inf, -np.inf], None)

                            for col in df_aprovar.select_dtypes(include=['datetime64[ns]']).columns:
                                df_aprovar[col] = df_aprovar[col].dt.strftime('%Y-%m-%d %H:%M:%S')

                            registros = df_aprovar.to_dict(orient="records")
                            registros = [r for r in registros if r.get("Serie_Numero_CTRC")]

                            supabase.table("pre_roterizacao").insert(registros).execute()
                            supabase.table("aprovacao_diretoria").delete().in_("Serie_Numero_CTRC", chaves).execute()

                            # Limpa sessão e força reload
                            for key in list(st.session_state.keys()):
                                if key.startswith("grid_aprovar_") or key.startswith("sucesso_"):
                                    st.session_state.pop(key, None)
                            st.success(f"✅ {len(chaves)} entregas aprovadas e enviadas para Pré-Roteirização.")
                            st.rerun()

                        except Exception as e:
                            st.error(f"❌ Erro ao aprovar entregas: {e}")



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
        "Serie_Numero_CTRC", "Rota", "Valor do Frete", "Cliente Pagador", "Chave CT-e", "Cliente Destinatario",
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

            df_formatado = df_rota[[col for col in colunas_exibir if col in df_rota.columns]].copy()

            gb = GridOptionsBuilder.from_dataframe(df_formatado)
            gb.configure_default_column(minWidth=150)
            gb.configure_selection("multiple", use_checkbox=True)
            gb.configure_grid_options(paginationPageSize=12)
            gb.configure_grid_options(alwaysShowHorizontalScroll=True)
            gb.configure_grid_options(rowStyle={'font-size': '11px'})
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
                    try:
                        df_confirmar = selecionadas.drop(columns=["_selectedRowNodeInfo"], errors="ignore").copy()
                        df_confirmar["Rota"] = rota

                        df_confirmar = df_confirmar.replace([np.nan, np.inf, -np.inf], None)
                        for col in df_confirmar.select_dtypes(include=["datetime64[ns]"]).columns:
                            df_confirmar[col] = df_confirmar[col].dt.strftime("%Y-%m-%d %H:%M:%S")

                        registros = df_confirmar.to_dict(orient="records")
                        registros = [r for r in registros if r.get("Serie_Numero_CTRC")]

                        supabase.table("rotas_confirmadas").insert(registros).execute()
                        chaves = [r["Serie_Numero_CTRC"] for r in registros]
                        supabase.table("pre_roterizacao").delete().in_("Serie_Numero_CTRC", chaves).execute()

                        # Limpa o estado da sessão para forçar a recarga dos grids e evitar problemas de cache.
                        st.session_state["reload_pre_roterizacao"] = True
                        # AJUSTE AQUI: ADICIONA FLAG PARA RECARREGAR ROTAS CONFIRMADAS
                        st.session_state["reload_rotas_confirmadas"] = True 
                        st.session_state.pop(grid_key, None)
                        st.session_state.pop(checkbox_key, None)


                        st.success(f"✅ {len(chaves)} entregas da Rota {rota} foram confirmadas com sucesso.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro ao confirmar entregas da rota {rota}: {e}")






##########################################

# PÁGINA ROTAS CONFIRMADAS

#########################################

def pagina_rotas_confirmadas():
    st.markdown("## Rotas Confirmadas")

    # Adicionando a lógica de cache ou recarga
    with st.spinner("🔄 Carregando dados das entregas..."):
        recarregar = st.session_state.pop("reload_rotas_confirmadas", False)
        if recarregar or "df_rotas_confirmadas_cache" not in st.session_state:          
            # AQUI É O PONTO CRÍTICO DA BUSCA (Correção da redundância)
            data_from_supabase = supabase.table("rotas_confirmadas").select("*").execute().data
            df_rotas = pd.DataFrame(data_from_supabase) # Usando os dados já buscados
            st.session_state["df_rotas_confirmadas_cache"] = df_rotas
        else:
            
            df_rotas = st.session_state["df_rotas_confirmadas_cache"]
    if df_rotas.empty:
        st.info("Nenhuma Rota Confirmada.")
        return

    # Lógica para criação de nova carga avulsa (mantida inalterada para o foco no problema)
    chaves_input = ""
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
                except Exception as e:
                    st.error(f"Erro ao criar nova carga: {e}")

    if st.session_state["nova_carga_em_criacao"]:
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
                    return

                entregas_encontradas = []

                def detectar_coluna_chave(tabela):
                    dados = supabase.table(tabela).select("*").limit(1).execute().data
                    if not dados:
                        return None
                    return next((k for k in dados[0].keys() if "chave" in k.lower() and "ct" in k.lower()), None)

                chave_coluna_rotas = detectar_coluna_chave("rotas_confirmadas") or "Chave CT-e"
                chave_coluna_pre = detectar_coluna_chave("pre_roterizacao") or "Chave CT-e"

                # Buscar todos os dados uma única vez para maior controle
                dados_rotas = supabase.table("rotas_confirmadas").select("*").execute().data
                dados_pre = supabase.table("pre_roterizacao").select("*").execute().data
                
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

                        # Verificar se a chave já está em alguma carga
                        if chave in entregas_ja_em_carga:
                            st.warning(f"⚠️ A entrega com chave '{chave}' já está na carga {entregas_ja_em_carga[chave]}.")
                            continue

                        # Busca manual nas tabelas
                        dados = [d for d in dados_rotas if str(d.get(chave_coluna_rotas, "")).strip() == chave]
                        if dados:
                            origem = "rotas_confirmadas"
                            entrega = dados[0]
                            entrega.pop("id", None) # Remove 'id' que pode ser gerado pelo Supabase
                        else:
                            dados = [d for d in dados_pre if str(d.get(chave_coluna_pre, "")).strip() == chave]
                            if dados:
                                origem = "pre_roterizacao"
                                entrega = dados[0]
                                entrega.pop("id", None) # Remove 'id' que pode ser gerado pelo Supabase

                        if not entrega:
                            st.warning(f"⚠️ Chave {chave} não encontrada em nenhuma tabela ou já foi processada.")
                            continue

                        entrega["numero_carga"] = st.session_state["numero_nova_carga"]
                        entrega["Data_Hora_Gerada"] = data_hora_brasil_str() # Formato string para Supabase
                        entrega["Status"] = "Fechada" # Assume que ao virar carga, o status é "Fechada"

                        # Limpa valores que podem causar problemas na inserção (NaN, NaT, objetos complexos)
                        entrega = {k: (
                            v.isoformat() if isinstance(v, (pd.Timestamp, datetime, date)) else # Converte datas para ISO
                            None if (isinstance(v, float) and (np.isnan(v) or np.isinf(v))) or pd.isna(v) else # Float NaN/Inf ou Pandas NaT para None
                            str(v) if isinstance(v, (dict, list)) else # Converte dict/list para string (se não forem JSON válidos)
                            v
                        ) for k, v in entrega.items()}

                        # 🔒 Colunas válidas para serem inseridas em cargas_geradas
                        colunas_validas = [
                            'Serie_Numero_CTRC', 'Rota', 'Cliente Pagador', 'Chave CT-e', 'Cliente Destinatario',
                            'Cidade de Entrega', 'Bairro do Destinatario', 'Previsao de Entrega',
                            'Numero da Nota Fiscal', 'Status', 'Entrega Programada', 'Particularidade',
                            'Codigo da Ultima Ocorrencia', 'Peso Real em Kg', 'Peso Calculado em Kg',
                            'Cubagem em m³', 'Quantidade de Volumes', 'Valor do Frete',
                            'numero_carga', 'Data_Hora_Gerada'
                        ]

                        entrega_filtrada = {k: v for k, v in entrega.items() if k in colunas_validas}

                        # Tenta inserir no Supabase
                        supabase.table("cargas_geradas").insert(entrega_filtrada).execute()
                        time.sleep(0.1) # Pequena pausa para evitar sobrecarga no Supabase
                        entregas_encontradas.append(entrega)
                        chaves_inseridas_com_sucesso.append(chave)

                        # Remove da tabela de origem
                        if origem == "rotas_confirmadas":
                            supabase.table("rotas_confirmadas").delete().eq("Chave CT-e", chave).execute()
                            time.sleep(0.1)
                        elif origem == "pre_roterizacao":
                            supabase.table("pre_roterizacao").delete().eq("Chave CT-e", chave).execute() # Assume "Chave CT-e" como PK
                            time.sleep(0.1)

                    except Exception as e_inner:
                        st.warning(f"Erro ao processar chave {chave}: {e_inner}")

                if entregas_encontradas:
                    st.success(f"✅ {len(entregas_encontradas)} entrega(s) adicionada(s) à carga {st.session_state['numero_nova_carga']} com sucesso.")
                    # Limpa o estado da carga criada para voltar à visualização normal
                    st.session_state["nova_carga_em_criacao"] = False
                    st.session_state["numero_nova_carga"] = ""
                    # Força a recarga dos caches para que as tabelas reflitam as mudanças
                    st.session_state["reload_rotas_confirmadas"] = True
                    st.session_state["reload_cargas_geradas"] = True
                    # Limpa keys dos grids para forçar reconstrução se necessário
                    for key_prefix in ["grid_rotas_confirmadas_", "grid_carga_gerada_"]:
                        for key in list(st.session_state.keys()):
                            if key.startswith(key_prefix):
                                st.session_state.pop(key, None)
                    st.rerun()

                else:
                    st.warning("⚠️ Nenhuma entrega válida foi adicionada ou encontrada.")

            except Exception as e:
                st.error(f"Erro ao adicionar entregas: {e}")

    # A partir daqui, a lógica de exibição das rotas confirmadas continua
    try:
        # Reutiliza o DataFrame do cache ou recarrega para exibição
        df = st.session_state.get("df_rotas_confirmadas_cache", pd.DataFrame())
        df.columns = df.columns.str.strip()
        # st.write("DEBUG: Conteúdo de df_rotas antes da exibição:") # DEBUG
        # st.dataframe(df) # DEBUG
        # st.write(f"DEBUG: df_rotas está vazia? {df.empty}") # DEBUG

        if df.empty:
            st.info("🛈 Nenhuma Rota Confirmada.")
            # st.info("DEBUG: DataFrame df_rotas está vazio.") # DEBUG
            return

        col1, col2, _ = st.columns([1, 1, 8])
        with col1:
            st.metric("Total de Rotas", df["Rota"].nunique() if "Rota" in df.columns else 0)
        with col2:
            st.metric("Total de Entregas", len(df))

        def badge(label):
            return f"<span style='background:#eef2f7;border-radius:12px;padding:6px 12px;margin:4px;color:inherit;display:inline-block;'>{label}</span>"

        colunas_exibir = [
            "Serie_Numero_CTRC", "Rota","Valor do Frete", "Cliente Pagador", "Chave CT-e", "Cliente Destinatario",
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
                df_formatado = df_rota[[col for col in colunas_exibir if col in df_rota.columns]].copy()

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
                            st.info("DEBUG: Tentando criar nova carga com entregas selecionadas.") # DEBUG
                            df_selecionadas = pd.DataFrame(selecionadas)
                            chaves = df_selecionadas["Serie_Numero_CTRC"].dropna().astype(str).str.strip().tolist()

                            df_rota["Serie_Numero_CTRC"] = df_rota["Serie_Numero_CTRC"].astype(str).str.strip()
                            df_confirmar = df_rota[df_rota["Serie_Numero_CTRC"].isin(chaves)].copy()
                            df_confirmar = df_confirmar.replace([np.nan, np.inf, -np.inf], None)

                            for col in df_confirmar.select_dtypes(include=['datetime64[ns]']).columns:
                                df_confirmar[col] = df_confirmar[col].dt.strftime('%Y-%m-%d %H:%M:%S')

                            numero_carga = gerar_proximo_numero_carga(supabase)
                            df_confirmar["numero_carga"] = numero_carga
                            df_confirmar["Data_Hora_Gerada"] = datetime.now().isoformat()
                            df_confirmar["Status"] = "Fechada"

                            colunas_validas = [
                                'Serie_Numero_CTRC', 'Rota', 'Cliente Pagador', 'Chave CT-e', 'Cliente Destinatario',
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
                                    st.info(f"DEBUG: Tentativa {tentativa+1} - Inserção em 'cargas_geradas' bem-sucedida.") # DEBUG
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
                                st.info("DEBUG: Chaves inseridas correspondem às selecionadas. Deletando de 'rotas_confirmadas'.") # DEBUG
                                for tentativa in range(2):
                                    try:
                                        supabase.table("rotas_confirmadas").delete().in_("Serie_Numero_CTRC", chaves_inseridas).execute()
                                        st.info(f"DEBUG: Tentativa {tentativa+1} - Deleção de 'rotas_confirmadas' bem-sucedida.") # DEBUG
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


                                time.sleep(1)
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
                                st.info(f"DEBUG: Tentando adicionar à carga existente {carga_escolhida}.") # DEBUG
                                df_selecionadas = pd.DataFrame(selecionadas)
                                chaves = df_selecionadas["Serie_Numero_CTRC"].dropna().astype(str).str.strip().tolist()

                                df_rota["Serie_Numero_CTRC"] = df_rota["Serie_Numero_CTRC"].astype(str).str.strip()
                                df_confirmar = df_rota[df_rota["Serie_Numero_CTRC"].isin(chaves)].copy()
                                df_confirmar = df_confirmar.replace([np.nan, np.inf, -np.inf], None)

                                for col in df_confirmar.select_dtypes(include=['datetime64[ns]']).columns:
                                    df_confirmar[col] = df_confirmar[col].dt.strftime('%Y-%m-%d %H:%M:%S')

                                df_confirmar["numero_carga"] = carga_escolhida
                                df_confirmar["Data_Hora_Gerada"] = datetime.now().isoformat()
                                df_confirmar["Status"] = "Fechada"

                                colunas_validas = [
                                    'Serie_Numero_CTRC', 'Rota', 'Cliente Pagador', 'Chave CT-e', 'Cliente Destinatario',
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
                                st.info(f"DEBUG: Inseridos {len(dados_filtrados)} registros em 'cargas_geradas' para carga existente.") # DEBUG
                                supabase.table("rotas_confirmadas").delete().in_("Serie_Numero_CTRC", chaves).execute()
                                st.info(f"DEBUG: Removidos {len(chaves)} registros de 'rotas_confirmadas'.") # DEBUG

                                # Força recarga dos caches para que as tabelas reflitam as mudanças
                                st.session_state["reload_rotas_confirmadas"] = True
                                st.session_state["reload_cargas_geradas"] = True
                                # Limpa keys dos grids para forçar reconstrução se necessário
                                st.session_state.pop(grid_key, None)
                                st.session_state.pop(checkbox_key, None) # Limpa o estado do checkbox
                                st.session_state.pop(f"selectbox_carga_existente_{rota}", None) # Limpa o selectbox

                                st.success(f"✅ Entregas adicionadas à carga {carga_escolhida}.")
                                time.sleep(2)
                                st.rerun()

                            except Exception as e:
                                st.error(f"Erro ao adicionar à carga existente: {e}")
                else:
                    st.info("Nenhuma carga existente encontrada para seleção.")

    except Exception as e:
        st.error(f"Erro ao processar entregas confirmadas: {e}")


##########################################

# PÁGINA CARGAS GERADAS

##########################################

def pagina_cargas_geradas():
    st.markdown("## Cargas Geradas")

    try:
        with st.spinner("🔄 Carregando dados das cargas..."):
            # ✅ Recarrega os dados sempre ou sob flag
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

        with st.spinner("🔄 Processando estatísticas e estrutura da página..."):
            df.columns = df.columns.str.strip()

            col1, col2 = st.columns([1, 1])
            with col1:
                st.metric("Total de Cargas", df["numero_carga"].nunique())
            with col2:
                st.metric("Total de Entregas", len(df))

            colunas_exibir = [
                "numero_carga", "Data_Hora_Gerada", "Serie_Numero_CTRC", "Rota", "Valor do Frete", "Cliente Pagador", "Chave CT-e", "Cliente Destinatario",
                "Cidade de Entrega", "Bairro do Destinatario", "Previsao de Entrega",
                "Numero da Nota Fiscal", "Status", "Entrega Programada", "Particularidade",
                "Codigo da Ultima Ocorrencia", "Peso Real em Kg", "Peso Calculado em Kg",
                "Cubagem em m³", "Quantidade de Volumes"
            ]

            formatter = JsCode("""
                function(params) {
                    if (!params.value) return '';
                    return Number(params.value).toLocaleString('pt-BR', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                    });
                }
            """)

            def badge(label):
                return f"<span style='background:#eef2f7;border-radius:12px;padding:6px 12px;margin:4px;color:inherit;display:inline-block;'>{label}</span>"

            cargas_unicas = sorted(df["numero_carga"].dropna().unique())

        for carga in cargas_unicas:
            df_carga = df[df["numero_carga"] == carga].copy()
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
                with st.spinner("🔄 Formatando entregas da carga..."):
                    df_formatado = df_carga[[col for col in colunas_exibir if col in df_carga.columns]].copy()
                    df_formatado = df_formatado.replace([np.nan, pd.NaT], "")

                    if "Data_Hora_Gerada" in df_formatado.columns:
                        df_formatado["Data_Hora_Gerada"] = df_formatado["Data_Hora_Gerada"].apply(formatar_data_hora_br)

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

                    for col in ['Peso Real em Kg', 'Peso Calculado em Kg', 'Cubagem em m³', 'Quantidade de Volumes', 'Valor do Frete']:
                        if col in df_formatado.columns:
                            gb.configure_column(col, type=["numericColumn"], valueFormatter=formatter)

                    grid_options = gb.build()

                    grid_key_id = f"grid_carga_gerada_{carga}"
                    if grid_key_id not in st.session_state:
                        st.session_state[grid_key_id] = str(uuid.uuid4())

                    grid_key = st.session_state[grid_key_id]

                with st.spinner("🔄 Carregando entregas da carga no grid..."):
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
                                        def parse_para_iso(data_str):
                                            try:
                                                return datetime.strptime(data_str, "%d-%m-%Y %H:%M:%S").isoformat()
                                            except:
                                                return data_str

                                        df_remover["Data_Hora_Gerada"] = df_remover["Data_Hora_Gerada"].apply(parse_para_iso)

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

                                    st.session_state["reload_cargas_geradas"] = True
                                    st.success(f"{len(chaves)} entrega(s) removida(s) da carga {carga} e retornada(s) à pré-rota.")
                                    time.sleep(1)
                                    st.rerun()

                            except Exception as e:
                                st.error(f"Erro ao retirar entregas da carga: {e}")

                    with col_aprov:
                        st.button(f"💰 Enviar para Aprovação (em breve)", key=f"btn_aprov_{carga}")

    except Exception as e:
        st.error("Erro ao carregar cargas geradas:")
        st.exception(e)



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
menu_principal = [
    "Sincronização",
    "Confirmar Produção",
    "Aprovação Diretoria",
    "Pré Roterização",
    "Rotas Confirmadas",
    "Cargas Geradas"
]

menu_avancado = ["Alterar Senha"]
if st.session_state.get("is_admin", False):
    menu_avancado.append("Gerenciar Usuários")

# Linha separadora visual (não clicável)
separador = "────────────────────────"

# Menu completo com separador visual
menu_total = menu_principal + [separador] + menu_avancado

# Garante que a opção atual esteja na lista (evita erros ao abrir Gerenciar direto)
if st.session_state.get("pagina") not in menu_total:
    st.session_state.pagina = "Sincronização"

# Define índice atual com base na página ativa
index_atual = menu_total.index(st.session_state.pagina)

# Radio unificado
escolha = st.sidebar.radio("📁 Menu", menu_total, index=index_atual)

# Impede seleção do separador e força rerun ao mudar de página
if escolha == separador:
    pass  # Ignora, mantém a página atual
elif escolha != st.session_state.pagina:
    st.session_state.pagina = escolha
    st.rerun()  # 🔁 Faz a troca de página acontecer imediatamente

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
elif st.session_state.pagina == "Cargas Geradas":
    pagina_cargas_geradas()
elif st.session_state.pagina == "Alterar Senha":
    pagina_trocar_senha()
elif st.session_state.pagina == "Gerenciar Usuários":
    pagina_gerenciar_usuarios()
