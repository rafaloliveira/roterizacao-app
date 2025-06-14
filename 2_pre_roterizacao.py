#sincronização, Pré Roterização e Rotas Confirmadas funcionando

import streamlit as st

st.set_page_config(page_title="Roterização", layout="wide")



import pandas as pd
import numpy as np
import io
import time
import hashlib
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
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
import uuid
import time
import numpy as np
import pandas as pd
import streamlit as st
from st_aggrid.shared import GridUpdateMode


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





##############################
# Página de sincronização
##############################
import time

import streamlit as st
import pandas as pd
import time

def pagina_sincronizacao():
    st.title("🔄 Sincronização de Dados com Supabase")

    st.markdown("### Passo 1: Carregar Planilha Excel")
    arquivo_excel = st.file_uploader("Selecione a planilha da fBaseroter:", type=["xlsx"])
    if not arquivo_excel:
        return

    try:
        df = pd.read_excel(arquivo_excel)
        df.columns = df.columns.str.strip()

        # 🔧 Remove colunas indesejadas
        colunas_para_remover = ['Capa de Canhoto de NF','Unnamed: 70']
        colunas_existentes_para_remover = [col for col in colunas_para_remover if col in df.columns]
        if colunas_existentes_para_remover:
            df.drop(columns=colunas_existentes_para_remover, inplace=True)
            st.text(f"[DEBUG] Colunas removidas: {colunas_existentes_para_remover}")

        # 🔄 Renomeia colunas para casar com o Supabase
        renomear_colunas = {
            'Cubagem em m3': 'Cubagem em m³',
            'Serie/Numero CTRC': 'Serie_Numero_CTRC'
        }
        colunas_renomeadas = {k: v for k, v in renomear_colunas.items() if k in df.columns}
        if colunas_renomeadas:
            df.rename(columns=colunas_renomeadas, inplace=True)
            st.text(f"[DEBUG] Colunas renomeadas: {colunas_renomeadas}")

        # ✅ Corrige tipos com base na definição de colunas texto, número e data
        df = corrigir_tipos(df)

        st.success(f"Arquivo lido com sucesso: {df.shape[0]} linhas")
        st.dataframe(df.head())

    except Exception as e:
        st.error(f"Erro ao ler o arquivo: {e}")
        return

    st.markdown("### Passo 2: Importando para fBaseroter")
    try:
        supabase.table("fBaseroter").delete().neq("Serie_Numero_CTRC", "").execute()
        inserir_em_lote("fBaseroter", df)
        st.success("Dados inseridos em fBaseroter com sucesso.")
    except Exception as e:
        st.error(f"[ERRO] Inserção na fBaseroter falhou: {e}")
        return

    st.markdown("### Passo 3: Limpando tabelas dependentes")
    limpar_tabelas_relacionadas()

    st.markdown("### Passo 4: Aplicando regras de negócio")
    aplicar_regras_e_preencher_tabelas()


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
                chave = list(res.data[0].keys())[0]  # Pega primeira chave (coluna)
                supabase.table(tabela).delete().neq(chave, "").execute()
                st.warning(f"[DEBUG] Dados da tabela '{tabela}' foram apagados.")
            else:
                st.info(f"[DEBUG] Tabela '{tabela}' já estava vazia.")
        except Exception as e:
            st.error(f"[ERRO] Ao limpar tabela '{tabela}': {e}")


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


















###########################################

# PÁGINA Confirmar Produção

##########################################

def pagina_confirmar_producao():
    st.title("🚛 Confirmar Produção")

    # ✅ Dados vindos da sincronização (com fallback)
    df = st.session_state.get("dados_sincronizados")
    if df is None or df.empty:
        df = carregar_base_supabase()

    if df is None or df.empty:
        st.warning("⚠️ Nenhuma entrega encontrada na base de dados.")
        return

    colunas_necessarias = [
        "Chave CT-e", "Cliente Pagador", "Cliente Destinatario",
        "Cidade de Entrega", "Bairro do Destinatario"
    ]
    colunas_faltantes = [col for col in colunas_necessarias if col not in df.columns]
    if colunas_faltantes:
        st.error(f"❌ As seguintes colunas não existem na base carregada: {', '.join(colunas_faltantes)}")
        return

    df = df.dropna(subset=colunas_necessarias)
    if df.empty:
        st.info("Nenhuma entrega pendente para confirmação após filtragem.")
        return

    # 🔄 Recarrega a tabela confirmadas_producao apenas se necessário
    try:
        if st.session_state.get("reload_confirmadas_producao"):
            st.session_state.pop("reload_confirmadas_producao")
            df_confirmadas = pd.DataFrame(
                supabase.table("confirmadas_producao").select("*").execute().data
            )
            st.session_state["df_confirmadas_cache"] = df_confirmadas
        else:
            df_confirmadas = st.session_state.get("df_confirmadas_cache")
            if df_confirmadas is None:
                df_confirmadas = pd.DataFrame(
                    supabase.table("confirmadas_producao").select("*").execute().data
                )
                st.session_state["df_confirmadas_cache"] = df_confirmadas
    except Exception as e:
        st.error(f"Erro ao carregar entregas confirmadas: {e}")
        return

    if df_confirmadas is None or df_confirmadas.empty:
        st.info("Nenhuma entrega confirmada na produção.")
        return

    # Conversão de data e filtro de obrigatórias
    df["Previsao de Entrega"] = pd.to_datetime(df["Previsao de Entrega"], format="%d-%m-%Y", errors='coerce')
    d_mais_1 = pd.Timestamp.now().normalize() + pd.Timedelta(days=1)

    obrigatorias = df[
        (df["Previsao de Entrega"] < d_mais_1) |
        ((df["Status"] == "AGENDAR") & (df["Entrega Programada"].isnull() | (df["Entrega Programada"].str.strip() == "")))
    ].copy()

    if not df_confirmadas.empty:
        obrigatorias = obrigatorias[~obrigatorias["Serie_Numero_CTRC"].isin(df_confirmadas["Serie_Numero_CTRC"])]

    df_exibir = df_confirmadas[
        ~df_confirmadas["Serie_Numero_CTRC"].isin(obrigatorias["Serie_Numero_CTRC"])
    ].copy()





    total_clientes = df_exibir["Cliente Pagador"].nunique()
    total_entregas = len(df_exibir)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f"<div style='background:#2f2f2f;padding:8px;border-radius:8px'>"
            f"<span style='color:white;font-weight:bold;font-size:18px;'>Total de Clientes:</span>"
            f"<span style='color:white;font-size:24px;'> {total_clientes}</span></div>",
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            f"<div style='background:#2f2f2f;padding:8px;border-radius:8px'>"
            f"<span style='color:white;font-weight:bold;font-size:18px;'>Total de Entregas:</span>"
            f"<span style='color:white;font-size:24px;'> {total_entregas}</span></div>",
            unsafe_allow_html=True
        )

    colunas_exibir = [
        "Serie_Numero_CTRC", "Rota", "Valor do Frete", "Cliente Pagador", "Chave CT-e",
        "Cliente Destinatario", "Cidade de Entrega", "Bairro do Destinatario", "Previsao de Entrega",
        "Numero da Nota Fiscal", "Status", "Entrega Programada", "Particularidade", "Codigo da Ultima Ocorrencia",
        "Peso Real em Kg", "Peso Calculado em Kg", "Cubagem em m³", "Quantidade de Volumes"
    ]

    linha_destacar = JsCode("""
    function(params) {
        const status = params.data.Status;
        const entregaProg = params.data["Entrega Programada"];
        const particularidade = params.data.Particularidade;

        if (status === "AGENDAR" && (entregaProg === null || entregaProg === undefined || entregaProg.trim() === "")) {
            return { 'background-color': 'orange', 'color': 'black', 'font-weight': 'bold' };
        }
        if (particularidade !== null && particularidade !== undefined && particularidade.trim() !== "") {
            return { 'background-color': 'yellow', 'color': 'black', 'font-weight': 'bold' };
        }
        return null;
    }
    """)

    for cliente in sorted(df_exibir["Cliente Pagador"].fillna("(Vazio)").unique()):
        df_cliente = df_exibir[df_exibir["Cliente Pagador"].fillna("(Vazio)") == cliente].copy()
        if df_cliente.empty:
            continue

        total_entregas = len(df_cliente)
        peso_calculado = df_cliente['Peso Calculado em Kg'].sum()
        peso_real = df_cliente['Peso Real em Kg'].sum()
        valor_frete = df_cliente['Valor do Frete'].sum()
        cubagem = df_cliente['Cubagem em m³'].sum()
        volumes = df_cliente['Quantidade de Volumes'].sum()

        st.markdown(f"""
        <div style="background-color: #444; padding: 8px 16px; border-radius: 6px; margin-top: 20px; margin-bottom: 8px;">
            <div style="color: white; margin: 0; font-size: 15px; font-weight: bold;">🏭 Cliente: {cliente}</div>
        </div>

        <div style="display: flex; flex-wrap: wrap; gap: 20px; font-size: 16px; margin-bottom: 20px;">
            <div><strong>Quantidade de Entregas:</strong> {total_entregas}</div>
            <div><strong>Peso Calculado (kg):</strong> {formatar_brasileiro(peso_calculado)}</div>
            <div><strong>Peso Real (kg):</strong> {formatar_brasileiro(peso_real)}</div>
            <div><strong>Valor do Frete:</strong> R$ {formatar_brasileiro(valor_frete)}</div>
            <div><strong>Cubagem (m³):</strong> {formatar_brasileiro(cubagem)}</div>
            <div><strong>Volumes:</strong> {int(volumes) if pd.notnull(volumes) else 0}</div>
        </div>
        """, unsafe_allow_html=True)

        df_formatado = df_cliente[[col for col in colunas_exibir if col in df_cliente.columns]].copy()

        gb = GridOptionsBuilder.from_dataframe(df_formatado)
        gb.configure_default_column(minWidth=150)
        gb.configure_selection('multiple', use_checkbox=True)
        gb.configure_grid_options(paginationPageSize=12)
        # gb.configure_grid_options(domLayout="autoHeight")  # comentado
        gb.configure_grid_options(alwaysShowHorizontalScroll=True)
        grid_options = gb.build()
        grid_options["getRowStyle"] = linha_destacar

        grid_key_id = f"grid_confirmar_{cliente}"
        if st.session_state.get("reload_confirmadas_producao", False):
            st.session_state[grid_key_id] = str(uuid.uuid4())
        elif grid_key_id not in st.session_state:
            st.session_state[grid_key_id] = str(uuid.uuid4())

        # Calcular altura dinâmica para exibir de 10 a 15 linhas
        num_linhas_exibir = min(max(len(df_formatado), 10), 15)  # no mínimo 10, máximo 15 linhas
        altura_linha = 30  # px, ajuste se quiser
        altura_total = altura_linha * num_linhas_exibir + 40  # 40 px extra para cabeçalho

        grid_response = AgGrid(
            df_formatado,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            fit_columns_on_grid_load=False,
            height=altura_total,
            width=1500,
            allow_unsafe_jscode=True,
            key=st.session_state[grid_key_id],
            data_return_mode="AS_INPUT"
        )

        # Agora a parte das seleções:
        selecionadas = pd.DataFrame(grid_response.get("selected_rows", []))
        session_key_selecionadas = f"selecionadas_{cliente}"
        session_key_sucesso = f"sucesso_{cliente}"

        if not selecionadas.empty:
            st.session_state[session_key_selecionadas] = selecionadas
            st.session_state[session_key_sucesso] = f"{len(selecionadas)} entregas selecionadas para {cliente}."
        else:
            st.session_state.pop(session_key_selecionadas, None)
            st.session_state.pop(session_key_sucesso, None)

        if st.session_state.get(session_key_sucesso):
            st.success(st.session_state[session_key_sucesso])




            if st.button(f"✅ Confirmar entregas de {cliente}", key=f"botao_{cliente}"):
                try:
                    selecionadas = st.session_state.get(session_key_selecionadas, pd.DataFrame())
                    if selecionadas.empty:
                        st.warning("⚠️ Nenhuma entrega selecionada.")
                        return

                    chaves = selecionadas["Serie_Numero_CTRC"].dropna().astype(str).str.strip().tolist()
                    df_cliente["Serie_Numero_CTRC"] = df_cliente["Serie_Numero_CTRC"].astype(str).str.strip()
                    df_confirmar = df_cliente[df_cliente["Serie_Numero_CTRC"].isin(chaves)].copy()
                    colunas_validas = [col for col in colunas_exibir if col != "Serie_Numero_CTRC" and col in df_confirmar.columns]
                    df_confirmar = df_confirmar[["Serie_Numero_CTRC"] + colunas_validas]
                    df_confirmar = df_confirmar.replace([np.nan, np.inf, -np.inf], None)

                    for col in df_confirmar.select_dtypes(include=['datetime64[ns]']).columns:
                        df_confirmar[col] = df_confirmar[col].dt.strftime('%Y-%m-%d %H:%M:%S')

                    if df_confirmar.empty or df_confirmar["Serie_Numero_CTRC"].isnull().all():
                        st.warning("⚠️ Nenhuma entrega válida para confirmar.")
                    else:
                        dados_confirmar = df_confirmar.to_dict(orient="records")
                        dados_confirmar = [d for d in dados_confirmar if d.get("Serie_Numero_CTRC")]

                        if not dados_confirmar:
                            st.warning("⚠️ Nenhum registro com 'Serie_Numero_CTRC' válido.")
                        else:
                            resultado_insercao = supabase.table("aprovacao_diretoria").insert(dados_confirmar).execute()
                            chaves_inseridas = [
                                str(item.get("Serie_Numero_CTRC")).strip()
                                for item in resultado_insercao.data
                                if item.get("Serie_Numero_CTRC")
                            ]

                            if set(chaves_inseridas) == set(chaves):
                                try:
                                    supabase.table("confirmadas_producao").delete().in_("Serie_Numero_CTRC", chaves_inseridas).execute()

                                    # Limpa caches e seleções para forçar reload total
                                    st.session_state.pop("df_confirmadas_cache", None)
                                    st.session_state.pop("dados_sincronizados", None)
                                    for key in list(st.session_state.keys()):
                                        if key.startswith("grid_confirmar_") or key.startswith("selecionadas_") or key.startswith("sucesso_"):
                                            st.session_state.pop(key, None)

                                    # Gatilho para recarregar a tabela confirmadas_producao
                                    st.session_state["reload_confirmadas_producao"] = True

                                    st.success(f"{len(chaves_inseridas)} entregas confirmadas e movidas para Aprovação Diretoria.")

                                    st.rerun()

                                except Exception as delete_error:
                                    st.error(f"Erro ao deletar entregas: {delete_error}")
                            else:
                                st.error("❌ Nem todas as entregas foram inseridas corretamente em 'aprovacao_diretoria'. Nenhuma foi removida.")
                except Exception as e:
                    st.error(f"Erro ao processar confirmação: {e}")
















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
    with col1:
        st.markdown(
            f"<div style='background:#2f2f2f;padding:8px;border-radius:8px'>"
            f"<span style='color:white;font-weight:bold;font-size:18px;'>Total de Clientes:</span>"
            f"<span style='color:white;font-size:24px;'> {total_clientes}</span></div>",
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            f"<div style='background:#2f2f2f;padding:8px;border-radius:8px'>"
            f"<span style='color:white;font-weight:bold;font-size:18px;'>Total de Entregas:</span>"
            f"<span style='color:white;font-size:24px;'> {total_entregas}</span></div>",
            unsafe_allow_html=True
        )

    colunas_exibir = [
        "Serie_Numero_CTRC", "Rota", "Valor do Frete", "Cliente Pagador", "Chave CT-e",
        "Cliente Destinatario", "Cidade de Entrega", "Bairro do Destinatario", "Previsao de Entrega",
        "Numero da Nota Fiscal", "Status", "Entrega Programada", "Particularidade", "Codigo da Ultima Ocorrencia",
        "Peso Real em Kg", "Peso Calculado em Kg", "Cubagem em m³", "Quantidade de Volumes"
    ]

    formatter_brasileiro = JsCode("""
        function(params) {
            if (!params.value) return '';
            return Number(params.value).toLocaleString('pt-BR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
        }
    """)

    for cliente in sorted(df["Cliente Pagador"].unique()):
        df_cliente = df[df["Cliente Pagador"] == cliente].copy()

        total_entregas = len(df_cliente)
        peso_calculado = df_cliente['Peso Calculado em Kg'].sum()
        peso_real = df_cliente['Peso Real em Kg'].sum()
        valor_frete = df_cliente['Valor do Frete'].sum()
        cubagem = df_cliente['Cubagem em m³'].sum()
        volumes = df_cliente['Quantidade de Volumes'].sum()

        st.markdown(f"""
        <div style=\"background-color: #444; padding: 8px 16px; border-radius: 6px; margin-top: 20px; margin-bottom: 8px;\">
            <div style=\"color: white; margin: 0; font-size: 15px; font-weight: bold;\">📦 Cliente: {cliente}</div>
        </div>

        <div style=\"display: flex; flex-wrap: wrap; gap: 20px; font-size: 16px; margin-bottom: 20px;\">
            <div><strong>Quantidade de Entregas:</strong> {total_entregas}</div>
            <div><strong>Peso Calculado (kg):</strong> {formatar_brasileiro(peso_calculado)}</div>
            <div><strong>Peso Real (kg):</strong> {formatar_brasileiro(peso_real)}</div>
            <div><strong>Valor do Frete:</strong> R$ {formatar_brasileiro(valor_frete)}</div>
            <div><strong>Cubagem (m³):</strong> {formatar_brasileiro(cubagem)}</div>
            <div><strong>Volumes:</strong> {int(volumes) if pd.notnull(volumes) else 0}</div>
        </div>
        """, unsafe_allow_html=True)

        df_formatado = df_cliente[[col for col in colunas_exibir if col in df_cliente.columns]].copy()

        linha_destacar = JsCode("""
        function(params) {
            const status = params.data['Status'];
            const entrega = params.data['Entrega Programada'];
            if (status && status.toUpperCase() === 'AGENDAR' && (!entrega || entrega.toString().trim() === '')) {
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
        gb.configure_default_column(minWidth=150)
        gb.configure_selection("multiple", use_checkbox=True)
        gb.configure_grid_options(paginationPageSize=500)
        gb.configure_grid_options(domLayout="autoHeight")
        gb.configure_grid_options(alwaysShowHorizontalScroll=True)

        for col in ["Peso Real em Kg", "Peso Calculado em Kg", "Cubagem em m³", "Quantidade de Volumes", "Valor do Frete"]:
            if col in df_formatado.columns:
                gb.configure_column(col, type=["numericColumn"], valueFormatter=formatter_brasileiro)

        grid_options = gb.build()
        grid_options["getRowStyle"] = linha_destacar

        grid_response = AgGrid(
            df_formatado,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            fit_columns_on_grid_load=False,
            height=500,
            width=1500,
            allow_unsafe_jscode=True,
            key=f"grid_aprovacao_{cliente}",
            data_return_mode="AS_INPUT"
        )

        selecionadas = pd.DataFrame(grid_response.get("selected_rows", []))

        with st.container():
            col_sel1, col_sel2 = st.columns([1, 1])
            with col_sel1:
                st.button("🔘 Selecionar todas", key=f"btn_sel_{cliente}", use_container_width=True)
            with col_sel2:
                st.button("❌ Desmarcar todas", key=f"btn_desmarcar_{cliente}", use_container_width=True)

        if not selecionadas.empty:
            st.success(f"{len(selecionadas)} entregas selecionadas.")
            if st.button(f"✅ Aprovar entregas de {cliente}", key=f"btn_aprovar_{cliente}"):
                try:
                    aprovadas = selecionadas.copy()
                    colunas_numericas = ["Peso Real em Kg", "Peso Calculado em Kg", "Cubagem em m³", "Quantidade de Volumes", "Valor do Frete"]
                    for col in colunas_numericas:
                        if col in aprovadas.columns:
                            aprovadas[col] = aprovadas[col].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False).astype(float)

                    if "Rota" not in aprovadas.columns:
                        st.warning("Coluna 'Rota' não encontrada nos dados selecionados.")
                        return

                    aprovadas.drop(columns=["_selectedRowNodeInfo"], errors="ignore", inplace=True)

                    ctrcs_existentes = supabase.table("pre_roterizacao").select("Serie_Numero_CTRC").execute().data
                    ctrcs_existentes = {item["Serie_Numero_CTRC"] for item in ctrcs_existentes}
                    aprovadas = aprovadas[~aprovadas["Serie_Numero_CTRC"].isin(ctrcs_existentes)]

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


# Função PÁGINA PRÉ ROTERIZAÇÃO
##########################################

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

    rotas_unicas = sorted(df["Rota"].dropna().unique())

    for rota in rotas_unicas:
        df_rota = df[df["Rota"] == rota].copy()

        total_entregas_rota = len(df_rota)
        peso_calculado = df_rota['Peso Calculado em Kg'].sum()
        peso_real = df_rota['Peso Real em Kg'].sum()
        valor_frete = df_rota['Valor do Frete'].sum()
        cubagem = df_rota['Cubagem em m³'].sum()
        volumes = df_rota['Quantidade de Volumes'].sum()

        st.markdown(f"""
        <div style=\"background-color: #444; padding: 8px 16px; border-radius: 6px; margin-top: 20px; margin-bottom: 8px;\">
            <div style=\"color: white; margin: 0; font-size: 15px; font-weight: bold;\">🚛 Rota: {rota}</div>
        </div>

        <div style=\"display: flex; flex-wrap: wrap; gap: 20px; font-size: 16px; margin-bottom: 20px;\">
            <div><strong>Quantidade de Entregas:</strong> {total_entregas_rota}</div>
            <div><strong>Peso Calculado (kg):</strong> {formatar_brasileiro(peso_calculado)}</div>
            <div><strong>Peso Real (kg):</strong> {formatar_brasileiro(peso_real)}</div>
            <div><strong>Valor do Frete:</strong> R$ {formatar_brasileiro(valor_frete)}</div>
            <div><strong>Cubagem (m³):</strong> {formatar_brasileiro(cubagem)}</div>
            <div><strong>Volumes:</strong> {int(volumes) if pd.notnull(volumes) else 0}</div>
        </div>
        """, unsafe_allow_html=True)

        colunas_exibir = [
            "Serie_Numero_CTRC", "Cliente Pagador", "Chave CT-e", "Cliente Destinatario",
            "Cidade de Entrega", "Bairro do Destinatario", "Previsao de Entrega",
            "Numero da Nota Fiscal", "Status", "Entrega Programada", "Particularidade",
            "Codigo da Ultima Ocorrencia", "Peso Real em Kg", "Peso Calculado em Kg",
            "Cubagem em m³", "Quantidade de Volumes", "Valor do Frete"
        ]
        colunas_exibir = [col for col in colunas_exibir if col in df_rota.columns]

        df_formatado = df_rota[colunas_exibir].copy()

        formatter_brasileiro = JsCode("""
        function(params) {
            if (!params.value) return '';
            return Number(params.value).toLocaleString('pt-BR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
        }
        """)

        gb = GridOptionsBuilder.from_dataframe(df_formatado)
        gb.configure_default_column(minWidth=150)
        gb.configure_selection('multiple', use_checkbox=True)
        gb.configure_grid_options(paginationPageSize=500)
        gb.configure_grid_options(domLayout="autoHeight")
        gb.configure_grid_options(alwaysShowHorizontalScroll=True)
        gb.configure_grid_options(suppressHorizontalScroll=False)
        gb.configure_grid_options(suppressScrollOnNewData=False)

        for col in ['Peso Real em Kg', 'Peso Calculado em Kg', 'Cubagem em m³', 'Quantidade de Volumes', 'Valor do Frete']:
            if col in df_formatado.columns:
                gb.configure_column(col, type=["numericColumn"], valueFormatter=formatter_brasileiro)

        grid_options = gb.build()

        with st.container():
            st.markdown("<div style='overflow-x:auto'>", unsafe_allow_html=True)
            grid_response = AgGrid(
                df_formatado,
                gridOptions=grid_options,
                update_mode=GridUpdateMode.SELECTION_CHANGED,
                fit_columns_on_grid_load=False,
                height=500,
                width=1500,
                allow_unsafe_jscode=True,
                key=f"grid_pre_roterizacao_{rota}"
            )
            st.markdown("</div>", unsafe_allow_html=True)

        selecionadas = pd.DataFrame(grid_response.get("selected_rows", []))

        with st.container():
            col_sel1, col_sel2 = st.columns([1, 1])
            with col_sel1:
                st.button("🔘 Selecionar todas", key=f"btn_sel_pre_rota_{rota}", use_container_width=True)
            with col_sel2:
                st.button("❌ Desmarcar todas", key=f"btn_desmarcar_pre_rota_{rota}", use_container_width=True)

        if not selecionadas.empty:
            st.warning(f"{len(selecionadas)} entrega(s) selecionada(s). Clique abaixo para confirmar ou retornar para produção.")

            confirmar = st.checkbox("Confirmar seleção de entregas", key=f"confirmar_pre_rota_{rota}")
            col_conf, col_ret = st.columns(2)
            with col_conf:
                if st.button(f"✅ Confirmar Rota: {rota}", key=f"confirmar_rota_{rota}") and confirmar:
                    try:
                        df_selecionadas = selecionadas.copy()
                        df_selecionadas = df_selecionadas.drop(columns=["_selectedRowNodeInfo"], errors="ignore")
                        supabase.table("rotas_confirmadas").insert(df_selecionadas.to_dict(orient="records")).execute()
                        st.success("Entregas confirmadas com sucesso!")
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao confirmar entregas: {e}")

            with col_ret:
                if st.button(f"❌ Retirar da Pré Rota: {rota}", key=f"retirar_rota_{rota}") and confirmar:
                    try:
                        for ctrc in selecionadas["Serie_Numero_CTRC"]:
                            supabase.table("rotas_confirmadas").delete().eq("Serie_Numero_CTRC", ctrc).execute()
                        registros_confirmar = [{"Serie_Numero_CTRC": ctrc} for ctrc in selecionadas["Serie_Numero_CTRC"]]
                        supabase.table("confirmadas_producao").insert(registros_confirmar).execute()
                        st.success("Entregas retornadas para a produção com sucesso.")
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao retornar entregas: {e}")




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
            total_rotas = df_confirmadas['Rota'].nunique()
            total_entregas = len(df_confirmadas)

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(
                    f"<div style='background:#2f2f2f;padding:8px;border-radius:8px'>"
                    f"<span style='color:white;font-weight:bold;font-size:18px;'>Total de Rotas:</span>"
                    f"<span style='color:white;font-size:24px;'> {total_rotas}</span></div>",
                    unsafe_allow_html=True
                )
            with col2:
                st.markdown(
                    f"<div style='background:#2f2f2f;padding:8px;border-radius:8px'>"
                    f"<span style='color:white;font-weight:bold;font-size:18px;'>Total de Entregas:</span>"
                    f"<span style='color:white;font-size:24px;'> {total_entregas}</span></div>",
                    unsafe_allow_html=True
                )

            rotas_unicas = sorted(df_confirmadas['Rota'].dropna().unique())

            for rota in rotas_unicas:
                df_rota = df_confirmadas[df_confirmadas['Rota'] == rota].copy()

                total_entregas_rota = len(df_rota)
                peso_calculado = df_rota['Peso Calculado em Kg'].sum()
                peso_real = df_rota['Peso Real em Kg'].sum()
                valor_frete = df_rota['Valor do Frete'].sum()
                cubagem = df_rota['Cubagem em m³'].sum()
                volumes = df_rota['Quantidade de Volumes'].sum()

                st.markdown(f"""
                <div style=\"background-color: #444; padding: 8px 16px; border-radius: 6px; margin-top: 20px; margin-bottom: 8px;\">
                    <div style=\"color: white; margin: 0; font-size: 15px; font-weight: bold;\">🚛 Rota: {rota}</div>
                </div>

                <div style=\"display: flex; flex-wrap: wrap; gap: 20px; font-size: 16px; margin-bottom: 20px;\">
                    <div><strong>Quantidade de Entregas:</strong> {total_entregas_rota}</div>
                    <div><strong>Peso Calculado (kg):</strong> {formatar_brasileiro(peso_calculado)}</div>
                    <div><strong>Peso Real (kg):</strong> {formatar_brasileiro(peso_real)}</div>
                    <div><strong>Valor do Frete:</strong> R$ {formatar_brasileiro(valor_frete)}</div>
                    <div><strong>Cubagem (m³):</strong> {formatar_brasileiro(cubagem)}</div>
                    <div><strong>Volumes:</strong> {int(volumes) if pd.notnull(volumes) else 0}</div>
                </div>
                """, unsafe_allow_html=True)

                colunas_exibidas = [
                    'Serie_Numero_CTRC', 'Cliente Pagador', 'Chave CT-e', 'Cliente Destinatario',
                    'Cidade de Entrega', 'Bairro do Destinatario', 'Previsao de Entrega',
                    'Numero da Nota Fiscal', 'Status', 'Entrega Programada', 'Particularidade',
                    'Codigo da Ultima Ocorrencia', 'Peso Real em Kg', 'Peso Calculado em Kg',
                    'Cubagem em m³', 'Quantidade de Volumes', 'Valor do Frete'
                ]
                colunas_exibidas = [col for col in colunas_exibidas if col in df_rota.columns]

                df_formatado = df_rota[colunas_exibidas].copy()

                formatter_brasileiro = JsCode("""
                function(params) {
                    if (!params.value) return '';
                    return Number(params.value).toLocaleString('pt-BR', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                    });
                }
                """)

                gb = GridOptionsBuilder.from_dataframe(df_formatado)
                gb.configure_default_column(minWidth=150)
                gb.configure_selection('multiple', use_checkbox=True)
                gb.configure_grid_options(paginationPageSize=500)
                gb.configure_grid_options(domLayout="autoHeight")
                gb.configure_grid_options(alwaysShowHorizontalScroll=True)
                gb.configure_grid_options(suppressHorizontalScroll=False)
                gb.configure_grid_options(suppressScrollOnNewData=False)

                for col in ['Peso Real em Kg', 'Peso Calculado em Kg', 'Cubagem em m³', 'Quantidade de Volumes', 'Valor do Frete']:
                    if col in df_formatado.columns:
                        gb.configure_column(col, type=["numericColumn"], valueFormatter=formatter_brasileiro)

                grid_options = gb.build()

                # Container com largura forçada e barra horizontal ativada
                with st.container():
                    st.markdown("<div style='overflow-x:auto'>", unsafe_allow_html=True)
                    grid_response = AgGrid(
                    df_formatado,
                    gridOptions=grid_options,
                    update_mode=GridUpdateMode.SELECTION_CHANGED,
                    fit_columns_on_grid_load=False,
                    height=500,
                    width=1500,  # 👈 força largura para scroll
                    allow_unsafe_jscode=True,
                    key=f"grid_rotas_confirmadas_{rota}"
                )
                    st.markdown("</div>", unsafe_allow_html=True)

                    

                selecionadas = pd.DataFrame(grid_response.get("selected_rows", []))

                # Botões de seleção ao final do grid, discretos
                with st.container():
                    col_sel1, col_sel2 = st.columns([1, 1])
                    with col_sel1:
                        st.button("🔘 Selecionar todas", key=f"btn_sel_rotas_confirmadas_{rota}", use_container_width=True)
                    with col_sel2:
                        st.button("❌ Desmarcar todas", key=f"btn_desmarcar_rotas_confirmadas_{rota}", use_container_width=True)

                if not selecionadas.empty:
                    st.warning(f"{len(selecionadas)} entrega(s) selecionada(s). Clique abaixo para remover da rota confirmada.")

                    confirmar = st.checkbox("Confirmar remoção das entregas selecionadas", key=f"confirmar_remocao_{rota}")
                    if st.button(f"❌ Remover selecionadas da Rota {rota}", key=f"remover_{rota}") and confirmar:
                        try:
                            if "Serie_Numero_CTRC" in selecionadas.columns:
                                chaves_ctrc = selecionadas["Serie_Numero_CTRC"].dropna().astype(str).tolist()
                                for ctrc in chaves_ctrc:
                                    supabase.table("rotas_confirmadas").delete().eq("Serie_Numero_CTRC", ctrc).execute()
                                st.success("✅ Entregas removidas com sucesso!")
                                time.sleep(2)
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