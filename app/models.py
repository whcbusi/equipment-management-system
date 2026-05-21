from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import enum

class UserRole(enum.Enum):
    ADMIN = 'admin'
    USER = 'user'

class EquipmentStatus(enum.Enum):
    AVAILABLE = 'available'
    BORROWED = 'borrowed'
    MAINTENANCE = 'maintenance'
    RETIRED = 'retired'

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(120), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
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
            'created_at': self.created_at.isoformat()
        }

class EquipmentType(db.Model):
    __tablename__ = 'equipment_types'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    equipment = db.relationship('Equipment', backref='equipment_type', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'created_at': self.created_at.isoformat()
        }

class Equipment(db.Model):
    __tablename__ = 'equipment'
    
    id = db.Column(db.Integer, primary_key=True)
    equipment_type_id = db.Column(db.Integer, db.ForeignKey('equipment_types.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    serial_number = db.Column(db.String(120), unique=True, nullable=True, index=True)
    barcode = db.Column(db.String(120), unique=True, nullable=True, index=True)
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
            'status': self.status.value,
            'location': self.location,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class BorrowRecord(db.Model):
    __tablename__ = 'borrow_records'
    
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    borrowed_at = db.Column(db.DateTime, default=datetime.utcnow)
    returned_at = db.Column(db.DateTime, nullable=True)
    expected_return = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'equipment_id': self.equipment_id,
            'equipment_name': self.equipment.name if self.equipment else None,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else None,
            'borrowed_at': self.borrowed_at.isoformat(),
            'returned_at': self.returned_at.isoformat() if self.returned_at else None,
            'expected_return': self.expected_return.isoformat() if self.expected_return else None,
            'notes': self.notes
        }
