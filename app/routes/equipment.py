from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Equipment, EquipmentType, User, UserRole, EquipmentStatus
from app.utils import generate_qr_code, generate_qr_code_file
from app import db
from app.routes.auth import admin_required

equipment_bp = Blueprint('equipment', __name__, url_prefix='/equipment')

@equipment_bp.route('/')
@jwt_required(optional=True)
def list_equipment():
    user_id = get_jwt_identity()
    if not user_id:
        return redirect(url_for('auth.login'))
    
    page = request.args.get('page', 1, type=int)
    equipment = Equipment.query.paginate(page=page, per_page=10)
    
    return render_template('equipment/list.html', equipment=equipment)

@equipment_bp.route('/<int:equipment_id>')
@jwt_required(optional=True)
def detail(equipment_id):
    user_id = get_jwt_identity()
    if not user_id:
        return redirect(url_for('auth.login'))
    
    equipment = Equipment.query.get_or_404(equipment_id)
    borrow_history = equipment.borrow_records.order_by(
        equipment.borrow_records.model.borrowed_at.desc()
    ).limit(10).all()
    
    return render_template('equipment/detail.html', 
                         equipment=equipment,
                         borrow_history=borrow_history)

@equipment_bp.route('/add', methods=['GET', 'POST'])
@admin_required
def add_equipment():
    if request.method == 'POST':
        equipment_type_id = request.form.get('equipment_type_id')
        name = request.form.get('name')
        serial_number = request.form.get('serial_number')
        location = request.form.get('location')
        notes = request.form.get('notes')
        
        # Generate QR code
        qr_data = f"EQP-{serial_number}" if serial_number else f"EQP-{name}"
        qr_code = generate_qr_code(qr_data)
        
        equipment = Equipment(
            equipment_type_id=equipment_type_id,
            name=name,
            serial_number=serial_number,
            qr_code=qr_code,
            location=location,
            notes=notes
        )
        
        db.session.add(equipment)
        db.session.commit()
        
        flash(f'Equipment "{name}" added successfully', 'success')
        return redirect(url_for('equipment.list_equipment'))
    
    equipment_types = EquipmentType.query.all()
    return render_template('equipment/add.html', equipment_types=equipment_types)

@equipment_bp.route('/<int:equipment_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_equipment(equipment_id):
    equipment = Equipment.query.get_or_404(equipment_id)
    
    if request.method == 'POST':
        equipment.equipment_type_id = request.form.get('equipment_type_id')
        equipment.name = request.form.get('name')
        equipment.serial_number = request.form.get('serial_number')
        equipment.location = request.form.get('location')
        equipment.notes = request.form.get('notes')
        equipment.status = request.form.get('status')
        
        db.session.commit()
        flash(f'Equipment "{equipment.name}" updated successfully', 'success')
        return redirect(url_for('equipment.detail', equipment_id=equipment_id))
    
    equipment_types = EquipmentType.query.all()
    statuses = [status.value for status in EquipmentStatus]
    return render_template('equipment/edit.html', 
                         equipment=equipment,
                         equipment_types=equipment_types,
                         statuses=statuses)

@equipment_bp.route('/<int:equipment_id>/delete', methods=['POST'])
@admin_required
def delete_equipment(equipment_id):
    equipment = Equipment.query.get_or_404(equipment_id)
    name = equipment.name
    db.session.delete(equipment)
    db.session.commit()
    flash(f'Equipment "{name}" deleted successfully', 'success')
    return redirect(url_for('equipment.list_equipment'))

# API endpoints
@equipment_bp.route('/api/equipment')
@jwt_required(optional=True)
def api_list_equipment():
    user_id = get_jwt_identity()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    equipment = Equipment.query.all()
    return jsonify([e.to_dict() for e in equipment])

@equipment_bp.route('/api/equipment/<int:equipment_id>')
@jwt_required(optional=True)
def api_get_equipment(equipment_id):
    user_id = get_jwt_identity()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    equipment = Equipment.query.get_or_404(equipment_id)
    return jsonify(equipment.to_dict())
