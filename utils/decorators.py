from functools import wraps
from flask import session, request, jsonify, current_app
from models.user import User
from models.database import db
import time
from collections import defaultdict

# Rate limiting storage (use Redis in production)
rate_limit_storage = defaultdict(list)

def login_required(f):
    """Decorator to require authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user_id exists in session
        user_id = session.get('user_id')
        
        if not user_id:
            # For API routes, return JSON error
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            # For web routes, redirect to login
            from flask import redirect, url_for
            return redirect(url_for('auth.signin'))
        
        # Get user from database
        user = User.query.get(user_id)
        
        if not user or not user.is_active:
            session.clear()
            if request.path.startswith('/api/'):
                return jsonify({'error': 'User not found or inactive'}), 401
            return redirect(url_for('auth.signin'))
        
        # Pass user to the route
        return f(user, *args, **kwargs)
    
    return decorated_function

def rate_limit(limit=100, per=60):
    """
    Rate limiting decorator
    limit: number of requests allowed
    per: time window in seconds
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get client identifier
            client_id = request.headers.get('X-Forwarded-For', request.remote_addr)
            if request.headers.get('Authorization'):
                client_id = request.headers.get('Authorization')[:50]
            
            key = f"{client_id}:{f.__name__}"
            now = time.time()
            
            # Clean old entries
            rate_limit_storage[key] = [t for t in rate_limit_storage[key] if now - t < per]
            
            # Check limit
            if len(rate_limit_storage[key]) >= limit:
                return jsonify({
                    'error': f'Rate limit exceeded. Max {limit} requests per {per} seconds.'
                }), 429
            
            # Add current request
            rate_limit_storage[key].append(now)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(current_user, *args, **kwargs):
        if not current_user.is_admin:
            return jsonify({'error': 'Admin privileges required'}), 403
        return f(current_user, *args, **kwargs)
    return decorated_function

def validate_json(schema=None):
    """Decorator to validate JSON request body"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({'error': 'Content-Type must be application/json'}), 400
            
            data = request.get_json()
            
            if schema:
                # Basic schema validation
                for required_field in schema.get('required', []):
                    if required_field not in data:
                        return jsonify({'error': f'Missing required field: {required_field}'}), 400
            
            return f(data, *args, **kwargs)
        return decorated_function
    return decorator

def cache_control(max_age=300):
    """Add cache control headers to response"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            response = f(*args, **kwargs)
            if isinstance(response, tuple):
                response = response[0]
            response.headers['Cache-Control'] = f'public, max-age={max_age}'
            return response
        return decorated_function
    return decorator

def log_execution_time(f):
    """Log function execution time"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        result = f(*args, **kwargs)
        execution_time = time.time() - start_time
        
        if execution_time > 0.1:  # Log slow operations
            current_app.logger.warning(
                f"Slow operation: {f.__name__} took {execution_time:.2f} seconds"
            )
        
        return result
    return decorated_function