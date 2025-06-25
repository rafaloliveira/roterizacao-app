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
from st_aggrid.shared import AgGridTheme

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
        st.error(f"❌ Faltam colunas: {', '.join(colunas_faltantes)}")
        return

    df = df.dropna(subset=colunas_necessarias)
    if df.empty:
        st.info("Nenhuma entrega pendente após filtragem.")
        return

    try:
        # ✅ Captura a flag e remove do session_state
        recarregar = st.session_state.pop("reload_confirmadas_producao", False)

        # ✅ Recarrega do Supabase se necessário
        if recarregar or "df_confirmadas_cache" not in st.session_state:
            df_confirmadas = pd.DataFrame(
                supabase.table("confirmadas_producao").select("*").execute().data
            )
            st.session_state["df_confirmadas_cache"] = df_confirmadas
        else:
            df_confirmadas = st.session_state["df_confirmadas_cache"]

    except Exception as e:
        st.error(f"Erro ao carregar entregas confirmadas: {e}")
        return


    if df_confirmadas is None or df_confirmadas.empty:
        st.info("Nenhuma entrega confirmada na produção.")
        return

    df["Previsao de Entrega"] = pd.to_datetime(df["Previsao de Entrega"], format="%d-%m-%Y", errors='coerce')
    d_mais_1 = pd.Timestamp.now().normalize() + pd.Timedelta(days=1)

    obrigatorias = df[
        (df["Previsao de Entrega"] < d_mais_1) |
        ((df["Status"] == "AGENDAR") & (df["Entrega Programada"].isnull() | (df["Entrega Programada"].str.strip() == "")))
    ].copy()

    if not df_confirmadas.empty:
        obrigatorias = obrigatorias[~obrigatorias["Serie_Numero_CTRC"].isin(df_confirmadas["Serie_Numero_CTRC"])]

    df_aprovadas = pd.DataFrame(
    supabase.table("aprovacao_diretoria").select("Serie_Numero_CTRC").execute().data
    )

    chaves_aprovadas = df_aprovadas.get("Serie_Numero_CTRC", pd.Series()).dropna().unique().tolist()

    df_exibir = df_confirmadas[
        ~df_confirmadas["Serie_Numero_CTRC"].isin(chaves_aprovadas)
    ].copy()


    col1, col2, _ = st.columns([1, 1, 8])
    with col1:
        st.metric("Total de Clientes", df_exibir["Cliente Pagador"].nunique())
    with col2:
        st.metric("Total de Entregas", len(df_exibir))

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
        if (status === "AGENDAR" && (!entregaProg || entregaProg.trim() === "")) {
            return { 'background-color': '#ffe0b2', 'color': '#333' };
        }
        if (particularidade && particularidade.trim() !== "") {
            return { 'background-color': '#fff59d', 'color': '#333' };
        }
        return null;
    }
    """)

    def badge(label):
        return f"<span style='background:#eef2f7;border-radius:12px;padding:6px 12px;margin:4px;color:inherit;display:inline-block;'>{label}</span>"

    for cliente in sorted(df_exibir["Cliente Pagador"].fillna("(Vazio)").unique()):
        df_cliente = df_exibir[df_exibir["Cliente Pagador"].fillna("(Vazio)") == cliente].copy()
        if df_cliente.empty:
            continue

        st.markdown(f"""
        <div style="margin-top:20px;padding:10px;background:#e8f0fe;border-left:4px solid #4285f4;border-radius:6px;display:inline-block;max-width:100%;">
            <strong>Cliente:</strong> {cliente}
        </div>
        """, unsafe_allow_html=True)

            # Badge e checkbox master
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

        marcar_todas = col_check.checkbox("Marcar todas", key=f"marcar_todas_{cliente}")

        with st.expander("🔽 Selecionar entregas", expanded=False):
            df_formatado = df_cliente[[col for col in colunas_exibir if col in df_cliente.columns]].copy()

            if not df_formatado.empty:    
                gb = GridOptionsBuilder.from_dataframe(df_formatado)
                gb.configure_default_column(minWidth=150)
                gb.configure_selection('multiple', use_checkbox=True, pre_selected_rows=list(range(len(df_formatado))) if marcar_todas else [])
                gb.configure_grid_options(paginationPageSize=12)
                gb.configure_grid_options(alwaysShowHorizontalScroll=True)
                gb.configure_grid_options(rowStyle={'font-size': '8px'})
                grid_options = gb.build()
                grid_options["getRowStyle"] = linha_destacar



                grid_key_id = f"grid_confirmar_{cliente}"
                if st.session_state.get("reload_confirmadas_producao", False):
                    st.session_state[grid_key_id] = str(uuid.uuid4())
                elif grid_key_id not in st.session_state:
                    st.session_state[grid_key_id] = str(uuid.uuid4())

                gb.configure_grid_options(domLayout='normal')

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

                quantidade = len(selecionadas)
                st.markdown(f"**📦 Entregas selecionadas:** {quantidade}")

                if not selecionadas.empty:
                    if st.button(f"✅ Confirmar entregas", key=f"btn_confirmar_{cliente}"):
                        try:
                            chaves = selecionadas["Serie_Numero_CTRC"].dropna().astype(str).str.strip().tolist()
                            df_cliente["Serie_Numero_CTRC"] = df_cliente["Serie_Numero_CTRC"].astype(str).str.strip()
                            df_confirmar = df_cliente[df_cliente["Serie_Numero_CTRC"].isin(chaves)].copy()
                            df_confirmar = df_confirmar.replace([np.nan, np.inf, -np.inf], None)

                            for col in df_confirmar.select_dtypes(include=['datetime64[ns]']).columns:
                                df_confirmar[col] = df_confirmar[col].dt.strftime('%Y-%m-%d %H:%M:%S')

                            dados_confirmar = df_confirmar.to_dict(orient="records")
                            dados_confirmar = [d for d in dados_confirmar if d.get("Serie_Numero_CTRC")]

                            # Tentativa com retry (até 2 tentativas)
                            for tentativa in range(2):
                                try:
                                    resultado_insercao = supabase.table("aprovacao_diretoria").insert(dados_confirmar).execute()
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
                                for tentativa in range(2):
                                    try:
                                        supabase.table("confirmadas_producao").delete().in_("Serie_Numero_CTRC", chaves_inseridas).execute()
                                        break
                                    except Exception as e:
                                        if tentativa == 1:
                                            raise e
                                        st.warning("Erro temporário ao remover entregas. Tentando novamente em 2s...")
                                        time.sleep(2)

                                # ✅ Limpa todos os caches relacionados e força atualização
                                st.session_state.pop("df_confirmadas_cache", None)
                                st.session_state.pop("dados_sincronizados", None)
                                for key in list(st.session_state.keys()):
                                    if key.startswith("grid_confirmar_") or key.startswith("selecionadas_") or key.startswith("sucesso_"):
                                        st.session_state.pop(key, None)

                                st.session_state["reload_confirmadas_producao"] = True
                                st.success(f"{len(chaves_inseridas)} entregas confirmadas para {cliente}.")
                                st.rerun()

                            else:
                                st.error("❌ Nem todas as entregas foram inseridas corretamente.")
                        except Exception as e:
                            st.error(f"Erro ao processar confirmação: {e}")





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
        df_aprovacao = pd.DataFrame(supabase.table("aprovacao_diretoria").select("*").execute().data)
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

        marcar_todas = col_check.checkbox("Marcar todas", key=f"marcar_todas_aprov_{cliente}")


        with st.expander("🔽 Selecionar entregas", expanded=False):
            df_formatado = df_cliente[[col for col in colunas_exibir if col in df_cliente.columns]].copy()

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
            df = carregar_base_supabase()

            # 🔒 Apenas uma chamada ao Supabase aqui
            dados_confirmados_raw = supabase.table("rotas_confirmadas").select("*").execute().data
            dados_confirmados = pd.DataFrame(dados_confirmados_raw)

        except Exception as e:
            st.error(f"Erro ao consultar as tabelas do Supabase: {e}")
            return

        if df is None or df.empty:
            st.info("Nenhuma entrega disponível.")
            return

        if not dados_confirmados.empty:
            df = df[~df["Serie_Numero_CTRC"].isin(dados_confirmados["Serie_Numero_CTRC"].astype(str))]


    # Painel inicial de totais
    col1, col2, _ = st.columns([1, 1, 8])
    with col1:
        st.metric("Total de Rotas", df["Rota"].nunique())
    with col2:
        st.metric("Total de Entregas", len(df))

    def badge(label):
        return f"<span style='background:#eef2f7;border-radius:12px;padding:6px 12px;margin:4px;color:inherit;display:inline-block;'>{label}</span>"

    colunas_exibir = [
        "Serie_Numero_CTRC", "Rota", "Cliente Pagador", "Chave CT-e", "Cliente Destinatario",
        "Cidade de Entrega", "Bairro do Destinatario", "Previsao de Entrega",
        "Numero da Nota Fiscal", "Status", "Entrega Programada", "Particularidade",
        "Codigo da Ultima Ocorrencia", "Peso Real em Kg", "Peso Calculado em Kg",
        "Cubagem em m³", "Quantidade de Volumes", "Valor do Frete"
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

    for rota in rotas_unicas:
        df_rota = df[df["Rota"] == rota].copy()
        if df_rota.empty:
            continue

        st.markdown(f"""
        <div style="margin-top:20px;padding:10px;background:#e8f0fe;border-left:4px solid #4285f4;border-radius:6px;display:inline-block;max-width:100%;">
            <strong>Rota:</strong> {rota}
        </div>
        """, unsafe_allow_html=True)

        col_badge, col_check = st.columns([5, 1])
        with col_badge:
            st.markdown(
                badge(f"{len(df_rota)} entregas") +
                badge(f"{formatar_brasileiro(df_rota['Peso Calculado em Kg'].sum())} kg calc") +
                badge(f"{formatar_brasileiro(df_rota['Peso Real em Kg'].sum())} kg real") +
                badge(f"R$ {formatar_brasileiro(df_rota['Valor do Frete'].sum())}") +
                badge(f"{formatar_brasileiro(df_rota['Cubagem em m³'].sum())} m³") +
                badge(f"{int(df_rota['Quantidade de Volumes'].sum())} volumes"),
                unsafe_allow_html=True
            )

        marcar_todas = col_check.checkbox("Marcar todas", key=f"marcar_todas_pre_rota_{rota}")


        with st.expander("🔽 Selecionar entregas", expanded=False):
            df_formatado = df_rota[[col for col in colunas_exibir if col in df_rota.columns]].copy()

            gb = GridOptionsBuilder.from_dataframe(df_formatado)
            gb.configure_default_column(minWidth=150)
            gb.configure_selection('multiple', use_checkbox=True)
            gb.configure_grid_options(paginationPageSize=12)
            gb.configure_grid_options(alwaysShowHorizontalScroll=True)

            grid_options = gb.build()
            grid_options["getRowStyle"] = linha_destacar

            grid_key = f"grid_pre_rota_{rota}"
            if grid_key not in st.session_state:
                st.session_state[grid_key] = str(uuid.uuid4())


            with st.spinner("🔄 Carregando entregas da rota..."):
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

                if marcar_todas:
                    selecionadas = df_formatado[df_formatado["Serie_Numero_CTRC"].notna()].copy()
                else:
                    selecionadas = pd.DataFrame(grid_response.get("selected_rows", []))

                st.markdown(f"**📦 Entregas selecionadas:** {len(selecionadas)}")

                if not selecionadas.empty:
                    st.warning(f"{len(selecionadas)} entrega(s) selecionada(s).")

                    confirmar = st.checkbox("Confirmar seleção de entregas", key=f"confirmar_rota_{rota}")

                    col_conf, col_ret = st.columns(2)
                    with col_conf:
                        if st.button(f"✅ Enviar para Rota Confirmada", key=f"btn_confirma_rota_{rota}") and confirmar:
                            with st.spinner("🔄 Processando envio para Rotas Confirmadas..."):
                                try:
                                    df_confirmar = selecionadas.copy()
                                    df_confirmar = df_confirmar.drop(columns=["_selectedRowNodeInfo"], errors="ignore")
                                    df_confirmar["Rota"] = rota

                                    # Garante consistência de datas e valores nulos
                                    df_confirmar = df_confirmar.replace([np.nan, np.inf, -np.inf], None)
                                    for col in df_confirmar.select_dtypes(include=["datetime64[ns]"]).columns:
                                        df_confirmar[col] = df_confirmar[col].dt.strftime("%Y-%m-%d %H:%M:%S")

                                    registros = df_confirmar.to_dict(orient="records")
                                    registros = [r for r in registros if r.get("Serie_Numero_CTRC")]

                                    # ✅ Insere na tabela final
                                    supabase.table("rotas_confirmadas").insert(registros).execute()

                                    # ✅ Remove da pré-roterização (como no caso da diretoria)
                                    chaves = [r["Serie_Numero_CTRC"] for r in registros]
                                    supabase.table("pre_roterizacao").delete().in_("Serie_Numero_CTRC", chaves).execute()

                                    # ✅ Limpa estados de grid e força reload
                                    for key in list(st.session_state.keys()):
                                        if key.startswith("grid_pre_rota_") or key.startswith("confirmar_rota_") or key.startswith("sucesso_"):
                                            st.session_state.pop(key, None)

                                    st.success(f"✅ {len(chaves)} entregas enviadas para Rotas Confirmadas.")
                                    st.rerun()

                                except Exception as e:
                                    st.error(f"❌ Erro ao confirmar entregas: {e}")



##########################################

# PÁGINA ROTAS CONFIRMADAS

##########################################

def pagina_rotas_confirmadas():
    st.markdown("## Entregas Confirmadas por Rota")

    if "nova_carga_em_criacao" not in st.session_state:
        st.session_state["nova_carga_em_criacao"] = False
        st.session_state["numero_nova_carga"] = ""

    if not st.session_state["nova_carga_em_criacao"]:
        if st.button("🆕 Criar Nova Carga Avulsa"):
            hoje = datetime.now().strftime("%Y%m%d")
            try:
                filtro = f"CARGA-{hoje}-%"
                st.write("🔍 Filtro utilizado para buscar cargas existentes:", filtro)

                query = supabase.table("cargas_geradas").select("numero_carga").like("numero_carga", filtro)
                st.write("📤 Query pronta para execução.")
                
                resultado = query.execute()
                st.write("📥 Resultado bruto do Supabase:", resultado)
                
                ultimas = resultado.data

            except Exception as e:
                st.error("❌ Erro ao buscar cargas existentes:")
                st.exception(e)
                st.stop()

                sequencias_existentes = [
                    int(c["numero_carga"].split("-")[-1])
                    for c in ultimas if c.get("numero_carga", "").startswith(f"CARGA-{hoje}")
                ]
                proximo_num = max(sequencias_existentes + [0]) + 1
                numero_carga = f"CARGA-{hoje}-{proximo_num:03d}"
            except Exception as e:
                st.error(f"Erro ao buscar cargas existentes: {e}")
                return

            st.session_state["nova_carga_em_criacao"] = True
            st.session_state["numero_nova_carga"] = numero_carga
            st.rerun()

    if st.session_state["nova_carga_em_criacao"]:
        st.success(f"Nova Carga Criada: {st.session_state['numero_nova_carga']}")
        st.markdown("### Inserir Entregas na Carga")
        chaves_input = st.text_area("Insira as Chaves CT-e (uma por linha)")
        if st.button("🚛 Adicionar Entregas à Carga"):
            try:
                chaves = [c.strip() for c in chaves_input.splitlines() if c.strip()]
                if not chaves:
                    st.warning("Nenhuma Chave CT-e válida informada.")
                    return

                for chave in chaves:
                    resultado = supabase.table("rotas_confirmadas").select("*").eq("Chave CT-e", chave).execute()
                    if not resultado.data:
                        resultado = supabase.table("pre_roterizacao").select("*").eq("Chave CT-e", chave).execute()
                        if not resultado.data:
                            st.warning(f"Chave {chave} não encontrada na base.")
                            continue
                    entrega = resultado.data[0]
                    entrega["numero_carga"] = st.session_state["numero_nova_carga"]
                    entrega["Data_Hora_Gerada"] = datetime.now().isoformat()
                    entrega["Status"] = "Fechada"
                    # Limpeza e serialização da entrega avulsa
                    import json

                    entrega = {k: (v if not isinstance(v, (pd.Timestamp, datetime)) else v.isoformat()) for k, v in entrega.items()}
                    entrega = {k: (None if v in [np.nan, np.inf, -np.inf] else v) for k, v in entrega.items()}
                    entrega = {k: (json.dumps(v) if isinstance(v, dict) else v) for k, v in entrega.items()}

                    supabase.table("cargas_geradas").insert(entrega).execute()

                    if "Serie_Numero_CTRC" in entrega:
                        supabase.table("rotas_confirmadas").delete().eq("Serie_Numero_CTRC", entrega["Serie_Numero_CTRC"]).execute()
                    elif "Chave CT-e" in entrega:
                        supabase.table("pre_roterizacao").delete().eq("Chave CT-e", entrega["Chave CT-e"]).execute()

                st.success(f"Entregas adicionadas à carga {st.session_state['numero_nova_carga']} com sucesso.")
                time.sleep(2)
                st.switch_page("cargas_geradas")

            except Exception as e:
                st.error(f"Erro ao adicionar entregas: {e}")

    # Exibição das rotas confirmadas
    try:
        df = pd.DataFrame(supabase.table("rotas_confirmadas").select("*").execute().data)
        if df.empty:
            st.info("Nenhuma entrega foi confirmada ainda.")
            return

        col1, col2, _ = st.columns([1, 1, 8])
        with col1:
            st.metric("Total de Rotas", df["Rota"].nunique())
        with col2:
            st.metric("Total de Entregas", len(df))

        def badge(label):
            return f"<span style='background:#eef2f7;border-radius:12px;padding:6px 12px;margin:4px;color:inherit;display:inline-block;'>{label}</span>"

        colunas_exibir = [
            "Serie_Numero_CTRC", "Cliente Pagador", "Chave CT-e", "Cliente Destinatario",
            "Cidade de Entrega", "Bairro do Destinatario", "Previsao de Entrega",
            "Numero da Nota Fiscal", "Status", "Entrega Programada", "Particularidade",
            "Codigo da Ultima Ocorrencia", "Peso Real em Kg", "Peso Calculado em Kg",
            "Cubagem em m³", "Quantidade de Volumes", "Valor do Frete"
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
                badge(f"R$ {formatar_brasileiro(df_rota['Valor do Frete'].sum())}") +
                badge(f"{formatar_brasileiro(df_rota['Cubagem em m³'].sum())} m³") +
                badge(f"{int(df_rota['Quantidade de Volumes'].sum())} volumes"),
                unsafe_allow_html=True
            )

            with st.expander("🔽 Selecionar entregas", expanded=False):
                df_formatado = df_rota[[col for col in colunas_exibir if col in df_rota.columns]].copy()

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
                    show_toolbar=False
                )

                selecionadas = pd.DataFrame(grid_response.get("selected_rows", []))

                if not selecionadas.empty:
                    if st.button(f"🚛 Gerar Carga com Selecionadas da Rota {rota}", key=f"btn_gerar_carga_{rota}"):
                        try:
                            hoje = datetime.now().strftime("%Y%m%d")
                            cargas_hoje = supabase.table("cargas_geradas") \
                                .select("numero_carga") \
                                .like("numero_carga", f"CARGA-{hoje}-%") \
                                .execute().data

                            sequencias_existentes = [
                                int(c["numero_carga"].split("-")[-1])
                                for c in cargas_hoje if c.get("numero_carga", "").startswith(f"CARGA-{hoje}")
                            ]
                            proximo_num = max(sequencias_existentes + [0]) + 1
                            numero_carga = f"CARGA-{hoje}-{proximo_num:03d}"

                            registros = selecionadas.copy()
                            registros = registros.drop(columns=["_selectedRowNodeInfo"], errors="ignore")
                            registros["numero_carga"] = numero_carga
                            registros["Data_Hora_Gerada"] = datetime.now().isoformat()
                            registros["Status"] = "Fechada"

                            # Limpeza geral para evitar erro de serialização
                            registros = registros.replace([np.nan, np.inf, -np.inf], None)

                            # Converte datetime para string ISO, se houver colunas desse tipo
                            for col in registros.columns:
                                if registros[col].dtype == "datetime64[ns]":
                                    registros[col] = registros[col].astype(str)

                            # Garante que nenhum valor seja um tipo não serializável
                            import json

                            # Limpeza geral
                            registros = registros.replace([np.nan, np.inf, -np.inf], None)
                            registros = registros.drop(columns=[col for col in registros.columns if col.startswith("_")], errors="ignore")

                            dados_limpos = []
                            for row in registros.to_dict(orient="records"):
                                linha = {}
                                for k, v in row.items():
                                    if isinstance(v, (pd.Timestamp, datetime)):
                                        linha[k] = v.isoformat()
                                    elif isinstance(v, (np.integer, np.floating)):
                                        linha[k] = v.item()
                                    elif isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
                                        linha[k] = None
                                    elif isinstance(v, dict):
                                        linha[k] = json.dumps(v)
                                    else:
                                        linha[k] = v
                                dados_limpos.append(linha)

                            # st.write(dados_limpos)  # Descomente se quiser debug
                            # DEBUG PROFUNDO: Testar serialização JSON por linha
                            import json

                            erros = 0
                            for idx, row in enumerate(dados_limpos):
                                try:
                                    json.dumps(row)
                                except Exception as e:
                                    st.error(f"❌ Linha {idx} contém erro de serialização: {e}")
                                    st.write("🔍 Linha com problema:")
                                    st.json(row)
                                    erros += 1

                            if erros > 0:
                                st.stop()



                            supabase.table("cargas_geradas").insert(dados_limpos).execute()

                            chaves = registros["Serie_Numero_CTRC"].dropna().astype(str).tolist()
                            for ctrc in chaves:
                                supabase.table("rotas_confirmadas").delete().eq("Serie_Numero_CTRC", ctrc).execute()

                            st.success(f"🚛 Carga {numero_carga} criada com {len(chaves)} entregas.")
                            time.sleep(2)
                            st.switch_page("cargas_geradas")  # ou st.rerun() se preferir

                        except Exception as e:
                            st.error(f"❌ Erro ao gerar carga: {e}")

    except Exception as e:
        st.error(f"Erro ao carregar rotas confirmadas: {e}")



##########################################

# PÁGINA CARGAS GERADAS

##########################################


def pagina_cargas_geradas():
    st.markdown("## 🚛 Cargas Geradas")

    try:
        df_cargas = pd.DataFrame(supabase.table("cargas_geradas").select("*").execute().data)
    except Exception as e:
        st.error(f"Erro ao carregar dados de cargas: {e}")
        return

    if df_cargas.empty:
        st.info("Nenhuma carga gerada encontrada.")
        return

    df_cargas["numero_carga"] = df_cargas["numero_carga"].fillna("(Sem Número)")
    cargas_unicas = sorted(df_cargas["numero_carga"].unique())

    def badge(label):
        return f"<span style='background:#eef2f7;border-radius:12px;padding:6px 12px;margin:4px;color:inherit;display:inline-block;'>{label}</span>"

    colunas_exibir = [
        "Serie_Numero_CTRC", "Rota", "Valor do Frete", "Cliente Pagador", "Chave CT-e",
        "Cliente Destinatario", "Cidade de Entrega", "Bairro do Destinatario", "Previsao de Entrega",
        "Numero da Nota Fiscal", "Status", "Entrega Programada", "Particularidade",
        "Codigo da Ultima Ocorrencia", "Peso Real em Kg", "Peso Calculado em Kg",
        "Cubagem em m³", "Quantidade de Volumes", "numero_carga", "Localizacao Atual"
    ]

    linha_destacar = JsCode("""
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
    """)

    for carga in cargas_unicas:
        df_carga = df_cargas[df_cargas["numero_carga"] == carga].copy()
        if df_carga.empty:
            continue

        st.markdown(f"""
        <div style="margin-top:20px;padding:10px;background:#e8f0fe;border-left:4px solid #4285f4;border-radius:6px;display:inline-block;max-width:100%;">
            <strong>Número da Carga:</strong> {carga}
        </div>
        """, unsafe_allow_html=True)

        col_badge, col_check = st.columns([5, 1])
        with col_badge:
            st.markdown(
                badge(f"{len(df_carga)} entregas") +
                badge(f"{formatar_brasileiro(df_carga['Peso Calculado em Kg'].sum())} kg calc") +
                badge(f"{formatar_brasileiro(df_carga['Peso Real em Kg'].sum())} kg real") +
                badge(f"R$ {formatar_brasileiro(df_carga['Valor do Frete'].sum())}") +
                badge(f"{formatar_brasileiro(df_carga['Cubagem em m³'].sum())} m³") +
                badge(f"{int(df_carga['Quantidade de Volumes'].sum())} volumes"),
                unsafe_allow_html=True
            )

        marcar_todas = col_check.checkbox("Marcar todas", key=f"marcar_todas_carga_{carga}")

        with st.expander("🔽 Visualizar entregas da carga", expanded=False):
            df_formatado = df_carga[[col for col in colunas_exibir if col in df_carga.columns]].copy()

            gb = GridOptionsBuilder.from_dataframe(df_formatado)
            gb.configure_default_column(minWidth=150)
            gb.configure_selection("multiple", use_checkbox=True,
                pre_selected_rows=list(range(len(df_formatado))) if marcar_todas else [])
            gb.configure_grid_options(paginationPageSize=12)
            gb.configure_grid_options(alwaysShowHorizontalScroll=True)
            grid_options = gb.build()
            grid_options["getRowStyle"] = linha_destacar

            grid_key = f"grid_carga_{carga}"
            if grid_key not in st.session_state:
                st.session_state[grid_key] = str(uuid.uuid4())

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
                        "font-size": "11px", "line-height": "18px", "border-right": "1px solid #ccc",
                    },
                    ".ag-theme-material .ag-row:last-child .ag-cell": {
                        "border-bottom": "1px solid #ccc",
                    },
                    ".ag-theme-material .ag-header-cell": {
                        "border-right": "1px solid #ccc", "border-bottom": "1px solid #ccc",
                    },
                    ".ag-theme-material .ag-root-wrapper": {
                        "border": "1px solid black", "border-radius": "6px", "padding": "4px",
                    },
                    ".ag-theme-material .ag-header-cell-label": {
                        "font-size": "11px",
                    },
                    ".ag-center-cols-container": {
                        "min-width": "100% !important",
                    }
                }
            )

            selecionadas = pd.DataFrame(grid_response.get("selected_rows", []))
            st.markdown(f"**📦 Entregas selecionadas:** {len(selecionadas)}")






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
