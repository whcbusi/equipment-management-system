from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.models import User, UserRole
from app.scanner_utils import format_tag_id, generate_qr_code, generate_unique_qr_id
from app import db
from functools import wraps

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def admin_required(f):
    @wraps(f)
    @jwt_required(optional=True)
    def decorated_function(*args, **kwargs):
        user_id = get_jwt_identity()
        if not user_id:
            return redirect(url_for('auth.login'))
        user = User.query.get(user_id)
        if not user or user.role != UserRole.ADMIN:
            flash('Admin access required', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password) and user.is_active:
            access_token = create_access_token(identity=user.id)
            response = redirect(url_for('main.dashboard'))
            response.set_cookie('access_token_cookie', access_token, httponly=True, secure=True, samesite='Lax')
            flash(f'Welcome back, {user.name}!', 'success')
            return response
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
@admin_required
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        department = request.form.get('department')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('auth.register'))
        
        user = User(
            email=email,
            name=name,
            department=department,
            role=UserRole.USER
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash(f'User {name} registered successfully', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('auth/register.html')

@auth_bp.route('/logout')
def logout():
    response = redirect(url_for('auth.login'))
    response.delete_cookie('access_token_cookie')
    flash('Logged out successfully', 'info')
    return response

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
