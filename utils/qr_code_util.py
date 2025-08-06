import qrcode
from io import BytesIO

def generate_qr_code_image(uri):
    """
    Gera uma imagem de QR Code a partir de uma URI e a retorna como bytes.
    """
    img = qrcode.make(uri)
    # Salva a imagem em um buffer de bytes na memória
    buf = BytesIO()
    img.save(buf)
    buf.seek(0)
    return buf
