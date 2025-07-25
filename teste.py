import os

image_file = "logo.jpg" # Certifique-se que este nome é EXATO!

if os.path.exists(image_file):
    print(f"O arquivo '{image_file}' existe na pasta.")
    try:
        with open(image_file, 'rb') as f:
            f.read()
        print(f"O arquivo '{image_file}' pode ser lido pelo Python.")
    except Exception as e:
        print(f"ERRO: Não foi possível ler o arquivo '{image_file}'. Motivo: {e}")
else:
    print(f"ERRO: O arquivo '{image_file}' NÃO foi encontrado na pasta.")

print("Teste de leitura de arquivo concluído.")