import pandas as pd
from supabase import create_client, Client

# Configurações Supabase
url = "https://xhwotwefiqfwfabenwsi.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhod290d2VmaXFmd2ZhYmVud3NpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDgzNjc4NTMsImV4cCI6MjA2Mzk0Mzg1M30.3E2z-1SaABbCaV_HjQf0Rj8249mnPeGv7YkV4gOGhlg"
supabase: Client = create_client(url, key)

# Arquivos locais
arquivos = {
    "Clientes_Entrega_Agendada": "ClienteEntregaAgendada.xlsx",
    "Particularidades": "Particularidades.xlsx"
}

for tabela, arquivo in arquivos.items():
    try:
        print(f"➡️ Lendo {arquivo}...")
        df = pd.read_excel(arquivo)
        df = df.where(pd.notnull(df), None)  # limpa valores NaN
        data = df.to_dict(orient="records")

        print(f"🔄 Limpando dados existentes em {tabela}...")
        supabase.table(tabela).delete().neq("id", 0).execute()  # cuidado: limpa tudo

        print(f"⬆️ Enviando {len(data)} registros para {tabela}...")
        supabase.table(tabela).insert(data).execute()

        print(f"✅ Upload para {tabela} concluído com sucesso.\n")

    except Exception as e:
        print(f"❌ Erro ao processar {arquivo} para {tabela}: {e}")
