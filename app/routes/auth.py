from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.models import User, UserRole
from app import db
from functools import wraps

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
