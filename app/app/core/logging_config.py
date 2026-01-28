import logging
import sys
from pathlib import Path
from typing import Optional
import json
from datetime import datetime
import inspect

# Log directory
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        log_record = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
            'process_id': record.process,
            'thread_id': record.thread,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'extra'):
            log_record.update(record.extra)
        
        return json.dumps(log_record)

class DebugFilter(logging.Filter):
    """Filter to add debug context"""
    
    def filter(self, record):
        # Add caller information for debug logs
        if record.levelno == logging.DEBUG:
            stack = inspect.stack()
            if len(stack) > 8:
                caller = stack[8]
                record.caller_file = caller.filename
                record.caller_line = caller.lineno
                record.caller_function = caller.function
        
        # Add request ID for web requests
        if hasattr(record, 'request_id'):
            record.request_id = getattr(record, 'request_id', 'N/A')
        
        return True

def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    json_format: bool = False
) -> logging.Logger:
    """
    Setup comprehensive logging configuration
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file to write logs to
        json_format: Use JSON format for logs
    """
    
    # Create logger
    logger = logging.getLogger("research_automation")
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if json_format:
        console_formatter = JSONFormatter()
    else:
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - '
            '[%(module)s.%(funcName)s:%(lineno)d] - %(message)s'
        )
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(DebugFilter())
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_path = LOG_DIR / log_file
        file_handler = logging.FileHandler(file_path, encoding='utf-8')
        if json_format:
            file_formatter = JSONFormatter()
        else:
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - '
                '%(module)s.%(funcName)s:%(lineno)d - %(message)s'
            )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # Special handlers for different log types
    error_handler = logging.FileHandler(LOG_DIR / 'errors.log')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(console_formatter)
    logger.addHandler(error_handler)
    
    # Scraping specific logger
    scraping_logger = logging.getLogger("research_automation.scraper")
    scraping_file_handler = logging.FileHandler(LOG_DIR / 'scraping.log')
    scraping_file_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(levelname)s - URL: %(url)s - %(message)s')
    )
    scraping_logger.addHandler(scraping_file_handler)
    
    # Email specific logger
    email_logger = logging.getLogger("research_automation.email")
    email_file_handler = logging.FileHandler(LOG_DIR / 'email.log')
    email_file_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(levelname)s - To: %(recipient)s - %(message)s')
    )
    email_logger.addHandler(email_file_handler)
    
    return logger

# Context manager for detailed logging
class LogContext:
    """Context manager for detailed operation logging"""
    
    def __init__(self, operation: str, logger: logging.Logger, **kwargs):
        self.operation = operation
        self.logger = logger
        self.kwargs = kwargs
        self.start_time = None
        
    def __enter__(self):
        self.start_time = datetime.utcnow()
        self.logger.info(f"Starting {self.operation}", extra=self.kwargs)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.utcnow() - self.start_time).total_seconds()
        if exc_type:
            self.logger.error(
                f"Failed {self.operation} after {duration:.2f}s",
                extra={**self.kwargs, 'error': str(exc_val), 'duration': duration}
            )
        else:
            self.logger.info(
                f"Completed {self.operation} in {duration:.2f}s",
                extra={**self.kwargs, 'duration': duration}
            )

# Decorator for function logging
def log_execution(logger_name: str = "research_automation"):
    """Decorator to log function execution details"""
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(logger_name)
            
            # Get function info
            func_name = func.__name__
            module = func.__module__
            
            # Log entry
            logger.debug(
                f"Entering {module}.{func_name}",
                extra={
                    'function': func_name,
                    'module': module,
                    'args': str(args),
                    'kwargs': str(kwargs)
                }
            )
            
            start_time = datetime.utcnow()
            
            try:
                result = func(*args, **kwargs)
                duration = (datetime.utcnow() - start_time).total_seconds()
                
                # Log success
                logger.debug(
                    f"Exiting {module}.{func_name}",
                    extra={
                        'function': func_name,
                        'module': module,
                        'duration': duration,
                        'result_type': type(result).__name__
                    }
                )
                
                return result
                
            except Exception as e:
                duration = (datetime.utcnow() - start_time).total_seconds()
                
                # Log error with traceback
                logger.error(
                    f"Error in {module}.{func_name}",
                    extra={
                        'function': func_name,
                        'module': module,
                        'error': str(e),
                        'error_type': type(e).__name__,
                        'duration': duration,
                        'traceback': traceback.format_exc()
                    },
                    exc_info=True
                )
                raise
        
        return wrapper
    
    return decorator

# Setup default logger
logger = setup_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    log_file="app.log",
    json_format=os.getenv("JSON_LOGS", "false").lower() == "true"
)