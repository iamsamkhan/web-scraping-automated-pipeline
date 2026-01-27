import time
import asyncio
from functools import wraps
from typing import List, Dict, Any
from urllib.parse import urlparse

def timing_decorator(func):
    """Decorator to measure function execution time"""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        return result, execution_time
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        return result, execution_time
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper

def validate_url(url: str) -> bool:
    """Validate if URL is from an educational institution"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Check for educational domains
        edu_domains = ['.edu', '.ac.', '.school', '.university', '.college']
        return any(edu in domain for edu in edu_domains) or domain.endswith('.edu')
    except:
        return False

def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split list into chunks"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]