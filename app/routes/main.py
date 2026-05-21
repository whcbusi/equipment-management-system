from flask import Blueprint, render_template, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User, Equipment, BorrowRecord, EquipmentStatus
from app import db
from datetime import datetime, timedelta

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return redirect(url_for('main.dashboard'))

@main_bp.route('/dashboard')
@jwt_required(optional=True)
def dashboard():
    user_id = get_jwt_identity()
    
    if not user_id:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('auth.login'))
    
    # Get statistics
    total_equipment = Equipment.query.count()
    available_equipment = Equipment.query.filter_by(status=EquipmentStatus.AVAILABLE).count()
    borrowed_equipment = Equipment.query.filter_by(status=EquipmentStatus.BORROWED).count()
    
    # Get user's active borrows
    user_active_borrows = BorrowRecord.query.filter_by(
        user_id=user_id,
        returned_at=None
    ).all()
    
    # Get recent activity
    recent_borrows = BorrowRecord.query.order_by(
        BorrowRecord.borrowed_at.desc()
    ).limit(5).all()
    
    return render_template('dashboard.html',
                         user=user,
                         total_equipment=total_equipment,
                         available_equipment=available_equipment,
                         borrowed_equipment=borrowed_equipment,
                         user_active_borrows=user_active_borrows,
                         recent_borrows=recent_borrows)
