# NFC & QR Code Implementation Guide

## Overview
Support both NFC tag reading and QR code scanning for:
1. **User Authentication** - Read NFC tag or scan QR code to auto-login
2. **Equipment Recognition** - Read NFC tag or scan QR code on equipment to borrow

---

## 1. HARDWARE REQUIREMENTS

### NFC Reader Options:

**Option A: USB NFC Reader (Recommended for desktop)**
- ACR122U USB RFID Reader (~$30-50)
- Works with: Windows, Mac, Linux
- Library: `nfcpy` or `pyaml-nfc`

**Option B: Mobile Phone (Easy)**
- Android/iOS with NFC capability
- Use web-based NFC API (modern browsers)
- Library: `Web NFC API` (Chrome 89+)

**Option C: Fixed Terminal**
- Raspberry Pi + NFC Hat (~$50-100)
- Industrial NFC readers
- Perfect for kiosk-style setup

### QR Code Scanner:
- Any device with camera (smartphone, webcam, USB scanner)
- Browser-based or hardware scanner
- Libraries: `jsQR`, `html5-qrcode`, or USB scanner driver

### NFC Tags:
- **NTAG216** (most common)
- **MIFARE Classic**
- **ISO 14443 Type A**
- Cost: ~$0.50-$2 per tag

---

## 2. UPDATE BACKEND - NFC & QR CODE AUTHENTICATION

### Step 1: Install Required Libraries

Update `requirements.txt`:

```
Flask==2.3.2
Flask-SQLAlchemy==3.0.5
Flask-Migrate==4.0.4
Flask-JWT-Extended==4.4.4
Flask-CORS==4.0.0
Python-dotenv==1.0.0
psycopg2-binary==2.9.6
qrcode==7.4.2
pillow==10.0.0
Werkzeug==2.3.6
nfcpy==1.0.4
pyzbar==0.1.9
opencv-python==4.8.0.74
```

Install:
```bash
pip install -r requirements.txt
```

### Step 2: Update User Model to Store NFC & QR Tag IDs

Edit `app/models.py`:

```python
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(120), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    nfc_tag_id = db.Column(db.String(255), unique=True, nullable=True, index=True)  # NEW
    qr_code_id = db.Column(db.String(255), unique=True, nullable=True, index=True)   # NEW
    role = db.Column(db.Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    borrow_records = db.relationship('BorrowRecord', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'department': self.department,
            'role': self.role.value,
            'nfc_tag_id': self.nfc_tag_id,
            'qr_code_id': self.qr_code_id,
            'created_at': self.created_at.isoformat()
        }
```

### Step 3: Update Equipment Model to Store NFC & QR Tag IDs

```python
class Equipment(db.Model):
    __tablename__ = 'equipment'
    
    id = db.Column(db.Integer, primary_key=True)
    equipment_type_id = db.Column(db.Integer, db.ForeignKey('equipment_types.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    serial_number = db.Column(db.String(120), unique=True, nullable=True, index=True)
    barcode = db.Column(db.String(120), unique=True, nullable=True, index=True)
    nfc_tag_id = db.Column(db.String(255), unique=True, nullable=True, index=True)  # NEW
    qr_code_id = db.Column(db.String(255), unique=True, nullable=True, index=True)   # NEW
    qr_code_image = db.Column(db.String(255), nullable=True)
    status = db.Column(db.Enum(EquipmentStatus), default=EquipmentStatus.AVAILABLE, nullable=False)
    location = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    borrow_records = db.relationship('BorrowRecord', backref='equipment', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'equipment_type_id': self.equipment_type_id,
            'equipment_type': self.equipment_type.name if self.equipment_type else None,
            'name': self.name,
            'serial_number': self.serial_number,
            'barcode': self.barcode,
            'nfc_tag_id': self.nfc_tag_id,
            'qr_code_id': self.qr_code_id,
            'qr_code_image': self.qr_code_image,
            'status': self.status.value,
            'location': self.location,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
```

### Step 4: Create NFC & QR Code Utility Functions

Create `app/scanner_utils.py`:

```python
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
```

### Step 5: Create Combined Login & Scanner Routes

Update `app/routes/auth.py`:

```python
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.models import User, UserRole
from app.scanner_utils import format_tag_id, generate_qr_code, generate_unique_qr_id
from app import db
from functools import wraps

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# ... existing code ...

@auth_bp.route('/smart-login', methods=['GET', 'POST'])
def smart_login():
    """Combined NFC/QR login page"""
    if request.method == 'POST':
        scan_type = request.form.get('scan_type')  # 'nfc' or 'qr'
        tag_id = request.form.get('tag_id')
        
        user = None
        if scan_type == 'nfc':
            user = User.query.filter_by(nfc_tag_id=format_tag_id(tag_id)).first()
        elif scan_type == 'qr':
            user = User.query.filter_by(qr_code_id=tag_id).first()
        
        if user and user.is_active:
            access_token = create_access_token(identity=user.id)
            response = redirect(url_for('main.dashboard'))
            response.set_cookie('access_token_cookie', access_token, httponly=True, secure=True, samesite='Lax')
            flash(f'Welcome, {user.name}!', 'success')
            return response
        else:
            flash('Tag not recognized', 'danger')
    
    return render_template('auth/smart_login.html')


@auth_bp.route('/api/smart-login', methods=['POST'])
def api_smart_login():
    """API endpoint for NFC/QR login (AJAX)"""
    data = request.get_json()
    scan_type = data.get('scan_type')  # 'nfc' or 'qr'
    tag_id = data.get('tag_id')
    
    user = None
    if scan_type == 'nfc':
        user = User.query.filter_by(nfc_tag_id=format_tag_id(tag_id)).first()
    elif scan_type == 'qr':
        user = User.query.filter_by(qr_code_id=tag_id).first()
    
    if user and user.is_active:
        access_token = create_access_token(identity=user.id)
        return jsonify({
            'success': True,
            'message': f'Welcome, {user.name}!',
            'access_token': access_token,
            'user': user.to_dict()
        }), 200
    else:
        return jsonify({
            'success': False,
            'message': 'Tag not recognized'
        }), 401


@auth_bp.route('/link-tag', methods=['GET', 'POST'])
@jwt_required(optional=True)
def link_tag():
    """Link NFC/QR tag to user account"""
    user_id = get_jwt_identity()
    if not user_id:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(user_id)
    
    if request.method == 'POST':
        tag_type = request.form.get('tag_type')  # 'nfc' or 'qr'
        tag_id = request.form.get('tag_id')
        
        if tag_type == 'nfc':
            # Check if NFC tag already registered
            existing_user = User.query.filter_by(nfc_tag_id=format_tag_id(tag_id)).first()
            if existing_user and existing_user.id != user.id:
                flash('This NFC tag is already registered to another user', 'danger')
                return redirect(url_for('auth.link_tag'))
            
            user.nfc_tag_id = format_tag_id(tag_id)
            flash('NFC tag linked successfully!', 'success')
        
        elif tag_type == 'qr':
            # Check if QR code already registered
            existing_user = User.query.filter_by(qr_code_id=tag_id).first()
            if existing_user and existing_user.id != user.id:
                flash('This QR code is already registered to another user', 'danger')
                return redirect(url_for('auth.link_tag'))
            
            user.qr_code_id = tag_id
            flash('QR code linked successfully!', 'success')
        
        db.session.commit()
        return redirect(url_for('main.dashboard'))
    
    return render_template('auth/link_tag.html', user=user)


@auth_bp.route('/register', methods=['GET', 'POST'])
@admin_required
def register():
    """Register new user with optional NFC/QR tags"""
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        department = request.form.get('department')
        nfc_tag_id = request.form.get('nfc_tag_id')
        qr_code_id = request.form.get('qr_code_id')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('auth.register'))
        
        # Check if NFC tag already used
        if nfc_tag_id and User.query.filter_by(nfc_tag_id=format_tag_id(nfc_tag_id)).first():
            flash('NFC tag already registered', 'danger')
            return redirect(url_for('auth.register'))
        
        # Check if QR code already used
        if qr_code_id and User.query.filter_by(qr_code_id=qr_code_id).first():
            flash('QR code already registered', 'danger')
            return redirect(url_for('auth.register'))
        
        user = User(
            email=email,
            name=name,
            department=department,
            nfc_tag_id=format_tag_id(nfc_tag_id) if nfc_tag_id else None,
            qr_code_id=qr_code_id if qr_code_id else None,
            role=UserRole.USER
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash(f'User {name} registered successfully', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('auth/register.html')
```

### Step 6: Update Borrow Route for NFC & QR Equipment

Update `app/routes/borrow.py`:

```python
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Equipment, BorrowRecord, User, EquipmentStatus
from app.scanner_utils import format_tag_id, generate_qr_code, generate_unique_qr_id
from app import db
from datetime import datetime, timedelta

borrow_bp = Blueprint('borrow', __name__, url_prefix='/borrow')

# ... existing code ...

@borrow_bp.route('/scanner')
@jwt_required(optional=True)
def scanner():
    """NFC/QR scanner page for equipment"""
    user_id = get_jwt_identity()
    if not user_id:
        return redirect(url_for('auth.login'))
    
    return render_template('borrow/scanner.html')


@borrow_bp.route('/api/scan', methods=['POST'])
@jwt_required()
def api_scan():
    """Scan NFC/QR tag on equipment to borrow"""
    user_id = get_jwt_identity()
    data = request.get_json()
    scan_type = data.get('scan_type')  # 'nfc' or 'qr'
    tag_id = data.get('tag_id')
    
    # Find equipment by NFC or QR tag
    equipment = None
    if scan_type == 'nfc':
        equipment = Equipment.query.filter_by(nfc_tag_id=format_tag_id(tag_id)).first()
    elif scan_type == 'qr':
        equipment = Equipment.query.filter_by(qr_code_id=tag_id).first()
    
    if not equipment:
        return jsonify({'error': 'Equipment not found'}), 404
    
    # Check if equipment is available
    if equipment.status != EquipmentStatus.AVAILABLE:
        return jsonify({'error': f'Equipment is {equipment.status.value}'}), 400
    
    # Create borrow record
    borrow_record = BorrowRecord(
        equipment_id=equipment.id,
        user_id=user_id,
        expected_return=datetime.utcnow() + timedelta(days=7)
    )
    equipment.status = EquipmentStatus.BORROWED
    
    db.session.add(borrow_record)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Successfully borrowed {equipment.name}',
        'equipment': equipment.to_dict()
    }), 201


@borrow_bp.route('/generate-qr/<int:equipment_id>', methods=['GET'])
@jwt_required(optional=True)
def generate_equipment_qr(equipment_id):
    """Generate QR code for equipment"""
    user_id = get_jwt_identity()
    if not user_id:
        return redirect(url_for('auth.login'))
    
    equipment = Equipment.query.get(equipment_id)
    if not equipment:
        flash('Equipment not found', 'danger')
        return redirect(url_for('borrow.scanner'))
    
    # Generate unique QR ID if not exists
    if not equipment.qr_code_id:
        equipment.qr_code_id = generate_unique_qr_id()
    
    # Generate QR code image
    qr_data = f"eq_{equipment.qr_code_id}"
    qr_image = generate_qr_code(qr_data)
    equipment.qr_code_image = qr_image
    
    db.session.commit()
    
    flash('QR code generated successfully', 'success')
    return redirect(url_for('equipment.view_equipment', equipment_id=equipment_id))
```

---

## 3. FRONTEND - COMBINED NFC/QR SCANNING

### Step 1: Create Combined Login Template

Create `app/templates/auth/smart_login.html`:

```html
{% extends "base.html" %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-8">
        <div class="card">
            <div class="card-body">
                <h1 class="mb-4 text-center">
                    <i class="bi bi-wifi" style="font-size: 2rem; color: #0066cc;"></i>
                    <i class="bi bi-qr-code" style="font-size: 2rem; color: #dc3545;"></i>
                </h1>
                <h2 class="mb-4 text-center">Smart Login</h2>
                
                <!-- Tab Navigation -->
                <ul class="nav nav-tabs mb-4" role="tablist">
                    <li class="nav-item" role="presentation">
                        <button class="nav-link active" id="nfc-tab" data-bs-toggle="tab" 
                                data-bs-target="#nfc-content" type="button">
                            <i class="bi bi-wifi"></i> NFC
                        </button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="qr-tab" data-bs-toggle="tab" 
                                data-bs-target="#qr-content" type="button">
                            <i class="bi bi-qr-code"></i> QR Code
                        </button>
                    </li>
                </ul>
                
                <!-- NFC Tab -->
                <div class="tab-content">
                    <div class="tab-pane fade show active" id="nfc-content" role="tabpanel">
                        <div class="text-center">
                            <div id="nfc-status" class="alert alert-info">
                                <i class="bi bi-hourglass-split"></i> Waiting for NFC tag...
                            </div>
                            
                            <button class="btn btn-primary btn-lg" id="start-nfc">
                                <i class="bi bi-wifi"></i> Start NFC Reader
                            </button>
                        </div>
                    </div>
                    
                    <!-- QR Code Tab -->
                    <div class="tab-pane fade" id="qr-content" role="tabpanel">
                        <div class="text-center">
                            <div id="qr-status" class="alert alert-info">
                                <i class="bi bi-hourglass-split"></i> Initializing camera...
                            </div>
                            
                            <div id="qr-reader" style="max-width: 100%; display: none;"></div>
                            
                            <button class="btn btn-danger btn-lg" id="start-qr" style="display: none;">
                                <i class="bi bi-camera"></i> Start Camera
                            </button>
                            
                            <button class="btn btn-secondary btn-lg" id="stop-qr" style="display: none;">
                                <i class="bi bi-stop-circle"></i> Stop Camera
                            </button>
                        </div>
                    </div>
                </div>
                
                <hr class="my-4">
                
                <p class="text-center text-muted">
                    Or use <a href="{{ url_for('auth.login') }}">traditional login</a>
                </p>
            </div>
        </div>
    </div>
</div>

<!-- Include QR Code Library -->
<script src="https://cdn.jsdelivr.net/npm/html5-qrcode@2.3.4/minified/html5-qrcode.min.js"></script>

<script>
let html5QrcodeScanner = null;
let ndefReader = null;

document.getElementById('start-nfc').addEventListener('click', startNFCReader);
document.getElementById('start-qr').addEventListener('click', startQRScanner);
document.getElementById('stop-qr').addEventListener('click', stopQRScanner);

// NFC Implementation
async function startNFCReader() {
    if (!('NDEFReader' in window)) {
        updateNFCStatus('NFC not supported on this device', 'danger');
        return;
    }
    
    try {
        ndefReader = new NDEFReader();
        await ndefReader.scan();
        
        updateNFCStatus('Touch NFC tag...', 'warning');
        
        ndefReader.addEventListener('reading', async (event) => {
            const tagId = extractNFCTagId(event);
            await loginWithTag('nfc', tagId);
        });
        
    } catch (error) {
        updateNFCStatus('Error: ' + error.message, 'danger');
    }
}

function extractNFCTagId(event) {
    if (event.serialNumber) {
        return event.serialNumber;
    }
    
    const decoder = new TextDecoder();
    for (const record of event.message.records) {
        if (record.recordType === 'text') {
            return decoder.decode(record.data);
        }
    }
    return 'unknown';
}

function updateNFCStatus(message, type) {
    document.getElementById('nfc-status').innerHTML = 
        '<div class="alert alert-' + type + '"><i class="bi bi-info-circle"></i> ' + 
        message + '</div>';
}

// QR Code Implementation
function startQRScanner() {
    document.getElementById('qr-reader').style.display = 'block';
    document.getElementById('start-qr').style.display = 'none';
    document.getElementById('stop-qr').style.display = 'inline-block';
    
    html5QrcodeScanner = new Html5Qrcode("qr-reader");
    
    html5QrcodeScanner.start(
        { facingMode: "environment" },
        {
            fps: 10,
            qrbox: { width: 250, height: 250 }
        },
        async (decodedText, decodedResult) => {
            await loginWithTag('qr', decodedText);
            stopQRScanner();
        },
        (errorMessage) => {
            // Handle scan errors silently
        }
    ).catch(err => {
        updateQRStatus('Camera error: ' + err.message, 'danger');
    });
}

function stopQRScanner() {
    if (html5QrcodeScanner) {
        html5QrcodeScanner.stop().then(() => {
            document.getElementById('qr-reader').style.display = 'none';
            document.getElementById('start-qr').style.display = 'inline-block';
            document.getElementById('stop-qr').style.display = 'none';
        });
    }
}

function updateQRStatus(message, type) {
    document.getElementById('qr-status').innerHTML = 
        '<div class="alert alert-' + type + '"><i class="bi bi-info-circle"></i> ' + 
        message + '</div>';
}

// Combined Login
async function loginWithTag(scanType, tagId) {
    try {
        const response = await fetch('/auth/api/smart-login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                scan_type: scanType,
                tag_id: tagId
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            if (scanType === 'nfc') {
                updateNFCStatus('Success! ' + data.message + ' Redirecting...', 'success');
            } else {
                updateQRStatus('Success! ' + data.message + ' Redirecting...', 'success');
            }
            
            localStorage.setItem('access_token', data.access_token);
            setTimeout(() => {
                window.location.href = "{{ url_for('main.dashboard') }}";
            }, 1500);
        } else {
            const status = scanType === 'nfc' ? 
                () => updateNFCStatus('Error: ' + data.message, 'danger') :
                () => updateQRStatus('Error: ' + data.message, 'danger');
            status();
        }
    } catch (error) {
        if (scanType === 'nfc') {
            updateNFCStatus('Error: ' + error.message, 'danger');
        } else {
            updateQRStatus('Error: ' + error.message, 'danger');
        }
    }
}

// Initialize QR tab UI
document.getElementById('qr-tab').addEventListener('shown.bs.tab', function () {
    document.getElementById('start-qr').style.display = 'inline-block';
    document.getElementById('stop-qr').style.display = 'none';
    updateQRStatus('Ready to scan QR code', 'info');
});
</script>
{% endblock %}
```

### Step 2: Create Combined Equipment Scanner Template

Create `app/templates/borrow/scanner.html`:

```html
{% extends "base.html" %}

{% block content %}
<h1 class="mb-4">
    <i class="bi bi-wifi"></i> <i class="bi bi-qr-code"></i> Equipment Scanner
</h1>

<div class="row">
    <div class="col-md-6">
        <div class="card">
            <div class="card-body text-center">
                <h3>Scan Equipment</h3>
                
                <!-- Tab Navigation -->
                <ul class="nav nav-tabs mt-3 mb-3" role="tablist">
                    <li class="nav-item" role="presentation">
                        <button class="nav-link active" id="nfc-eq-tab" data-bs-toggle="tab" 
                                data-bs-target="#nfc-eq-content" type="button">
                            <i class="bi bi-wifi"></i>
                        </button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="qr-eq-tab" data-bs-toggle="tab" 
                                data-bs-target="#qr-eq-content" type="button">
                            <i class="bi bi-qr-code"></i>
                        </button>
                    </li>
                </ul>
                
                <div class="tab-content">
                    <!-- NFC Equipment Tab -->
                    <div class="tab-pane fade show active" id="nfc-eq-content" role="tabpanel">
                        <div id="nfc-eq-status" class="alert alert-info">
                            <i class="bi bi-hourglass-split"></i> Waiting for equipment tag...
                        </div>
                        
                        <button class="btn btn-primary btn-lg mt-3" id="start-nfc-eq">
                            <i class="bi bi-wifi"></i> Start NFC Reader
                        </button>
                        
                        <button class="btn btn-secondary btn-lg mt-3" id="stop-nfc-eq" style="display: none;">
                            Stop Scanning
                        </button>
                    </div>
                    
                    <!-- QR Equipment Tab -->
                    <div class="tab-pane fade" id="qr-eq-content" role="tabpanel">
                        <div id="qr-eq-status" class="alert alert-info">
                            <i class="bi bi-hourglass-split"></i> Initializing camera...
                        </div>
                        
                        <div id="qr-eq-reader" style="max-width: 100%; display: none;"></div>
                        
                        <button class="btn btn-danger btn-lg mt-3" id="start-qr-eq">
                            <i class="bi bi-camera"></i> Start Camera
                        </button>
                        
                        <button class="btn btn-secondary btn-lg mt-3" id="stop-qr-eq" style="display: none;">
                            Stop Camera
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="col-md-6">
        <div class="card">
            <div class="card-body">
                <h3>Borrowed Equipment</h3>
                <div id="scanned-list" class="list-group">
                    <p class="text-muted">Scan equipment to see details...</p>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Include QR Code Library -->
<script src="https://cdn.jsdelivr.net/npm/html5-qrcode@2.3.4/minified/html5-qrcode.min.js"></script>

<script>
let ndefReader = null;
let qrScanner = null;

// Event Listeners
document.getElementById('start-nfc-eq').addEventListener('click', startNFCEquipmentScan);
document.getElementById('stop-nfc-eq').addEventListener('click', stopNFCEquipmentScan);
document.getElementById('start-qr-eq').addEventListener('click', startQREquipmentScan);
document.getElementById('stop-qr-eq').addEventListener('click', stopQREquipmentScan);

// NFC Equipment Scanning
async function startNFCEquipmentScan() {
    if (!('NDEFReader' in window)) {
        updateNFCEQStatus('NFC not supported', 'danger');
        return;
    }
    
    try {
        ndefReader = new NDEFReader();
        await ndefReader.scan();
        
        document.getElementById('start-nfc-eq').style.display = 'none';
        document.getElementById('stop-nfc-eq').style.display = 'inline-block';
        updateNFCEQStatus('Ready to scan... Hold equipment near device', 'info');
        
        ndefReader.addEventListener('reading', async (event) => {
            const tagId = extractNFCTagId(event);
            await scanEquipment('nfc', tagId);
        });
    } catch (error) {
        updateNFCEQStatus('Error: ' + error.message, 'danger');
    }
}

function stopNFCEquipmentScan() {
    if (ndefReader) {
        ndefReader.abort();
        ndefReader = null;
    }
    document.getElementById('start-nfc-eq').style.display = 'inline-block';
    document.getElementById('stop-nfc-eq').style.display = 'none';
    updateNFCEQStatus('Scanning stopped', 'warning');
}

function extractNFCTagId(event) {
    if (event.serialNumber) {
        return event.serialNumber;
    }
    const decoder = new TextDecoder();
    for (const record of event.message.records) {
        if (record.recordType === 'text') {
            return decoder.decode(record.data);
        }
    }
    return 'unknown';
}

function updateNFCEQStatus(message, type) {
    document.getElementById('nfc-eq-status').innerHTML = 
        '<div class="alert alert-' + type + '"><i class="bi bi-info-circle"></i> ' + 
        message + '</div>';
}

// QR Equipment Scanning
function startQREquipmentScan() {
    document.getElementById('qr-eq-reader').style.display = 'block';
    document.getElementById('start-qr-eq').style.display = 'none';
    document.getElementById('stop-qr-eq').style.display = 'inline-block';
    
    qrScanner = new Html5Qrcode("qr-eq-reader");
    
    qrScanner.start(
        { facingMode: "environment" },
        { fps: 10, qrbox: { width: 250, height: 250 } },
        async (decodedText, decodedResult) => {
            await scanEquipment('qr', decodedText);
        },
        (errorMessage) => {}
    ).catch(err => {
        updateQREQStatus('Camera error: ' + err.message, 'danger');
    });
}

function stopQREquipmentScan() {
    if (qrScanner) {
        qrScanner.stop().then(() => {
            document.getElementById('qr-eq-reader').style.display = 'none';
            document.getElementById('start-qr-eq').style.display = 'inline-block';
            document.getElementById('stop-qr-eq').style.display = 'none';
        });
    }
}

function updateQREQStatus(message, type) {
    document.getElementById('qr-eq-status').innerHTML = 
        '<div class="alert alert-' + type + '"><i class="bi bi-info-circle"></i> ' + 
        message + '</div>';
}

// Equipment Borrowing
async function scanEquipment(scanType, tagId) {
    const statusElement = scanType === 'nfc' ? 'nfc-eq-status' : 'qr-eq-status';
    const updateStatus = scanType === 'nfc' ? updateNFCEQStatus : updateQREQStatus;
    
    updateStatus('Processing...', 'info');
    
    try {
        const response = await fetch('/borrow/api/scan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + localStorage.getItem('access_token')
            },
            body: JSON.stringify({
                scan_type: scanType,
                tag_id: tagId
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            updateStatus('Success! ' + data.message, 'success');
            addToScannedList(data.equipment);
            
            setTimeout(() => {
                updateStatus('Ready for next scan', 'info');
            }, 2000);
        } else {
            updateStatus('Error: ' + data.error, 'danger');
        }
    } catch (error) {
        updateStatus('Error: ' + error.message, 'danger');
    }
}

function addToScannedList(equipment) {
    const list = document.getElementById('scanned-list');
    const item = document.createElement('div');
    item.className = 'list-group-item';
    item.innerHTML = `
        <div class="d-flex justify-content-between align-items-start">
            <div>
                <h6 class="mb-0">${equipment.name}</h6>
                <small class="text-muted">${equipment.equipment_type}</small>
                <br>
                <small>Serial: ${equipment.serial_number || 'N/A'}</small>
            </div>
            <span class="badge bg-success">Borrowed</span>
        </div>
    `;
    
    if (list.querySelector('.text-muted')) {
        list.innerHTML = '';
    }
    list.appendChild(item);
}

// Tab Change Handlers
document.getElementById('qr-eq-tab').addEventListener('shown.bs.tab', function () {
    document.getElementById('start-qr-eq').style.display = 'inline-block';
    document.getElementById('stop-qr-eq').style.display = 'none';
    updateQREQStatus('Ready to scan QR code', 'info');
});
</script>
{% endblock %}
```

### Step 3: Create Combined Link Tag Template

Create `app/templates/auth/link_tag.html`:

```html
{% extends "base.html" %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-8">
        <div class="card">
            <div class="card-body">
                <h1 class="mb-4">Link Identification Tag to Your Account</h1>
                
                <!-- Tab Navigation -->
                <ul class="nav nav-tabs mb-4" role="tablist">
                    <li class="nav-item" role="presentation">
                        <button class="nav-link active" id="nfc-link-tab" data-bs-toggle="tab" 
                                data-bs-target="#nfc-link-content" type="button">
                            <i class="bi bi-wifi"></i> NFC Tag
                        </button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="qr-link-tab" data-bs-toggle="tab" 
                                data-bs-target="#qr-link-content" type="button">
                            <i class="bi bi-qr-code"></i> QR Code
                        </button>
                    </li>
                </ul>
                
                <div class="tab-content">
                    <!-- NFC Link Tab -->
                    <div class="tab-pane fade show active" id="nfc-link-content" role="tabpanel">
                        <form method="POST">
                            <input type="hidden" name="tag_type" value="nfc">
                            
                            <div class="mb-3">
                                <label for="nfc_tag_id" class="form-label">NFC Tag ID</label>
                                <input type="text" class="form-control" id="nfc_tag_id" name="tag_id" 
                                       placeholder="Scan NFC tag or enter ID manually" required>
                                <small class="form-text text-muted">
                                    Tap your NFC tag to your device or enter the tag ID
                                </small>
                            </div>
                            
                            <div class="d-flex gap-2">
                                <button type="button" class="btn btn-secondary" id="scan-nfc-link">
                                    <i class="bi bi-wifi"></i> Scan Tag
                                </button>
                                <button type="submit" class="btn btn-primary">Link NFC Tag</button>
                            </div>
                        </form>
                    </div>
                    
                    <!-- QR Link Tab -->
                    <div class="tab-pane fade" id="qr-link-content" role="tabpanel">
                        <form method="POST">
                            <input type="hidden" name="tag_type" value="qr">
                            
                            <div class="mb-3">
                                <label for="qr_code_id" class="form-label">QR Code ID</label>
                                <input type="text" class="form-control" id="qr_code_id" name="tag_id" 
                                       placeholder="Scan QR code or enter ID manually" required>
                                <small class="form-text text-muted">
                                    Scan your QR code or enter the code ID
                                </small>
                            </div>
                            
                            <div id="qr-link-reader" style="max-width: 100%; display: none;"></div>
                            
                            <div class="d-flex gap-2">
                                <button type="button" class="btn btn-secondary" id="scan-qr-link">
                                    <i class="bi bi-camera"></i> Scan QR Code
                                </button>
                                <button type="button" class="btn btn-danger" id="stop-qr-link" style="display: none;">
                                    Stop Camera
                                </button>
                                <button type="submit" class="btn btn-primary">Link QR Code</button>
                            </div>
                        </form>
                    </div>
                </div>
                
                <hr class="my-4">
                
                <a href="{{ url_for('main.dashboard') }}" class="btn btn-outline-secondary">Back to Dashboard</a>
            </div>
        </div>
    </div>
</div>

<!-- Include QR Code Library -->
<script src="https://cdn.jsdelivr.net/npm/html5-qrcode@2.3.4/minified/html5-qrcode.min.js"></script>

<script>
let ndefReader = null;
let qrLinkScanner = null;

document.getElementById('scan-nfc-link').addEventListener('click', scanNFCLink);
document.getElementById('scan-qr-link').addEventListener('click', startQRLinkScan);
document.getElementById('stop-qr-link').addEventListener('click', stopQRLinkScan);

// NFC Linking
async function scanNFCLink() {
    if (!('NDEFReader' in window)) {
        alert('NFC not supported on this device');
        return;
    }
    
    try {
        ndefReader = new NDEFReader();
        await ndefReader.scan();
        
        ndefReader.addEventListener('reading', (event) => {
            const tagId = extractNFCTagId(event);
            document.getElementById('nfc_tag_id').value = tagId;
        });
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

function extractNFCTagId(event) {
    if (event.serialNumber) {
        return event.serialNumber;
    }
    const decoder = new TextDecoder();
    for (const record of event.message.records) {
        if (record.recordType === 'text') {
            return decoder.decode(record.data);
        }
    }
    return 'unknown';
}

// QR Linking
function startQRLinkScan() {
    document.getElementById('qr-link-reader').style.display = 'block';
    document.getElementById('scan-qr-link').style.display = 'none';
    document.getElementById('stop-qr-link').style.display = 'inline-block';
    
    qrLinkScanner = new Html5Qrcode("qr-link-reader");
    
    qrLinkScanner.start(
        { facingMode: "environment" },
        { fps: 10, qrbox: { width: 250, height: 250 } },
        (decodedText) => {
            document.getElementById('qr_code_id').value = decodedText;
            stopQRLinkScan();
        },
        (errorMessage) => {}
    );
}

function stopQRLinkScan() {
    if (qrLinkScanner) {
        qrLinkScanner.stop().then(() => {
            document.getElementById('qr-link-reader').style.display = 'none';
            document.getElementById('scan-qr-link').style.display = 'inline-block';
            document.getElementById('stop-qr-link').style.display = 'none';
        });
    }
}
</script>
{% endblock %}
```

---

## 4. DATABASE MIGRATION

Create migration file `migrations/versions/add_nfc_qr_tags.py`:

```python
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Users table
    op.add_column('users', sa.Column('nfc_tag_id', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('qr_code_id', sa.String(255), nullable=True))
    op.create_unique_constraint('uq_users_nfc_tag_id', 'users', ['nfc_tag_id'])
    op.create_unique_constraint('uq_users_qr_code_id', 'users', ['qr_code_id'])
    op.create_index('ix_users_nfc_tag_id', 'users', ['nfc_tag_id'])
    op.create_index('ix_users_qr_code_id', 'users', ['qr_code_id'])
    
    # Equipment table
    op.add_column('equipment', sa.Column('nfc_tag_id', sa.String(255), nullable=True))
    op.add_column('equipment', sa.Column('qr_code_id', sa.String(255), nullable=True))
    op.add_column('equipment', sa.Column('qr_code_image', sa.String(255), nullable=True))
    op.create_unique_constraint('uq_equipment_nfc_tag_id', 'equipment', ['nfc_tag_id'])
    op.create_unique_constraint('uq_equipment_qr_code_id', 'equipment', ['qr_code_id'])
    op.create_index('ix_equipment_nfc_tag_id', 'equipment', ['nfc_tag_id'])
    op.create_index('ix_equipment_qr_code_id', 'equipment', ['qr_code_id'])

def downgrade():
    op.drop_index('ix_equipment_qr_code_id', table_name='equipment')
    op.drop_index('ix_equipment_nfc_tag_id', table_name='equipment')
    op.drop_constraint('uq_equipment_qr_code_id', 'equipment', type_='unique')
    op.drop_constraint('uq_equipment_nfc_tag_id', 'equipment', type_='unique')
    op.drop_column('equipment', 'qr_code_image')
    op.drop_column('equipment', 'qr_code_id')
    op.drop_column('equipment', 'nfc_tag_id')
    
    op.drop_index('ix_users_qr_code_id', table_name='users')
    op.drop_index('ix_users_nfc_tag_id', table_name='users')
    op.drop_constraint('uq_users_qr_code_id', 'users', type_='unique')
    op.drop_constraint('uq_users_nfc_tag_id', 'users', type_='unique')
    op.drop_column('users', 'qr_code_id')
    op.drop_column('users', 'nfc_tag_id')
```

Run migration:
```bash
flask db upgrade
```

---

## 5. NAVIGATION: Update Base Template

Update `app/templates/base.html`:

```html
<nav class="navbar navbar-expand-lg navbar-dark bg-dark">
    <div class="container-fluid">
        <a class="navbar-brand" href="{{ url_for('main.dashboard') }}">
            <i class="bi bi-box-seam"></i> Equipment Management
        </a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
            <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
            <ul class="navbar-nav ms-auto">
                <li class="nav-item dropdown">
                    <a class="nav-link dropdown-toggle" href="#" id="scannerDropdown" role="button" data-bs-toggle="dropdown">
                        <i class="bi bi-wifi"></i> <i class="bi bi-qr-code"></i> Scanner
                    </a>
                    <ul class="dropdown-menu" aria-labelledby="scannerDropdown">
                        <li><a class="dropdown-item" href="{{ url_for('borrow.scanner') }}">
                            <i class="bi bi-wifi"></i> NFC/QR Scanner
                        </a></li>
                        <li><a class="dropdown-item" href="{{ url_for('auth.smart_login') }}">
                            <i class="bi bi-door-open"></i> Smart Login
                        </a></li>
                        <li><a class="dropdown-item" href="{{ url_for('auth.link_tag') }}">
                            <i class="bi bi-link"></i> Link Tag
                        </a></li>
                    </ul>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="{{ url_for('equipment.list_equipment') }}">
                        <i class="bi bi-list"></i> Equipment
                    </a>
                </li>
            </ul>
        </div>
    </div>
</nav>
```

---

## 6. SETUP INSTRUCTIONS

### For USB NFC Reader:

1. **Install dependencies:**
   ```bash
   pip install nfcpy
   ```

2. **Connect USB NFC reader to computer**

3. **Test connection:**
   ```python
   import nfc
   clf = nfc.clf.ContactlessFrontend('usb')
   ```

### For Web NFC (Mobile):

1. **Requirements:**
   - Android 11+ or iOS 15+
   - Chrome 89+ or Edge 89+
   - Secure HTTPS connection required

2. **Enable Web NFC API on Android:**
   - Go to `chrome://flags`
   - Search "NFC"
   - Enable the flag

### For QR Code Scanner (Browser):

1. **No installation needed** - Uses `html5-qrcode` library (CDN)

2. **Camera access required** (browser will prompt permission)

---

## 7. ADMIN PANEL: Assign Tags

Create `app/templates/admin/assign_tags.html`:

```html
{% extends "base.html" %}

{% block content %}
<h1 class="mb-4">Assign Identification Tags</h1>

<div class="row">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5><i class="bi bi-wifi"></i> Assign NFC Tags</h5>
            </div>
            <div class="card-body">
                <div class="mb-3">
                    <h6>User NFC Tag</h6>
                    <form method="POST" action="{{ url_for('admin.assign_user_nfc') }}">
                        <div class="mb-2">
                            <select class="form-select" name="user_id" required>
                                <option value="">Select User</option>
                                {% for user in users %}
                                <option value="{{ user.id }}">{{ user.name }}</option>
                                {% endfor %}
                            </select>
                        </div>
                        <div class="mb-2">
                            <input type="text" class="form-control" name="nfc_tag_id" 
                                   placeholder="NFC Tag ID" required>
                        </div>
                        <button type="submit" class="btn btn-sm btn-primary">Assign</button>
                    </form>
                </div>
                
                <hr>
                
                <div class="mb-3">
                    <h6>Equipment NFC Tag</h6>
                    <form method="POST" action="{{ url_for('admin.assign_equipment_nfc') }}">
                        <div class="mb-2">
                            <select class="form-select" name="equipment_id" required>
                                <option value="">Select Equipment</option>
                                {% for equipment in equipment_list %}
                                <option value="{{ equipment.id }}">{{ equipment.name }}</option>
                                {% endfor %}
                            </select>
                        </div>
                        <div class="mb-2">
                            <input type="text" class="form-control" name="nfc_tag_id" 
                                   placeholder="NFC Tag ID" required>
                        </div>
                        <button type="submit" class="btn btn-sm btn-primary">Assign</button>
                    </form>
                </div>
            </div>
        </div>
    </div>
    
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5><i class="bi bi-qr-code"></i> Assign QR Codes</h5>
            </div>
            <div class="card-body">
                <div class="mb-3">
                    <h6>User QR Code</h6>
                    <form method="POST" action="{{ url_for('admin.assign_user_qr') }}">
                        <div class="mb-2">
                            <select class="form-select" name="user_id" required>
                                <option value="">Select User</option>
                                {% for user in users %}
                                <option value="{{ user.id }}">{{ user.name }}</option>
                                {% endfor %}
                            </select>
                        </div>
                        <div class="mb-2">
                            <input type="text" class="form-control" name="qr_code_id" 
                                   placeholder="QR Code ID" required>
                        </div>
                        <button type="submit" class="btn btn-sm btn-primary">Assign</button>
                    </form>
                </div>
                
                <hr>
                
                <div class="mb-3">
                    <h6>Equipment QR Code</h6>
                    <form method="POST" action="{{ url_for('admin.assign_equipment_qr') }}">
                        <div class="mb-2">
                            <select class="form-select" name="equipment_id" required>
                                <option value="">Select Equipment</option>
                                {% for equipment in equipment_list %}
                                <option value="{{ equipment.id }}">{{ equipment.name }}</option>
                                {% endfor %}
                            </select>
                        </div>
                        <div class="mb-2">
                            <input type="text" class="form-control" name="qr_code_id" 
                                   placeholder="QR Code ID" required>
                        </div>
                        <button type="submit" class="btn btn-sm btn-primary">Generate & Assign</button>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

---

## 8. COMPARISON: NFC vs QR Code

| Feature | NFC | QR Code |
|---------|-----|---------|
| **Range** | Close proximity (10cm) | Line-of-sight (30cm) |
| **Speed** | Instantaneous | Requires camera/processing |
| **Hardware** | NFC-enabled phone/reader | Any camera device |
| **Security** | Medium-High | Low (text-based) |
| **Cost per tag** | $0.50-$2.00 | $0.10-$0.50 |
| **User Experience** | Tap & go | Point & scan |
| **Durability** | Robust (embedded) | Fragile (printed) |
| **Data Capacity** | Large | Limited (URL only) |
| **Writing** | Can write data | Read-only |
| **Mobile Support** | Recent Android/iOS | All devices |

---

## 9. SUMMARY OF CHANGES

✅ **Dual Authentication:** NFC tag OR QR code for login  
✅ **Dual Equipment Recognition:** NFC tag OR QR code on equipment  
✅ **Database:** Added `nfc_tag_id` and `qr_code_id` columns  
✅ **Frontend:** Combined scanning pages with tab interface  
✅ **Backend:** Unified API endpoints for both scanners  
✅ **Admin Panel:** Tag assignment for both technologies  
✅ **Security:** Unique identifiers per user/equipment  
✅ **Flexibility:** Use either technology based on device capability  

Your system now supports both NFC and QR code scanning!
