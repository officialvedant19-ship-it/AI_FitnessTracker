import logging
import os
from logging.handlers import RotatingFileHandler, SMTPHandler
from datetime import datetime

def setup_logger(app):
    """Configure application logging"""
    
    # Remove default handlers
    for handler in app.logger.handlers[:]:
        app.logger.removeHandler(handler)
    
    # Set log level
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO'))
    app.logger.setLevel(log_level)
    
    # Console handler (for development)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_format)
    app.logger.addHandler(console_handler)
    
    # File handler with rotation (for production)
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    file_handler = RotatingFileHandler(
        'logs/fitness_app.log',
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setLevel(logging.WARNING)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_format)
    app.logger.addHandler(file_handler)
    
    # Error handler for HTTP requests
    @app.after_request
    def log_response(response):
        if response.status_code >= 400:
            app.logger.error(
                f"Error {response.status_code}: {request.method} {request.path} - "
                f"User: {session.get('user_id', 'anonymous')} - "
                f"IP: {request.remote_addr}"
            )
        return response
    
    return app.logger

class RequestLogger:
    """Context manager for logging request details"""
    
    def __init__(self, app, request):
        self.app = app
        self.request = request
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.utcnow()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.utcnow() - self.start_time).total_seconds()
        
        log_data = {
            'method': self.request.method,
            'path': self.request.path,
            'ip': self.request.remote_addr,
            'duration_ms': round(duration * 1000, 2),
            'user_id': session.get('user_id', 'anonymous')
        }
        
        if exc_type:
            log_data['error'] = str(exc_val)
            self.app.logger.error(f"Request failed: {log_data}")
        else:
            self.app.logger.info(f"Request completed: {log_data}")

# Custom log formatter for JSON output (for production)
class JSONFormatter(logging.Formatter):
    """Format log records as JSON"""
    
    def format(self, record):
        import json
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'name': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        if hasattr(record, 'exc_info') and record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)