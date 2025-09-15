import os

# COLOQUE AQUI O CAMINHO EXATO DA SUA IMAGEM (como você usou no código)
image_path = r"C:\Users\Rafael\Roteriza\Scripts\assets\Logo FA.png"

print(f"Tentando verificar o caminho: {image_path}")

if os.path.exists(image_path):
    print("SUCESSO: O arquivo de imagem existe e o Python consegue encontrá-lo neste caminho.")
    # Opcional: Tenta abrir o arquivo para verificar permissões básicas
    try:
        with open(image_path, 'rb') as f:
            content = f.read(10) # Lê os primeiros 10 bytes
        print("SUCESSO: O Python também conseguiu abrir o arquivo de imagem (permissões OK).")
    except Exception as e:
        print(f"ERRO: O Python encontrou o arquivo, mas não conseguiu abri-lo. Pode ser um problema de permissão. Erro: {e}")
else:
    print("ERRO: O arquivo de imagem NÃO existe neste caminho ou o Python não consegue encontrá-lo.")
    print("Por favor, verifique:")
    print(f"1. A capitalização do nome do arquivo ('Logo FA.png' vs 'logo-fa.png').")
    print(f"2. A extensão do arquivo (é '.png' mesmo?).")
    print(f"3. Cada barra '\' no caminho está correta.")
    print(f"4. Se o arquivo realmente está na pasta 'assets'.")
