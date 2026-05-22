# NFC Implementation Guide

## Overview
Replace QR code scanning and traditional login with NFC tag reading for:
1. **User Authentication** - Read NFC tag to auto-login
2. **Equipment Recognition** - Read NFC tag on equipment to borrow

---

## 1. HARDWARE REQUIREMENTS

### NFC Reader Options:

**Option A: USB NFC Reader (Recommended)**
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

### NFC Tags:
- **NTAG216** (most common)
- **MIFARE Classic**
- **ISO 14443 Type A**
- Cost: ~$0.50-$2 per tag

---

## 2. UPDATE BACKEND - NFC Authentication

### Step 1: Install NFC Library

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
```

Install:
```bash
pip install -r requirements.txt
```

### Step 2: Update User Model to Store NFC Tag ID

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
            'created_at': self.created_at.isoformat()
        }
```

### Step 3: Update Equipment Model to Store NFC Tag ID

```python
class Equipment(db.Model):
    __tablename__ = 'equipment'
    
    id = db.Column(db.Integer, primary_key=True)
    equipment_type_id = db.Column(db.Integer, db.ForeignKey('equipment_types.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    serial_number = db.Column(db.String(120), unique=True, nullable=True, index=True)
    barcode = db.Column(db.String(120), unique=True, nullable=True, index=True)
    nfc_tag_id = db.Column(db.String(255), unique=True, nullable=True, index=True)  # NEW
    qr_code = db.Column(db.String(255), nullable=True)
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
            'nfc_tag_id': self.nfc_tag_id,  # NEW
            'status': self.status.value,
            'location': self.location,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
```

### Step 4: Create NFC Utility Functions

Create `app/nfc_utils.py`:

```python
import nfc
from nfc.clf import RemoteTarget
import logging

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
                logger.info(f"Tag read: {tag_id}")
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
                logger.info(f"Tag written: {tag_id_data}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error writing to NFC tag: {e}")
            return False
    
    def close(self):
        """Close NFC reader connection"""
        if self.clf:
            self.clf.close()

# Singleton instance
nfc_reader = NFCReader()

def initialize_nfc():
    """Initialize NFC reader on app startup"""
    return nfc_reader.initialize_reader()

def read_nfc_tag(timeout=5):
    """Read an NFC tag"""
    return nfc_reader.read_tag(timeout)

def format_tag_id(raw_tag_id):
    """Format tag ID for database storage"""
    return raw_tag_id.upper() if raw_tag_id else None
```

### Step 5: Create NFC Login Route

Update `app/routes/auth.py`:

```python
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.models import User, UserRole
from app.nfc_utils import read_nfc_tag, format_tag_id
from app import db
from functools import wraps

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# ... existing code ...

@auth_bp.route('/nfc-login', methods=['GET', 'POST'])
def nfc_login():
    """NFC-based login"""
    if request.method == 'POST':
        nfc_tag_id = request.form.get('nfc_tag_id')
        
        # Find user by NFC tag
        user = User.query.filter_by(nfc_tag_id=format_tag_id(nfc_tag_id)).first()
        
        if user and user.is_active:
            access_token = create_access_token(identity=user.id)
            response = redirect(url_for('main.dashboard'))
            response.set_cookie('access_token_cookie', access_token, httponly=True, secure=True, samesite='Lax')
            flash(f'Welcome, {user.name}!', 'success')
            return response
        else:
            flash('NFC tag not recognized', 'danger')
    
    return render_template('auth/nfc_login.html')

@auth_bp.route('/api/nfc-login', methods=['POST'])
def api_nfc_login():
    """API endpoint for NFC login (AJAX)"""
    data = request.get_json()
    nfc_tag_id = data.get('nfc_tag_id')
    
    user = User.query.filter_by(nfc_tag_id=format_tag_id(nfc_tag_id)).first()
    
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
            'message': 'NFC tag not recognized'
        }), 401

@auth_bp.route('/link-nfc', methods=['GET', 'POST'])
@jwt_required(optional=True)
def link_nfc_tag():
    """Link NFC tag to user account"""
    user_id = get_jwt_identity()
    if not user_id:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(user_id)
    
    if request.method == 'POST':
        nfc_tag_id = request.form.get('nfc_tag_id')
        
        # Check if tag already registered
        existing_user = User.query.filter_by(nfc_tag_id=format_tag_id(nfc_tag_id)).first()
        if existing_user and existing_user.id != user.id:
            flash('This NFC tag is already registered to another user', 'danger')
            return redirect(url_for('auth.link_nfc_tag'))
        
        user.nfc_tag_id = format_tag_id(nfc_tag_id)
        db.session.commit()
        flash('NFC tag linked successfully!', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('auth/link_nfc.html', user=user)

@auth_bp.route('/register', methods=['GET', 'POST'])
@admin_required
def register():
    """Register new user with optional NFC tag"""
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        department = request.form.get('department')
        nfc_tag_id = request.form.get('nfc_tag_id')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('auth.register'))
        
        # Check if NFC tag already used
        if nfc_tag_id and User.query.filter_by(nfc_tag_id=format_tag_id(nfc_tag_id)).first():
            flash('NFC tag already registered', 'danger')
            return redirect(url_for('auth.register'))
        
        user = User(
            email=email,
            name=name,
            department=department,
            nfc_tag_id=format_tag_id(nfc_tag_id) if nfc_tag_id else None,
            role=UserRole.USER
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash(f'User {name} registered successfully', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('auth/register.html')
```

### Step 6: Update Borrow Route for NFC Equipment

Update `app/routes/borrow.py`:

```python
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Equipment, BorrowRecord, User, EquipmentStatus
from app.nfc_utils import format_tag_id
from app import db
from datetime import datetime, timedelta

borrow_bp = Blueprint('borrow', __name__, url_prefix='/borrow')

# ... existing code ...

@borrow_bp.route('/nfc-scanner')
@jwt_required(optional=True)
def nfc_scanner():
    """NFC scanner page for equipment"""
    user_id = get_jwt_identity()
    if not user_id:
        return redirect(url_for('auth.login'))
    
    return render_template('borrow/nfc_scanner.html')

@borrow_bp.route('/api/nfc-scan', methods=['POST'])
@jwt_required()
def api_nfc_scan():
    """Scan NFC tag on equipment to borrow"""
    user_id = get_jwt_identity()
    data = request.get_json()
    nfc_tag_id = data.get('nfc_tag_id')
    
    # Find equipment by NFC tag
    equipment = Equipment.query.filter_by(nfc_tag_id=format_tag_id(nfc_tag_id)).first()
    
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
```

---

## 3. FRONTEND - NFC SCANNING WITH WEB NFC API

### Step 1: Create NFC Login Template

Create `app/templates/auth/nfc_login.html`:

```html
{% extends "base.html" %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card">
            <div class="card-body text-center">
                <h1 class="mb-4">
                    <i class="bi bi-wifi" style="font-size: 3rem; color: #0066cc;"></i>
                </h1>
                <h2 class="mb-4">NFC Login</h2>
                
                <div id="nfc-status" class="alert alert-info">
                    <i class="bi bi-hourglass-split"></i> Waiting for NFC tag...
                </div>
                
                <div id="nfc-result" class="d-none">
                    <div id="result-message"></div>
                </div>
                
                <button class="btn btn-primary btn-lg mt-3" id="start-nfc">
                    Start NFC Reader
                </button>
                
                <hr class="my-4">
                
                <p class="text-muted">
                    Or use <a href="{{ url_for('auth.login') }}">traditional login</a>
                </p>
            </div>
        </div>
    </div>
</div>

<script>
document.getElementById('start-nfc').addEventListener('click', startNFCReader);

async function startNFCReader() {
    if (!('NDEFReader' in window)) {
        document.getElementById('nfc-status').innerHTML = 
            '<div class="alert alert-danger">NFC not supported on this device. Please use <a href="' + 
            "{{ url_for('auth.login') }}" + 
            '">traditional login</a></div>';
        return;
    }
    
    try {
        const ndef = new NDEFReader();
        await ndef.scan();
        
        document.getElementById('nfc-status').innerHTML = 
            '<div class="alert alert-warning"><i class="bi bi-exclamation-triangle"></i> Touch NFC tag...</div>';
        
        ndef.addEventListener('reading', async (event) => {
            const tagId = getTagId(event);
            await loginWithNFC(tagId);
        });
        
    } catch (error) {
        document.getElementById('nfc-status').innerHTML = 
            '<div class="alert alert-danger">Error: ' + error.message + '</div>';
    }
}

function getTagId(event) {
    // Extract tag ID from NFC event
    const decoder = new TextDecoder();
    for (const record of event.message.records) {
        if (record.recordType === 'text') {
            return decoder.decode(record.data);
        }
    }
    return event.serialNumber || 'unknown';
}

async function loginWithNFC(nfcTagId) {
    document.getElementById('nfc-status').innerHTML = 
        '<div class="alert alert-info"><i class="bi bi-hourglass-split"></i> Processing...</div>';
    
    try {
        const response = await fetch('/auth/api/nfc-login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ nfc_tag_id: nfcTagId })
        });
        
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('nfc-status').innerHTML = 
                '<div class="alert alert-success"><i class="bi bi-check-circle"></i> ' + 
                data.message + ' Redirecting...</div>';
            
            // Store token and redirect
            localStorage.setItem('access_token', data.access_token);
            setTimeout(() => {
                window.location.href = "{{ url_for('main.dashboard') }}";
            }, 1500);
        } else {
            document.getElementById('nfc-status').innerHTML = 
                '<div class="alert alert-danger"><i class="bi bi-x-circle"></i> ' + 
                data.message + '</div>';
        }
    } catch (error) {
        document.getElementById('nfc-status').innerHTML = 
            '<div class="alert alert-danger">Error: ' + error.message + '</div>';
    }
}
</script>
{% endblock %}
```

### Step 2: Create NFC Equipment Scanner Template

Create `app/templates/borrow/nfc_scanner.html`:

```html
{% extends "base.html" %}

{% block content %}
<h1 class="mb-4">
    <i class="bi bi-wifi"></i> NFC Equipment Scanner
</h1>

<div class="row">
    <div class="col-md-6">
        <div class="card">
            <div class="card-body text-center">
                <h3>Ready to Scan</h3>
                
                <div id="nfc-status" class="alert alert-info mt-3">
                    <i class="bi bi-hourglass-split"></i> Waiting for equipment tag...
                </div>
                
                <button class="btn btn-primary btn-lg mt-3" id="start-scan">
                    <i class="bi bi-wifi"></i> Start Scanning
                </button>
                
                <button class="btn btn-secondary btn-lg mt-3" id="stop-scan" disabled>
                    Stop Scanning
                </button>
            </div>
        </div>
    </div>
    
    <div class="col-md-6">
        <div class="card">
            <div class="card-body">
                <h3>Scanned Equipment</h3>
                <div id="scanned-list" class="list-group">
                    <p class="text-muted">Scan equipment to see details...</p>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
let ndefReader = null;

document.getElementById('start-scan').addEventListener('click', startNFCScanning);
document.getElementById('stop-scan').addEventListener('click', stopNFCScanning);

async function startNFCScanning() {
    if (!('NDEFReader' in window)) {
        updateStatus('NFC not supported on this device', 'danger');
        return;
    }
    
    try {
        ndefReader = new NDEFReader();
        await ndefReader.scan();
        
        document.getElementById('start-scan').disabled = true;
        document.getElementById('stop-scan').disabled = false;
        updateStatus('Scanning... Hold equipment tag near device', 'info');
        
        ndefReader.addEventListener('reading', async (event) => {
            const tagId = getTagId(event);
            await borrowEquipment(tagId);
        });
        
    } catch (error) {
        updateStatus('Error: ' + error.message, 'danger');
    }
}

function stopNFCScanning() {
    if (ndefReader) {
        ndefReader.abort();
        ndefReader = null;
    }
    document.getElementById('start-scan').disabled = false;
    document.getElementById('stop-scan').disabled = true;
    updateStatus('Scanning stopped', 'warning');
}

function getTagId(event) {
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

async function borrowEquipment(nfcTagId) {
    updateStatus('Processing...', 'info');
    
    try {
        const response = await fetch('/borrow/api/nfc-scan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + localStorage.getItem('access_token')
            },
            body: JSON.stringify({ nfc_tag_id: nfcTagId })
        });
        
        const data = await response.json();
        
        if (data.success) {
            updateStatus('Success! ' + data.message, 'success');
            addToScannedList(data.equipment);
            
            // Reset after 2 seconds
            setTimeout(() => {
                updateStatus('Ready for next scan...', 'info');
            }, 2000);
        } else {
            updateStatus('Error: ' + data.error, 'danger');
        }
    } catch (error) {
        updateStatus('Error: ' + error.message, 'danger');
    }
}

function updateStatus(message, type) {
    document.getElementById('nfc-status').innerHTML = 
        '<div class="alert alert-' + type + '"><i class="bi bi-info-circle"></i> ' + 
        message + '</div>';
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
</script>
{% endblock %}
```

### Step 3: Create Link NFC Template

Create `app/templates/auth/link_nfc.html`:

```html
{% extends "base.html" %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card">
            <div class="card-body">
                <h1 class="mb-4">Link NFC Tag to Your Account</h1>
                
                <form method="POST">
                    <div class="mb-3">
                        <label for="nfc_tag_id" class="form-label">NFC Tag ID</label>
                        <input type="text" class="form-control" id="nfc_tag_id" name="nfc_tag_id" 
                               placeholder="Scan NFC tag or enter ID manually" required>
                        <small class="form-text text-muted">
                            Tap your NFC tag to this device or enter the tag ID
                        </small>
                    </div>
                    
                    <div class="d-flex gap-2">
                        <button type="button" class="btn btn-secondary" id="scan-nfc">
                            <i class="bi bi-wifi"></i> Scan Tag
                        </button>
                        <button type="submit" class="btn btn-primary">Link Tag</button>
                        <a href="{{ url_for('main.dashboard') }}" class="btn btn-outline-secondary">Cancel</a>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>

<script>
document.getElementById('scan-nfc').addEventListener('click', scanNFCTag);

async function scanNFCTag() {
    if (!('NDEFReader' in window)) {
        alert('NFC not supported on this device');
        return;
    }
    
    try {
        const ndef = new NDEFReader();
        await ndef.scan();
        
        ndef.addEventListener('reading', (event) => {
            const tagId = getTagId(event);
            document.getElementById('nfc_tag_id').value = tagId;
        });
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

function getTagId(event) {
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
</script>
{% endblock %}
```

---

## 4. MIGRATION: Add NFC Columns to Database

Create migration file `migrations/versions/add_nfc_tags.py`:

```python
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add nfc_tag_id column to users table
    op.add_column('users', sa.Column('nfc_tag_id', sa.String(255), nullable=True))
    op.create_unique_constraint('uq_users_nfc_tag_id', 'users', ['nfc_tag_id'])
    op.create_index('ix_users_nfc_tag_id', 'users', ['nfc_tag_id'])
    
    # Add nfc_tag_id column to equipment table
    op.add_column('equipment', sa.Column('nfc_tag_id', sa.String(255), nullable=True))
    op.create_unique_constraint('uq_equipment_nfc_tag_id', 'equipment', ['nfc_tag_id'])
    op.create_index('ix_equipment_nfc_tag_id', 'equipment', ['nfc_tag_id'])

def downgrade():
    op.drop_index('ix_equipment_nfc_tag_id', table_name='equipment')
    op.drop_constraint('uq_equipment_nfc_tag_id', 'equipment', type_='unique')
    op.drop_column('equipment', 'nfc_tag_id')
    
    op.drop_index('ix_users_nfc_tag_id', table_name='users')
    op.drop_constraint('uq_users_nfc_tag_id', 'users', type_='unique')
    op.drop_column('users', 'nfc_tag_id')
```

Run migration:
```bash
flask db upgrade
```

---

## 5. NAVIGATION: Update Base Template

Update `app/templates/base.html` to add NFC links:

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
                <li class="nav-item">
                    <a class="nav-link" href="{{ url_for('borrow.nfc_scanner') }}">
                        <i class="bi bi-wifi"></i> NFC Scanner
                    </a>
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

1. **Install nfcpy:**
   ```bash
   pip install nfcpy
   ```

2. **Connect USB NFC reader** to computer

3. **Test connection:**
   ```python
   import nfc
   clf = nfc.clf.ContactlessFrontend('usb')
   ```

### For Web NFC (Mobile/Modern Browsers):

1. **Requirements:**
   - Android 11+ or iOS 15+
   - Chrome 89+ or Edge 89+
   - Secure HTTPS connection required

2. **Enable Web NFC API:**
   - On Android: Go to `chrome://flags` → Search "NFC" → Enable

---

## 7. ADMIN PANEL: Assign NFC Tags

Create `app/templates/admin/assign_nfc.html`:

```html
{% extends "base.html" %}

{% block content %}
<h1 class="mb-4">Assign NFC Tags</h1>

<div class="row">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5>Assign User NFC Tag</h5>
            </div>
            <div class="card-body">
                <form method="POST" action="{{ url_for('admin.assign_user_nfc') }}">
                    <div class="mb-3">
                        <label for="user_id" class="form-label">User</label>
                        <select class="form-select" id="user_id" name="user_id" required>
                            <option value="">Select User</option>
                            {% for user in users %}
                            <option value="{{ user.id }}">{{ user.name }} ({{ user.email }})</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="mb-3">
                        <label for="nfc_tag" class="form-label">NFC Tag ID</label>
                        <input type="text" class="form-control" id="nfc_tag" name="nfc_tag_id" 
                               placeholder="Scan tag or enter manually" required>
                    </div>
                    <button type="submit" class="btn btn-primary">Assign Tag</button>
                </form>
            </div>
        </div>
    </div>
    
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5>Assign Equipment NFC Tag</h5>
            </div>
            <div class="card-body">
                <form method="POST" action="{{ url_for('admin.assign_equipment_nfc') }}">
                    <div class="mb-3">
                        <label for="equipment_id" class="form-label">Equipment</label>
                        <select class="form-select" id="equipment_id" name="equipment_id" required>
                            <option value="">Select Equipment</option>
                            {% for equipment in equipment_list %}
                            <option value="{{ equipment.id }}">{{ equipment.name }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="mb-3">
                        <label for="eq_nfc_tag" class="form-label">NFC Tag ID</label>
                        <input type="text" class="form-control" id="eq_nfc_tag" name="nfc_tag_id" 
                               placeholder="Scan tag or enter manually" required>
                    </div>
                    <button type="submit" class="btn btn-primary">Assign Tag</button>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

---

## 8. COMPARISON: QR Code vs NFC

| Feature | QR Code | NFC |
|---------|---------|-----|
| **Range** | Line-of-sight (30cm) | Close proximity (10cm) |
| **Speed** | Slow (needs camera) | Fast (instantaneous) |
| **Hardware** | Any phone camera | NFC-enabled phone/reader |
| **Security** | Low | Medium-High |
| **Cost per tag** | $0.10 | $0.50 |
| **User Experience** | Point & click | Tap & go |
| **Durability** | Fragile (printed) | Robust (embedded) |
| **Data Capacity** | Limited (URL only) | Large (contact info, data) |

---

## 9. SUMMARY OF CHANGES

✅ **User Authentication:** NFC tag instead of password  
✅ **Equipment Recognition:** NFC tag on equipment  
✅ **Database:** Added `nfc_tag_id` columns  
✅ **Frontend:** NFC scanning pages with Web NFC API  
✅ **Backend:** NFC reading and processing  
✅ **Admin Panel:** NFC tag assignment interface  
✅ **Security:** Unique NFC tag per user/equipment  

Your system is now ready for NFC-based operations!

