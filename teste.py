from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from PIL import Image
from io import BytesIO

# Caminho do logo
logo_path = r"C:\Users\Rafael\Roteriza\Scripts\logo.jpg"

# Abre e converte a imagem para RGB
img = Image.open(logo_path).convert("RGB")
logo_reader = ImageReader(img)

# Gera PDF
buffer = BytesIO()
c = canvas.Canvas(buffer, pagesize=landscape(letter))
width, height = landscape(letter)

# Desenha imagem no centro
img_width = 2 * inch
img_height = 0.6 * inch
x = (width - img_width) / 2
y = (height - img_height) / 2
c.drawImage(logo_reader, x, y, width=img_width, height=img_height)

# Texto abaixo da imagem
c.drawString(x, y - 20, "Imagem deve aparecer acima")
c.showPage()
c.save()

# Salva PDF
with open("logo_teste_final.pdf", "wb") as f:
    f.write(buffer.getvalue())
