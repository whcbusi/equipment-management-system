import qrcode
import os
from io import BytesIO
import base64
from datetime import datetime

def generate_qr_code(data, size=10, border=2):
    """
    Generate QR code and return as base64 encoded string
    
    Args:
        data: String to encode in QR code
        size: Box size in pixels
        border: Border size in boxes
    
    Returns:
        Base64 encoded QR code image
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"

def generate_qr_code_file(data, filename, size=10, border=2):
    """
    Generate QR code and save to file
    
    Args:
        data: String to encode in QR code
        filename: Output filename
        size: Box size in pixels
        border: Border size in boxes
    
    Returns:
        Filepath
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    filepath = os.path.join('app/static/qrcodes', filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    img.save(filepath)
    
    return filepath

def format_datetime(dt):
    """Format datetime for display"""
    if not dt:
        return None
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def is_admin(user):
    """Check if user is admin"""
    from app.models import UserRole
    return user.role == UserRole.ADMIN

def is_overdue(expected_return):
    """Check if return is overdue"""
    if not expected_return:
        return False
    return datetime.utcnow() > expected_return
