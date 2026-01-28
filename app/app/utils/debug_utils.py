"""
Debug utilities for the Academic Research Automation System
"""

import time
import inspect
import json
import traceback
from typing import Any, Dict, List, Optional, Callable
from functools import wraps
from datetime import datetime
import psutil
import gc
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

@dataclass
class PerformanceMetrics:
    """Performance metrics for debugging"""
    execution_time: float
    memory_usage_mb: float
    cpu_percent: float
    function_name: str
    timestamp: datetime

class DebugProfiler:
    """Performance profiler for debugging"""
    
    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self.process = psutil.Process()
    
    @contextmanager
    def profile(self, function_name: str):
        """Context manager for profiling code blocks"""
        start_time = time.time()
        start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        start_cpu = self.process.cpu_percent()
        
        try:
            yield
        finally:
            end_time = time.time()
            end_memory = self.process.memory_info().rss / 1024 / 1024
            end_cpu = self.process.cpu_percent()
            
            metrics = PerformanceMetrics(
                execution_time=end_time - start_time,
                memory_usage_mb=end_memory - start_memory,
                cpu_percent=end_cpu - start_cpu,
                function_name=function_name,
                timestamp=datetime.now()
            )
            
            self.metrics.append(metrics)
            
            # Log if performance is poor
            if metrics.execution_time > 5.0:  # > 5 seconds
                print(f"⚠️ Performance warning: {function_name} took {metrics.execution_time:.2f}s")
            
            if metrics.memory_usage_mb > 100:  # > 100MB
                print(f"⚠️ Memory warning: {function_name} used {metrics.memory_usage_mb:.2f}MB")

def debug_decorator(enable_trace: bool = False):
    """Decorator for debugging function calls"""
    
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get function info
            func_name = func.__name__
            module = func.__module__
            
            print(f"🔍 DEBUG: Entering {module}.{func_name}")
            print(f"   Args: {args}")
            print(f"   Kwargs: {kwargs}")
            
            if enable_trace:
                print(f"   Caller: {traceback.extract_stack()[-2]}")
            
            # Time execution
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                print(f"✅ DEBUG: Exiting {module}.{func_name}")
                print(f"   Execution time: {execution_time:.4f}s")
                print(f"   Result type: {type(result)}")
                
                # Show result preview
                if isinstance(result, (list, tuple)) and len(result) > 0:
                    print(f"   Result preview (first {min(3, len(result))} items):")
                    for i, item in enumerate(result[:3]):
                        print(f"     [{i}] {str(item)[:100]}...")
                elif isinstance(result, dict):
                    print(f"   Result keys: {list(result.keys())[:5]}...")
                elif result is not None:
                    print(f"   Result preview: {str(result)[:200]}...")
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                print(f"❌ DEBUG: Error in {module}.{func_name}")
                print(f"   Execution time: {execution_time:.4f}s")
                print(f"   Error: {type(e).__name__}: {str(e)}")
                print(f"   Traceback:")
                for line in traceback.format_exc().split('\n'):
                    print(f"     {line}")
                
                raise
        
        return wrapper
    
    return decorator

class MemoryDebugger:
    """Memory usage debugger"""
    
    @staticmethod
    def get_memory_usage():
        """Get current memory usage"""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,
            'vms_mb': memory_info.vms / 1024 / 1024,
            'percent': process.memory_percent(),
            'available_mb': psutil.virtual_memory().available / 1024 / 1024,
            'total_mb': psutil.virtual_memory().total / 1024 / 1024,
        }
    
    @staticmethod
    def track_object_memory(obj: Any, label: str = "object"):
        """Track memory usage of an object"""
        import sys
        
        size_bytes = sys.getsizeof(obj)
        
        # For collections, get size recursively
        if isinstance(obj, dict):
            size_bytes += sum(sys.getsizeof(k) + sys.getsizeof(v) for k, v in obj.items())
        elif isinstance(obj, (list, tuple, set)):
            size_bytes += sum(sys.getsizeof(item) for item in obj)
        
        print(f"📦 Memory: {label} uses {size_bytes / 1024:.2f} KB")
        return size_bytes
    
    @staticmethod
    def find_memory_leaks():
        """Find potential memory leaks"""
        objects = gc.get_objects()
        print(f"Total objects in memory: {len(objects)}")
        
        # Count objects by type
        type_counts = {}
        for obj in objects:
            obj_type = type(obj).__name__
            type_counts[obj_type] = type_counts.get(obj_type, 0) + 1
        
        # Show top 10 types
        print("\nTop 10 object types:")
        for obj_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {obj_type}: {count}")

class RequestDebugger:
    """HTTP request debugging utilities"""
    
    @staticmethod
    def debug_request(response, show_headers: bool = False, show_body: bool = False):
        """Debug HTTP request/response"""
        print(f"\n🌐 HTTP Request Debug:")
        print(f"  URL: {response.request.url}")
        print(f"  Method: {response.request.method}")
        print(f"  Status: {response.status_code}")
        
        if show_headers:
            print(f"\n  Request Headers:")
            for key, value in response.request.headers.items():
                print(f"    {key}: {value}")
            
            print(f"\n  Response Headers:")
            for key, value in response.headers.items():
                print(f"    {key}: {value}")
        
        if show_body and response.text:
            print(f"\n  Response Body (first 500 chars):")
            print(f"    {response.text[:500]}...")
        
        print(f"  Time: {response.elapsed.total_seconds():.3f}s")

class DatabaseDebugger:
    """Database query debugging"""
    
    @staticmethod
    def debug_query(query, params=None, execution_time=None):
        """Debug database query"""
        print(f"\n🗃️ Database Query Debug:")
        print(f"  Query: {query}")
        if params:
            print(f"  Params: {params}")
        if execution_time:
            print(f"  Execution time: {execution_time:.3f}s")

# Interactive debug helpers
def interactive_debug(local_vars: Dict[str, Any]):
    """Start interactive debug session"""
    import code
    
    print("\n🐛 Interactive Debug Session")
    print("Available variables:")
    for var_name, var_value in local_vars.items():
        print(f"  {var_name}: {type(var_value).__name__}")
    
    # Start interactive console
    code.interact(local=local_vars)

def debug_inspect(obj: Any, depth: int = 2):
    """Inspect object structure"""
    print(f"\n🔬 Object Inspection: {type(obj).__name__}")
    
    if hasattr(obj, '__dict__'):
        print(f"  Attributes:")
        for key, value in obj.__dict__.items():
            print(f"    {key}: {type(value).__name__} = {repr(value)[:100]}")
    
    if isinstance(obj, dict):
        print(f"  Dictionary items (first 5):")
        for i, (key, value) in enumerate(list(obj.items())[:5]):
            print(f"    {key}: {type(value).__name__} = {repr(value)[:100]}")
    
    if isinstance(obj, (list, tuple)):
        print(f"  Sequence items (first 5):")
        for i, item in enumerate(obj[:5]):
            print(f"    [{i}]: {type(item).__name__} = {repr(item)[:100]}")

# Exception debugging
def debug_exception(exception: Exception, show_full_trace: bool = True):
    """Debug exception with details"""
    print(f"\n💥 Exception Debug:")
    print(f"  Type: {type(exception).__name__}")
    print(f"  Message: {str(exception)}")
    
    if show_full_trace:
        print(f"\n  Traceback:")
        for line in traceback.format_exc().split('\n'):
            print(f"    {line}")
    
    # Inspect exception attributes
    if hasattr(exception, '__dict__'):
        print(f"\n  Exception attributes:")
        for key, value in exception.__dict__.items():
            print(f"    {key}: {repr(value)[:200]}")

# Performance benchmarking
@contextmanager
def benchmark(operation_name: str):
    """Benchmark execution time"""
    start_time = time.time()
    start_memory = psutil.Process().memory_info().rss / 1024 / 1024
    
    try:
        yield
    finally:
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        print(f"\n⏱️ Benchmark: {operation_name}")
        print(f"  Time: {end_time - start_time:.3f}s")
        print(f"  Memory: {end_memory - start_memory:.2f}MB")