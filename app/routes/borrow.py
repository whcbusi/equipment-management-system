from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Equipment, BorrowRecord, User, EquipmentStatus
from app import db
from datetime import datetime, timedelta

borrow_bp = Blueprint('borrow', __name__, url_prefix='/borrow')

@borrow_bp.route('/scanner')
@jwt_required(optional=True)
def scanner():
    user_id = get_jwt_identity()
    if not user_id:
        return redirect(url_for('auth.login'))
    
    return render_template('borrow/scanner.html')

@borrow_bp.route('/history')
@jwt_required(optional=True)
def history():
    user_id = get_jwt_identity()
    if not user_id:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(user_id)
    page = request.args.get('page', 1, type=int)
    borrow_records = BorrowRecord.query.filter_by(user_id=user_id).paginate(
        page=page, per_page=10
    )
    
    return render_template('borrow/history.html', 
                         user=user,
                         borrow_records=borrow_records)

@borrow_bp.route('/my-items')
@jwt_required(optional=True)
def my_items():
    user_id = get_jwt_identity()
    if not user_id:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(user_id)
    borrowed_items = BorrowRecord.query.filter_by(
        user_id=user_id,
        returned_at=None
    ).all()
    
    return render_template('borrow/my_items.html',
                         user=user,
                         borrowed_items=borrowed_items)

# API endpoints
@borrow_bp.route('/api/scan', methods=['POST'])
@jwt_required()
def api_scan_qr():
    user_id = get_jwt_identity()
    data = request.get_json()
    qr_code = data.get('qr_code')
    
    # Find equipment by QR code
    equipment = Equipment.query.filter_by(qr_code=qr_code).first()
    
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

@borrow_bp.route('/api/borrow/<int:borrow_id>/return', methods=['POST'])
@jwt_required()
def api_return_equipment(borrow_id):
    user_id = get_jwt_identity()
    borrow_record = BorrowRecord.query.get_or_404(borrow_id)
    
    # Verify ownership
    if borrow_record.user_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Check if already returned
    if borrow_record.returned_at:
        return jsonify({'error': 'Item already returned'}), 400
    
    borrow_record.returned_at = datetime.utcnow()
    borrow_record.equipment.status = EquipmentStatus.AVAILABLE
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Successfully returned {borrow_record.equipment.name}'
    })

@borrow_bp.route('/api/history')
@jwt_required()
def api_get_history():
    user_id = get_jwt_identity()
    borrow_records = BorrowRecord.query.filter_by(user_id=user_id).all()
    return jsonify([br.to_dict() for br in borrow_records])
