from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User, Equipment, EquipmentType, BorrowRecord, UserRole, EquipmentStatus
from app.utils import generate_qr_code
from app import db
from app.routes.auth import admin_required
from datetime import datetime, timedelta
import csv
from io import StringIO
from flask import make_response

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    # Get statistics
    total_users = User.query.count()
    total_equipment = Equipment.query.count()
    total_borrows = BorrowRecord.query.count()
    active_borrows = BorrowRecord.query.filter_by(returned_at=None).count()
    
    # Equipment by status
    status_stats = {}
    for status in EquipmentStatus:
        status_stats[status.value] = Equipment.query.filter_by(status=status).count()
    
    # Recent activity
    recent_borrows = BorrowRecord.query.order_by(
        BorrowRecord.borrowed_at.desc()
    ).limit(10).all()
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_equipment=total_equipment,
                         total_borrows=total_borrows,
                         active_borrows=active_borrows,
                         status_stats=status_stats,
                         recent_borrows=recent_borrows)

@admin_bp.route('/users')
@admin_required
def users():
    page = request.args.get('page', 1, type=int)
    users = User.query.paginate(page=page, per_page=10)
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.name = request.form.get('name')
        user.department = request.form.get('department')
        user.role = request.form.get('role')
        user.is_active = 'is_active' in request.form
        
        db.session.commit()
        flash(f'User {user.name} updated successfully', 'success')
        return redirect(url_for('admin.users'))
    
    roles = [role.value for role in UserRole]
    return render_template('admin/edit_user.html', user=user, roles=roles)

@admin_bp.route('/equipment-types')
@admin_required
def equipment_types():
    equipment_types = EquipmentType.query.all()
    return render_template('admin/equipment_types.html', equipment_types=equipment_types)

@admin_bp.route('/equipment-types/add', methods=['GET', 'POST'])
@admin_required
def add_equipment_type():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        category = request.form.get('category')
        
        if EquipmentType.query.filter_by(name=name).first():
            flash('Equipment type already exists', 'danger')
            return redirect(url_for('admin.equipment_types'))
        
        equipment_type = EquipmentType(
            name=name,
            description=description,
            category=category
        )
        db.session.add(equipment_type)
        db.session.commit()
        flash(f'Equipment type "{name}" added successfully', 'success')
        return redirect(url_for('admin.equipment_types'))
    
    return render_template('admin/add_equipment_type.html')

@admin_bp.route('/reports')
@admin_required
def reports():
    # Get statistics for report
    total_borrows = BorrowRecord.query.count()
    active_borrows = BorrowRecord.query.filter_by(returned_at=None).count()
    
    # Most borrowed items
    most_borrowed = db.session.query(
        Equipment.name,
        db.func.count(BorrowRecord.id).label('count')
    ).join(BorrowRecord).group_by(Equipment.id).order_by(
        db.func.count(BorrowRecord.id).desc()
    ).limit(10).all()
    
    # Users with most borrows
    top_users = db.session.query(
        User.name,
        User.email,
        db.func.count(BorrowRecord.id).label('count')
    ).join(BorrowRecord).group_by(User.id).order_by(
        db.func.count(BorrowRecord.id).desc()
    ).limit(10).all()
    
    # Overdue items
    overdue_items = BorrowRecord.query.filter(
        BorrowRecord.returned_at == None,
        BorrowRecord.expected_return < datetime.utcnow()
    ).all()
    
    return render_template('admin/reports.html',
                         total_borrows=total_borrows,
                         active_borrows=active_borrows,
                         most_borrowed=most_borrowed,
                         top_users=top_users,
                         overdue_items=overdue_items)

@admin_bp.route('/reports/export')
@admin_required
def export_reports():
    # Get all borrow records
    borrow_records = BorrowRecord.query.all()
    
    # Create CSV
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Equipment', 'User', 'Borrowed At', 'Returned At', 'Status'])
    
    for record in borrow_records:
        status = 'Returned' if record.returned_at else 'Active'
        writer.writerow([
            record.equipment.name,
            record.user.name,
            record.borrowed_at.strftime('%Y-%m-%d %H:%M:%S'),
            record.returned_at.strftime('%Y-%m-%d %H:%M:%S') if record.returned_at else 'N/A',
            status
        ])
    
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=borrow_records.csv"
    response.headers["Content-Type"] = "text/csv"
    return response
