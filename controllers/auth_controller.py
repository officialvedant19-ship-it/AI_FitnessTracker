from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session
from models.user import User
from models.database import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        # Validate
        if len(name) < 2:
            return render_template('signup.html', error="Name must be at least 2 characters")
        if len(password) < 6:
            return render_template('signup.html', error="Password must be at least 6 characters")
        
        # Check if user exists
        existing = User.query.filter_by(email=email).first()
        if existing:
            return render_template('signup.html', error="Email already registered")
        
        # Create user
        user = User(email=email, name=name)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Login
        session.clear()
        session['user_id'] = user.id
        session['user_name'] = user.name
        session['user_email'] = user.email
        
        return redirect(url_for('dashboard'))
    
    return render_template('signup.html')

@auth_bp.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            return render_template('signin.html', error="Invalid email or password")
        
        if not user.is_active:
            return render_template('signin.html', error="Account deactivated")
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Login
        session.clear()
        session['user_id'] = user.id
        session['user_name'] = user.name
        session['user_email'] = user.email
        
        return redirect(url_for('dashboard'))
    
    return render_template('signin.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.signin'))

@auth_bp.route('/api/me')
@login_required
def get_current_user(current_user):
    """Get current authenticated user info"""
    return jsonify(current_user.to_dict())

@auth_bp.route('/api/update-profile', methods=['POST'])
@login_required
def update_profile(current_user):
    """Update user profile"""
    name = request.form.get('name', '').strip()
    
    if name and validate_name(name):
        current_user.name = name
        db.session.commit()
        session['user_name'] = name
    
    return redirect(url_for('dashboard'))