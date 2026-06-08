import jwt
import bcrypt
from datetime import datetime, timedelta
from flask import current_app, session
from functools import wraps
from models.user import User
from models.database import db

class AuthService:
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt(rounds=current_app.config['BCRYPT_LOG_ROUNDS'])
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    @staticmethod
    def generate_jwt(user_id: int) -> str:
        """Generate JWT token for API authentication"""
        expiration = datetime.utcnow() + timedelta(hours=current_app.config['JWT_EXPIRATION_HOURS'])
        payload = {
            'user_id': user_id,
            'exp': expiration,
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
    
    @staticmethod
    def verify_jwt(token: str) -> dict:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            return {'valid': True, 'user_id': payload['user_id']}
        except jwt.ExpiredSignatureError:
            return {'valid': False, 'error': 'Token expired'}
        except jwt.InvalidTokenError:
            return {'valid': False, 'error': 'Invalid token'}
    
    @staticmethod
    def register_user(email: str, name: str, password: str) -> dict:
        """Register new user"""
        # Validate input
        if not email or not name or not password:
            return {'success': False, 'error': 'All fields are required'}
        
        # Check if user exists
        existing = User.query.filter_by(email=email).first()
        if existing:
            return {'success': False, 'error': 'Email already registered'}
        
        # Create new user
        user = User(email=email.lower(), name=name)
        user.set_password(password)  # Using werkzeug's method
        
        db.session.add(user)
        db.session.commit()
        
        return {
            'success': True,
            'user': user.to_dict(),
            'token': AuthService.generate_jwt(user.id)
        }
    
    @staticmethod
    def login_user(email: str, password: str) -> dict:
        """Authenticate user"""
        user = User.query.filter_by(email=email.lower()).first()
        
        if not user or not user.check_password(password):
            return {'success': False, 'error': 'Invalid email or password'}
        
        if not user.is_active:
            return {'success': False, 'error': 'Account is deactivated'}
        
        # Update last login
        user.update_last_login()
        
        return {
            'success': True,
            'user': user.to_dict(),
            'token': AuthService.generate_jwt(user.id)
        }