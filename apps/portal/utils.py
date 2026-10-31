import io
import base64
import qrcode

def generate_qr_base64(data_url: str) -> str:
    """
    Generates a base64 encoded PNG QR code image suitable for embedding
    directly into HTML (<img src="data:image/png;base64,...">).
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(data_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1e293b", back_color="#ffffff")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()

def get_client_ip(request) -> str:
    """Retrieves client IP considering potential proxy forwarding."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '127.0.0.1')
