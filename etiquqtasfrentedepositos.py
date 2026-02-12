# etiquqtasfrentedepositos.py
import io
import re
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pystrich.datamatrix import DataMatrixEncoder

# Fuente predeterminada
font_name = "Helvetica-Bold"

try:
    pdfmetrics.registerFont(TTFont("Arial-Black", "Arial-Black.ttf"))
    font_name = "Arial-Black"
except Exception:
    # Si no está disponible, usamos Helvetica-Bold
    pass


def create_arrow_image(direction, size_mm):
    """Genera una flecha como imagen en memoria usando matplotlib"""
    size_inches = size_mm / 25.4
    fig, ax = plt.subplots(figsize=(size_inches, size_inches), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    if direction == "down":
        arrow = patches.FancyArrow(
            0.5, 0.9,
            0, -0.6,
            width=0.2, head_width=0.5, head_length=0.2,
            fc="black", ec="black"
        )
    elif direction == "up":
        arrow = patches.FancyArrow(
            0.5, 0.1,
            0, 0.6,
            width=0.2, head_width=0.5, head_length=0.2,
            fc="black", ec="black"
        )
    else:
        plt.close(fig)
        return None

    ax.add_patch(arrow)
    buf = io.BytesIO()
    plt.savefig(buf, format="png", transparent=True, bbox_inches="tight", pad_inches=0)
    buf.seek(0)
    plt.close(fig)
    return ImageReader(buf)


def generate_label_pdf(dataframe, output_filename):
    """
    Genera etiquetas en PDF.
    - dataframe: debe contener la columna 'Ubicaciones'
    - output_filename: puede ser un string (nombre de archivo) o un BytesIO (en memoria)
    """
    # Soporte para archivo en memoria
    if isinstance(output_filename, io.BytesIO):
        c = canvas.Canvas(output_filename, pagesize=landscape(A4))
    else:
        c = canvas.Canvas(str(output_filename), pagesize=landscape(A4))

    width, height = landscape(A4)
    label_width_mm = 260
    label_height_mm = 80
    label_width_pt = label_width_mm * mm
    label_height_pt = label_height_mm * mm
    margin_x = (width - label_width_pt) / 2

    # posiciones Y para 2 etiquetas por página
    y_pos_top = height - (label_height_pt * 1) - 20 * mm
    y_pos_bottom = height - (label_height_pt * 2) - 40 * mm
    y_positions = [y_pos_top, y_pos_bottom]

    labels_per_page = 2
    label_on_page_count = 0

    for _, row in dataframe.iterrows():
        ubicacion = str(row["Ubicaciones"])

        if label_on_page_count == labels_per_page:
            c.showPage()
            label_on_page_count = 0

        # Detectar nivel según 4to carácter
        nivel = 0
        match = re.match(r"^.{3}(\d).*", ubicacion)
        if match:
            try:
                nivel = int(match.group(1))
            except ValueError:
                nivel = 0

        current_x = margin_x
        current_y = y_positions[label_on_page_count]

                 # --- CONTORNO PUNTEADO ESTILO GUÍA DE CORTE ---
        padding_mm = 5  # separación interna del borde
        padding_pt = padding_mm * mm

        c.setLineWidth(2)
        c.setStrokeColorRGB(0.4, 0.3, 0.25)  # marrón grisáceo tipo imprenta
        c.setDash(8, 6)  # patrón más visible

        c.roundRect(
            current_x + padding_pt,
            current_y + padding_pt,
            label_width_pt - (2 * padding_pt),
            label_height_pt - (2 * padding_pt),
            10,  # radio de esquinas redondeadas
            stroke=1,
            fill=0
        )

        c.setDash()  # volver a línea normal
        c.setStrokeColorRGB(0, 0, 0)  # volver a negro



        # --- 1. Código Data Matrix ---
        encoder = DataMatrixEncoder(ubicacion)
        datamatrix_img_data = encoder.get_imagedata()
        datamatrix_image = ImageReader(io.BytesIO(datamatrix_img_data))

        dm_size_mm = 60
        dm_size_pt = dm_size_mm * mm
        dm_x = current_x
        dm_y = current_y + (label_height_pt / 2) - (dm_size_pt / 2)
        c.drawImage(datamatrix_image, dm_x, dm_y, width=dm_size_pt, height=dm_size_pt)

        # --- 2. Texto de Ubicación ---
        font_size = 80
        c.setFont(font_name, font_size)
        text_ubicacion_x = current_x + (label_width_pt / 2)
        text_height = font_size * 0.8
        text_ubicacion_y = current_y + (label_height_pt / 2) - (text_height / 2)
        c.drawCentredString(text_ubicacion_x, text_ubicacion_y, ubicacion)

        # --- 3. Flecha (si aplica) ---
        arrow_image = None
        arrow_size_mm = 50
        arrow_size_pt = arrow_size_mm * mm

        if nivel == 1:
            arrow_image = create_arrow_image("down", arrow_size_mm)
        elif nivel == 2:
            arrow_image = create_arrow_image("up", arrow_size_mm)

        if arrow_image:
            arrow_x = current_x + label_width_pt - arrow_size_pt - 10 * mm
            arrow_y = current_y + (label_height_pt / 2) - (arrow_size_pt / 2)
            c.drawImage(arrow_image, arrow_x, arrow_y,
                        width=arrow_size_pt, height=arrow_size_pt, mask="auto")

        label_on_page_count += 1

    c.save()
