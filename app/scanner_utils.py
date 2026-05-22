import nfc
from nfc.clf import RemoteTarget
import qrcode
import logging
from io import BytesIO
import base64
import uuid

logger = logging.getLogger(__name__)

class NFCReader:
    """Handle NFC tag reading and processing"""
    
    def __init__(self):
        self.clf = None
    
    def initialize_reader(self):
        """Initialize NFC reader"""
        try:
            import nfc.clf
            self.clf = nfc.clf.ContactlessFrontend('usb')
            logger.info("NFC reader initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize NFC reader: {e}")
            return False
    
    def read_tag(self, timeout=5):
        """
        Read NFC tag
        
        Returns:
            tag_id (str): Unique identifier from NFC tag
        """
        try:
            if not self.clf:
                self.initialize_reader()
            
            target = self.clf.sense(RemoteTarget, timeout=timeout)
            if target:
                # Extract tag ID (UID)
                tag_id = target.nfcid.hex()
                logger.info(f"NFC Tag read: {tag_id}")
                return tag_id
            return None
        except Exception as e:
            logger.error(f"Error reading NFC tag: {e}")
            return None
    
    def write_tag(self, tag_id_data):
        """Write data to NFC tag"""
        try:
            if not self.clf:
                self.initialize_reader()
            
            target = self.clf.sense(RemoteTarget, timeout=5)
            if target:
                # Write tag_id_data to tag
                logger.info(f"NFC Tag written: {tag_id_data}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error writing to NFC tag: {e}")
            return False
    
    def close(self):
        """Close NFC reader connection"""
        if self.clf:
            self.clf.close()


class QRCodeGenerator:
    """Handle QR code generation and storage"""
    
    @staticmethod
    def generate_qr_code(data, size=10, border=2):
        """
        Generate QR code image
        
        Args:
            data (str): Data to encode in QR code
            size (int): Size of QR code box
            border (int): Border size
        
        Returns:
            str: Base64 encoded image data
        """
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
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
            
            logger.info(f"QR Code generated for: {data}")
            return f"data:image/png;base64,{img_str}"
        except Exception as e:
            logger.error(f"Error generating QR code: {e}")
            return None
    
    @staticmethod
    def generate_qr_id():
        """Generate unique QR code ID"""
        return str(uuid.uuid4())


# Singleton instances
nfc_reader = NFCReader()
qr_generator = QRCodeGenerator()


def initialize_nfc():
    """Initialize NFC reader on app startup"""
    return nfc_reader.initialize_reader()


def read_nfc_tag(timeout=5):
    """Read an NFC tag"""
    return nfc_reader.read_tag(timeout)


def write_nfc_tag(data):
    """Write data to NFC tag"""
    return nfc_reader.write_tag(data)


def format_tag_id(raw_tag_id):
    """Format tag ID for database storage"""
    return raw_tag_id.upper() if raw_tag_id else None


def generate_qr_code(data, size=10, border=2):
    """Generate QR code image"""
    return qr_generator.generate_qr_code(data, size, border)


def generate_unique_qr_id():
    """Generate unique QR ID"""
    return qr_generator.generate_qr_id()
