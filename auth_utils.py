"""
Password hashing and security utilities
This makes your project SECURE - a MUST for any resume!
"""

import hashlib
import secrets
import re
from datetime import datetime, timedelta

def hash_password(password):
    """
    Hash password using PBKDF2 (industry standard)
    This is what Google, Facebook, and banks use!
    """
    # Generate random salt (32 bytes = 256 bits)
    salt = secrets.token_hex(32)
    
    # Hash using PBKDF2 with 100,000 iterations (slow = secure)
    hash_obj = hashlib.pbkdf2_hmac(
        'sha256',           # Hash algorithm
        password.encode(),  # Password to hash
        salt.encode(),      # Salt 
        100000              # Iterations (slow down attackers)
    )
    
    # Return salt + hash (both needed for verification)
    return f"pbkdf2:sha256:100000${salt}${hash_obj.hex()}"

def verify_password(password, stored_hash):
    """
    Verify a password against its stored hash
    """
    try:
        # Parse the stored hash
        algorithm, iterations, salt, hash_value = parse_stored_hash(stored_hash)
        
        # Hash the input password with the same parameters
        new_hash = hashlib.pbkdf2_hmac(
            algorithm.replace('sha256', 'sha256'),
            password.encode(),
            salt.encode(),
            int(iterations)
        )
        
        # Compare securely (constant time to prevent timing attacks)
        return secrets.compare_digest(new_hash.hex(), hash_value)
    except Exception:
        return False

def parse_stored_hash(stored_hash):
    """
    Parse stored hash format: algorithm:iterations$salt$hash
    """
    parts = stored_hash.split('$')
    algo_part = parts[0]
    algorithm = algo_part.split(':')[0]
    iterations = algo_part.split(':')[1] if ':' in algo_part else '100000'
    salt = parts[1]
    hash_value = parts[2]
    return algorithm, iterations, salt, hash_value

def validate_strong_password(password):
    """
    Enforce strong password policy
    Returns (is_valid, message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is strong"

def generate_reset_token():
    """Generate secure password reset token"""
    return secrets.token_urlsafe(32)

def sanitize_input(text, max_length=500):
    """Sanitize user input to prevent XSS attacks"""
    if not text:
        return ""
    
    # HTML escape
    import html
    text = html.escape(text)
    
    # Truncate
    if len(text) > max_length:
        text = text[:max_length]
    
    return text