from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen import canvas # Importar o canvas diretamente

# Use o caminho completo para o seu logo.png
IMAGE_PATH = r"C:\Users\Rafael\Roteriza\Scripts\logo.png"
OUTPUT_PDF_PATH = "test_image_output.pdf" # Nome do PDF de saída

def add_image_to_page(canvas_obj, doc):
    try:
        # Desenha a imagem no canto inferior esquerdo (0,0)
        canvas_obj.drawImage(IMAGE_PATH, 0, 0, width=1*inch, height=0.75*inch, preserveAspectRatio=True)
        print(f"DEBUG: Tentou desenhar a imagem '{IMAGE_PATH}' no PDF.")
    except Exception as e:
        print(f"ERRO CRÍTICO no ReportLab: Não foi possível desenhar a imagem. Detalhes: {e}")

try:
    doc = SimpleDocTemplate(OUTPUT_PDF_PATH, pagesize=landscape(letter))
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("Teste de Imagem em PDF com ReportLab", styles['h1']),
        Spacer(1, 0.2 * inch),
        Paragraph(f"Este PDF deve conter a imagem '{IMAGE_PATH}' no canto inferior esquerdo de cada página.", styles['Normal'])
    ]
    doc.build(elements, onFirstPage=add_image_to_page, onLaterPages=add_image_to_page)
    print(f"\nPDF de teste gerado com sucesso em: {OUTPUT_PDF_PATH}")
except Exception as e:
    print(f"\nERRO: Falha ao construir o PDF de teste. Detalhes: {e}")
