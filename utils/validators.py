import re
from email_validator import validate_email as validate_email_lib, EmailNotValidError

def validate_email(email):
    """Validate email format"""
    try:
        # Use email-validator library for thorough validation
        validation = validate_email_lib(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False

def validate_password(password):
    """Validate password strength"""
    if len(password) < 6:
        return False
    
    # Optional: Enforce stronger passwords
    # has_upper = any(c.isupper() for c in password)
    # has_lower = any(c.islower() for c in password)
    # has_digit = any(c.isdigit() for c in password)
    # has_special = any(c in '!@#$%^&*' for c in password)
    # return all([has_upper, has_lower, has_digit, has_special])
    
    return True

def validate_name(name):
    """Validate user name"""
    if not name or len(name) < 2 or len(name) > 50:
        return False
    # Allow letters, spaces, hyphens, apostrophes
    return bool(re.match(r'^[A-Za-z\s\-\']+$', name))

def validate_exercise(exercise_key):
    """Validate exercise key exists"""
    from services.pose_detection import EXERCISE_CONFIGS
    return exercise_key in EXERCISE_CONFIGS

def validate_positive_integer(value, min_val=1, max_val=None):
    """Validate positive integer within range"""
    try:
        value = int(value)
        if value < min_val:
            return False
        if max_val and value > max_val:
            return False
        return True
    except (ValueError, TypeError):
        return False

def validate_date(date_string):
    """Validate date format YYYY-MM-DD"""
    try:
        from datetime import datetime
        datetime.strptime(date_string, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def sanitize_input(text, max_length=500):
    """Sanitize user input to prevent XSS"""
    if not text:
        return ""
    
    # Remove HTML tags
    import html
    text = html.escape(text)
    
    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length]
    
    return text

def validate_workout_data(data):
    """Validate workout session data"""
    errors = []
    
    required_fields = ['exercise', 'reps', 'calories', 'duration']
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing field: {field}")
    
    if 'exercise' in data and not validate_exercise(data['exercise']):
        errors.append(f"Invalid exercise: {data['exercise']}")
    
    if 'reps' in data and not validate_positive_integer(data['reps'], 0):
        errors.append(f"Invalid reps value: {data['reps']}")
    
    if 'calories' in data:
        try:
            calories = float(data['calories'])
            if calories < 0 or calories > 1000:
                errors.append(f"Invalid calories: {calories}")
        except (ValueError, TypeError):
            errors.append(f"Invalid calories format: {data['calories']}")
    
    return {'valid': len(errors) == 0, 'errors': errors}

def validate_plan_data(data):
    """Validate workout plan data"""
    errors = []
    
    if 'date' not in data or not validate_date(data['date']):
        errors.append("Invalid or missing date")
    
    if 'focus' not in data or data['focus'] not in ['Full Body', 'Upper Body', 'Lower Body', 'Cardio', 'Rest']:
        errors.append("Invalid workout focus")
    
    return {'valid': len(errors) == 0, 'errors': errors}